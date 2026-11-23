from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/attendance"
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 480
    FERNET_KEY: str
    TIMEZONE: str = "Asia/Karachi"

    ADMIN_EMAIL: str = "admin@smartattendance.com"
    ADMIN_PASSWORD: str = "Admin@12345"
    ADMIN_NAME: str = "System Administrator"
    CORS_ORIGINS: str = "http://localhost:5173"

    FACE_ENGINE_URL: str = "http://localhost:8001"
    FACE_ENGINE_TOKEN: str

    RECOGNITION_MIN_CONFIDENCE: float = 0.5
    EVENT_MAX_SKEW_SECONDS: int = 120
    DUPLICATE_WINDOW_SECONDS: int = 60
    MIN_STAY_MINUTES: int = 5
    ABSENT_VERIFICATION_MINUTES: int = 30
    MIN_ENROLL_SAMPLES: int = 3
    ENROLL_CONSISTENCY_THRESHOLD: float = 0.5
    DUPLICATE_FACE_THRESHOLD: float = 0.6
    FINALIZE_INTERVAL_SECONDS: int = 300
    EVENT_RETENTION_DAYS: int = 90

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
