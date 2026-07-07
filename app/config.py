from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "local"
    use_mock_provider: bool = True

    accommodation_scout_api_token: str | None = None

    amadeus_api_key: str | None = None
    amadeus_api_secret: str | None = None
    booking_api_key: str | None = None
    expedia_api_key: str | None = None
    hotelbeds_api_key: str | None = None
    hotelbeds_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
