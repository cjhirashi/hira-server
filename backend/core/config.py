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
    license_key: str = Field(default="", description="Clave de licencia Hira")
    cors_origins: str = Field(default="http://localhost:5173")

    # ── MQTT ──────────────────────────────────────────────────────────────
    mqtt_broker_host: str = Field(default="mosquitto")
    mqtt_broker_port: int = Field(default=1883)
    mqtt_user: str = Field(description="Usuario MQTT")
    mqtt_password: str = Field(description="Contraseña MQTT")

    # ── AI ────────────────────────────────────────────────────────────────
    ai_encryption_key: str = Field(default="", description="Clave Fernet para el agente AI")

    # ── Hub ───────────────────────────────────────────────────────────────
    hub_api_url: str = Field(default="")
    hub_api_key: str = Field(default="")

    # ── Observabilidad ─────────────────────────────────────────────────────
    crash_reporter_enabled: bool = Field(default=False)
    environment: Literal["development", "production", "test"] = Field(default="development")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]
