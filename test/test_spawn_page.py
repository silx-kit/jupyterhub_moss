import json
import re
from unittest import mock

from jupyterhub.tests.utils import get_page

from .utils import MOSlurmSpawnerMock, post_request


class MOSSMockSimple(MOSlurmSpawnerMock):
    """MOSlurmSpawner with mocks and a simple configuration"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Partition name, nnodes (allocated/idle/other/total), ncores_per_node,
        # ncores (allocated/idle/other/total), gpu, memory, timelimit
        self.slurm_info_cmd = (
            'echo "partition_1 2/46/0/48 35+ 38/1642/0/1680 (null) 196000+ 1-00:00:00"'
        )

        # Set partitions here so that validation is run
        # Minimalistic default partitions config
        self.partitions = {
            "partition_1": {
                "architecture": "x86_86",
                "description": "Partition 1",
                "simple": True,
                "jupyter_environments": {
                    "default": {
                        "path": "/default/jupyter_env_path/bin/",
                        "description": "default",
                        "add_to_path": True,
                    },
                },
            },
        }


async def test_spawn_page(app):
    """Test display of spawn page and check embedded SLURM resources info"""
    with mock.patch.dict(app.users.settings, {"spawner_class": MOSSMockSimple}):
        cookies = await app.login_user("jones")
        r = await get_page("spawn", app, cookies=cookies)

        assert r.status_code == 200
        assert r.url.endswith("/spawn")

        match = re.search(r"window.SLURM_DATA = JSON.parse\('(?P<json>.*)'\)", r.text)
        assert match is not None
        slurm_data = json.loads(match.group("json"))

        ref_partitions_info = {
            "partition_1": {
                "nnodes_idle": 46,
                "nnodes_total": 48,
                "ncores_total": 1680,
                "ncores_idle": 1642,
                "max_nprocs": 35,
                "max_mem": 196000,
                "gpu": "",
                "max_ngpus": 0,
                "max_runtime": 86400,
                "architecture": "x86_86",
                "description": "Partition 1",
                "simple": True,
                "jupyter_environments": {
                    "default": {
                        "path": "/default/jupyter_env_path/bin/",
                        "description": "default",
                        "add_to_path": True,
                    },
                },
            }
        }
        assert ref_partitions_info == slurm_data["partitions"]


async def test_spawn_from_get_query(app):
    """Test spawning through a GET query"""
    with mock.patch.dict(app.users.settings, {"spawner_class": MOSSMockSimple}):
        cookies = await app.login_user("jones")
        r = await get_page("spawn?partition=partition_1&nprocs=4", app, cookies=cookies)

        assert r.status_code == 200
        assert "/hub/spawn-pending" in r.url


async def test_spawn_from_post_request(app):
    """Test spawning through a POST request"""
    with mock.patch.dict(app.users.settings, {"spawner_class": MOSSMockSimple}):
        cookies = await app.login_user("jones")
        r = await post_request(
            "spawn",
            app,
            cookies=cookies,
            data={"partition": "partition_1", "nprocs": 4},
        )

        assert r.status_code == 200
        assert "/hub/spawn-pending" in r.url
