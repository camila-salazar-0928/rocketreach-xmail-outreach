from functools import lru_cache
from pydantic import EmailStr, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RocketReach Xmail Outreach"
    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="sqlite:///./data/outreach_local.db",
        alias="DATABASE_URL",
    )
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=465, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: SecretStr | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: EmailStr | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="RocketReach Outreach", alias="SMTP_FROM_NAME")
    smtp_use_ssl: bool = Field(default=True, alias="SMTP_USE_SSL")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")
    enable_real_email_sending: bool = Field(
        default=False,
        alias="ENABLE_REAL_EMAIL_SENDING",
    )

    @field_validator(
        "smtp_host",
        "smtp_username",
        "smtp_password",
        "smtp_from_email",
        mode="before",
    )
    @classmethod
    def empty_string_as_none(cls, value):
        if value == "":
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
