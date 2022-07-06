import datetime
import importlib.metadata
import json
import os.path
import re
from collections import defaultdict
from copy import deepcopy
from subprocess import check_output
from typing import Dict, List

import traitlets
from batchspawner import SlurmSpawner
from jinja2 import Environment, FileSystemLoader

from .utils import file_hash, find, local_path

TEMPLATE_PATH = local_path("templates")

# Compute resources hash once at start-up
RESOURCES_HASH = {
    name: file_hash(local_path(os.path.join("form", name)))
    for name in ("option_form.css", "option_form.js")
}

with open(local_path("batch_script.sh")) as f:
    BATCH_SCRIPT = f.read()

try:
    BATCHSPAWNER_VERSION = importlib.metadata.version("batchspawner")
except importlib.metadata.PackageNotFoundError:
    BATCHSPAWNER_VERSION = None
try:
    JUPYTERHUB_VERSION = importlib.metadata.version("jupyterhub")
except importlib.metadata.PackageNotFoundError:
    JUPYTERHUB_VERSION = None


class MOSlurmSpawner(SlurmSpawner):
    """SLURM spawner with simple/advanced spawning page"""

    # Override default batch script
    batch_script = traitlets.Unicode(BATCH_SCRIPT).tag(config=True)

    partitions = traitlets.Dict(
        value_trait=traitlets.Dict(
            key_trait=traitlets.Unicode(),
            per_key_traits={
                "description": traitlets.Unicode(),
                "architecture": traitlets.Unicode(),
                "gpu": traitlets.Unicode(allow_none=True, default_value=None),
                "simple": traitlets.Bool(),
                "jupyter_environments": traitlets.Dict(
                    key_trait=traitlets.Unicode(),
                    value_trait=traitlets.Dict(
                        key_trait=traitlets.Unicode(),
                        per_key_traits={
                            "path": traitlets.Unicode(),
                            "description": traitlets.Unicode(),
                            "add_to_path": traitlets.Bool(),
                        },
                    ),
                ),
                "max_ngpus": traitlets.Int(),
                "max_nprocs": traitlets.Int(),
                "max_runtime": traitlets.Int(),
            },
        ),
        key_trait=traitlets.Unicode(),
        config=True,
        help="Information on supported partitions",
    ).tag(config=True)

    @traitlets.validate("partitions")
    def _validate_partitions(self, proposal):
        # Set add_to_path if missing in jupyter_environments
        partitions = deepcopy(proposal["value"])
        for partition in partitions.values():
            for env in partition["jupyter_environments"].values():
                env.setdefault("add_to_path", True)
        return partitions

    singularity_cmd = traitlets.List(
        trait=traitlets.Unicode(),
        default_value=["singularity", "exec"],
        help="Singularity command to use for starting jupyter server in container",
    ).tag(config=True)

    FORM_TEMPLATE = Environment(
        loader=FileSystemLoader(TEMPLATE_PATH),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    ).get_template("option_form.html")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options_form = self.create_options_form

    def _get_slurm_info(self):
        """Returns information about partitions from slurm"""
        # Get number of nodes and idle nodes for all partitions
        state = check_output(
            ["sinfo", "-a", "-N", "--noheader", "-o", "%R %t %m"]
        ).decode("utf-8")
        slurm_info = defaultdict(lambda: {"nodes": 0, "idle": 0, "max_mem": 0})
        for line in state.splitlines():
            partition, state, memory = line.split()
            info = slurm_info[partition]
            info["nodes"] += 1
            if state == "idle":
                info["idle"] += 1
            info["max_mem"] = max(info["max_mem"], int(memory))
        return slurm_info

    @staticmethod
    def create_options_form(spawner):
        """Create a form for the user to choose the configuration for the SLURM job"""
        slurm_info = spawner._get_slurm_info()

        # Combine all partition info as a dict
        partitions = {}
        default_partition = None
        for name, info in spawner.partitions.items():
            partitions[name] = {
                "max_nnodes": slurm_info[name]["nodes"],
                "nnodes_idle": slurm_info[name]["idle"],
                "max_mem": slurm_info[name]["max_mem"],
                **info,
            }
            if info["simple"] and default_partition is None:
                default_partition = name

        # Prepare json info
        jsondata = json.dumps(
            {
                "partitions": partitions,
                "default_partition": default_partition,
            }
        )

        return spawner.FORM_TEMPLATE.render(
            hash_option_form_css=RESOURCES_HASH["option_form.css"],
            hash_option_form_js=RESOURCES_HASH["option_form.js"],
            partitions=partitions,
            default_partition=default_partition,
            batchspawner_version=BATCHSPAWNER_VERSION,
            jupyterhub_version=JUPYTERHUB_VERSION,
            jsondata=jsondata,
        )

    # Options retrieved from HTML form and associated converter functions
    _FORM_FIELD_CONVERSIONS = {
        "partition": str,
        "runtime": str,
        "nprocs": int,
        "mem": str,
        "reservation": str,
        "ngpus": int,
        "jupyterlab": lambda v: v == "true",
        "options": lambda v: v.strip(),
        "output": lambda v: v == "true",
        "environment_path": str,
    }

    _RUNTIME_REGEXP = re.compile(
        "^(?P<hours>[0-9]+)(?::(?P<minutes>[0-5]?[0-9]))?(?::(?P<seconds>[0-5]?[0-9]))?$"
    )

    _MEM_REGEXP = re.compile("^[0-9]*([0-9]+[KMGT])?$")

    def __validate_options(self, options):
        """Check validity of options"""
        assert "partition" in options, "Partition information is missing"
        assert options["partition"] in self.partitions, "Partition is not supported"

        partition_info = self.partitions[options["partition"]]

        if "runtime" in options:
            match = self._RUNTIME_REGEXP.match(options["runtime"])
            assert match is not None, "Error in runtime syntax"
            runtime = datetime.timedelta(
                **{k: int(v) for k, v in match.groupdict().items()}
            )
            max_runtime = datetime.timedelta(seconds=partition_info["max_runtime"])
            assert runtime <= max_runtime, "Requested runtime is too long"

        if (
            "nprocs" in options
            and not 1 <= options["nprocs"] <= partition_info["max_nprocs"]
        ):
            raise AssertionError("Error in number of CPUs")

        if "mem" in options and self._MEM_REGEXP.match(options["mem"]) is None:
            raise AssertionError("Error in memory syntax")

        if "reservation" in options and "\n" in options["reservation"]:
            raise AssertionError("Error in reservation")

        if (
            "ngpus" in options
            and not 0 <= options["ngpus"] <= partition_info["max_ngpus"]
        ):
            raise AssertionError("Error in number of GPUs")

        if "options" in options and "\n" in options["options"]:
            raise AssertionError("Error in extra options")

        if "environment_path" in options and "\n" in options["environment_path"]:
            raise AssertionError("Error in environment_path")

    def options_from_form(self, formdata: Dict[str, List[str]]) -> Dict[str, str]:
        """Parse the form and add options to the SLURM job script"""
        # Convert expected input from List[str] to appropriate type
        options = {}
        for name, convert in self._FORM_FIELD_CONVERSIONS.items():
            if name not in formdata:
                continue
            value = formdata[name][0].strip()
            if len(value) == 0:
                continue
            try:
                options[name] = convert(value)
            except ValueError:
                raise RuntimeError(f"Invalid {name} value")

        self.__validate_options(options)

        partition = options["partition"]

        # Specific handling of exclusive flag
        # When mem=0 or all CPU are requested, set the exclusive flag
        if (
            options["nprocs"] == self.partitions[partition]["max_nprocs"]
            or options.get("mem", None) == "0"
        ):
            options["exclusive"] = True

        # Specific handling of jupyterlab
        self.default_url = "/lab" if options.get("jupyterlab", False) else ""

        # Specific handling of ngpus as gres
        if options.get("ngpus", 0) > 0:
            gpu_gres_template = self.partitions[partition]["gpu"]
            if gpu_gres_template is None:
                raise RuntimeError("GPU(s) not available for this partition")
            options["gres"] = gpu_gres_template.format(options["ngpus"])

        partition_environments = tuple(
            self.partitions[partition]["jupyter_environments"].values()
        )
        if "environment_path" not in options:
            # Set path to use from first environment for the current partition
            options["environment_path"] = partition_environments[0]["path"]

        if options["environment_path"].endswith(".sif"):
            # Use singularity image
            self.batchspawner_singleuser_cmd = " ".join(
                [
                    *self.singularity_cmd,
                    options["environment_path"],
                    "batchspawner-singleuser",
                ]
            )
            return options

        corresponding_default_env = find(
            lambda env: env["path"] == options["environment_path"],
            partition_environments,
        )
        # custom envs are always added to PATH, defaults ones only if add_to_path is True
        if (
            corresponding_default_env is None
            or corresponding_default_env["add_to_path"]
        ):
            options["prologue"] = f"export PATH={options['environment_path']}:$PATH"

        # Virtualenv is not activated, we need to provide full path
        self.batchspawner_singleuser_cmd = os.path.join(
            options["environment_path"], "batchspawner-singleuser"
        )
        self.cmd = [os.path.join(options["environment_path"], "jupyterhub-singleuser")]

        return options

    async def submit_batch_script(self):
        self.log.info(f"Used environment: {self.user_options['environment_path']}")
        self.log.info(f"Used default URL: {self.default_url}")
        return await super().submit_batch_script()
