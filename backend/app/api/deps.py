"""API dependency injection: authentication, database sessions, authorization."""

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import credentials_exception, forbidden_exception
from app.core.security import decode_token, has_role
from app.database.session import get_db
from app.models.user import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception()

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception()

    if payload.get("type") != "access":
        raise credentials_exception()

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception()

    return user


async def require_viewer(user: User = Depends(get_current_user)) -> User:
    """Require at least viewer role."""
    if not has_role(user.role, "viewer"):
        raise forbidden_exception()
    return user


async def require_operator(user: User = Depends(get_current_user)) -> User:
    """Require at least operator role."""
    if not has_role(user.role, "operator"):
        raise forbidden_exception("Operator or admin role required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if not has_role(user.role, "admin"):
        raise forbidden_exception("Admin role required")
    return user
