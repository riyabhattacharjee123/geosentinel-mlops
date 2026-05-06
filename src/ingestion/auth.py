# src/ingestion/auth.py
"""
Handles OAuth2 token generation for the Copernicus Data Space Ecosystem.
Tokens expire after ~600 seconds, so always call get_access_token() fresh.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)

def get_access_token() -> str:
    """Fetch a short-lived Bearer token using username + password."""
    response = requests.post(
        url=CDSE_TOKEN_URL,
        data={
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": os.getenv("CDSE_USERNAME"),
            "password": os.getenv("CDSE_PASSWORD"),
        },
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    print("✅ Access token generated successfully.")
    return token