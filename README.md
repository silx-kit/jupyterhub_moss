# jupyterhub_moss: JupyterHub MOdular Slurm Spawner

**jupyterhub_moss** is a Python package that provides:
- A [JupyterHub](https://jupyterhub.readthedocs.io/) [Slurm](https://slurm.schedmd.com/) Spawner that can be configured by [setting the available partitions](#partition-settings). It is an extension of [`batchspawner.SlurmSpawner`](https://github.com/jupyterhub/batchspawner).
- An associated [spawn page](#spawn-page) that changes according to the partitions set in the Spawner and allows the user to select Slurm resources to use.

<img style="margin:auto" src=https://user-images.githubusercontent.com/42204205/116039349-e85bb300-a66a-11eb-9056-7392cf7a7ba9.png width="50%">


## Install

`pip install jupyterhub_moss`

## Usage

### Partition settings

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

The spawn page (available at `/hub/spawn`) will be generated according to the partition settings. For example, this is the spawn page generated for the partition settings above:

<img style="margin:1rem auto" src=https://user-images.githubusercontent.com/42204205/116039349-e85bb300-a66a-11eb-9056-7392cf7a7ba9.png width="50%">

This spawn page is separated in two tabs: a _Simple_ and an _Advanced_ tab. On the _Simple_ tab, the user can choose between the partitions set though `simple: True` (`partition_1` and `partition_2` in this case), choose to take a minimum, a half or a maximum number of cores and choose the job duration. The available resources are checked using `sinfo` and displayed on the table below. Clicking on the **Start** button will request the job.

The spawn page adapts to the chosen partition. This is the page when selecting the `partition_2`:
<img style="margin:1rem auto" src=https://user-images.githubusercontent.com/42204205/116039610-3bce0100-a66b-11eb-8413-73423a7a017e.png width="50%">

As the maximum number of cores is different, the CPUs row change accordingly. Also, as `gpu` was set for `partition_2`, a new button row appears to enable GPU requests.

The _Advanced_ tab allows finer control on the requested resources.

<img style="margin:1rem auto" src=https://user-images.githubusercontent.com/42204205/116039563-2c4eb800-a66b-11eb-81d9-79122ec771fa.png width="50%">

The user can select any partition (`partition_3` is added in this case) and the table of available resources reflects this. The user can also choose any number of nodes (with the max given by `max_nprocs`), of GPUs (max: `max_gpus`) and have more control on the job duration (max: `max_runtime`).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits:
We would like acknowledge the following ressources that served as base for this project and thank their authors:
 - This [gist](https://gist.github.com/zonca/aaed55502c4b16535fe947791d02ac32) for the initial spawner implementation.
 - The [DESY JupyterHub Slurm service](https://confluence.desy.de/display/IS/JupyterHub+on+Maxwell) for the table of available resources.
 - The [TUDresden JupyterHub Slurm service](https://doc.zih.tu-dresden.de/hpc-wiki/bin/view/Compendium/JupyterHub) for the spawn page design.
