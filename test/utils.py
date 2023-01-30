from jupyterhub.tests.utils import async_requests, public_host
from jupyterhub.utils import url_path_join
from traitlets import Unicode, default

from jupyterhub_moss import MOSlurmSpawner


def post_request(path, app, **kwargs):
    """Send a POST request on the hub

    Similar to jupyterhub.tests.utils.get_page
    """
    base_url = url_path_join(public_host(app), app.hub.base_url)
    return async_requests.post(url_path_join(base_url, path), **kwargs)


class MOSlurmSpawnerMock(MOSlurmSpawner):
    """MOSlurmSpawner with some overrides to mock some features.

    Adapted from jupyterhub.tests.mocking.MockSpawner and
    batchspawner.tests.test_spawner.BatchDummy
    """

    exec_prefix = Unicode("")
    batch_submit_cmd = Unicode("cat > /dev/null; sleep 1")
    batch_query_cmd = Unicode("echo PENDING")
    batch_cancel_cmd = Unicode("echo STOP")

    req_homedir = Unicode(help="The home directory for the user")

    @default("req_homedir")
    def _default_req_homedir(self):
        return f"/tmp/jupyterhub_moss_tests/{self.user.name}"

    def user_env(self, env):
        env["USER"] = self.user.name
        env["HOME"] = self.req_homedir
        env["SHELL"] = "/bin/bash"
        return env
