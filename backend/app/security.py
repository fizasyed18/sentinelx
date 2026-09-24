from fastapi import Header, HTTPException, status

from app.config import settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Simple shared-secret auth for mutating endpoints.

    In a production deployment this would be replaced with OAuth2 /
    per-service credentials, but demonstrates secure-by-default handling of
    write operations (event ingestion, remediation approval).
    """
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-API-Key header")
