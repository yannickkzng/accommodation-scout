from app.config import settings
from app.models import AccommodationResult, SearchRequest
from app.providers.base import AccommodationProvider, ProviderNotConfigured


class HotelbedsProvider(AccommodationProvider):
    name = "hotelbeds"

    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        if not settings.hotelbeds_api_key or not settings.hotelbeds_secret:
            raise ProviderNotConfigured("Hotelbeds credentials are missing.")

        # TODO: Implement once you have Hotelbeds/HBX credentials:
        # 1. Build signed requests according to provider requirements.
        # 2. Search availability for exact dates and occupancy.
        # 3. Normalize pricing, cancellation and policies into AccommodationResult.
        raise NotImplementedError("Hotelbeds connector skeleton is prepared but not implemented.")
