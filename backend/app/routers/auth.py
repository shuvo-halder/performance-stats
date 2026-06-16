from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_session, User, ApiKey
from app.auth import (
    hash_password, verify_password, create_access_token,
    generate_api_key, get_current_user, verify_admin
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ApiKeyCreate(BaseModel):
    name: Optional[str] = "default"


class ApiKeyResponse(BaseModel):
    id: int
    key: str
    name: Optional[str]
    is_active: bool
    created_at: str
    last_used_at: Optional[str]


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    is_approved: bool
    created_at: str


# ── Public Endpoints ──────────────────────────────────────────────────

SYSTEM_USERS = {}  # Populated on startup: {"admin": "hashed_password"}


def init_system_users():
    """Create system admin users from environment configuration."""
    # The first run seed creates the admin user in DB
    pass


@router.post("/register")
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """Register a new user account. Requires admin approval before access."""
    # Check if username already exists
    result = await session.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check if email already exists
    result = await session.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate password
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Check if any users exist - first user becomes admin and auto-approved
    result = await session.execute(select(User).limit(1))
    first_user = result.scalar_one_or_none() is None

    # Create user
    api_key = generate_api_key()
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        api_key=api_key,
        is_active=True,
        is_admin=first_user,       # First user becomes admin
        is_approved=first_user,    # First user auto-approved
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create initial API key entry
    api_key_entry = ApiKey(user_id=user.id, key=api_key, name="default")
    session.add(api_key_entry)
    await session.commit()

    # Generate JWT
    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_approved": user.is_approved,
            "message": "Account created and auto-approved as admin" if first_user else "Account created. Awaiting admin approval.",
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Authenticate and get a JWT token."""
    result = await session.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval. Please contact your administrator.")

    # Generate JWT
    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_approved": user.is_approved,
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": getattr(current_user, 'email', 'system'),
        "is_active": getattr(current_user, 'is_active', True),
        "is_admin": getattr(current_user, 'is_admin', False),
        "is_approved": getattr(current_user, 'is_approved', True),
        "created_at": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') and current_user.created_at else "N/A",
    }


# ── API Key Management ────────────────────────────────────────────────

@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all API keys for the current user."""
    result = await session.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": key.id,
            "key": key.key[:12] + "..." + key.key[-4:] if len(key.key) > 16 else key.key,
            "name": key.name,
            "is_active": key.is_active,
            "created_at": key.created_at.isoformat() if key.created_at else "N/A",
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        }
        for key in keys
    ]


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key."""
    new_key = generate_api_key()
    api_key_entry = ApiKey(
        user_id=current_user.id,
        key=new_key,
        name=request.name,
    )
    session.add(api_key_entry)
    await session.commit()
    await session.refresh(api_key_entry)

    return {
        "id": api_key_entry.id,
        "key": new_key,
        "name": api_key_entry.name,
        "is_active": api_key_entry.is_active,
        "created_at": api_key_entry.created_at.isoformat() if api_key_entry.created_at else "N/A",
        "last_used_at": None,
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Deactivate an API key."""
    result = await session.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await session.commit()
    return {"message": "API key deactivated"}


# ── Admin: User Management ────────────────────────────────────────────

@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(verify_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all users (admin only)."""
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "is_approved": u.is_approved,
            "created_at": u.created_at.isoformat() if u.created_at else "N/A",
        }
        for u in users
    ]


@router.post("/admin/users/{user_id}/approve")
async def approve_user(
    user_id: int,
    current_user: User = Depends(verify_admin),
    session: AsyncSession = Depends(get_session),
):
    """Approve a pending user account (admin only)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_approved:
        return {"message": f"User '{user.username}' is already approved"}

    user.is_approved = True
    await session.commit()
    return {"message": f"User '{user.username}' has been approved"}


@router.post("/admin/users/{user_id}/reject")
async def reject_user(
    user_id: int,
    current_user: User = Depends(verify_admin),
    session: AsyncSession = Depends(get_session),
):
    """Reject (disable) a user account (admin only)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.is_approved = False
    await session.commit()
    return {"message": f"User '{user.username}' has been rejected and disabled"}


@router.post("/admin/users/{user_id}/make-admin")
async def make_admin(
    user_id: int,
    current_user: User = Depends(verify_admin),
    session: AsyncSession = Depends(get_session),
):
    """Promote a user to admin role (admin only)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True
    await session.commit()
    return {"message": f"User '{user.username}' is now an admin"}