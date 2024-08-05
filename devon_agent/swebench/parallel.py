import copy
import json
import os
import shutil
from typing import List
from devon_agent.swebench.main import main
import concurrent

import modal

app = modal.App("swebench-parallel")


def split_instances(instances: List[str], workers: int):
    instance_groups: List[List[str]] = []
    for i in range(0, len(instances), len(instances) // workers + 1):
        print(i)
        instance_groups.append(instances[max(i-1, 0):i + workers])
    return instance_groups


def parallel_run(workers: int, args):
    print(args.instances)
    args.instances.sort()
    print(args.instances)
    instances: List[str] = args.instances
    instance_groups: List[List[str]] = []
    
    instance_groups = split_instances(instances, workers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers+1) as executor:
        futures = []
        executor.map(main, instance_groups)
        for i,group in enumerate(instance_groups):
            print(group,i)
            thread_args = copy.deepcopy(args)
            thread_args.instances = group
            thread_args.skip_existing = True
            thread_args.worker_id = i
            print(thread_args)
            future = executor.submit(main, thread_args)
            futures.append(future)

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)
        try:
            for future in concurrent.futures.as_completed(futures):
                traj_dir,experiment_id,run_name = future.result()

                
        except Exception as e:
            print(e)

        lines = []
        if traj_dir and os.path.exists(traj_dir):
            experminent_folder = os.path.dirname(traj_dir)
            for folder in os.listdir(experminent_folder):
                if os.path.isdir(os.path.join(experminent_folder, folder)):
                    pred_file = os.path.join(experminent_folder, folder, "all_preds.jsonl")
                    with open(pred_file, "r") as f:
                        lines.extend(f.readlines())

                    # copy all .traj files over 
                    for file in os.listdir(os.path.join(experminent_folder, folder)):
                        if file.endswith(".traj"):
                            shutil.copy(os.path.join(experminent_folder, folder, file), os.path.join(experminent_folder, file))
            

            with open(os.path.join(experminent_folder, "all_preds.jsonl"), "w") as f:
                for line in lines:
                    json_line = json.loads(line)
                    json_line["model_name_or_path"] = experiment_id
                    f.write(json.dumps(json_line) + "\n")



            

# @app.local_entrypoint()
# def main():
#     args = {
#         "experiment_id": "experiment_id",
#         "split": "train",
#         "environment": "environment",
#         "model": "model",
#         "temperature": 0.5,
#         "instances": ["django__django-14752"],
#         "workers": 2
#     }
#     parallel_run.remote(1, args)



if __name__ == "__main__":

    # cli args : 
    # --experiment_id
    # --split
    # --environment
    # --model
    # --agent_name
    # --temperature
    # --instances

    import argparse

    parser = argparse.ArgumentParser(description="Run SweBench experiment")
    parser.add_argument("--experiment_id", type=str, help="Experiment ID")
    parser.add_argument("--split", type=str, choices=["train", "dev", "test"], help="Data split")
    parser.add_argument("--environment", type=str, help="Environment configuration")
    parser.add_argument("--model", type=str, help="Model to use")
    parser.add_argument("--temperature", type=float, help="Temperature for model sampling")
    parser.add_argument("--instances", nargs="+", help="List of instances to run")

    parser.add_argument("--workers", type=int, help="Number of workers to use")
    args = parser.parse_args()
    print(args)
    parallel_run(args.workers, args)


    
    

    