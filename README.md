# jupyterhub_moss: JupyterHub MOdular Slurm Spawner

This package extends [`batchspawner.SlurmSpawner`](https://github.com/jupyterhub/batchspawner) to provide a [JupyterHub](https://jupyterhub.readthedocs.io/) [Slurm](https://slurm.schedmd.com/) Spawner with a spawn page allowing to select Slurm resources to use.

## Example

`jupyterhub_conf.py`:

```python
import batchspawner
import jupyterhub_moss

c = get_config()

# Init JupyterHub configuration to use this spawner
jupyterhub_moss.set_config(c)

# Partition descriptions
c.MOSlurmSpawner.partitions = {
    "partition_1": {  # Partition name
        "description": "Partition 1",      # Displayed description
        "architecture": "x86_86",          # Nodes architecture
        "gpu": None,                       # --gres= template to use for requesting GPUs
        "simple": True,                    # True to show in Simple tab
        "venv": "/jupyter_env_path/bin/",  # Path to Python environment bin/ used to start jupyter on the Slurm nodes 
        "max_ngpus": 0,                    # Maximum number of GPUs per node
        "max_nprocs": 28,                  # Maximum number of CPUs per node
    },
    "partition_2": {
        "description": "Partition 2",
        "architecture": "ppc64le",
        "gpu": "gpu:V100-SXM2-32GB:{}",
        "simple": True,
        "venv": "/path/to/jupyter/env/for/partition_2/bin/",
        "max_ngpus": 2,
        "max_nprocs": 128,
    },
    "partition_3": {
        "description": "Partition 3",
        "architecture": "x86_86",
        "gpu": None,
        "simple": False,
        "venv": "/path/to/jupyter/env/for/partition_3/bin/",
        "max_ngpus": 0,
        "max_nprocs": 28,
    },
}
```

## Build package from source

Pre-requisite: `pip install build`

From the project directory, run: `python3 -m build` to generate the wheel and tarball in `dist/`
