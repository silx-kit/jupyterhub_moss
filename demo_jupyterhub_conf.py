# Sample jupyterhub configuration using jupyterhub_moss

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import jupyterhub_moss

c = get_config()  # noqa

# Select the MOSlurmSpawner backend
jupyterhub_moss.set_config(c)


SINFO_OUTPUT = """unused 40 28+ 121/1191/0/1312 (null) 196000+
partition_1 48 35+ 38/1642/0/1680 (null) 196000+
partition_2 7 128 116/780/0/896 gpu:GPU-MODEL:2 512000
partition_3 28 40 114/1006/0/1120 (null) 310000
other_mixed 10 64 152/488/0/640 gpu:OTHER-GPU:2(S:0-1) 455000+
other_mixed 94 28+ 153/3583/0/3736 (null) 196000+
"""
c.MOSlurmSpawner.slurm_info_cmd = f'echo "{SINFO_OUTPUT}"'


# Partition descriptions, see https://github.com/silx-kit/jupyterhub_moss#partition-settings
c.MOSlurmSpawner.partitions = {
    "partition_1": {
        "architecture": "x86_86",
        "description": "Partition 1",
        "max_runtime": 12 * 3600,
        "simple": True,
        "jupyter_environments": {
            "default": {
                "path": "/default/jupyter_env_path/bin/",
                "description": "Operating system (default)",
                "add_to_path": False,
            },
            "new-x86": {
                "path": "/new-x86/jupyter_env_path/bin/",
                "description": "New environment x86 (latest)",
                "add_to_path": True,
            },
            "latest": {
                "path": "/latest/jupyter_env_path/bin/",
                "description": "Operating system (latest)",
            },
        },
    },
    "partition_2": {
        "architecture": "ppc64le",
        "description": "Partition 2",
        "max_runtime": 1 * 3600,
        "simple": True,
        "jupyter_environments": {
            "default": {
                "path": "/path/to/jupyter/env/for/partition_2/bin/",
                "description": "Current environment (default)",
            },
            "latest": {
                "path": "/latest/path/to/jupyter/env/for/partition_2/bin/",
                "description": "Current environment (latest)",
            },
            "new-ppx64le": {
                "path": "/new-ppc64le/jupyter_env_path/bin/",
                "description": "New environment ppc64le (latest)",
            },
        },
    },
    "partition_3": {
        "architecture": "x86_86",
        "description": "Partition 3",
        "max_runtime": 12 * 3600,
        "simple": False,
        "jupyter_environments": {
            "default": {
                "path": "/path/to/jupyter/env/for/partition_3/bin/",
                "description": "Operating system (default)",
            },
            "new-x86": {
                "path": "/new-x86/jupyter_env_path/bin/",
                "description": "New environment x86 (latest)",
            },
        },
    },
}


# JupyterHub
c.JupyterHub.ip = "127.0.0.1"
c.JupyterHub.hub_ip = "127.0.0.1"
c.JupyterHub.port = 8000

# Batchspawner
c.BatchSpawnerBase.exec_prefix = ""  # Do not run sudo
