from tornado.web import StaticFileHandler as _StaticFileHandler

from .utils import local_path as _local_path
from .spawner import MOSlurmSpawner
from .auth import KeycloakAuthenticator  # noqa: F401

version = "1.0.0"

STATIC_FORM_REGEX = r"/form/(.*)"
STATIC_FORM_PATH = _local_path("form")


def set_config(c):
    """Set JupyterHub config for using this SLURM Spawner."""
    c.JupyterHub.extra_handlers = [
        (STATIC_FORM_REGEX, _StaticFileHandler, {"path": STATIC_FORM_PATH})
    ]
    c.JupyterHub.spawner_class = MOSlurmSpawner
