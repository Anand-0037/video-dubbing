"""Shared configuration using Pydantic settings."""

from typing import List
from pydantic_settings import BaseSettings

class SharedSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str

    # AI Service Keys
    OPENAI_API_KEY: str
    GROQ_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str
    GEMINI_API_KEY: str | None = None
    FIRE_CRAWL_API_KEY: str | None = None
    HUGGING_FACE_TOKEN: str | None = None
    PPLX_API_KEY: str | None = None
    CEREBRAS_API_KEY: str | None = None
    RESEND_API_KEY: str | None = None
    MEMO_API_KEY: str | None = None
    ZEP_PERSONAL_API_KEY: str | None = None
    CLIPBOARD_API_KEY: str | None = None
    TESTPRITE_KEY: str | None = None
    BAIDU_API_KEY: str | None = None
    NOVITA_API_KEY: str | None = None
    PRESAGE_API_KEY: str | None = None
    WEATHER_MAP_API_KEY: str | None = None
    NEWS_API_KEY: str | None = None

    # Snowflake Configuration
    SNOWFLAKE_ACCOUNT: str | None = None
    SNOWFLAKE_USER: str | None = None
    SNOWFLAKE_PASSWORD: str | None = None
    SNOWFLAKE_WAREHOUSE: str | None = None
    SNOWFLAKE_DATABASE: str | None = None
    SNOWFLAKE_SCHEMA: str | None = None
    SNOWFLAKE_ROLE: str | None = None

    # Database
    DATABASE_URL: str = "sqlite:///./dubwizard.db"

    # Application
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Processing Limits
    MAX_VIDEO_SIZE_MB: int = 100
    MAX_VIDEO_DURATION_SECONDS: int = 60
    USE_LOCAL_STORAGE: bool = False
    USE_MOCK_AI: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


shared_settings = SharedSettings()
