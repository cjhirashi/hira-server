from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Modo de despliegue ────────────────────────────────────────────────
    hira_deploy_mode: Literal["server", "studio"] = Field(
        default="server",
        description="server=PostgreSQL, studio=SQLite offline",
    )

    # ── Base de datos ─────────────────────────────────────────────────────
    database_url: str = Field(description="URL de conexión a la base de datos")
    postgres_db: str = Field(default="hira")
    postgres_user: str = Field(default="hira")
    postgres_password: str = Field(description="Contraseña de PostgreSQL")

    # ── Redis ──────────────────────────────────────────────────────────────
    redis_url: str = Field(description="URL de conexión a Redis")
    redis_password: str = Field(description="Contraseña de Redis")

    # ── Seguridad ──────────────────────────────────────────────────────────
    secret_key: str = Field(description="Clave secreta para JWT y cifrado")
    license_key: str = Field(default="", description="Clave de licencia emitida por Hira Hub. Vacío en modo dev.")
    cors_origins: str = Field(default="http://localhost:5173")

    # ── MQTT ──────────────────────────────────────────────────────────────
    mqtt_broker_host: str = Field(default="mosquitto")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_user: str = Field(description="Usuario MQTT")
    mqtt_password: str = Field(description="Contraseña MQTT")

    # ── AI ────────────────────────────────────────────────────────────────
    ai_encryption_key: str = Field(default="", description="Clave Fernet para el agente AI")
    openai_api_key: str = Field(default="", description="API key de OpenAI para embeddings RAG")

    # ── Hub ───────────────────────────────────────────────────────────────
    hub_url: str = Field(default="", description="URL base de Hira Hub. Vacío en modo dev (sin restricciones).")

    # ── Admin inicial ──────────────────────────────────────────────────────
    admin_email: str = Field(default="admin@hira.local", description="Email del usuario Admin inicial")
    admin_password: str = Field(default="", description="Contraseña del usuario Admin inicial")
    admin_full_name: str = Field(default="Administrador Hira")

    # ── SMTP ──────────────────────────────────────────────────────────────
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="")

    # ── Observabilidad ─────────────────────────────────────────────────────
    crash_reporter_enabled: bool = Field(default=False)
    crash_reporter_url: str = Field(default="https://crashes.hira.io/v1/report")
    environment: Literal["development", "production", "test"] = Field(default="development")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return v

    @property
    def deploy_mode(self) -> str:
        return self.hira_deploy_mode

    @property
    def sync_database_url(self) -> str:
        if self.hira_deploy_mode == "studio":
            return "sqlite+pysqlite:///./hira_studio.db"
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    @property
    def async_database_url(self) -> str:
        if self.hira_deploy_mode == "studio":
            return "sqlite+aiosqlite:///./hira_studio.db"
        return self.database_url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]
