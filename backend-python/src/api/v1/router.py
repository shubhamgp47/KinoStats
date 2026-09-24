"""
Central API v1 Router aggregation.
"""

from fastapi import APIRouter
from src.api.v1.endpoints import imports, stats

api_router = APIRouter()
api_router.include_router(imports.router, tags=["Imports"])
api_router.include_router(stats.router, tags=["Analytics"])