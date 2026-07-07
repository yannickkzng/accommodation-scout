from app.config import settings
from app.models import AccommodationResult, SearchRequest
from app.providers.base import AccommodationProvider, ProviderNotConfigured


class AmadeusProvider(AccommodationProvider):
    name = "amadeus"

    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        if not settings.amadeus_api_key or not settings.amadeus_api_secret:
            raise ProviderNotConfigured("Amadeus credentials are missing.")

        # TODO: Implement real Amadeus flow:
        # 1. Get OAuth token from Amadeus.
        # 2. Resolve destination to city code / geocode.
        # 3. Search available hotel offers for check-in/check-out, guests and rooms.
        # 4. Fetch details/policies where needed.
        # 5. Normalize every offer into AccommodationResult.
        # Keep this connector free of GPT-specific wording. It should return facts only.
        raise NotImplementedError("Amadeus connector skeleton is prepared but not implemented.")
