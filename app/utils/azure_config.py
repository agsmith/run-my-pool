import os

CLIENT_ID = os.getenv("SSO_CLIENT_ID")
CLIENT_SECRET = os.getenv("SSO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SSO_REDIRECT_URI")

TENANT_ID = os.getenv("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORITY_V2 = f"{AUTHORITY}/v2.0"

AUTHORIZE_ENDPOINT = f"{AUTHORITY_V2}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"{AUTHORITY_V2}/oauth2/v2.0/token"
METADATA_ENDPOINT = f"{AUTHORITY_V2}/.well-known/openid-configuration"
JWKS_ENDPOINT = f"{AUTHORITY}/discovery/v2.0/keys"
SCOPES = ["openid", "profile", "email"]
