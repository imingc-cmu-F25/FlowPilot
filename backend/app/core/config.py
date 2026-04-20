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

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from: str = "noreply@flowpilot.local"

    sendgrid_api_key: str = ""
    sendgrid_from: str = ""

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    # OAuth redirect callback — must exactly match the URI registered in the
    # Google Cloud Console. Defaults to the dev setup (API on :8000).
    google_redirect_uri: str = "http://localhost:8000/api/connectors/google/callback"
    # Where to send the browser after OAuth finishes. Frontend dev server by
    # default; override to the public site in production.
    frontend_base_url: str = "http://localhost:5173"

    # Hard upper bound on how long a single action (HTTP / email / calendar)
    # may run before the engine treats it as a step failure. Prevents a hung
    # external call from holding a worker indefinitely.
    action_execution_timeout_seconds: float = 30.0

    # Strong fault isolation for action execution. When true, the engine
    # dispatches each step to a dedicated Celery queue ("actions") whose
    # worker is a separate OS process. A crashing / OOM action therefore
    # cannot take down the engine worker. Defaults to false so unit tests
    # and single-process dev setups keep the fast in-process path.
    action_worker_enabled: bool = False
    # Upper bound on how long the engine waits for a remote action worker
    # to return a result. Slightly higher than action_execution_timeout_seconds
    # to leave room for broker round-trip.
    action_worker_result_timeout_seconds: float = 45.0

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
