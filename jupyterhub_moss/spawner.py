import datetime
import importlib.metadata
import json
import os.path
import re
from collections import defaultdict
from copy import deepcopy
from typing import Dict, List

import traitlets
from batchspawner import SlurmSpawner, format_template
from jinja2 import Environment, FileSystemLoader

from .utils import file_hash, find, local_path, parse_timelimit

TEMPLATE_PATH = local_path("templates")

# Compute resources hash once at start-up
RESOURCES_HASH = {
    name: file_hash(local_path(os.path.join("form", name)))
    for name in ("option_form.css", "option_form.js")
}

# Required resources per partition
RESOURCES_COUNTS = [
    "max_nprocs",
    "max_mem",
    "gpu",
    "max_ngpus",
    "max_runtime",
    "available_counts",
]

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
                            "prologue": traitlets.Unicode(),
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
                env.setdefault("prologue", "")
        return partitions

    slurm_info_cmd = traitlets.Unicode(
        # Get number of nodes, cores, gpus, total memory, time limit for all partitions
        r"sinfo -a --noheader -o '%R %D %c %C %G %m %l'",
        help="Command to query cluster information from Slurm. Formatted using req_xyz traits as {xyz}."
        "Output will be parsed by ``slurm_info_resources``.",
    ).tag(config=True)

    slurm_info_resources = traitlets.Callable(
        help="""Provides information about resources in Slurm cluster.

        It will be called with the output of ``slurm_info_cmd`` as argument and should return a tuple:
        - list of resource labels to be displayed in table of available resources
        - dictionary mapping each partition name to resources defined in ``RESOURCES_COUNTS``""",
    ).tag(config=True)

    @traitlets.default("slurm_info_resources")
    def _get_slurm_info_resources_default(self):
        """Returns default for `slurm_info_resources` traitlet."""
        return self._slurm_info_resources

    def _slurm_info_resources(self, slurm_info_out):
        """
        Parses output from Slurm command: sinfo -a --noheader -o '%R %D %C %G %m'
        Returns information about partition resources listed in RESOURCES_COUNTS: number of cores,
        max memory, gpus and resource counts to be shown in table of available resources
        :param slurm_info_out: string with output of slurm_info_cmd
        :rtype: tuple with:
            - list of resource labels to be displayed in table of available resources
            - dict with mapping per partition: {
                partition: {max_nprocs, max_ngpus, max_mem, max_runtime, ...},
              }
        """
        # Resources displayed in table of available resources (column labels in display order)
        resources_display = ["Idle Cores", "Total Cores", "Total Nodes"]

        # Parse output
        resources_count = defaultdict(
            lambda: {resource: 0 for resource in RESOURCES_COUNTS + resources_display}
        )
        for line in slurm_info_out.splitlines():
            (
                partition,
                nodes,
                ncores_per_node,
                cores,
                gpus,
                memory,
                timelimit,
            ) = line.split()
            # core count - allocated/idle/other/total
            _, cores_idle, _, cores_total = cores.split("/")
            # gpu count - gpu:name:total(indexes)
            try:
                gpus_gres = gpus.replace("(", ":").split(":")
                gpus_total = gpus_gres[2]
                gpu = ":".join(gpus_gres[0:2]) + ":{}"
            except IndexError:
                gpus_total = 0
                gpu = None

            try:
                max_runtime = parse_timelimit(timelimit)
            except ValueError:
                self.log.warning(
                    f"Parsing timelimit '{timelimit}' failed: set to 1 day"
                )
                max_runtime = datetime.timedelta(days=1)

            count = resources_count[partition]
            try:
                # display resource counts
                count["Total Nodes"] = int(nodes)
                count["Total Cores"] = int(cores_total)
                count["Idle Cores"] = int(cores_idle)
                # required resource counts
                count["max_nprocs"] = int(ncores_per_node.rstrip("+"))
                count["max_mem"] = int(memory.rstrip("+"))
                count["gpu"] = gpu
                count["max_ngpus"] = int(gpus_total)
                count["max_runtime"] = int(max_runtime.total_seconds())
            except ValueError as err:
                self.log.error("Error parsing output of slurm_info_cmd: %s", err)
                raise
            else:
                count["available_counts"] = [
                    count[resource] for resource in resources_display
                ]

        resources_info = {
            partition: {
                resource: resources_count[partition][resource]
                for resource in RESOURCES_COUNTS
            }
            for partition in resources_count
        }

        return (resources_display, resources_info)

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

    async def _get_partitions_info(self):
        """Returns information about used SLURM partitions

        1. Executes slurm_info_cmd
        2. Parses output with slurm_info_resources
        3. Combines info with partitions traitlet
        """
        # Execute given slurm info command
        subvars = self.get_req_subvars()
        cmd = " ".join(
            (
                format_template(self.exec_prefix, **subvars),
                format_template(self.slurm_info_cmd, **subvars),
            )
        )
        self.log.debug("Slurm info command: %s", cmd)
        out = await self.run_command(cmd)

        # Parse command output
        resources_display, resources_info = self.slurm_info_resources(out)
        dbgmsg = "Slurm partition resources displayed as available resources: %s"
        self.log.debug(dbgmsg, resources_display)
        self.log.debug("Slurm partition resources: %s", resources_info)

        for partition in resources_info:
            if not all(
                counter in resources_info[partition] for counter in RESOURCES_COUNTS
            ):
                errmsg = "Missing required resource counter in Slurm partition: {}"
                raise KeyError(errmsg.format(partition))

        # use data from Slurm as base and overwrite with manual configuration settings
        partitions_info = {
            partition: {**resources_info[partition], **config_partition_info}
            for partition, config_partition_info in self.partitions.items()
        }

        # Ensure returning a dict that can be modified by the callers
        return (resources_display, deepcopy(partitions_info))

    @staticmethod
    async def create_options_form(spawner):
        """Create a form for the user to choose the configuration for the SLURM job"""
        resources_display, partitions_info = await spawner._get_partitions_info()

        simple_partitions = [
            partition for partition, info in partitions_info.items() if info["simple"]
        ]
        if not simple_partitions:
            raise RuntimeError("No 'simple' partition defined: No default partition")
        default_partition = simple_partitions[0]

        # Strip prologue from partitions_info:
        # it is not useful and can cause some parsing issues
        for partition_info in partitions_info.values():
            for env_info in partition_info["jupyter_environments"].values():
                env_info.pop("prologue", None)

        # Prepare json info
        jsondata = json.dumps(
            {
                "partitions": partitions_info,
                "default_partition": default_partition,
                "resources_display": resources_display,
            }
        )

        return spawner.FORM_TEMPLATE.render(
            hash_option_form_css=RESOURCES_HASH["option_form.css"],
            hash_option_form_js=RESOURCES_HASH["option_form.js"],
            partitions=partitions_info,
            default_partition=default_partition,
            resources_display=resources_display,
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
        "options": lambda v: v.strip(),
        "output": lambda v: v == "true",
        "environment_path": str,
        "default_url": str,
        "root_dir": str,
    }

    _MEM_REGEXP = re.compile("^[0-9]*([0-9]+[KMGT])?$")

    def __validate_options(self, options):
        """Check validity/syntax of options

        Checks performed here do not rely on partition resources.
        See :meth:`__check_user_options` for partition resources-based checks.

        Reason: The async method :meth:`_get_partitions_info` cannot be called here
        unless `options_from_form` can be async as well.

        Raises an exception when a check fails.
        """
        assert "partition" in options, "Partition information is missing"
        assert options["partition"] in self.partitions, "Partition is not supported"

        if "runtime" in options:
            parse_timelimit(options["runtime"])  # Raises exception if malformed

        if "nprocs" in options and options["nprocs"] < 1:
            raise AssertionError("Error: Number of CPUs must be at least 1")

        if "mem" in options and self._MEM_REGEXP.match(options["mem"]) is None:
            raise AssertionError("Error in memory syntax")

        if "reservation" in options and "\n" in options["reservation"]:
            raise AssertionError("Error in reservation")

        if "ngpus" in options and options["ngpus"] < 0:
            raise AssertionError("Error: Number of GPUs must be positive")

        if "options" in options and "\n" in options["options"]:
            raise AssertionError("Error in extra options")

        if "environment_path" in options and "\n" in options["environment_path"]:
            raise AssertionError("Error in environment_path")

        if "default_url" in options:
            default_url = options["default_url"]
            if default_url and not default_url.startswith("/"):
                raise AssertionError("Must start with /")

        if "root_dir" in options and "\n" in options["root_dir"]:
            raise AssertionError("Error in root_dir")

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

        partition_environments = tuple(
            self.partitions[options["partition"]]["jupyter_environments"].values()
        )
        if "environment_path" not in options:
            # Set path to use from first environment for the current partition
            options["environment_path"] = partition_environments[0]["path"]

        corresponding_default_env = find(
            lambda env: env["path"] == options["environment_path"],
            partition_environments,
        )

        # Generate prologue
        prologue = self.req_prologue

        if corresponding_default_env is not None:
            prologue += f"\n{corresponding_default_env['prologue']}"

        # Singularity images are never added to PATH
        # Custom envs are always added to PATH
        # Defaults envs only if add_to_path is True
        if not options["environment_path"].endswith(".sif") and (
            corresponding_default_env is None
            or corresponding_default_env["add_to_path"]
        ):
            prologue += f"\nexport PATH={options['environment_path']}:$PATH"

        options["prologue"] = prologue

        return options

    def __check_user_options(self, partition_info):
        """Check if requested resources are valid for the given partition info.

        See :meth:`__validate_options` for the other user options checks.

        Raises AssertionError if request does not match available resources.
        """
        if "runtime" in self.user_options:
            runtime = parse_timelimit(self.user_options["runtime"])
            assert (
                runtime.total_seconds() <= partition_info["max_runtime"]
            ), "Requested runtime exceeds partition time limit"

        if (
            "nprocs" in self.user_options
            and self.user_options["nprocs"] > partition_info["max_nprocs"]
        ):
            raise AssertionError("Error in number of CPUs")

        if (
            "ngpus" in self.user_options
            and self.user_options["ngpus"] > partition_info["max_ngpus"]
        ):
            raise AssertionError("Error in number of GPUs")

    def __update_spawn_options(self, partition_info):
        """Update user_options and other attributes controlling the spawn"""
        # Specific handling of exclusive flag
        # When mem=0 or all CPU are requested, set the exclusive flag
        if (
            self.user_options.get("nprocs") == partition_info["max_nprocs"]
            or self.user_options.get("mem") == "0"
        ):
            self.user_options["exclusive"] = True

        # Specific handling of landing URL (e.g., to start jupyterlab)
        self.default_url = self.user_options.get("default_url", "")
        self.log.info(f"Used default URL: {self.default_url}")

        if "root_dir" in self.user_options:
            self.notebook_dir = self.user_options["root_dir"]

        # Specific handling of ngpus as gres
        ngpus = self.user_options.get("ngpus", 0)
        if ngpus > 0:
            gpu_gres_template = partition_info["gpu"]
            if gpu_gres_template is None:
                raise RuntimeError("GPU(s) not available for this partition")
            self.user_options["gres"] = gpu_gres_template.format(ngpus)

    def __update_spawn_commands(self, cmd_path):
        """Add path to commands"""
        if cmd_path.endswith(".sif"):
            # Use singularity image
            self.batchspawner_singleuser_cmd = " ".join(
                [
                    *self.singularity_cmd,
                    cmd_path,
                    "batchspawner-singleuser",
                ]
            )
            return

        # Since virtualenvs are not activated, the full path of executables must be provided
        self.batchspawner_singleuser_cmd = os.path.join(
            cmd_path, "batchspawner-singleuser"
        )
        self.cmd = [os.path.join(cmd_path, "jupyterhub-singleuser")]

    async def start(self):
        _, partitions_info = await self._get_partitions_info()
        partition_info = partitions_info[self.user_options["partition"]]

        # Exceptions raised by the checks are catched by the caller, and
        # a "500 Internal Server Error" is returned to the frontend.
        self.__check_user_options(partition_info)

        self.__update_spawn_options(partition_info)

        environment_path = self.user_options["environment_path"]
        self.log.info(f"Used environment: {environment_path}")
        self.__update_spawn_commands(environment_path)

        return await super().start()

    async def submit_batch_script(self):
        # refresh environment to be kept in the job
        self.req_keepvars = self.trait_defaults("req_keepvars")

        return await super().submit_batch_script()
