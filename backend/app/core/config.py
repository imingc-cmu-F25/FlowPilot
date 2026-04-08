from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FlowPilot API"
    app_env: str = "development"
    app_port: int = 8000

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "flowpilot"
    postgres_user: str = "flowpilot"
    postgres_password: str = "flowpilot"

    database_check_on_startup: bool = True

    database_url_override: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url_override"),
    )

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    openai_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return self.database_url

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
