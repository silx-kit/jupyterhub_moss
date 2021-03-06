# Contributing to jupyterlab_moss

## Development

The dependencies needed to contribute can be installed by

```
pip install .[dev]
```

### Linting

[flake8](https://flake8.pycqa.org/en/latest/index.html) is used to lint the
code. The config is located in [setup.cfg](./setup.cfg). Linting can be run
using

```
flake8 .
```

### Formatting

[black](https://black.readthedocs.io/en/stable/) is used to format Python files.
Most editors can be configured to format on save but you can run the formatting
manually using

```
black .
```

### CI

The CI will check that the lint check passes and that all files are correctly
formatted (using `black --check .`). Before commiting, be sure to run `flake8`
and `black` to ensure CI passes.

## Generate the spawn page locally

Even if you do not have access to a Slurm cluster, it is possible to mock the
Slurm info to generate the spawn page for a local development JupyterHub
instance. For instance, see the
[`demo_jupyterhub_conf.py`](demo_jupyterhub_conf.py) file which which you can
use to start jupyterhub using jupyterhub_moss:

```
jupyterhub -f demo_jupyterhub_conf.py
```

## Release

### Build package from source

From the project directory, run: `python3 -m build` to generate the wheel and
tarball in `dist/`

### Make a new release

First, be sure to be up to date with the remote `main` and that your working
tree is clean. Then, run `bumpversion`:

```
bumpversion [major|minor|patch]
```

This will bump the version, commit the result and tag the current HEAD. You can
then push the commit and the tag to the repo:

```
git push && git push --tags
```

This will trigger a CI job that should release automatically the package on
PyPI.
