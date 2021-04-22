from oauthenticator.generic import GenericOAuthenticator
from jupyterhub.handlers.login import LogoutHandler
from tornado.httputil import url_concat
from traitlets import Unicode


class KeycloakLogoutHandler(LogoutHandler):
    """Logout handler for keycloak"""

    async def render_logout_page(self):
        params = {
            "redirect_uri": "%s://%s%s"
            % (self.request.protocol, self.request.host, self.hub.server.base_url),
        }
        self.redirect(
            url_concat(self.authenticator.keycloak_logout_url, params), permanent=False
        )


class KeycloakAuthenticator(GenericOAuthenticator):
    """Authenticator handle keycloak logout"""

    keycloak_logout_url = Unicode(config=True, help="The keycloak logout URL")

    def get_handlers(self, app):
        return super().get_handlers(app) + [(r"/logout", KeycloakLogoutHandler)]
