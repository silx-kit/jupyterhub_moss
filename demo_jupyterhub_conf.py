# Sample jupyterhub configuration using jupyterhub_moss

import os
import random
import sys
import batchspawner  # noqa

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import jupyterhub_moss  # noqa

c = get_config()  # noqa

# Select the MOSlurmSpawner backend
jupyterhub_moss.set_config(c)


class MOckSlurmSpawner(jupyterhub_moss.MOSlurmSpawner):
    def _get_slurm_info(self):
        return {
            k: {"nodes": v["max_nprocs"], "idle": random.randint(0, v["max_nprocs"])}
            for k, v in self.partitions.items()
        }


c.JupyterHub.spawner_class = MOckSlurmSpawner

# Partition descriptions, see https://github.com/silx-kit/jupyterhub_moss#partition-settings
c.MOSlurmSpawner.partitions = {
    "partition_1": {
        "architecture": "x86_86",
        "description": "Partition 1",
        "gpu": None,
        "max_ngpus": 0,
        "max_nprocs": 28,
        "max_runtime": 12 * 3600,
        "simple": True,
        "jupyter_environments": {
            "default": "/default/jupyter_env_path/bin/",
            "new-x86": "/new-x86/jupyter_env_path/bin/",
        },
    },
    "partition_2": {
        "architecture": "ppc64le",
        "description": "Partition 2",
        "gpu": "gpu:V100-SXM2-32GB:{}",
        "max_ngpus": 2,
        "max_nprocs": 128,
        "max_runtime": 1 * 3600,
        "simple": True,
        "jupyter_environments": {
            "default": "/path/to/jupyter/env/for/partition_2/bin/",
            "new-ppx64le": "/new-ppc64le/jupyter_env_path/bin/",
        },
    },
    "partition_3": {
        "architecture": "x86_86",
        "description": "Partition 3",
        "gpu": None,
        "max_ngpus": 0,
        "max_nprocs": 28,
        "max_runtime": 12 * 3600,
        "simple": False,
        "jupyter_environments": {
            "default": "/path/to/jupyter/env/for/partition_3/bin/",
            "new-x86": "/new-x86/jupyter_env_path/bin/",
        },
    },
}


# JupyterHub
c.JupyterHub.ip = "127.0.0.1"
c.JupyterHub.hub_ip = "127.0.0.1"
c.JupyterHub.port = 8000

# Batchspawner
c.BatchSpawnerBase.exec_prefix = ""  # Do not run sudo
