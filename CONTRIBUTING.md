# Contributing to jupyterlab_moss

## Development

The dependencies needed to contribute can be installed by

```
pip install .[dev]
```

# Formatting/Linting

From the source directory:

- Format code with [black](https://black.readthedocs.io/):

  ```
  black .
  ```

- Sort imports with [isort](https://pycqa.github.io/isort/):

  ```
  isort .
  ```

- Check code with [flake8](https://flake8.pycqa.org/):

  ```
  flake8
  ```

- Check code with [bandit](https://bandit.readthedocs.io/) security linter:

  ```
  bandit -c pyproject.toml -r .
  ```

- Check typing with [mypy](https://mypy.readthedocs.io):
  ```
  mypy
  ```

### Testing

[pytest](https://docs.pytest.org/en/latest/) is used to run the tests. The
config is located in `pyproject.toml`. Tests can be run using:

```
python -m pytest
```

Note: This is different from calling `pytest`, see
[Invoking pytest versus python -m pytest](https://docs.pytest.org/en/latest/explanation/pythonpath.html#invoking-pytest-versus-python-m-pytest).

## Generate the spawn page locally

Even if you do not have access to a Slurm cluster, it is possible to mock the
Slurm info to generate the spawn page for a local development JupyterHub
instance. For instance, see the
[`demo/jupyterhub_conf.py`](demo/jupyterhub_conf.py) file which which you can
use to start jupyterhub using jupyterhub_moss:

```
jupyterhub -f demo/jupyterhub_conf.py
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
