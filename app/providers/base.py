from abc import ABC, abstractmethod

from app.models import AccommodationResult, SearchRequest


class ProviderError(Exception):
    pass


class ProviderNotConfigured(ProviderError):
    pass


class AccommodationProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        """Return normalized, available accommodation results for the request."""
        raise NotImplementedError
