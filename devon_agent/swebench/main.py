from argparse import Namespace
import datetime
import inspect
import json
import logging
import os
import re
import traceback
from typing import Any, List, Optional, TypedDict
from pydantic import BaseModel
from pathlib import Path
from datasets import load_dataset, load_from_disk
from swebench.harness.constants import KEY_INSTANCE_ID, KEY_MODEL, KEY_PREDICTION
from unidiff import PatchSet

from devon_agent.agents.task_agent import TaskAgent

from devon_agent.environments.swebenchenv import SWEEnvEnvironment
from devon_agent.tool import ToolNotFoundException
from devon_agent.tools import parse_command
from devon_agent.tools.codeindex import FindClassTool, FindFunctionTool
from devon_agent.tools.codenav import CodeGoTo, CodeSearch
from devon_agent.tools.editorblock import EditBlockTool
from devon_agent.tools.editortools import CreateFileTool, DeleteFileTool, OpenFileTool, ScrollDownTool, ScrollToLineTool, ScrollUpTool, save_create_file, save_delete_file
from devon_agent.tools.filesearchtools import FindFileTool, GetCwdTool, SearchDirTool
from devon_agent.tools.filetools import SearchFileTool
from devon_agent.tools.lifecycle import NoOpTool
from devon_agent.tools.swebenchtools import SubmitTool
from devon_agent.tools.shelltool import ShellTool



class InstanceBuilder:
    def __init__(self, token: str | None = None):
        """This helper class is used to build the data for an instance object,
        retrieving problem statements from github issues or local files and setting
        repo paths from github urls or local paths.
        """
        # Args that will be passed to the Instance constructor
        self.args = {}
        self.token = token
        self._instance_id_problem_suffix = ""



    def set_from_dict(self, instance_dict: dict[str, Any]):
        self.args |= instance_dict

    def set_missing_fields(self):
        # TODO: This field is only needed while swe_env is using some questionable logic
        # to determine whether to clone from a mirror or not. This should be removed in the future.
        # Values: 'swe-bench' (loaded from json/jsonl for swe-bench style inference),
        # 'online' (loaded from github issue or similar) or 'local' (loaded from local file)
        if "problem_statement_source" not in self.args:
            self.args["problem_statement_source"] = "swe-bench"
        if "repo_type" not in self.args:
            self.args["repo_type"] = "github"

    def validate(self):
        required_fields = [
            "problem_statement",
            "instance_id",
            "repo",
            "repo_type",
            "base_commit",
            "version",
            "problem_statement_source",
        ]
        if not all(x in self.args for x in required_fields):
            missing = set(required_fields) - set(self.args.keys())
            msg = f"Missing required fields: {missing=}"
            raise ValueError(msg)
        if self.args["repo_type"] not in {"github", "local"}:
            msg = f"Invalid repo type: {self.args['repo_type']=}"
            raise ValueError(msg)
        if self.args["repo_type"] == "github" and self.args["repo"].count("/") != 1:
            msg = f"Invalid repo format for {self.args['repo_type']=}: {self.args['repo']=}"
            raise ValueError(msg)

    def build(self) -> dict[str, Any]:
        self.set_missing_fields()
        self.validate()
        return self.args


def get_submission(output: str) -> str | None:
    """
    Function for extracting diff patch submission at the end of an episode.

    Args:
        output: `submit` observation

    Returns:
        submission: diff patch submission
    """
    print(output)
    pattern = r"\<\<SUBMISSION\|\|(.*)\|\|SUBMISSION\>\>"
    match = re.search(pattern, output, re.DOTALL)
    if match is None:
        return None
    return match.group(1)

def get_instances(
    file_path: str,
    base_commit: str | None = None,
    split: str | None = None,
    token: str | None = None,
    *,
    repo_path: str = "",
) -> list[dict[str, Any]]:
    """
    Getter function for handling json, jsonl files

    Args:
        file_path (str): Path to file

    Returns:
        List of instances as dictionaries
    """

    def instance_from_dict(instances):
        ib = InstanceBuilder(token=token)
        ib.set_from_dict(instances)
        return ib.build()

    def postproc_instance_list(instances):
        if isinstance(instances, dict):
            msg = "Expected a list of instances, got a dictionary."
            raise ValueError(msg)
        return [instance_from_dict(x) for x in instances]


    if base_commit:
        msg = "base_commit must be empty if running over multiple problem statements"
        raise ValueError(msg)

    if repo_path:
        msg = "repo_path must be empty if running over multiple problem statements"
        raise ValueError(msg)

    # If file_path is a directory, attempt load from disk
    if os.path.isdir(file_path):
        try:
            dataset_or_dict = load_from_disk(file_path)
            if isinstance(dataset_or_dict, dict):
                return postproc_instance_list(dataset_or_dict[split])
            return postproc_instance_list(dataset_or_dict)
        except FileNotFoundError:
            # Raised by load_from_disk if the directory is not a dataset directory
            pass


    if base_commit is not None:
        msg = "base_commit must be None if data_path is not a github issue url"
        raise ValueError(msg)

    # If file_path is a file, load the file
    if file_path.endswith(".json"):
        with open(file_path) as file:
            return postproc_instance_list(json.load(file))
    if file_path.endswith(".jsonl"):
        return postproc_instance_list([json.loads(x) for x in Path(file_path).read_text().splitlines(keepends=True)])

    # Attempt load from HF datasets as a last resort
    try:
        return postproc_instance_list(load_dataset(file_path, split=split))
    except Exception as e:
        msg = (
            f"Could not load instances from {file_path}. "
            "Please ensure --data_path is a GitHub URL, a SWE-bench HuggingFace dataset, or a JSON/JSONL file."
        )
        raise ValueError(msg) from e

def save_trajectory(
    trajectory: list[dict[str, Any]], log_path: Path, env_name: str, info: dict[str, Any]
) -> None:
    """Save the trajectory"""
    log_dict = {
        "environment": env_name,
        "trajectory": trajectory,
        "info": info,
    }
    log_path.write_text(json.dumps(log_dict, indent=2))

class AgentConfig(BaseModel):
    model: str
    agent_name: str
    agent_type: str
    api_base: Optional[str] = None
    prompt_type: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.0
    chat_history: List[dict] = []

class EnvironmentArguments(BaseModel):
    """Configure data sources and setup instructions for the environment in which we solve the tasks."""

    # Source of issue statement/problem statement. To run over a batch of issues: Path to a data file
    # (`json`, `jsonl`) or directory. To run over single issue: github issue url or path to markdown file
    # with problem statement or problem statement as text prefixed with `text://`.
    # Name of the docker image to use for the environment. Defaults to sweagent/swe-agent:latest
    image_name: str = "sweagent/swe-agent:latest"
    # When running over SWE-bench issues: Specify the split to use.


    # Specify a branch name or a commit hash to checkout before running the task.
    # Only used when running over a single problem statement/issue.
    base_commit: str | None = None
    # Use a persistent container with this name. After every task, the container will be paused, but not removed.
    # This is useful for speedup when running multiple tasks from the same repositories in a row, as the repositories
    # will have already been cloned and the conda environments will have been installed.
    container_name: str | None = None

    # No effect, kept for backwards compatibility.
    timeout: int | None = None
    # Enable environment logger.
    verbose: bool = False
    # Do not use attempt to use a repository mirror from https://github.com/swe-bench.
    no_mirror: bool = False
    # Cache task images to speed up task initialization. This means that the environment will be saved as a
    # docker image for every repository, base commit, and setup combination. This uses quite a bit of disk space
    # but speeds up task initialization significantly when running over multiple issues from the same repository
    # (or using different models for the same issues).
    # Custom environment setup. Currently only used when data_path points to a single issue.
    # This needs to be either a string pointing to a yaml file (with yaml, yml file extension)
    # or a shell script (with sh extension).
    # See https://princeton-nlp.github.io/SWE-agent/usage/cl_tutorial#environment-setup
    environment_setup: str | None = None
    # Only used when running on single issue. Path to local repository or github repository.
    repo_path: str = ""



    def __post_init__(self):
        if self.cache_task_images and self.container_name:
            msg = (
                "Not allowed to use persistent container with caching task images "
                "(probably doesn't make sense and takes excessive space)."
            )
            raise ValueError(msg)
        if self.container_name is not None and self.container_name.strip() == "":
            msg = "Set container_name to None if you don't want to use a persistent container."
            raise ValueError(msg)

class SweBenchConfig(BaseModel):

    logger_name: str
    environment: EnvironmentArguments
    # Only run instances that completely match this regex
    instance_filter: str = ".*"

    instances: List[str]

    experiment_id : str = "default"
    worker_id: int = 0

    # Skip instances with existing trajectories
    skip_existing: bool = True
    # Suffix for the run name (used for example in trajectory directory naming)
    suffix: str = ""
    # Raise unhandled exceptions during the run (useful for debugging)
    raise_exceptions: bool = False
    # Dump the entire config to the log
    print_config: bool = True

    data_path: str

    split: str = "dev"

    cache_task_images: bool = False

    agent_config: AgentConfig

    # Try to install the environment before running the task.
    install_environment: bool = True

    state: dict[str, Any] = {}

    ignore_files: List[str] = []

    @property
    def run_name(self) -> str:
        """Generate a unique name for this run based on the arguments."""
        model_name = self.agent_config.model.replace(":", "-")
        # data_stem = get_data_path_name(self.data_path)
        # assert self.agent.config_file is not None  # mypy
        # config_stem = Path(self.agent.config_file).stem

        temp = self.agent_config.temperature

        install_env = self.install_environment

        return (
            f"{model_name}__t-{temp:.2f}"
            + f"__install-{int(install_env)}"
            + f"__{self.worker_id}"
            + (f"__{self.suffix}" if self.suffix else "")
            + f"__{self.experiment_id}"
        )
    
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.logger_name + "_" + self.run_name)


class TrajectoryStep(TypedDict):
    action: str
    observation: str
    response: str
    state: str | None
    thought: str


class SweBenchSession:
    def __init__(self, config: SweBenchConfig):
        self.config = config
        self.traj_dir = Path("trajectories") / config.experiment_id / config.run_name
        self.traj_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        log_path = self.traj_dir  / f"{self.config.run_name}=run-{timestamp}.log"
        self.logger = logging.getLogger(self.config.logger_name + "_" + self.config.run_name)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        if self.config.print_config:
            self.logger.info(f"📙 Arguments: {self.config}")


        self.agent = TaskAgent(
            name="devon",
            global_config=self.config,
            agent_config=self.config.agent_config,
            interrupt="",
            scratchpad="",
        )

        self.environments = {
            "swebench" : SWEEnvEnvironment(
                logger=self.logger,
                image_name=self.config.environment.image_name,
            )
        }
        self.environments["swebench"].register_tools(
            {
                "find_function": FindFunctionTool(),
                "find_class": FindClassTool(),

                "create_file": CreateFileTool().register_post_hook(save_create_file),
                "open_file": OpenFileTool(),
                "scroll_up": ScrollUpTool(),
                "scroll_down": ScrollDownTool(),
                "scroll_to_line": ScrollToLineTool(),
                "search_file": SearchFileTool(),
                "edit": EditBlockTool(),

                # "search_dir": SearchDirTool(),
                "find_file": FindFileTool(),
                "get_cwd": GetCwdTool(),
                "no_op": NoOpTool(),
                "delete_file": DeleteFileTool().register_post_hook(save_delete_file),
                # "code_search": CodeSearch(),
                # "code_goto": CodeGoTo(),
                "submit": SubmitTool(),
                # "file_tree_display": FileTreeDisplay(),
            }
        )

        # Load Task Instances
        self.data_path = self.config.data_path
        
        self.data = get_instances(
            self.data_path,
            split=self.config.split,
        )
        if self.config.instances:
            self.data = [x for x in self.data if x["instance_id"] in self.config.instances]
        #: Instance we're currently processing. Gets set in self.reset.
        self.record: dict[str, Any] | None = None

        self.default_environment = self.environments["swebench"]
        self.default_environment.default_tool = ShellTool()
        self.event_log: List[dict] = []



    def setup(self):
        self.environments["swebench"].setup()

    def generate_command_docs(self, format="docstring"):
        """
        Generates a dictionary of function names and their docstrings.
        """
        docs = {}
        for env in self.environments.values():
            for name, tool in env.tools.items():
                signature = inspect.signature(tool.function)
                docs[name] = {
                    "docstring": tool.documentation(format),
                    "signature": str(signature),
                }

        return docs
    
    def _save_predictions(self, instance_id: str, info):
        print("PRDEICTIONS")
        output_file = self.traj_dir / "all_preds.jsonl"
        model_patch = info["submission"] if "submission" in info else None
        datum = {
            KEY_MODEL: Path(self.traj_dir).name,
            KEY_INSTANCE_ID: instance_id,
            KEY_PREDICTION: model_patch,
        }
        with open(output_file, "a+") as fp:
            print(json.dumps(datum), file=fp, flush=True)
        self.logger.info(f"Saved predictions to {output_file}")

        


    def run_task(self, index):
        self.config.state = {}
        self.state = self.config.state
        self.agent.reset()

        instance_id = self.data[index]["instance_id"]
        record = self.data[index]
        assert isinstance(instance_id, str)  # mypy
        self.logger.info(f"▶️  Beginning task {index} {instance_id}")

        self.environments["swebench"].reset(record)
        for tool in self.environments["swebench"].tools.values():
            tool.setup({
                "environment": self.environments["swebench"],
                "config": self.config,
                "state": self.config.state,
                "event_log": [],
            },codebase_path="./environments/"+record["repo"].replace("/","__"))
                # Get info, patch information
        issue = record["problem_statement"]
        files = []
        assert record  is not None  # mypy
        if "patch" in record:
            files = "\n".join([f"- {x.path}" for x in PatchSet(record["patch"]).modified_files])
        # Get test files, F2P tests information
        test_files = []
        if "test_patch" in record:
            test_patch_obj = PatchSet(record["test_patch"])
            test_files = "\n".join([f"- {x.path}" for x in test_patch_obj.modified_files + test_patch_obj.added_files])
        tests = ""
        if "FAIL_endTO_PASS" in record:
            tests = "\n".join([f"- {x}" for x in self.env.record["FAIL_TO_PASS"]])

        setup_args = {"issue": issue, "files": files, "test_files": test_files, "tests": tests}
        info = {}

        steps = 0
        observation = ""
        trajectory = []
        while steps < 15:
            steps+=1
            thought, action, output = self.agent.predict(
                issue, observation, self
            )
            trajectory.append(TrajectoryStep(
                action=action,
                observation=observation,
                response=output,
                thought=thought,
            ))
            try:
                toolname, args = parse_command(action)
            except Exception as e:
                self.logger.error(f"❌ Failed to parse command: {action}")
                observation = f"Failed to parse command: {action}"
                continue

            if (
                toolname == "submit"
                or toolname == "exit"
                or toolname == "stop"
                or toolname == "exit_error"
                or toolname == "exit_api"
            ):  
                break

            try:

                env = None

                for _env in list(self.environments.values()):
                    if toolname in _env.tools:
                        env = _env

                if not env:
                    raise ToolNotFoundException(toolname, self.environments)

                print(toolname,args)
                response = env.tools[toolname](
                    {
                        "environment": env,
                        "config": self.config,
                        "state": self.config.state,
                        "event_log": [],
                        "raw_command": action,
                    },
                    *args,
                )
                observation = response
                print("RESPONSE",response,observation)

            except ToolNotFoundException as e:
                if not (
                    self.default_environment
                    and self.default_environment.default_tool
                ):
                    raise e

                try:


                    response = self.default_environment.default_tool(
                        {
                            "state": self.config.state,
                            "environment": self.default_environment,
                            "session": self,
                            "raw_command": output,
                        },
                        toolname,
                        args,
                    )
                    observation = response
                    print("RESPONSE",response,observation)


                except Exception as e:
                    self.logger.error(traceback.format_exc())
                    self.logger.error(f"Error routing tool call: {e}")
                    observation = f"Error routing tool call: {e}"

            except Exception as e:
                self.logger.error(traceback.format_exc())
                self.logger.error(f"Error routing tool call: {e}")
                observation = f"Error routing tool call: {e}"
                print("RESPONSE",f"Error routing tool call: {e}",observation)


        
        print("LOOP ENDED")
        try:
            observation = self.environments["swebench"].tools["submit"](
                {
                    "environment": self.environments["swebench"],
                    "config": self.config,
                    "state": self.config.state,
                    "event_log": [],
                    "raw_command": output,
                },
            )
            print("SUBMIT",observation)
            submission = get_submission(observation)
            # assert submission is not None and submission.strip() != "", AssertionError("No submission found.")
            self.logger.info(f"Found submission: {submission}")
            info["submission"] = submission
            observation = "Exited (autosubmitted)"
            self.logger.info("Exiting with autosubmission")
            # return observation, 0, True, info

        except KeyboardInterrupt:
            raise
        except:
            self.logger.error(traceback.format_exc())
            pass
        
        save_trajectory(trajectory, self.traj_dir / f"{instance_id}.traj", "swebench", info)

        self._save_predictions(instance_id, info)

        self.environments["swebench"].tools["find_function"].cleanup({
            "environment": self.environments["swebench"],
            "config": self.config,
            "state": self.config.state,
            "event_log": [],
        },cache_path="cache.json")


    def should_skip(self, instance_id: str) -> bool:
        """Check if we should skip this instance based on the instance filter and skip_existing flag."""

        if self.config.instances:
            if instance_id not in self.config.instances:
                return True

        # Skip instances that don't match the instance filter
        if re.match(self.config.instance_filter, instance_id) is None:
            self.logger.info(f"⏭️ Instance filter not matched. Skipping instance {instance_id}")
            return True

        # If flag is set to False, don't skip
        if not self.config.skip_existing:
            return False

        # Check if there's an existing trajectory for this instance
        log_path = self.traj_dir / (instance_id + ".traj")
        if not log_path.exists():
            return False

        content = log_path.read_text()
        if not content.strip():
            self.logger.warning("Found empty trajectory: %s. Removing.", log_path)
            log_path.unlink()
            return False

        data = json.loads(content)
        # If the trajectory has no exit status, it's incomplete and we will redo it
        # exit_status = data["info"].get("exit_status", None)
        # if exit_status == "early_exit" or exit_status is None:
        #     self.logger.warning(f"Found existing trajectory with no exit status: {log_path}. Removing.")
        #     log_path.unlink()
        #     return False

        self.logger.info(f"⏭️ Skipping existing trajectory: {log_path}")
        return True



    def run(self):
        # Reset environment
        self.setup()

        for index in range(len(self.data)):

            record = self.data[index]
            instance_id = record["instance_id"]
            assert isinstance(instance_id, str)  # mypy
            if self.should_skip(instance_id):
                self.logger.info(f"Skipping instance {instance_id}")
                continue
            self.run_task(index)

        self.teardown()



    def teardown(self):
        for env in self.environments.values():
            env.teardown()


def main(args : Namespace):
    print("HERE",args)
    config = SweBenchConfig(
        logger_name="swebench",
        data_path="SWE-bench_Lite-test.jsonl",
        split=args.split,
        skip_existing=True,
        experiment_id=args.experiment_id,
        environment=EnvironmentArguments(
        ),
        worker_id=args.worker_id if "worker_id" in args else 0,
        instances=args.instances,
        agent_config=AgentConfig(
            model=args.model,
            agent_name="devon",
            agent_type="task",
            temperature=args.temperature,
        )
    )
    print("HERE2",config)
    swebench = SweBenchSession(config)

    print("RUNNNING")
    swebench.run()
    return swebench.traj_dir,config.experiment_id,config.run_name


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
    parser.add_argument("--experiment_id", type=str, help="Experiment ID",default="default")
    parser.add_argument("--split", type=str, choices=["train", "dev", "test"], help="Data split")
    # parser.add_argument("--environment", type=str, help="Environment configuration")
    parser.add_argument("--model", type=str, help="Model to use")
    parser.add_argument("--temperature", type=float, help="Temperature for model sampling")
    parser.add_argument("--instances", nargs="+", help="List of instances to run")

    args = parser.parse_args()
    main(args)