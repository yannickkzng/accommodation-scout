from app.config import settings
from app.models import AccommodationResult, SearchRequest
from app.providers.base import AccommodationProvider, ProviderNotConfigured


class BookingProvider(AccommodationProvider):
    name = "booking_com"

    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        if not settings.booking_api_key:
            raise ProviderNotConfigured("Booking.com API key is missing.")

        # TODO: Implement once you have Booking.com Demand API partner access:
        # 1. Resolve destination.
        # 2. Search available accommodations for the exact dates and occupancy.
        # 3. Retrieve price, taxes, fees, policies, reviews and deep links.
        # 4. Normalize into AccommodationResult.
        raise NotImplementedError("Booking.com connector skeleton is prepared but not implemented.")
