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
    hotelbeds_base_url: str = "https://api.test.hotelbeds.com"
    hotelbeds_search_radius_km: int = 5
    hotelbeds_max_hotels: int = 20
    hotelbeds_max_rates_per_room: int = 3
    hotelbeds_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
