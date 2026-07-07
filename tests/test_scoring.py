from datetime import date

from app.models import SearchRequest
from app.providers.mock import MockProvider
from app.scoring import calculate_score, filter_result


def test_mock_results_filter_and_score():
    request = SearchRequest(
        destination="Florenz",
        checkin=date(2026, 9, 12),
        checkout=date(2026, 9, 16),
        adults=2,
        max_total_price=900,
        min_rating=8.5,
        accommodation_types=["hotel", "apartment"],
        must_haves=["free_cancellation"],
        no_gos=[],
    )

    provider = MockProvider()
    import asyncio

    results = asyncio.run(provider.search(request))
    filtered = [item for item in results if filter_result(item, request)]
    assert len(filtered) == 1
    assert filtered[0].name.startswith("Palazzo Verde")
    assert calculate_score(filtered[0], request) > 80
