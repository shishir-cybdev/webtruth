from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment configuration."""

    APP_NAME: str = "WebTruth API"
    APP_VERSION: str = "0.2.0-phase2a"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Configuration - allow local Next.js dev and deployed Vercel frontend
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://webtruth.vercel.app",
    ]
    
    # MCP Status (Phase 2B onward)
    MCP_INTEGRATION_STATUS: str = "Phase 2B - Pending Integration"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
