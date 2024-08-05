


# Experiment harness
# input: experiment_id, split, dataset, environment, model, temperature, inference_number, eval_instances_number, experiment_asset_path
# if rerun append to experiment_id
# run inference
# spin up eval_instances_number instances
# run evaluation
# download logs and report
# spin down instances
# output: report json, inference logs, inference trajectories, evaluation trajectories

import argparse
from pathlib import Path
import shutil
import time
import signal
import sys

from devon_agent.swebench.distributed_evaluation import distribute_evaluation, get_evaluation_results
from devon_agent.swebench.parallel import parallel_run
from devon_agent.swebench.servers import spin_down, spin_up




# 100 %
SUPER_EASY_ISSUES = ["pytest-dev__pytest-5227", "sympy__sympy-20212", "sympy__sympy-24152", "matplotlib__matplotlib-23964", "django__django-14855", "django__django-14752", "django__django-11039", "django__django-11099", "sympy__sympy-13480", "pytest-dev__pytest-11143", "django__django-11133", "django__django-14382", "django__django-13658", "sympy__sympy-14774", "django__django-16046", "django__django-16527", "django__django-16255", "scikit-learn__scikit-learn-14894", "mwaskom__seaborn-3010"]

# 80 - 90%
EASY_ISSUES = ["django__django-14915", "django__django-11049", "django__django-16379", "django__django-16873", "django__django-11583", "django__django-16595", "scikit-learn__scikit-learn-13779", "django__django-13933", "pydata__xarray-5131", "scikit-learn__scikit-learn-13480","django__django-12286","django__django-16139","django__django-12453","pytest-dev__pytest-7373","django__django-13590","pytest-dev__pytest-5692","django__django-12700","sympy__sympy-13647","django__django-10914"]

# 60 - 80%
MEDIUM_ISSUES = ["psf__requests-2317", "sympy__sympy-21847", "sympy__sympy-17655", "django__django-11179", "sympy__sympy-22714", "django__django-12983", "django__django-16041", "sympy__sympy-24213", "django__django-15347", "psf__requests-2674", "matplotlib__matplotlib-23913","psf__requests-863","django__django-13710","django__django-15851","django__django-14238","sphinx-doc__sphinx-8713","django__django-13447","scikit-learn__scikit-learn-11281","sympy__sympy-12481","django__django-13230","scikit-learn__scikit-learn-15535","sphinx-doc__sphinx-8721"]

# 40 - 60%
# 40 - 60%
MEDIUM_HARD_ISSUES = ["django__django-12497", "scikit-learn__scikit-learn-13584", "sympy__sympy-13971", "sphinx-doc__sphinx-8595", "django__django-11848", "scikit-learn__scikit-learn-25570", "sympy__sympy-17022", "sympy__sympy-17139", "django__django-12915", "django__django-13028","sympy__sympy-18057","matplotlib__matplotlib-26020","sympy__sympy-18532","scikit-learn__scikit-learn-13496","pytest-dev__pytest-7432","django__django-14999","scikit-learn__scikit-learn-10297","django__django-12708","sympy__sympy-23117","astropy__astropy-14995","django__django-14787","scikit-learn__scikit-learn-13241","sympy__sympy-21055","django__django-14608","django__django-13401","django__django-14016","matplotlib__matplotlib-23562","django__django-13158",
"sympy__sympy-15678",
"django__django-11999",
"django__django-11815",
"sympy__sympy-18621",
"sympy__sympy-20154",
"scikit-learn__scikit-learn-12471",
"sympy__sympy-24066",
"django__django-15814",
"django__django-15789",
"sympy__sympy-13471",
"django__django-15790",
"django__django-15498",
"pylint-dev__pylint-7993",
"matplotlib__matplotlib-24149",
"sympy__sympy-15609"]

# 20 - 40%
HARD_ISSUES = [
    "psf__requests-1963",
    "django__django-13964",
    "django__django-11964",
    "django__django-14017",
    "astropy__astropy-6938",
    "django__django-14672",
    "django__django-12125",
    "django__django-11422",
    "django__django-17087",
    "django__django-12284",
    "django__django-17051",
    "django__django-13315",
    "django__django-11001",
    "sympy__sympy-14396",
    "pytest-dev__pytest-11148",
    "sympy__sympy-13031",
    "sympy__sympy-15011",
    "matplotlib__matplotlib-24970",
    "matplotlib__matplotlib-23314",
    "scikit-learn__scikit-learn-13497",
    "scikit-learn__scikit-learn-13142",
    "sympy__sympy-23262",
    "sympy__sympy-21614",
    "matplotlib__matplotlib-26011",
    "pylint-dev__pylint-6506",
    "sympy__sympy-18189",
    "mwaskom__seaborn-3190",
    "scikit-learn__scikit-learn-15512",
    "sympy__sympy-16988",
    "psf__requests-3362"
]

# 1 - 20%
HARD_HARD_ISSUES = [
"django__django-13551",
"astropy__astropy-14182",
"sympy__sympy-21379",
"astropy__astropy-14365",
"sphinx-doc__sphinx-8627",
"django__django-10924",
"sphinx-doc__sphinx-8506",
"matplotlib__matplotlib-24334",
"sympy__sympy-22840",
"sympy__sympy-22005",
"matplotlib__matplotlib-25442",
"django__django-12747",
"django__django-15902",
"sympy__sympy-20442",
"sphinx-doc__sphinx-10325",
"pytest-dev__pytest-7490",
"django__django-13925",
"django__django-12308",
"pylint-dev__pylint-7114",
"sympy__sympy-24909",
"scikit-learn__scikit-learn-14092",
"scikit-learn__scikit-learn-25500",
"django__django-13768",
"django__django-14411",
"django__django-12113",
"django__django-11620",
"pytest-dev__pytest-5495",
"django__django-12856",
"django__django-14580"]

# 0 - 1%
ALMOST_IMPOSSIBLE_ISSUES = [
"django__django-16820",
"django__django-16910",
"matplotlib__matplotlib-25079",
"matplotlib__matplotlib-25311",
"django__django-16820",
"django__django-16910",
"matplotlib__matplotlib-25079",
"matplotlib__matplotlib-25311",
"matplotlib__matplotlib-25332",
"matplotlib__matplotlib-25433",
"matplotlib__matplotlib-25498",
"sphinx-doc__sphinx-11445",
"django__django-16816",
"mwaskom__seaborn-2848",
"django__django-15388",
"pytest-dev__pytest-5103",
"django__django-13321",
"matplotlib__matplotlib-23987",
"matplotlib__matplotlib-24265",
"mwaskom__seaborn-3407",
"matplotlib__matplotlib-18869",
"matplotlib__matplotlib-23563",
"matplotlib__matplotlib-22711",
"matplotlib__matplotlib-23476",
"django__django-16408",
"django__django-16400",
"scikit-learn__scikit-learn-14983",
"pallets__flask-4045",
"django__django-15400",
"pylint-dev__pylint-7228",
"pylint-dev__pylint-7080",
"django__django-15695",
"django__django-15738",
"django__django-15781",
"pydata__xarray-4493",
"scikit-learn__scikit-learn-14087",
"pytest-dev__pytest-5221",
"django__django-13757",
"django__django-15061",
"pytest-dev__pytest-5413",
"django__django-15213",
"pytest-dev__pytest-6116",
"pytest-dev__pytest-7168",
"pytest-dev__pytest-7220",
"django__django-15202",
"pytest-dev__pytest-8365",
"django__django-13660",
"pytest-dev__pytest-8906",
"pytest-dev__pytest-9359",
"django__django-14997",
"scikit-learn__scikit-learn-10508",
"scikit-learn__scikit-learn-10949",
"scikit-learn__scikit-learn-11040",
"django__django-15252",
"django__django-14730",
"django__django-14667",
"django__django-14534",
"django__django-14155",
"django__django-13448",
"sphinx-doc__sphinx-8474",
"sphinx-doc__sphinx-8435",
"sphinx-doc__sphinx-8282",
"sphinx-doc__sphinx-8273",
"sphinx-doc__sphinx-7975",
"matplotlib__matplotlib-22835",
"pydata__xarray-4248",
"sphinx-doc__sphinx-7686",
"sphinx-doc__sphinx-10451",
"scikit-learn__scikit-learn-25747",
"scikit-learn__scikit-learn-25638",
"django__django-15320",
"pallets__flask-4992",
"pydata__xarray-3364",
"sympy__sympy-19487",
"sympy__sympy-12419",
"sympy__sympy-13895",
"sympy__sympy-12236",
"sympy__sympy-16792",
"sympy__sympy-14817",
"sympy__sympy-19007",
"sympy__sympy-20049",
"django__django-15819",
"django__django-11630",
"sympy__sympy-20322",
"sympy__sympy-20590",
"sympy__sympy-20639",
"django__django-11564",
"sympy__sympy-21171",
"sympy__sympy-13177",
"sympy__sympy-13773",
"sympy__sympy-12171",
"sympy__sympy-13043",
"sympy__sympy-13915",
"django__django-12908",
"django__django-13265",
"sympy__sympy-12454",
"django__django-13220",
"sympy__sympy-14024",
"sympy__sympy-13437",
"sympy__sympy-13146",
"sympy__sympy-11897",
"django__django-12589",
"sympy__sympy-14308",
"sympy__sympy-14317",
"django__django-13033",
"sympy__sympy-21612",
"sympy__sympy-21627",
"django__django-11283",
"sympy__sympy-17630",
"django__django-15996",
"django__django-16229",
"psf__requests-2148",
"pallets__flask-5063",
"pydata__xarray-4094",
"sphinx-doc__sphinx-8801",
"matplotlib__matplotlib-23299",
"sympy__sympy-11870",
"django__django-11742",
"django__django-11797",
"sympy__sympy-18199",
"django__django-11905",
"sympy__sympy-18087",
"django__django-11910",
"django__django-12184",
"django__django-11019",
"sympy__sympy-11400",
"sympy__sympy-16503",
"sympy__sympy-16281",
"sympy__sympy-16106",
"sympy__sympy-15346",
"sympy__sympy-15345",
"sympy__sympy-15308",
"sympy__sympy-18698",
"django__django-12470",
"sympy__sympy-18835",
"sympy__sympy-19254",
"sympy__sympy-24102",
"astropy__astropy-7746",
"sympy__sympy-23191",
"sphinx-doc__sphinx-7738",
]



servers = []

def sigint_handler(signum, frame):
    print("\nReceived SIGINT. Spinning down instances and exiting...")
    try:
        spin_down(servers)
        sys.exit(0)
    except Exception as e:
        print(f"Error while spinning down instances: {e}")
    sys.exit(1)

# Register the SIGINT handler
signal.signal(signal.SIGINT, sigint_handler)


def run_experiment(experiment_id, rerun, split, dataset, instances, environment, model, temperature, inference_parallel_number, eval_instances_number, experiment_asset_path):
    global servers

    # spin up eval instances
    try:
        servers,ips = spin_up(eval_instances_number)
    except Exception as e:
        print(e)
        raise e

    # check if experiment_id exists
    experiment_path: Path = Path(experiment_asset_path) / experiment_id
    if experiment_path.exists():
        if rerun:
            experiment_path = Path(experiment_asset_path, experiment_id + "_rerun")
        else:
            if rerun:
                experiment_id = experiment_id + "_rerun"
    experiment_path = Path(experiment_asset_path) / experiment_id
    experiment_path.mkdir(parents=True, exist_ok=True)


    try:
        print(inference_parallel_number)
        parallel_run(workers=inference_parallel_number, args=argparse.Namespace(
            experiment_id=experiment_id,
            split=split,
            dataset=dataset,
            instances=instances,
            environment=environment,
            model=model,
            temperature=temperature,
        ))
    except Exception as e:
        print(e)
        raise e

    # copy trajectories and all_preds over
    inference_exp_path = "./trajectories/" + experiment_id
    shutil.copytree(inference_exp_path, (experiment_path / "trajectories").as_posix(), dirs_exist_ok=True)

    # wait for 1 minute
    time.sleep(60 * 4)

    try:
        distribute_evaluation(ips, experiment_path / "trajectories" / "all_preds.jsonl", experiment_id, 5, "~/.ssh/hetzner")
    except Exception as e:
        print(e)
        raise e

    try:
        get_evaluation_results(ips[0], experiment_id, experiment_path, experiment_path / "trajectories" / "all_preds.jsonl" , "~/.ssh/hetzner")
    except Exception as e:
        print(e)
        spin_down(servers)
        raise e

    # spin down eval instances
    try:
        spin_down(servers)
    except Exception as e:
        print(e)
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distribute SWE-bench evaluation across multiple servers")
    parser.add_argument('--experiment_id', type=str, required=True, help='Path to the evaluation command on remote servers')
    parser.add_argument('--rerun', type=bool, required=False, default=False, help='Rerun the experiment')
    parser.add_argument('--split', type=str, default="test", help='Split of the dataset')
    parser.add_argument('--dataset', type=str, default="princeton-nlp/SWE-bench_Lite", help='Dataset')
    parser.add_argument("--instances", nargs="+", help="List of instances to run")
    parser.add_argument('--environment', type=str, required=True, help='Environment')
    parser.add_argument('--model', type=str, required=True, help='Model')
    parser.add_argument('--temperature', type=float, required=True, help='Temperature')
    parser.add_argument('--inference_parallel_number', type=int, required=True, help='Number of inference parallel workers')
    parser.add_argument('--eval_instances_number', type=int, required=True, help='Number of evaluation instances')
    parser.add_argument('--experiment_asset_path', type=str, required=True, help='Path to the experiment asset path')

    args = parser.parse_args()

    run_experiment(args.experiment_id, args.rerun, args.split, args.dataset, args.instances, args.environment, args.model, args.temperature, args.inference_parallel_number, args.eval_instances_number, args.experiment_asset_path)




