"""
KinoStats Python Backend Entrypoint.
Exposes ASGI FastAPI application with Lifespan resource management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.services.tmdb_client import tmdb_client
from src.api.v1.router import api_router




@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown events.
    Guarantees clean socket disposal and avoids dangling HTTP connections.
    """
    # Startup: Client initialized
    yield
    # Shutdown: Close client HTTP connection pool
    await tmdb_client.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS to allow the React client (Vite on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-ID"],
)

# Include API v1 router prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "kinostats-python"}