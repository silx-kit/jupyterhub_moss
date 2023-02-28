from __future__ import annotations

import datetime
import functools
import importlib.metadata
import json
import os.path
from typing import Callable

import traitlets
from batchspawner import SlurmSpawner, format_template
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader
from pydantic import ValidationError

from .models import (
    PartitionAllResources,
    PartitionInfo,
    PartitionResources,
    PartitionsTrait,
    UserOptions,
)
from .utils import create_prologue, file_hash, local_path, parse_timelimit

# Compute resources hash once at start-up
RESOURCES_HASH = {
    name: file_hash(local_path(os.path.join("form", name)))
    for name in ("option_form.css", "option_form.js")
}


with open(local_path("batch_script.sh")) as f:
    BATCH_SCRIPT = f.read()

BATCHSPAWNER_VERSION = importlib.metadata.version("batchspawner")
JUPYTERHUB_VERSION = importlib.metadata.version("jupyterhub")


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
                "gpu": traitlets.Unicode(allow_none=True),
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
                "max_ngpus": traitlets.Int(allow_none=True),
                "max_nprocs": traitlets.Int(allow_none=True),
                "max_runtime": traitlets.Int(allow_none=True),
            },
        ),
        key_trait=traitlets.Unicode(),
        config=True,
        help="Information on supported partitions",
    ).tag(config=True)

    @traitlets.validate("partitions")
    def _validate_partitions(self, proposal: dict) -> dict[str, dict]:
        return PartitionsTrait.parse_obj(proposal["value"]).dict()

    slurm_info_cmd = traitlets.Unicode(
        # Get number of nodes/state, cores/node, cores/state, gpus, total memory for all partitions
        r"sinfo -a --noheader -o '%R %F %c %C %G %m %l'",
        help="Command to query cluster information from Slurm. Formatted using req_xyz traits as {xyz}."
        "Output will be parsed by ``slurm_info_resources``.",
    ).tag(config=True)

    slurm_info_resources = traitlets.Callable(
        help="""Provides information about resources in Slurm cluster.

        It will be called with the output of ``slurm_info_cmd`` as argument and should return a
        dict mapping each partition name to an instance of a :class:`models.PartitionResources`.
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

        Returns information about partition resources to constraint user choice and display available resources.

        :param slurm_info_out: Output of slurm_info_cmd
        :rtype: Mapping of partition information:
            {
                partition: {gpu, max_nprocs, max_ngpus, max_mem, max_runtime, ...},
            }
        """
        partitions_info: dict[str, PartitionResources] = {}

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
                resources = PartitionAllResources(
                    # display resource counts
                    nnodes_total=nnodes_total,
                    nnodes_idle=nnodes_idle,
                    ncores_total=ncores_total,
                    ncores_idle=ncores_idle,
                    # required resource counts
                    max_nprocs=ncores_per_node.rstrip("+"),
                    max_mem=memory.rstrip("+"),
                    gpu=gpu,
                    max_ngpus=gpus_total,
                    max_runtime=max_runtime.total_seconds(),
                )
            except ValidationError as err:
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

        partitions = PartitionsTrait.parse_obj(self.partitions)

        # use data from Slurm as base and overwrite with manual configuration settings
        partitions_info = {
            partition: PartitionInfo.parse_obj(
                {
                    **resources_info[partition].dict(),
                    **config_partition_info.dict(exclude_none=True),
                }
            )
            for partition, config_partition_info in partitions.items()
        }
        return partitions_info

    @staticmethod
    async def create_options_form(spawner: MOSlurmSpawner) -> str:
        """Create a form for the user to choose the configuration for the SLURM job"""
        partitions_info = await spawner._get_partitions_info()

        simple_partitions = [
            partition for partition, info in partitions_info.items() if info.simple
        ]
        if not simple_partitions:
            raise RuntimeError("No 'simple' partition defined: No default partition")
        default_partition = simple_partitions[0]

        # Strip prologue from partitions_info:
        # it is not useful and can cause some parsing issues
        partitions_dict = {
            name: info.dict(
                exclude={
                    "jupyter_environments": {
                        env_name: {"prologue"} for env_name in info.jupyter_environments
                    }
                }
            )
            for name, info in partitions_info.items()
        }

        # Prepare json info
        jsondata = json.dumps(
            {
                "partitions": partitions_dict,
                "default_partition": default_partition,
            }
        )

        return spawner.__option_form_template.render(
            hash_option_form_css=RESOURCES_HASH["option_form.css"],
            hash_option_form_js=RESOURCES_HASH["option_form.js"],
            partitions=partitions_dict,
            default_partition=default_partition,
            batchspawner_version=BATCHSPAWNER_VERSION,
            jupyterhub_version=JUPYTERHUB_VERSION,
            jsondata=jsondata,
        )

    def __validate_options(
        self, options: UserOptions, partition_info: PartitionInfo
    ) -> None:
        """Check if options match the given partition resources.

        Raises an exception when a check fails.
        """
        if options.runtime:
            assert (
                parse_timelimit(options.runtime).total_seconds()
                <= partition_info.max_runtime
            ), "Requested runtime exceeds partition time limit"

        if options.nprocs > partition_info.max_nprocs:
            raise AssertionError("Unsupported number of CPU cores")

        if options.ngpus > partition_info.max_ngpus:
            raise AssertionError("Unsupported number of GPUs")

    def __update_options(
        self, options: UserOptions, partition_info: PartitionInfo
    ) -> None:
        """Extends/Modify options to be used for the spawn.

        The provided `options` argument is modified in-place.
        """
        # Specific handling of exclusive flag
        # When memory=0 or all CPU are requested, set the exclusive flag
        if options.nprocs == partition_info.max_nprocs or options.memory == "0":
            options.options = f"--exclusive {options.options}"

        # Specific handling of ngpus as gres
        if options.ngpus > 0:
            gpu_gres_template = partition_info.gpu
            if not gpu_gres_template:
                raise RuntimeError("GPU(s) not available for this partition")
            options.gres = gpu_gres_template.format(options.ngpus)

        partition_environments = tuple(partition_info.jupyter_environments.values())
        if not options.environment_path:
            # Set path to use from first environment for the current partition
            options.environment_path = partition_environments[0].path

        options.prologue = create_prologue(
            self.req_prologue, options.environment_path, partition_environments
        )

    async def options_from_form(self, formdata: dict[str, list[str]]) -> dict:
        """Parse the form and add options to the SLURM job script"""
        options = UserOptions.parse_formdata(formdata)

        partitions_info = await self._get_partitions_info()
        try:
            partition_info = partitions_info[options.partition]
        except KeyError:
            raise RuntimeError(f"Partition {options.partition} is not available")

        self.__validate_options(options, partition_info)
        self.__update_options(options, partition_info)

        return options.dict()

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

        self.notebook_dir = self.user_options["root_dir"]

        environment_path = self.user_options["environment_path"]
        self.log.info(f"Used environment: {environment_path}")
        self.__update_spawn_commands(environment_path)

        return await super().start()

    async def submit_batch_script(self):
        # refresh environment to be kept in the job
        self.req_keepvars = self.trait_defaults("req_keepvars")

        return await super().submit_batch_script()
