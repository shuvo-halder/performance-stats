from fastapi import HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import secrets
import bcrypt

from app.config import settings
from app.database import get_session, User, ApiKey


# ── Password Hashing (direct bcrypt - no passlib) ────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


# ── API Key Generation ────────────────────────────────────────────────

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"sk-{secrets.token_hex(32)}"


# ── JWT Tokens ────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ── Auth Dependency: optional (returns None if not authenticated) ─────

async def get_current_user_optional(request: Request, session: AsyncSession = Depends(get_session)):
    """Extract user if JWT/API key present, but don't require auth. Returns None if unauthenticated."""
    # Try JWT from Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        if token.count(".") == 2:
            try:
                payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
                username = payload.get("sub")
                if username:
                    result = await session.execute(select(User).where(User.username == username))
                    user = result.scalar_one_or_none()
                    if user and user.is_active:
                        return user
            except JWTError:
                pass

    # Try API Key from header or query param
    api_key = request.headers.get(settings.api_key_name, "") or request.query_params.get("api_key", "")
    if api_key:
        if api_key == settings.master_api_key:
            class MasterUser:
                id = 0
                username = "admin"
                email = "admin@system"
                is_admin = True
                is_active = True
                is_approved = True
                created_at = datetime.now(timezone.utc)
            return MasterUser()
        result = await session.execute(select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True))
        ak = result.scalar_one_or_none()
        if ak:
            result = await session.execute(select(User).where(User.id == ak.user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    return None


# ── Auth Dependency: required (raises 401 if not authenticated) ──────

async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)):
    """Extract and verify the current user from JWT or API key."""
    # Try JWT from Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        if token.count(".") == 2:
            try:
                payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
                username = payload.get("sub")
                if username is None:
                    raise HTTPException(status_code=401, detail="Invalid token payload")
                result = await session.execute(select(User).where(User.username == username))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    if not user.is_approved:
                        raise HTTPException(status_code=403, detail="Account pending admin approval")
                    return user
            except JWTError:
                pass

    # Try API Key from header or query param
    api_key = request.headers.get(settings.api_key_name, "") or request.query_params.get("api_key", "")
    if api_key:
        if api_key == settings.master_api_key:
            class MasterUser:
                id = 0
                username = "admin"
                email = "admin@system"
                is_admin = True
                is_active = True
                is_approved = True
                created_at = datetime.now(timezone.utc)
            return MasterUser()
        result = await session.execute(select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True))
        ak = result.scalar_one_or_none()
        if ak:
            ak.last_used_at = datetime.now(timezone.utc)
            await session.commit()
            result = await session.execute(select(User).where(User.id == ak.user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                if not user.is_approved:
                    raise HTTPException(status_code=403, detail="Account pending admin approval")
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a valid JWT token (Bearer) or API key (X-API-Key header).",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── Admin check ──────────────────────────────────────────────────────

async def verify_admin(user: User = Depends(get_current_user)):
    """Verify the current user is an admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user