import time
import msal
from typing import Dict, Optional, Any, Tuple
import json
import requests
import jwt
from jwt.algorithms import RSAAlgorithm
from app.utils.azure_config import AUTHORITY, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, TENANT_ID, JWKS_ENDPOINT


class MSALAuthService:

    def __init__(self):
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=CLIENT_ID,
            client_credential=CLIENT_SECRET,
            authority=AUTHORITY
        )
        self.jwks_cache = None
        self.jwks_last_updated = 0

    def _get_jwks(self):
        # Cache JWKS for 24 hours (86400 seconds)
        current_time = int(time.time())
        if self.jwks_cache is None or current_time - self.jwks_last_updated > 86400:
            response = requests.get(JWKS_ENDPOINT)
            self.jwks_cache = response.json()
            self.jwks_last_updated = current_time
        return self.jwks_cache

    def get_auth_url(self, state: Optional[str] = None) -> str:
        client_scopes = []
        auth_params = {
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
        }
        if state:
            auth_params["state"] = state

        return self.msal_app.get_authorization_request_url(
            client_scopes,
            **auth_params
        )

    def get_token_from_code(self, auth_code: str) -> Dict[str, Any]:
        client_scopes = []
        result = self.msal_app.acquire_token_by_authorization_code(
            code=auth_code,
            scopes=client_scopes,
            redirect_uri=REDIRECT_URI
        )
        if "error" in result:
            error_msg = result.get('error_description', 'Unknown error')
            raise Exception(f"Error getting token: {error_msg}")
        return result

    def validate_token(self, id_token: str) -> Tuple[bool, Dict[str, Any]]:
        try:
            header = jwt.get_unverified_header(id_token)
            kid = header.get('kid')
            if not kid:
                raise jwt.InvalidTokenError("no kid in id_token")

            jwks = self._get_jwks()
            key = None
            for jwk in jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwk
                    break
            if not key:
                raise jwt.InvalidTokenError("kid does not match")

            public_key = RSAAlgorithm.from_jwk(json.dumps(key))
            claims = jwt.decode(
                id_token,
                public_key,
                algorithms=['RS256'],
                audience=CLIENT_ID,
                options={"verify_exp": True}
            )

            if claims.get("tid") != TENANT_ID:
                raise jwt.InvalidTokenError("tenant_id mismatch in token")

            return claims

        except Exception as e:
            raise jwt.InvalidTokenError(e.__cause__)
