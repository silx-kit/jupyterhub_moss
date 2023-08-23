# jupyterhub_moss: JupyterHub MOdular Slurm Spawner

**jupyterhub_moss** is a Python package that provides:

- A [JupyterHub](https://jupyterhub.readthedocs.io/)
  [Slurm](https://slurm.schedmd.com/) Spawner that can be configured by
  [setting the available partitions](#partition-settings). It is an extension of
  [`batchspawner.SlurmSpawner`](https://github.com/jupyterhub/batchspawner).
- An associated [spawn page](#spawn-page) that changes according to the
  partitions set in the Spawner and allows the user to select Slurm resources to
  use.

<img style="margin:auto" src=https://user-images.githubusercontent.com/9449698/215526389-2ef5ac32-5d50-49de-aa5f-46972feaccf1.png width="50%">

## Install

`pip install jupyterhub_moss`

## Usage

### Partition settings

To use **jupyterhub_moss**, you need first a working
[JupyterHub](https://jupyterhub.readthedocs.io/) instance. **jupyterhub_moss**
needs then to be imported in
[your JupyterHub configuration file](https://jupyterhub.readthedocs.io/en/stable/getting-started/config-basics.html)
(usually named `jupyterhub_conf.py`):

```python
import batchspawner
import jupyterhub_moss

c = get_config()

# ...your config

# Init JupyterHub configuration to use this spawner
jupyterhub_moss.set_config(c)
```

Once **jupyterhub_moss** is set up, you can define the partitions available on
Slurm by setting `c.MOSlurmSpawner.partitions` in the same file:

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
        "jupyter_environments": {
            "default": {                   # Jupyter environment identifier, at least "path" or "modules" is mandatory
                "description": "Default",  # Text displayed for this environment select option
                "path": "/env/path/bin/",  # Path to Python environment bin/ used to start Jupyter server on the Slurm nodes
                "modules": "",             # Space separated list of environment modules to load before starting Jupyter server
                "add_to_path": True,       # Toggle adding the environment to shell PATH (optional, default: True)
                "prologue": "",            # Shell commands to execute before starting the Jupyter server (optional, default: "")
            },
        },
    },
    "partition_2": {
        "architecture": "ppc64le",
        "description": "Partition 2",
        "gpu": "gpu:V100-SXM2-32GB:{}",
        "max_ngpus": 2,
        "max_nprocs": 128,
        "max_runtime": 1*3600,
        "simple": True,
        "jupyter_environments": {
            "default": {
                "description": "Default",
                "path": "",
                "modules": "JupyterLab/3.6.0",
                "add_to_path": True,
                "prologue": "echo 'Starting default environment'",
            },
        },
    },
    "partition_3": {
        "architecture": "x86_86",
        "description": "Partition 3",
        "gpu": None,
        "max_ngpus": 0,
        "max_nprocs": 28,
        "max_runtime": 12*3600,
        "simple": False,
        "jupyter_environments": {
            "default": {
                "description": "Partition 3 default",
                "path": "/path/to/jupyter/env/for/partition_3/bin/",
                "modules": "JupyterLab/3.6.0",
                "add_to_path": True,
                "prologue": "echo 'Starting default environment'",
        },
    },
}
```

For a minimalistic working demo, check the
[`demo/jupyterhub_conf.py`](demo/jupyterhub_conf.py) config file.

### Field descriptions

- `architecture`: The architecture of the partition. This is only cosmetic and
  will be used to generate subtitles in the spawn page.
- `description`: The description of the partition. This is only cosmetic and
  will be used to generate subtitles in the spawn page.
- `gpu`: [Optional] A template string that will be used to request GPU resources
  through `--gres`. The template should therefore include a `{}` that will be
  replaced by the number of requested GPU **and** follow the format expected by
  `--gres`. If no GPU is available for this partition, set to `""`. It is
  retrieved from SLURM if not provided.
- `max_ngpus`: [Optional] The maximum number of GPU that can be requested for
  this partition. The spawn page will use this to generate appropriate bounds
  for the user inputs. If no GPU is available for this partition, set to `0`. It
  is retrieved from SLURM if not provided.
- `max_nprocs`: [Optional] The maximum number of processors that can be
  requested for this partition. The spawn page will use this to generate
  appropriate bounds for the user inputs. It is retrieved from SLURM if not
  provided.
- `max_runtime`: [Optional] The maximum job runtime for this partition in
  seconds. It should be of minimum 1 hour as the _Simple_ tab only display
  buttons for runtimes greater than 1 hour. It is retrieved from SLURM if not
  provided.
- `simple`: Whether the partition should be available in the _Simple_ tab. The
  spawn page that will be generated is organized in a two tabs: a _Simple_ tab
  with minimal settings that will be enough for most users and an _Advanced_ tab
  where almost all Slurm job settings can be set. Some partitions can be hidden
  from the _Simple_ tab with setting `simple` to `False`.
- `jupyter_environments`: Mapping of identifer name to information about Python
  environment used to run Jupyter on the Slurm nodes. Either `path` or `modules`
  (or both) should be defined. This information is a mapping containing:
  - `description`: Text used for display in the selection options.
  - `path`: The path to a Python environment bin/ used to start jupyter on the
    Slurm nodes. **jupyterhub_moss** needs that a virtual (or conda) environment
    is used to start Jupyter. This path can be changed according to the
    partitions.
  - `modules`: Space separated list of environment modules to load before
    starting the Jupyter server. Environment modules will be loaded with the
    `module` command.
  - `add_to_path`: Whether or not to prepend the environment `path` to shell
    `PATH`.
  - `prologue`: Shell commands to execute on the Slurm node before starting the
    Jupyter single-user server. This can be used to run, e.g.,
    `module load <module>`. By default no command is run.

### Spawn page

The spawn page (available at `/hub/spawn`) will be generated according to the
partition settings. For example, this is the spawn page generated for the
partition settings above:

<img style="margin:1rem auto" src=https://user-images.githubusercontent.com/9449698/215526389-2ef5ac32-5d50-49de-aa5f-46972feaccf1.png width="50%">

This spawn page is separated in two tabs: a _Simple_ and an _Advanced_ tab. On
the _Simple_ tab, the user can choose between the partitions set though
`simple: True` (`partition_1` and `partition_2` in this case), choose to take a
minimum, a half or a maximum number of cores and choose the job duration. The
available resources are checked using `sinfo` and displayed on the table below.
Clicking on the **Start** button will request the job.

The spawn page adapts to the chosen partition. This is the page when selecting
the `partition_2`:

<img style="margin:1rem auto" src=https://user-images.githubusercontent.com/9449698/215526553-4ba57510-efac-4a28-a576-ef81ff9ec2f5.png width="50%">

As the maximum number of cores is different, the CPUs row change accordingly.
Also, as `gpu` was set for `partition_2`, a new button row appears to enable GPU
requests.

The _Advanced_ tab allows finer control on the requested resources.

<img style="margin:1rem auto" src=https://user-images.githubusercontent.com/9449698/262627623-91bd63de-6374-47d4-9064-d1a6e3d56411.png width="50%">

The user can select any partition (`partition_3` is added in this case) and the
table of available resources reflects this. The user can also choose any number
of nodes (with the max given by `max_nprocs`), of GPUs (max: `max_gpus`) and
have more control on the job duration (max: `max_runtime`).

### Spawn through URL

It is also possible to pass the spawning options as query arguments to the spawn
URL: `https://<server:port>/hub/spawn`. For example,
`https://<server:port>/hub/spawn?partition=partition_1&nprocs=4` will directly
spawn a Jupyter server on `partition_1` with 4 cores allocated.

The following query argument is required:

- `partition`: The name of the SLURM partition to use.

The following optional query arguments are available:

- SLURM configuration:

  - `memory`: Total amount of memory per node
    ([`--mem`](https://slurm.schedmd.com/sbatch.html#OPT_mem))
  - `ngpus`: Number of GPUs
    ([`--gres:<gpu>:`](https://slurm.schedmd.com/sbatch.html#OPT_gres))
  - `nprocs`: Number of CPUs per task
    ([`--cpus-per-task`](https://slurm.schedmd.com/sbatch.html#OPT_cpus-per-task))
  - `options`: Extra SLURM options
  - `output`: Set to `true` to save logs to `slurm-*.out` files.
  - `reservation`: SLURM reservation name
    ([`--reservation`](https://slurm.schedmd.com/sbatch.html#OPT_reservation))
  - `runtime`: Job duration as hh:mm:ss
    ([`--time`](https://slurm.schedmd.com/sbatch.html#OPT_time))

- Jupyter(Lab) configuration:

  - `default_url`: The URL to open the Jupyter environment with: use `/lab` to
    start [JupyterLab](https://jupyterlab.readthedocs.io/en/stable/) or use
    [JupyterLab URLs](https://jupyterlab.readthedocs.io/en/stable/user/urls.html)
  - `environment_id`: Name of the Python environment defined in the
    configuration used to start Jupyter
  - `environment_path`: Path to the Python environment bin/ used to start
    Jupyter
  - `environment_modules`: Space-separated list of
    [environment module](https://modules.sourceforge.net/) names to load before
    starting Jupyter
  - `root_dir`: The path of the "root" folder browsable from Jupyter(Lab)
    (user's home directory if not provided)

To use a Jupyter environment defined in the configuration, only provide its
`environment_id`, for example:
`https://<server:port>/hub/spawn?partition=partition_1&environment_id=default`.

To use a custom Jupyter environment, instead provide the corresponding
`environment_path` and/or `environment_modules`, for example:

- `https://<server:port>/hub/spawn?partition=partition_1&environment_path=/path/to/jupyter/bin`,
  or
- `https://<server:port>/hub/spawn?partition=partition_1&environment_modules=myjupytermodule`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits:

We would like acknowledge the following ressources that served as base for this
project and thank their authors:

- This [gist](https://gist.github.com/zonca/aaed55502c4b16535fe947791d02ac32)
  for the initial spawner implementation.
- The
  [DESY JupyterHub Slurm service](https://confluence.desy.de/display/IS/JupyterHub+on+Maxwell)
  for the table of available resources.
- The
  [TUDresden JupyterHub Slurm service](https://doc.zih.tu-dresden.de/hpc-wiki/bin/view/Compendium/JupyterHub)
  for the spawn page design.
