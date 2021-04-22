# Contributing to jupyterlab_moss

The dependencies needed to contribute can be installed by

```
pip install .[dev]
```

## Linting

[flake8](https://flake8.pycqa.org/en/latest/index.html) is used to lint the code. The config is located in [setup.cfg](./setup.cfg). Linting can be run using

```
flake8 .
```

## Formatting

[black](https://black.readthedocs.io/en/stable/) is used to format Python files. Most editors can be configured to format on save but you can run the formatting manually using

```
black .
```

## CI

The CI will check that the lint check passes and that all files are correctly formatted (using `black --check .`). Before commiting, be sure to run `flake8` and `black` to ensure CI passes.


## Build package from source

From the project directory, run: `python3 -m build` to generate the wheel and tarball in `dist/`
