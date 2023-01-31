from __future__ import annotations

import datetime
import functools
import importlib.metadata
import json
import os.path
import re
from copy import deepcopy
from typing import Callable, cast

import traitlets
from batchspawner import SlurmSpawner, format_template
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader

from .utils import (
    FormOptions,
    PartitionInfo,
    PartitionResources,
    UserOptions,
    create_prologue,
    file_hash,
    local_path,
    parse_timelimit,
)

# Compute resources hash once at start-up
RESOURCES_HASH = {
    name: file_hash(local_path(os.path.join("form", name)))
    for name in ("option_form.css", "option_form.js")
}

# Required resources per partition
REQUIRED_RESOURCES_COUNTS = "max_nprocs", "max_mem", "gpu", "max_ngpus", "max_runtime"

with open(local_path("batch_script.sh")) as f:
    BATCH_SCRIPT = f.read()

try:
    BATCHSPAWNER_VERSION = importlib.metadata.version("batchspawner")
except importlib.metadata.PackageNotFoundError:
    BATCHSPAWNER_VERSION = ""
try:
    JUPYTERHUB_VERSION = importlib.metadata.version("jupyterhub")
except importlib.metadata.PackageNotFoundError:
    JUPYTERHUB_VERSION = ""


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
        # Get number of nodes/state, cores/node, cores/state, gpus, total memory for all partitions
        r"sinfo -a --noheader -o '%R %F %c %C %G %m %l'",
        help="Command to query cluster information from Slurm. Formatted using req_xyz traits as {xyz}."
        "Output will be parsed by ``slurm_info_resources``.",
    ).tag(config=True)

    slurm_info_resources = traitlets.Callable(
        help="""Provides information about resources in Slurm cluster.

        It will be called with the output of ``slurm_info_cmd`` as argument and should return a
        dictionary mapping each partition name to resources defined in ``REQUIRED_RESOURCES_COUNTS``
        and resources used in option_form template.
        """,
    ).tag(config=True)

    @traitlets.default("slurm_info_resources")
    def _get_slurm_info_resources_default(
        self,
    ) -> Callable[[str], dict[str, PartitionResources]]:
        """Returns default for `slurm_info_resources` traitlet."""
        return self._slurm_info_resources

    def _slurm_info_resources(
        self, slurm_info_out: str
    ) -> dict[str, PartitionResources]:
        """Parses output from Slurm command: sinfo -a --noheader -o '%R %F %c %C %G %m %l'

        Returns information about partition resources listed in ``REQUIRED_RESOURCES_COUNTS``:
        number of cores, max memory, gpus and resource counts to be shown in table of available resources.

        :param slurm_info_out: Output of slurm_info_cmd
        :rtype: Mapping of partition information:
            {
                partition: {gpu, max_nprocs, max_ngpus, max_mem, max_runtime, ...},
            }
        """
        partitions_info = {}

        for line in slurm_info_out.splitlines():
            (
                partition,
                nnodes,
                ncores_per_node,
                ncores,
                gpus,
                memory,
                timelimit,
            ) = line.split()
            # node count - allocated/idle/other/total
            _, nnodes_idle, _, nnodes_total = nnodes.split("/")
            # core count - allocated/idle/other/total
            _, ncores_idle, _, ncores_total = ncores.split("/")
            # gpu count - gpu:name:total(indexes)
            try:
                gpus_gres = gpus.replace("(", ":").split(":")
                gpus_total = gpus_gres[2]
                gpu = ":".join(gpus_gres[0:2]) + ":{}"
            except IndexError:
                gpus_total = "0"
                gpu = ""

            try:
                max_runtime = parse_timelimit(timelimit)
            except ValueError:
                self.log.warning(
                    f"Parsing timelimit '{timelimit}' failed: set to 1 day"
                )
                max_runtime = datetime.timedelta(days=1)

            try:
                resources = PartitionResources(
                    # display resource counts
                    nnodes_total=int(nnodes_total),
                    nnodes_idle=int(nnodes_idle),
                    ncores_total=int(ncores_total),
                    ncores_idle=int(ncores_idle),
                    # required resource counts
                    max_nprocs=int(ncores_per_node.rstrip("+")),
                    max_mem=int(memory.rstrip("+")),
                    gpu=gpu,
                    max_ngpus=int(gpus_total),
                    max_runtime=int(max_runtime.total_seconds()),
                )
            except ValueError as err:
                self.log.error("Error parsing output of slurm_info_cmd: %s", err)
                raise

            partitions_info[partition] = resources

        return partitions_info

    singularity_cmd = traitlets.List(
        trait=traitlets.Unicode(),
        default_value=["singularity", "exec"],
        help="Singularity command to use for starting jupyter server in container",
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options_form = self.create_options_form

    @functools.cached_property
    def __option_form_template(self):
        """jinja2 template

        Templates look-up is similar to JupyterHub:
        Use 'templates/...' to extend and fall-back to embedded templates
        """
        template_path = local_path("templates")
        loader = ChoiceLoader(
            [
                PrefixLoader({"templates": FileSystemLoader(template_path)}),
                FileSystemLoader(
                    list(self.user.settings["template_path"]) + [template_path]
                ),
            ]
        )
        environment = Environment(
            loader=loader,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return environment.get_template("option_form.html")

    async def _get_partitions_info(self) -> dict[str, PartitionInfo]:
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
        resources_info = self.slurm_info_resources(out)
        self.log.debug("Slurm partition resources: %s", resources_info)

        # use data from Slurm as base and overwrite with manual configuration settings
        partitions_info = {
            partition: {**resources_info[partition], **config_partition_info}
            for partition, config_partition_info in self.partitions.items()
        }

        for partition, info in partitions_info.items():
            for key in REQUIRED_RESOURCES_COUNTS:
                if key not in info:
                    raise KeyError(
                        f"Missing required resource '{key}' for partition '{partition}'"
                    )

        # Ensure returning a dict that can be modified by the callers
        return cast(dict[str, PartitionInfo], deepcopy(partitions_info))

    @staticmethod
    async def create_options_form(spawner: MOSlurmSpawner) -> str:
        """Create a form for the user to choose the configuration for the SLURM job"""
        # Cast to allow stripping sent information
        partitions_info = cast(dict, await spawner._get_partitions_info())

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
            }
        )

        return spawner.__option_form_template.render(
            hash_option_form_css=RESOURCES_HASH["option_form.css"],
            hash_option_form_js=RESOURCES_HASH["option_form.js"],
            partitions=partitions_info,
            default_partition=default_partition,
            batchspawner_version=BATCHSPAWNER_VERSION,
            jupyterhub_version=JUPYTERHUB_VERSION,
            jsondata=jsondata,
        )

    def __convert_formdata(self, formdata: dict[str, list[str]]) -> FormOptions:
        """Convert expected input to appropriate type"""

        def get_from_formdata(name: str, default: str = "") -> str:
            try:
                return formdata.get(name, (default,))[0].strip()
            except ValueError:
                raise RuntimeError(f"Invalid {name} value")

        # Convert output option from boolean to file pattern
        has_output = get_from_formdata("output") == "true"
        output = "slurm-%j.out" if has_output else "/dev/null"

        return dict(
            partition=get_from_formdata("partition"),
            runtime=get_from_formdata("runtime"),
            nprocs=int(get_from_formdata("nprocs", default="1")),
            memory=get_from_formdata("mem"),  # Align naming with sbatch script
            reservation=get_from_formdata("reservation"),
            ngpus=int(get_from_formdata("ngpus", default="0")),
            options=get_from_formdata("options"),
            output=output,
            environment_path=get_from_formdata("environment_path"),
            default_url=get_from_formdata("default_url"),
            root_dir=get_from_formdata("root_dir"),
        )

    _MEM_REGEXP = re.compile("^[0-9]*([0-9]+[KMGT])?$")

    def __validate_options(
        self, options: FormOptions, partition_info: PartitionInfo
    ) -> None:
        """Check validity/syntax of options and if matchs the given partition resources.

        Raises an exception when a check fails.
        """
        if options["runtime"]:
            runtime = parse_timelimit(
                options["runtime"]
            )  # Raises exception if malformed
            assert (
                runtime.total_seconds() <= partition_info["max_runtime"]
            ), "Requested runtime exceeds partition time limit"

        if not 1 <= options["nprocs"] <= partition_info["max_nprocs"]:
            raise AssertionError("Error: Unsupported number of CPU cores")

        memory = options["memory"]
        if memory and self._MEM_REGEXP.match(memory) is None:
            raise AssertionError("Error in memory syntax")

        if "\n" in options["reservation"]:
            raise AssertionError("Error in reservation")

        if not 0 <= options["ngpus"] <= partition_info["max_ngpus"]:
            raise AssertionError("Error: Unsupported number of GPUs")

        if "\n" in options["options"]:
            raise AssertionError("Error in extra options")

        if "\n" in options["environment_path"]:
            raise AssertionError("Error in environment_path")

        default_url = options["default_url"]
        if default_url and not default_url.startswith("/"):
            raise AssertionError("Must start with /")

        if "\n" in options["root_dir"]:
            raise AssertionError("Error in root_dir")

    def __update_options(
        self, form_options: FormOptions, partition_info: PartitionInfo
    ) -> UserOptions:
        """Extends/Modify options to be used for the spawn."""
        # Cast to initialize UserOptions from FormOptions
        # Should be solved by https://github.com/python/mypy/pull/13353
        options = cast(UserOptions, dict(gres="", prologue="", **form_options))

        # Specific handling of exclusive flag
        # When memory=0 or all CPU are requested, set the exclusive flag
        if (
            options["nprocs"] == partition_info["max_nprocs"]
            or options["memory"] == "0"
        ):
            options["options"] = f"--exclusive {options['options']}"

        # Specific handling of ngpus as gres
        ngpus = options["ngpus"]
        if ngpus > 0:
            gpu_gres_template = partition_info["gpu"]
            if not gpu_gres_template:
                raise RuntimeError("GPU(s) not available for this partition")
            options["gres"] = gpu_gres_template.format(ngpus)

        partition_environments = tuple(
            self.partitions[options["partition"]]["jupyter_environments"].values()
        )
        if not options["environment_path"]:
            # Set path to use from first environment for the current partition
            options["environment_path"] = partition_environments[0]["path"]

        options["prologue"] = create_prologue(
            self.req_prologue, options["environment_path"], partition_environments
        )

        return options

    async def options_from_form(self, formdata: dict[str, list[str]]) -> UserOptions:
        """Parse the form and add options to the SLURM job script"""
        form_options = self.__convert_formdata(formdata)

        assert "partition" in form_options, "Partition information is missing"
        assert (
            form_options["partition"] in self.partitions
        ), "Partition is not supported"
        partitions_info = await self._get_partitions_info()
        partition_info = partitions_info[form_options["partition"]]

        self.__validate_options(form_options, partition_info)

        user_options = self.__update_options(form_options, partition_info)
        return user_options

    def __update_spawn_commands(self, cmd_path: str) -> None:
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
        # Specific handling of landing URL (e.g., to start jupyterlab)
        self.default_url = self.user_options["default_url"]
        self.log.info(f"Used default URL: {self.default_url}")

        if self.user_options["root_dir"]:
            self.notebook_dir = self.user_options["root_dir"]

        environment_path = self.user_options["environment_path"]
        self.log.info(f"Used environment: {environment_path}")
        self.__update_spawn_commands(environment_path)

        return await super().start()

    async def submit_batch_script(self):
        # refresh environment to be kept in the job
        self.req_keepvars = self.trait_defaults("req_keepvars")

        return await super().submit_batch_script()
