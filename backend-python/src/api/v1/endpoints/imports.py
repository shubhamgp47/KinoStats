"""
Letterboxd CSV batch ingestion REST controller endpoint.
Matches com.cinestats.backend_java.controller.ImportController.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.imports import ImportResponse, LetterboxdImportRequest
from src.services.ingestion import ingestion_service

router = APIRouter()


@router.post(
    "/imports/letterboxd",
    response_model=ImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch import Letterboxd diary and watched history",
)
async def import_letterboxd(
    payload: LetterboxdImportRequest,
    response: Response,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts parsed Letterboxd entries from the frontend client.
    Executes Database-First Lazy-Cache matching, concurrent TMDB resolution,
    and returns a 202 Accepted response along with the tenant X-Session-ID header.
    """
    result = await ingestion_service.process_import(
        payload=payload,
        session_token=x_session_id,
        db=db,
    )

    # Return active session token in response header for React client storage
    response.headers["X-Session-ID"] = result.session_token

    return result