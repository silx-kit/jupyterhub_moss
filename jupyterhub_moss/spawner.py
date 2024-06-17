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
    PartitionInfo,
    PartitionResources,
    PartitionsTrait,
    UserOptions,
)
from .utils import (
    create_prologue,
    file_hash,
    local_path,
    parse_gpu_resource,
    parse_partition_id,
    parse_timelimit,
)

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
                            "description": traitlets.Unicode(),
                            "add_to_path": traitlets.Bool(),
                            "path": traitlets.Unicode(),
                            "modules": traitlets.Unicode(),
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
        return PartitionsTrait.model_validate(proposal["value"]).model_dump()

    slurm_info_cmd = traitlets.Unicode(
        # Get number of nodes/state, cores/node, cores/state, gpus, total memory for all partitions
        r"sinfo -N -p {partition} {clusters} --noheader -O 'Cluster,PartitionName,StateCompact,CPUsState,Gres:64,GresUsed:64,Memory,Time'",
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
                cluster,
                partition,
                node_state,
                ncores,
                gres_total,
                gres_used,
                memory,
                timelimit,
            ) = line.split()

            # ignore nodes that are down
            # take into account full nodes, see AD#18521
            if node_state not in ["idle", "mix", "alloc"]:
                continue

            # unique reference from cluster and partition names
            if cluster != 'N/A':
               partition = f"{cluster}.{partition}"

            # core count - allocated/idle/other/total
            _, ncores_idle, _, ncores_total = ncores.split("/")
            ncores_idle = int(ncores_idle)
            ncores_total = int(ncores_total)

            # gpu count - gpu:name:total(indexes)
            try:
                gpus_gres = gres_total.replace("(", ":").split(":")
                gpus_total = int(gpus_gres[2])
                gpu = ":".join(gpus_gres[0:2]) + ":{}"
                gpus_used = int(gres_used.replace("(", ":").split(":")[2])
            except IndexError:
                gpus_total = 0
                gpus_used = 0
                gpu = ""

            # job slots for resource display
            # 1 core, 2 cores, 4 cores, 1 GPU
            job_slots = [ncores_idle, ncores_idle // 2, ncores_idle // 4, gpus_total-gpus_used]

            try:
                max_runtime = parse_timelimit(timelimit)
            except ValueError:
                self.log.warning(
                    f"Parsing timelimit '{timelimit}' failed: set to 1 day"
                )
                max_runtime = datetime.timedelta(days=1)

            try:
                resources = {
                    # display resource counts
                    "job_slots": job_slots,
                    # required resource counts
                    "max_nprocs": ncores_total,
                    "max_mem": memory.rstrip("+"),
                    "gpu": gpu,
                    "max_ngpus": gpus_total,
                    "max_runtime": max_runtime.total_seconds(),
                }
            except ValidationError as err:
                self.log.error("Error parsing output of slurm_info_cmd: %s", err)
                raise

            if partition in partitions_info:
                # update display counters of existing partition
                slots_counters = zip(partitions_info[partition]["job_slots"], resources["job_slots"])
                partitions_info[partition]["job_slots"] = [old + new for old, new in slots_counters]
            else:
                # add new partition
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
        partitions = PartitionsTrait.model_validate(self.partitions)
        partitions_info = {}

        # Execute given slurm info command on each partition
        for partition_id, config_partition_info in partitions.items():
            subvars = self.get_req_subvars()
            subvars["partition"], subvars["clusters"] = parse_partition_id(partition_id)
            if subvars["clusters"]:
                subvars["clusters"] = f"-M {subvars['clusters']}"

            sinfo_cmd = " ".join(
                (
                    format_template(self.exec_prefix, **subvars),
                    format_template(self.slurm_info_cmd, **subvars),
                )
            )
            self.log.debug("Slurm info command for partition ID '%s': %s", partition_id, sinfo_cmd)
            partition_sinfo_out = await self.run_command(sinfo_cmd)
            # self.log.debug("Slurm info command output: %s", partition_sinfo_out)

            # Parse command output
            resources_info = self.slurm_info_resources(partition_sinfo_out)
            self.log.debug("Slurm partition resources: %s", resources_info)

            # use data from Slurm as base and overwrite with manual configuration settings
            partitions_info[partition_id] = PartitionInfo.model_validate(
                {
                    **resources_info[partition_id],
                    **config_partition_info.dict(exclude_none=True),
                }
            )

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
            name: info.model_dump(
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
        # Handle multi-cluster partitions
        partition_name, cluster_name = parse_partition_id(options.partition)
        options.partition = partition_name
        if cluster_name:
            options.clusters = f"--clusters {cluster_name}"
        self.req_cluster = cluster_name
        self.state_exechost_exp = rf"\1.{cluster_name}.os"

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

        # Use first env from the partition if none is requested
        if (
            not options.environment_id
            and not options.environment_path
            and not options.environment_modules
        ):
            default_env = list(partition_info.jupyter_environments.keys())[0]
            options.environment_id = default_env

        if options.environment_id not in partition_info.jupyter_environments:
            # Custom env
            options.prologue = create_prologue(
                self.req_prologue,
                "",
                options.environment_path,  # Custom envs are always added to PATH
                options.environment_modules,
            )
            return

        # It's a known env: use its config instead of received path and modules
        jupyter_environment = partition_info.jupyter_environments[
            options.environment_id
        ]
        options.environment_path = jupyter_environment.path
        options.environment_modules = jupyter_environment.modules

        options.prologue = create_prologue(
            self.req_prologue,
            jupyter_environment.prologue,
            # Default envs only added to PATH if add_to_path is True
            jupyter_environment.path if jupyter_environment.add_to_path else "",
            jupyter_environment.modules,
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

        return options.model_dump()

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

        environment_id = self.user_options["environment_id"]
        environment_path = self.user_options["environment_path"]
        environment_modules = self.user_options["environment_modules"]
        self.log.info(
            f"Used environment: ID: {environment_id}, path: {environment_path}, modules: {environment_modules}"
        )
        self.__update_spawn_commands(environment_path)

        return await super().start()

    async def submit_batch_script(self):
        # refresh environment to be kept in the job
        self.req_keepvars = self.trait_defaults("req_keepvars")

        return await super().submit_batch_script()
