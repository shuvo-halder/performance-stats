from fastapi import Security, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer(auto_error=False)


async def verify_api_key(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify API key from Authorization header or custom header."""
    api_key = None

    # Check Authorization header (Bearer token)
    if credentials:
        api_key = credentials.credentials

    # Check custom header
    if not api_key:
        api_key = request.headers.get(settings.api_key_name)

    # Check query parameter
    if not api_key:
        api_key = request.query_params.get("api_key")

    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True