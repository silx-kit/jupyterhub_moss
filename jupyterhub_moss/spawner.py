from collections import defaultdict
import datetime
import json
import os.path
import re
from typing import Dict, List

from batchspawner import SlurmSpawner
import traitlets
from subprocess import check_output
from jinja2 import Environment, FileSystemLoader

from .utils import local_path, file_hash


TEMPLATE_PATH = local_path("templates")

# Compute resources hash once at start-up
RESOURCES_HASH = {
    name: file_hash(local_path(os.path.join("form", name)))
    for name in ("option_form.css", "option_form.js")
}

with open(local_path("batch_script.sh")) as f:
    BATCH_SCRIPT = f.read()


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
                    key_trait=traitlets.Unicode(), value_trait=traitlets.Unicode()
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
        state = check_output(["sinfo", "-a", "-N", "--noheader", "-o", "%R %t"]).decode(
            "utf-8"
        )
        slurm_info = defaultdict(lambda: {"nodes": 0, "idle": 0})
        for line in state.splitlines():
            partition, state = line.split()
            info = slurm_info[partition]
            info["nodes"] += 1
            if state == "idle":
                info["idle"] += 1
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
                **info
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
            jsondata=jsondata,
        )

    # Options retrieved from HTML form and associated converter functions
    _FORM_FIELD_CONVERSIONS = {
        "partition": str,
        "runtime": str,
        "nprocs": int,
        "reservation": str,
        "nnodes": int,
        "ntasks": int,
        "exclusive": lambda v: v == "true",
        "ngpus": int,
        "jupyterlab": lambda v: v == "true",
        "options": lambda v: v.strip(),
        "output": lambda v: v == "true",
        "environment_path": str,
    }

    _RUNTIME_REGEXP = re.compile(
        "^(?P<hours>[0-9]+)(?::(?P<minutes>[0-5]?[0-9]))?(?::(?P<seconds>[0-5]?[0-9]))?$"
    )

    def __validate_options(self, options):
        """Check validity of options"""
        assert "partition" in options, "Partition information is missing"
        assert options["partition"] in self.partitions, "Partition is not supported"

        partition_info = self.partitions[options["partition"]]
        slurm_info = self._get_slurm_info()[options["partition"]]

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

        if "reservation" in options and "\n" in options["reservation"]:
            raise AssertionError("Error in reservation")

        if "nnodes" in options and not 1 <= options["nnodes"] <= slurm_info["nodes"]:
            raise AssertionError("Error in number of nodes")

        if "ntasks" in options and options["ntasks"] < 1:
            raise AssertionError("Error in number ot tasks")

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

        # Specific handling of jupyterlab
        self.default_url = "/lab" if options.get("jupyterlab", False) else ""

        # Specific handling of ngpus as gres
        if options.get("ngpus", 0) > 0:
            gpu_gres_template = self.partitions[partition]["gpu"]
            if gpu_gres_template is None:
                raise RuntimeError("GPU(s) not available for this partition")
            options["gres"] = gpu_gres_template.format(options["ngpus"])

        # Virtualenv is not activated, we need to provide full path
        default_venv_path = tuple(self.partitions[partition]["jupyter_environments"].values())[0]
        venv_dir = options.get("environment_path", default_venv_path)
        self.batchspawner_singleuser_cmd = os.path.join(
            venv_dir, "batchspawner-singleuser"
        )
        self.cmd = [os.path.join(venv_dir, "jupyterhub-singleuser")]

        return options
