# Sample jupyterhub configuration using jupyterhub_moss

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import jupyterhub_moss  # noqa

c = get_config()  # type: ignore[name-defined] # noqa

# Select the MOSlurmSpawner backend
jupyterhub_moss.set_config(c)


# Partition descriptions, see https://github.com/silx-kit/jupyterhub_moss#partition-settings
c.MOSlurmSpawner.partitions = {
    "partition_1": {
        "architecture": "x86_86",
        "description": "Partition 1",
        "simple": True,
        "jupyter_environments": {
            "default": {
                "description": "Operating system (default)",
                "path": "/default/jupyter_env_path/bin/",
                "add_to_path": False,
                "prologue": 'echo "Starting default env."\n',
            },
            "Python 3.11": {
                "description": "New environment x86 (latest)",
                "modules": "Python/3.11 JupyterLab/3.6.0",
                "add_to_path": False,
                "prologue": "echo 'Starting new-x86 env.'",
            },
            "latest": {
                "description": "Operating system (latest)",
                "path": "/latest/jupyter_env_path/bin/",
                "prologue": "echo 'Starting latest env.'",
            },
        },
    },
    "partition_2": {
        "architecture": "ppc64le",
        "description": "Partition 2",
        "simple": True,
        "jupyter_environments": {
            "default": {
                "description": "Current environment (default)",
                "path": "/path/to/jupyter/env/for/partition_2/bin/",
            },
            "latest": {
                "description": "Current environment (latest)",
                "path": "/latest/path/to/jupyter/env/for/partition_2/bin/",
            },
            "Python 3.11": {
                "description": "New environment ppc64le (latest)",
                "modules": "Python/3.11 JupyterLab/3.6.0",
            },
        },
    },
    "partition_3": {
        "architecture": "x86_86",
        "description": "Partition 3",
        "simple": False,
        "jupyter_environments": {
            "default": {
                "description": "Operating system (default)",
                "path": "/path/to/jupyter/env/for/partition_3/bin/",
            },
            "new-x86": {
                "description": "New environment x86 (latest)",
                "path": "/new-x86/jupyter_env_path/bin/",
            },
        },
    },
}

# Uncomment the following to customize the options_form template
# c.JupyterHub.template_paths = [os.path.join(os.path.dirname(__file__), "templates")]

# Mock SLURM sinfo command for the demo
SINFO_OUTPUT = """unused 5/35/0/40 28+ 121/1191/0/1312 (null) 196000+ infinite
partition_1 2/46/0/48 35+ 38/1642/0/1680 (null) 196000+ 1-00:00:00
partition_2 2/5/0/7 128 116/780/0/896 gpu:GPU-MODEL:2 512000 12:00:00
partition_3 4/24/0/28 40 114/1006/0/1120 (null) 310000 4:00:00
other_mixed 3/7/0/10 64 152/488/0/640 gpu:OTHER-GPU:2(S:0-1) 455000+ 7-00:00:00
other_mixed 6/86/0/94 28+ 153/3583/0/3736 (null) 196000+ 7-00:00:00
"""
c.MOSlurmSpawner.slurm_info_cmd = f'echo "{SINFO_OUTPUT}"'

# Batchspawner: Do not run sudo for the demo
c.BatchSpawnerBase.exec_prefix = ""

# JupyterHub basic config
c.JupyterHub.ip = "127.0.0.1"
c.JupyterHub.hub_ip = "127.0.0.1"
c.JupyterHub.port = 8000
