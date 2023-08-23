import json
import re
from unittest import mock

import pytest

from .utils import MOSlurmSpawnerMock, request


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
                        "description": "Virtual environment",
                        "path": "/default/jupyter_env_path/bin/",
                        "add_to_path": True,
                    },
                    "modules": {
                        "description": "Environment modules",
                        "modules": "JupyterLab/3.6.0",
                        "add_to_path": False,
                    },
                },
            },
        }


async def test_spawn_page(app):
    """Test display of spawn page and check embedded SLURM resources info"""
    with mock.patch.dict(app.users.settings, {"spawner_class": MOSSMockSimple}):
        cookies = await app.login_user("jones")
        r = await request(app, "GET", "spawn", cookies=cookies)

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
                        "description": "Virtual environment",
                        "path": "/default/jupyter_env_path/bin/",
                        "modules": "",
                        "add_to_path": True,
                    },
                    "modules": {
                        "description": "Environment modules",
                        "path": "",
                        "modules": "JupyterLab/3.6.0",
                        "add_to_path": False,
                    },
                },
            }
        }
        assert ref_partitions_info == slurm_data["partitions"]


def assert_environment(spawner, partition: str, environment_id: str):
    """Assert that spawner is set to use given partition and environment"""
    expected_environment = spawner.partitions[partition]["jupyter_environments"][
        environment_id
    ]

    user_options = spawner.user_options
    assert user_options["partition"] == partition
    assert user_options["environment_id"] == environment_id
    assert user_options["environment_path"] == expected_environment["path"]
    assert user_options["environment_modules"] == expected_environment["modules"]


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_spawn_simple(app, method):
    """Test spawning with simple params"""
    with mock.patch.dict(app.users.settings, {"spawner_class": MOSSMockSimple}):
        cookies = await app.login_user("jones")
        r = await request(
            app,
            method,
            "spawn",
            data={"partition": "partition_1", "nprocs": 4},
            cookies=cookies,
        )

        spawner = app.users["jones"].get_spawner()
        assert_environment(spawner, "partition_1", "default")
        assert r.status_code == 200
        assert "/hub/spawn-pending" in r.url


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_spawn_with_environment_id(app, method):
    """Test spawning by giving only environment id"""
    with mock.patch.dict(app.users.settings, {"spawner_class": MOSSMockSimple}):
        cookies = await app.login_user("jones")
        r = await request(
            app,
            method,
            "spawn",
            data={"partition": "partition_1", "environment_id": "modules"},
            cookies=cookies,
        )

        spawner = app.users["jones"].get_spawner()
        assert_environment(spawner, "partition_1", "modules")

        assert r.status_code == 200
        assert "/hub/spawn-pending" in r.url
