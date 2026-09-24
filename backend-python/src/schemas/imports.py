"""
Pydantic v2 DTOs for Letterboxd import payloads and responses.
Matches Java records: LetterboxdImportRequest and ImportResponse.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DiaryEntryDto(BaseModel):
    """
    Individual film watch record parsed from Letterboxd CSVs.
    Maps directly to com.cinestats.backend_java.dto.request.LetterboxdImportRequest$DiaryEntry.
    """
    title: str = Field(..., min_length=1, description="Movie title is required")
    release_year: int = Field(..., alias="releaseYear", ge=1870, le=2100)
    watched_date: Optional[date] = Field(None, alias="watchedDate")
    
    # In Letterboxd exports, unrated films should map to None to prevent DB CHECK failures.
    # Decimal guarantees numeric precision without IEEE 754 binary floating drift.
    rating: Optional[Decimal] = Field(None, ge=Decimal("0.5"), le=Decimal("5.0"))
    
    is_rewatch: bool = Field(False, alias="isRewatch")
    letterboxd_uri: Optional[str] = Field(None, alias="letterboxdUri")

    model_config = ConfigDict(
        populate_by_name=True,  # Accepts both 'releaseYear' (camelCase) and 'release_year' (snake_case)
        extra="ignore",         # Silently discards extra CSV properties
    )


class LetterboxdImportRequest(BaseModel):
    """
    Batch import payload sent from React client.
    Maps to com.cinestats.backend_java.dto.request.LetterboxdImportRequest.
    """
    username: str = Field(..., min_length=1, description="Letterboxd username is required")
    entries: List[DiaryEntryDto] = Field(..., min_length=1, description="Entries cannot be empty")

    model_config = ConfigDict(populate_by_name=True)


class ImportResponse(BaseModel):
    """
    202 Accepted response payload returning batch enrichment summary.
    Maps to com.cinestats.backend_java.dto.response.ImportResponse.
    """
    total_received: int = Field(..., alias="totalReceived")
    matched_in_cache: int = Field(..., alias="matchedInCache")
    queued_for_enrichment: int = Field(..., alias="queuedForEnrichment")
    user_id: uuid.UUID = Field(..., alias="userId")
    session_token: str = Field(..., alias="sessionToken")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,  # Enables ORM model attribute extraction
    )