import asyncio
from datetime import datetime, timezone

from app.config import settings
from app.dedupe import dedupe_results
from app.models import AccommodationResult, SearchRequest, SearchResponse, SearchSummary
from app.providers.amadeus import AmadeusProvider
from app.providers.booking import BookingProvider
from app.providers.expedia import ExpediaProvider
from app.providers.hotelbeds import HotelbedsProvider
from app.providers.mock import MockProvider
from app.providers.base import ProviderNotConfigured
from app.scoring import calculate_score, filter_result, recommendation_reason, sort_results


def configured_providers():
    providers = []

    if settings.use_mock_provider:
        providers.append(MockProvider())

    # The live providers are only added when credentials exist.
    # Their skeletons intentionally raise NotImplementedError until you implement the API mapping.
    if settings.amadeus_api_key and settings.amadeus_api_secret:
        providers.append(AmadeusProvider())
    if settings.booking_api_key:
        providers.append(BookingProvider())
    if settings.expedia_api_key:
        providers.append(ExpediaProvider())
    if settings.hotelbeds_api_key and settings.hotelbeds_secret:
        providers.append(HotelbedsProvider())

    return providers


async def safe_provider_search(provider, request: SearchRequest) -> tuple[list[AccommodationResult], str | None]:
    try:
        return await provider.search(request), None
    except ProviderNotConfigured as exc:
        return [], f"{provider.name}: not configured ({exc})"
    except NotImplementedError as exc:
        return [], f"{provider.name}: connector not implemented yet ({exc})"
    except Exception as exc:  # noqa: BLE001 - provider errors should not break the whole search
        return [], f"{provider.name}: provider error ({exc})"


def relaxation_suggestions(request: SearchRequest) -> list[str]:
    suggestions = []
    if request.max_total_price is not None:
        suggestions.append("Budget leicht erhöhen oder Gesamtpreis-Limit entfernen.")
    if request.min_rating is not None and request.min_rating >= 8.5:
        suggestions.append("Mindestbewertung auf 8,0 oder 8,2 senken.")
    if "free_cancellation" in request.must_haves:
        suggestions.append("Kostenlose Stornierung als Wunsch statt Pflicht behandeln.")
    if request.no_gos:
        suggestions.append("No-Gos einzeln lockern, um mehr verfügbare Optionen zu prüfen.")
    if request.accommodation_types:
        suggestions.append("Unterkunftstypen erweitern, z. B. Hotel und Apartment gemeinsam suchen.")
    suggestions.append("Suchradius erweitern oder benachbarte Viertel zulassen.")
    return suggestions


async def search_accommodations(request: SearchRequest) -> SearchResponse:
    providers = configured_providers()
    provider_results = await asyncio.gather(*(safe_provider_search(provider, request) for provider in providers))

    notes = []
    all_results: list[AccommodationResult] = []
    for results, note in provider_results:
        all_results.extend(results)
        if note:
            notes.append(note)

    checked_count = len(all_results)
    available_count = len([item for item in all_results if item.availability.available])

    deduped = dedupe_results(all_results)
    filtered = [item for item in deduped if filter_result(item, request)]

    for item in filtered:
        item.score = calculate_score(item, request)
        item.why_recommended = recommendation_reason(item, request)

    ranked = sort_results(filtered, request.sort_preference)[: request.max_results]

    summary = SearchSummary(
        destination=request.destination,
        checkin=request.checkin,
        checkout=request.checkout,
        guests=f"{request.adults} Erwachsene" + (f", {request.children} Kinder" if request.children else ""),
        rooms=request.rooms,
        results_checked=checked_count,
        available_results=available_count,
        returned_results=len(ranked),
        currency=request.currency,
        price_last_checked=datetime.now(timezone.utc),
        notes=notes,
    )

    return SearchResponse(
        search_summary=summary,
        results=ranked,
        relaxation_suggestions=[] if ranked else relaxation_suggestions(request),
    )
