# Sample jupyterhub configuration using jupyterhub_moss

import os
import random
import sys
import batchspawner  # noqa

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import jupyterhub_moss  # noqa

c = get_config()  # noqa

# Select the MOSlurmSpawner backend and increase the timeout since batch jobs may take time to start
jupyterhub_moss.set_config(c)


class MOckSlurmSpawner(jupyterhub_moss.MOSlurmSpawner):
    def _get_slurm_info(self):
        return {
            k: {"nodes": v["max_nprocs"], "idle": random.randint(0, v["max_nprocs"])}
            for k, v in self.partitions.items()
        }


c.JupyterHub.spawner_class = MOckSlurmSpawner

# Partition descriptions
c.MOSlurmSpawner.partitions = {
    "partition_1": {  # Partition name     # (See description of fields below for more info)
        "architecture": "x86_86",  # Nodes architecture
        "description": "Partition 1",  # Displayed description
        "gpu": None,  # --gres= template to use for requesting GPUs
        "max_ngpus": 0,  # Maximum number of GPUs per node
        "max_nprocs": 28,  # Maximum number of CPUs per node
        "max_runtime": 12
        * 3600,  # Maximum time limit in seconds (Must be at least 1hour)
        "simple": True,  # True to show in Simple tab
        "venv": "/jupyter_env_path/bin/",  # Path to Python environment bin/ used to start jupyter on the Slurm nodes
    },
    "partition_2": {
        "architecture": "ppc64le",
        "description": "Partition 2",
        "gpu": "gpu:V100-SXM2-32GB:{}",
        "max_ngpus": 2,
        "max_nprocs": 128,
        "max_runtime": 1 * 3600,
        "simple": True,
        "venv": "/path/to/jupyter/env/for/partition_2/bin/",
    },
    "partition_3": {
        "architecture": "x86_86",
        "description": "Partition 3",
        "gpu": None,
        "max_ngpus": 0,
        "max_nprocs": 28,
        "max_runtime": 12 * 3600,
        "simple": False,
        "venv": "/path/to/jupyter/env/for/partition_3/bin/",
    },
}


# c.Authenticator.auto_login = True

# JupyterHub
c.JupyterHub.ip = "127.0.0.1"
c.JupyterHub.hub_ip = "127.0.0.1"
c.JupyterHub.port = 8000

# Batchspawner
c.BatchSpawnerBase.exec_prefix = ""  # Do not run sudo

# c.ConfigurableHTTPProxy.command = ["configurable-http-proxy", "--redirect-port", "8000"]
