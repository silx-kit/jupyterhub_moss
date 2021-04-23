# jupyterhub_moss: JupyterHub MOdular Slurm Spawner

**jupyterhub_moss** is a Python package that provides:
- A [JupyterHub](https://jupyterhub.readthedocs.io/) [Slurm](https://slurm.schedmd.com/) Spawner that can be configured by setting the available partitions. It is an extension of [`batchspawner.SlurmSpawner`](https://github.com/jupyterhub/batchspawner).
- An associated spawn page that changes according to the partitions set in the Spawner and allows the user to select Slurm resources to use.

## Install

`pip install jupyterhub_moss`

## Usage

To use **jupyterhub_moss**, you need first a working [JupyterHub](https://jupyterhub.readthedocs.io/) instance. **jupyterhub_moss** needs then to be imported in [your JupyterHub configuration file](https://jupyterhub.readthedocs.io/en/stable/getting-started/config-basics.html) (usually named `jupyterhub_conf.py`):

```python
import batchspawner
import jupyterhub_moss

c = get_config()

# ...your config 

# Init JupyterHub configuration to use this spawner
jupyterhub_moss.set_config(c)
```

Once **jupyterhub_moss** is set up, you can define the partitions available on Slurm by setting `c.MOSlurmSpawner.partitions` in the same file:

```python
# ...

# Partition descriptions
c.MOSlurmSpawner.partitions = {
    "partition_1": {  # Partition name     # (See description of fields below for more info)
        "architecture": "x86_86",          # Nodes architecture
        "description": "Partition 1",      # Displayed description
        "gpu": None,                       # --gres= template to use for requesting GPUs
        "max_ngpus": 0,                    # Maximum number of GPUs per node
        "max_nprocs": 28,                  # Maximum number of CPUs per node
        "max_runtime": 12*3600,            # Maximum time limit in seconds (Must be at least 1hour)
        "simple": True,                    # True to show in Simple tab
        "venv": "/jupyter_env_path/bin/",  # Path to Python environment bin/ used to start jupyter on the Slurm nodes 
    },
    "partition_2": {
        "architecture": "ppc64le",
        "description": "Partition 2",
        "gpu": "gpu:V100-SXM2-32GB:{}",
        "max_ngpus": 2,
        "max_nprocs": 128,
        "max_runtime": 1*3600,
        "simple": True,
        "venv": "/path/to/jupyter/env/for/partition_2/bin/",
    },
    "partition_3": {
        "architecture": "x86_86",
        "description": "Partition 3",
        "gpu": None,
        "max_ngpus": 0,
        "max_nprocs": 28,
        "max_runtime": 12*3600,
        "simple": False,
        "venv": "/path/to/jupyter/env/for/partition_3/bin/",
    },
}
```

### Field descriptions
- `architecture`: The architecture of the partition. This is only cosmetic and will be used to generate subtitles in the spawn page.
- `description`: The description of the partition. This is only cosmetic and will be used to generate subtitles in the spawn page.
- `gpu`: A template string that will be used to request GPU resources through `--gres`. The template should therefore include a `{}` that will be replaced by the number of requested GPU **and** follow the format expected by `--gres`. If no GPU is available for this partition, set to `None`.
- `max_ngpus`: The maximum number of GPU that can be requested for this partition. The spawn page will use this to generate appropriate bounds for the user inputs. If no GPU is available for this partition, set to `0`.
- `max_nprocs`: The maximum number of processors that can be requested for this partition. The spawn page will use this to generate appropriate bounds for the user inputs.
- `max_runtime`: The maximum job runtime for this partition in seconds. It should be of minimum 1 hour as the _Simple_ tab only display buttons for runtimes greater than 1 hour.
- `simple`: Whether the partition should be available in the _Simple_ tab. The spawn page that will be generated is organized in a two tabs: a _Simple_ tab with minimal settings that will be enough for most users and an _Advanced_ tab where almost all Slurm job settings can be set. Some partitions can be hidden from the _Simple_ tab with setting `simple` to `False`.
- `venv`: Path to Python environment bin/ used to start jupyter on the Slurm nodes. **jupyterhub_moss** expects that a virtual environment is used to start jupyter. The path of this venv is set in the `venv` field and can be changed according to the partition. If there is only one venv, simply set the same path to all partitions.

### Spawn page

`<To be added...>`