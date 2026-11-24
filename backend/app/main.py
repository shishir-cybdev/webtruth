import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes.health import router as health_router
from app.routes.investigations import router as investigations_router

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("webtruth.backend")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Starting %s v%s in %s mode", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    logger.info("Allowed CORS origins: %s", settings.CORS_ORIGINS)
    logger.info("MCP Status: %s", settings.MCP_INTEGRATION_STATUS)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend API for WebTruth — the MCP-powered product investigation platform. "
        "Phase 2A implements the core FastAPI modular service layer, typed Pydantic contracts, "
        "and placeholder investigation service. Multi-agent MCP servers will be connected in Phase 2B."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle 422 Unprocessable Entity with clean structured format."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "message": err.get("msg"),
            "type": err.get("type"),
        })
    logger.warning("Request validation failed on %s: %s", request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "Validation Error",
            "message": "Input data failed validation rules",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled internal server errors."""
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing the request.",
        },
    )


# Register Routers
app.include_router(health_router)
app.include_router(investigations_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Root redirect to docs or health info."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "phase": "Phase 2A (Backend Scaffold)",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "investigations_url": "/api/investigations",
    }
