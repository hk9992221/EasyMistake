from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 4320

    # S3
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_REGION: str = "cn-east-1"
    IMAGE_MAX_UPLOAD_BYTES: int = Field(20 * 1024 * 1024, ge=1)
    IMAGE_MAX_PIXELS: int = Field(40_000_000, ge=1)

    # AI / OCR
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    OCR_REQUEST_TIMEOUT_SECONDS: float = Field(120, gt=0)
    JOB_LEASE_TIMEOUT_SECONDS: int = Field(300, ge=30)
    JOB_HEARTBEAT_SECONDS: float = Field(15, gt=0, le=30)

    # Environment
    ENVIRONMENT: str = "development"
    SQL_ECHO: bool = False
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8000"]'
    APP_TIMEZONE: str = "Asia/Shanghai"

    # Export
    EXPORT_OUTPUT_DIR: str = "exports"
    EXPORT_WORKER_AUTO_START: bool = True
    EXPORT_WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    EXPORT_RETENTION_DAYS: int = 7
    EXPORT_CLEANUP_INTERVAL_SECONDS: float = 3600.0

    @property
    def export_output_dir(self) -> str:
        return self.EXPORT_OUTPUT_DIR

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
