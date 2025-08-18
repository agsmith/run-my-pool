import os
import time
import requests
from typing import Dict, Any, Optional


class APIService:
    """Service for making external API calls with token handling."""
    def __init__(self):
        self.sat_url = os.environ.get("SAT_URL")
        self.pbi_url = os.environ.get("PBI_URL")
        self.client_id = os.environ.get("SAT_CLIENT_ID")
        self.client_secret = os.environ.get("SAT_CLIENT_SECRET")
        self._token_cache = {"access_token": None, "expires_at": 0}

    def get_access_token(self) -> str:
        """
        Get a valid access token, fetching a new one if necessary.
        """
        now = int(time.time())
        token = self._token_cache["access_token"]
        expires = self._token_cache["expires_at"]
        if token and expires > now + 60:
            return token

        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": self.client_id,
            "X-Client-Secret": self.client_secret
        }
        resp = requests.post(self.sat_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        self._token_cache["access_token"] = data["access_token"]
        # Calculate token expiry time based on expires_in value
        expires_in = int(data.get("expires_in", 3600))
        self._token_cache["expires_at"] = now + expires_in
        return data["access_token"]

    def get_profile_data(
        self,
        customer_id: Optional[str] = None,
        billing_arrangement_id: Optional[str] = None
    ) -> Dict[str, Any]:
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }
        payload = {}
        if customer_id:
            payload["customerId"] = customer_id
        if billing_arrangement_id:
            payload["billingArrangementID"] = billing_arrangement_id
        
        resp = requests.post(self.pbi_url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
