"""
Centralized configuration using Pydantic BaseSettings.

All environment variables are loaded once at startup and validated.
Replaces the scattered load_dotenv() + os.getenv() calls across
config.py, fighter.py, and groq_processing.py.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # ── API Keys ──────────────────────────────────────────────
    GROQ_API_KEY: str = Field(..., description="Groq API key for LLM calls")
    TAVILY_API_KEY: str = Field(..., description="Tavily API key for web search")
    SERPER_API_KEY: str = Field("", description="Serper API key (optional, Tavily-only if empty)")

    # ── Clerk Auth ────────────────────────────────────────────
    CLERK_SECRET_KEY: str = Field("", description="Clerk secret key for JWT verification")
    CLERK_JWKS_URL: str = Field("", description="Clerk JWKS endpoint URL")
    CLERK_DISABLE_AUTH: bool = Field(False, description="Bypass auth for local development")

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = Field(
        "https://satya-2.vercel.app,http://localhost:3000",
        description="Comma-separated allowed origins"
    )

    # ── Paths ─────────────────────────────────────────────────
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent,
        description="Project root (backend/)"
    )

    @property
    def storage_dir(self) -> Path:
        return self.BASE_DIR / "storage"

    @property
    def history_dir(self) -> Path:
        return self.storage_dir / "history"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a clean list of origins."""
        if not self.CORS_ORIGINS or not self.CORS_ORIGINS.strip():
            return ["*"]
            
        # Split by comma, strip whitespace and quotes
        origins = [
            o.strip().strip("'").strip('"') 
            for o in self.CORS_ORIGINS.split(",") 
            if o.strip()
        ]
        
        return origins if origins else ["*"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# ── Singleton ─────────────────────────────────────────────────
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance (created once per process)."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure runtime directories exist
        _settings.history_dir.mkdir(parents=True, exist_ok=True)
    return _settings
