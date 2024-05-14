from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode
from jupyterhub.tests.utils import async_requests, public_host
from jupyterhub.utils import url_path_join
from traitlets import Unicode, default

from jupyterhub_moss import MOSlurmSpawner


def request(
    app,
    method: str,
    path: str,
    data: Optional[dict] = None,
    cookies: Optional[dict] = None,
    **kwargs,
):
    """Send a GET or POST request on the hub

    Similar to jupyterhub.tests.utils.get_page
    """
    if data is None:
        data = {}

    base_url = url_path_join(public_host(app), app.hub.base_url)
    url = url_path_join(base_url, path)

    if method == "POST":
        if cookies is not None and "_xsrf" in cookies:
            data["_xsrf"] = cookies["_xsrf"]
        return async_requests.post(url, data=data, cookies=cookies, **kwargs)

    assert method == "GET"
    if data:  # Convert data to query string
        url += f"?{urlencode(data)}"
    return async_requests.get(url, cookies=cookies, **kwargs)


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
