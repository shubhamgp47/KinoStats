"""
FastAPI route dependency providers for KinoStats.
Extracts tenant identity via X-Session-ID and validates session continuity.
"""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.entities import User


async def get_current_user(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the tenant User entity from the incoming X-Session-ID header.
    Rejects the request with HTTP 401 Unauthorized if the header is missing or unrecognized.
    """
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Session-ID header. Upload an export or initiate a session first.",
        )

    stmt = select(User).where(User.session_token == x_session_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired. Please re-import your Letterboxd archive.",
        )

    return user