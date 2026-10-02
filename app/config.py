from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://widget:widget@localhost:5432/widgetdb"
    jwt_secret: str = "dev-secret"
    jwt_expires_minutes: int = 60
    geo_provider_a_url: str = "http://ip-api.com/json/{ip}"
    geo_provider_b_url: str = "https://ipapi.co/{ip}/json/"
    geo_provider_a_disabled: bool = False
    geo_provider_b_disabled: bool = False
    rate_limit_per_ip: str = "20/minute"
    rate_limit_per_widget: str = "100/minute"
    cors_allow_origins: str = "*"
    notify_force_failure: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
