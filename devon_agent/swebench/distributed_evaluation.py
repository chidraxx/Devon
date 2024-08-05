import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import subprocess
from pathlib import Path


def split_instances(instances, ip_addresses):
    """
    Split instances across the given IP addresses.
    """
    num_ips = len(ip_addresses)
    split_instances = [[] for _ in range(num_ips)]
    for i, instance in enumerate(instances):
        split_instances[i % num_ips].append(instance)
    return dict(zip(ip_addresses, split_instances))


def upload_prediction_file(local_file: Path, ip_address: str, run_id : str, remote_path: str = "/home/ec2-user/workspace/experiments", key_name: str = "~/.ssh/hetzner"):
    # make remote dir
    cmd = f"ssh -i {key_name} -o StrictHostKeyChecking=no ec2-user@{ip_address} 'sudo mkdir -p {remote_path}/{run_id} && sudo chmod 777 {remote_path}/{run_id}'"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to create remote directory: {e}")
        raise e
    cmd = f"scp -i {key_name} -o StrictHostKeyChecking=no {local_file} ec2-user@{ip_address}:{remote_path}/{run_id}/all_preds.jsonl"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to upload prediction file: {e}")
        raise e
    return f"{remote_path}/{run_id}/all_preds.jsonl"

def run_remote_evaluation(key_name: str, run_id :str, ip_address: str, instances: list, remote_prediction_file: str, num_workers: int):
    instances_str = ' '.join(instances)
    # python3 -m swebench.harness.run_evaluation     --predictions_path gold     --max_workers 6  --run_id validate-g --cache instance
    print(f"ssh -i {key_name} ec2-user@{ip_address} 'cd /home/ec2-user/workspace && sudo chmod 666 /var/run/docker.sock && sudo chmod 777 -R /home/ec2-user/workspace && python3 -m swebench.harness.run_evaluation --predictions_path {remote_prediction_file} --instance_ids {instances_str} --max_workers {num_workers} --cache instance --run_id {run_id}'")
    cmd = f"ssh -i {key_name} ec2-user@{ip_address} 'cd /home/ec2-user/workspace && sudo chmod 666 /var/run/docker.sock && sudo chmod 777 -R /home/ec2-user/workspace && python3 -m swebench.harness.run_evaluation --predictions_path {remote_prediction_file} --instance_ids {instances_str} --max_workers {num_workers} --cache instance --run_id {run_id}'"
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if process.stdout:
            for line in process.stdout:
                print(line, end='',flush=True)
        if process.stderr:
            for line in process.stderr:
                print(line, end='',flush=True)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run evaluation: {e}")
        raise e

def distribute_evaluation(ip_addresses: list, prediction_file: Path,  run_id: str, num_workers: int, key_name: str = "~/.ssh/hetzner"):
    # predictions = load_swebench_dataset(prediction_file)
    prediction_instances = []
    with open(prediction_file, 'r') as f:
        for line in f:
            prediction_instances.append(json.loads(line)["instance_id"])

    distributed_instances = split_instances(prediction_instances, ip_addresses)
    
    with ThreadPoolExecutor() as executor:
        futures = []
        for ip, instances in distributed_instances.items():
            print(f"Processing server: {ip}")
            pred_file = upload_prediction_file(prediction_file, ip, run_id=run_id)
            future = executor.submit(run_remote_evaluation, key_name, run_id, ip, instances, pred_file, num_workers)
            futures.append(future)
        
        # Wait for all tasks to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred: {e}")

def get_evaluation_results(ip_address, run_id, local_path, pred_file, key_name: str = "~/.ssh/hetzner"):

    # run_remote_evaluation(key_name, run_id, ip_address, [], pred_file, 1)

    remote_logs_path = f"/home/ec2-user/workspace/logs/run_evaluation/{run_id}/{run_id}"

    remote_results_path = f"/home/ec2-user/workspace/{run_id}.{run_id}.json"

    experiment_path = Path(local_path) / "evaluation"
    print(experiment_path.as_posix())
    # copy logs directory
    cmd = f"scp -i {key_name} -r -o StrictHostKeyChecking=no ec2-user@{ip_address}:{remote_logs_path} {experiment_path.as_posix()}"
    try:
        subprocess.run(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to copy logs directory: {e}")
        raise e

    # copy results from remote server
    cmd = f"scp -i {key_name} -o StrictHostKeyChecking=no ec2-user@{ip_address}:{remote_results_path} {experiment_path.as_posix()}"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to copy evaluation results: {e}")
        raise e

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Distribute SWE-bench evaluation across multiple servers")
    parser.add_argument('--ip_addresses', nargs='+', required=True, help='List of IP addresses')
    parser.add_argument('--prediction_file', type=str, required=True, help='Path to local prediction file')
    parser.add_argument('--key_name', type=str, required=False, default="~/.ssh/hetzner", help='Path to the evaluation command on remote servers')
    # parser.add_argument('--remote_prediction_path', type=str, required=True, help='Path to store prediction file on remote servers')
    parser.add_argument('--run_id', type=str, required=True, help='Path to the evaluation command on remote servers')
    parser.add_argument('--num_workers', type=int, default=5, help='Number of workers for the evaluation')
    args = parser.parse_args()

    distribute_evaluation(args.ip_addresses, args.prediction_file, args.run_id, args.num_workers)
