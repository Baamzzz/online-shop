"""Google OAuth 2.0 / OpenID Connect client configuration."""
from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    # Google publishes its endpoints and signing keys here, so we don't hard-code them
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        # PKCE: protects the login code from being intercepted and reused
        "code_challenge_method": "S256",
    },
)