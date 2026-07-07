from app.config import settings
from app.models import AccommodationResult, SearchRequest
from app.providers.base import AccommodationProvider, ProviderNotConfigured


class ExpediaProvider(AccommodationProvider):
    name = "expedia"

    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        if not settings.expedia_api_key:
            raise ProviderNotConfigured("Expedia Rapid API key is missing.")

        # TODO: Implement once you have Expedia Rapid partner access:
        # 1. Search properties and availability for exact dates and occupancy.
        # 2. Extract room rates, taxes/fees, cancellation penalties and booking URLs.
        # 3. Normalize into AccommodationResult.
        raise NotImplementedError("Expedia connector skeleton is prepared but not implemented.")
