# Credits:
# - Initial CometSpawner implementation: https://gist.github.com/zonca/aaed55502c4b16535fe947791d02ac32
# - DESY jupyterhub slurm service: https://confluence.desy.de/display/IS/JupyterHub+on+Maxwell
# - Ideas for the spawning page from: https://doc.zih.tu-dresden.de/hpc-wiki/bin/view/Compendium/JupyterHub

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

from .utils import local_path


TEMPLATE_PATH = local_path("templates")


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
                "venv": traitlets.Unicode(),
                "max_ngpus": traitlets.Int(),
                "max_nprocs": traitlets.Int(),
            },
        ),
        key_trait=traitlets.Unicode(),
        config=True,
        help="Information on supported partitions",
    ).tag(config=True)

    jinja_env = Environment(
        loader=FileSystemLoader(TEMPLATE_PATH),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def _options_form_default(self):
        """Create a form for the user to choose the configuration for the SLURM job"""

        # Get number of nodes and idle nodes for all partitions
        state = check_output(["sinfo", "-a", "-N", "--noheader", "-o", "%R %t"]).decode(
            "utf-8"
        )
        partitions_info = defaultdict(lambda: {"nodes": 0, "idle": 0})
        for line in state.splitlines():
            partition, state = line.split()
            info = partitions_info[partition]
            info["nodes"] += 1
            if state == "idle":
                info["idle"] += 1

        # Combine all partition info as a dict
        partitions_desc = {}
        default_partition = None
        for name, info in self.partitions.items():
            partitions_desc[name] = {
                "max_nnodes": partitions_info[name]["nodes"],
                "nnodes_idle": partitions_info[name]["idle"],
                **dict((k, v) for k, v in info.items() if k != "venv"),
            }
            if info["simple"] and default_partition is None:
                default_partition = name

        # Prepare json info
        jsondata = json.dumps(
            {
                "partitions": partitions_desc,
                "default_partition": default_partition,
            }
        )

        form_template = self.jinja_env.get_template("option_form.html")
        return form_template.render(
            partitions=partitions_desc,
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
    }

    _RUNTIME_REGEXP = re.compile(
        "^(?P<hour>(?:[0-1]?[0-9])|(?:2[0-3]))(?::(?P<minute>[0-5]?[0-9]))?(?::(?P<seconds>[0-5]?[0-9]))?$"
    )

    def __validate_options(self, options):
        """Check validity of options"""
        assert "partition" in options, "Partition information is missing"
        assert options["partition"] in self.partitions, "Partition is not supported"

        if "runtime" in options:
            match = self._RUNTIME_REGEXP.match(options["runtime"])
            assert match is not None, "Error in runtime syntax"
            runtime = datetime.time(*[int(v) for v in match.groups() if v is not None])
            assert runtime <= datetime.time(12), "Maximum runtime is 12h"

        if "nprocs" in options and options["nprocs"] < 1:
            raise AssertionError("Error in number of CPUs")
        if "reservation" in options and "\n" not in options["reservation"]:
            raise AssertionError("Error in reservation")
        if "nnodes" in options and not 1 <= options["nnodes"] <= 30:
            raise AssertionError("Error in number of nodes")
        if "ntasks" in options and options["ntasks"] < 1:
            raise AssertionError("Error in number ot tasks")
        if "ngpus" in options and not 0 <= options["ngpus"] <= 2:
            raise AssertionError("Error in number of GPUs")

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
        venv_dir = self.partitions[partition]["venv"]
        self.batchspawner_singleuser_cmd = os.path.join(
            venv_dir, "batchspawner-singleuser"
        )
        self.cmd = [os.path.join(venv_dir, "jupyterhub-singleuser")]

        return options
