from app.models import AccommodationResult, CancellationCategory, SearchRequest, SortPreference


NO_GO_RISK_MAP = {
    "noise_complaints": ["noise", "lärm", "laut", "some_noise_mentions"],
    "cleanliness_complaints": ["dirty", "schmutz", "cleanliness"],
    "high_deposit": ["deposit", "kaution", "possible_deposit", "high_deposit"],
    "limited_checkin": ["limited_checkin", "limited_checkin_window"],
    "non_refundable": ["non_refundable"],
}

MUST_HAVE_AMENITY_MAP = {
    "free_cancellation": "free_cancellation",
    "central_location": "central_location",
    "parking": "parking",
    "breakfast": "breakfast",
    "pool": "pool",
    "kitchen": "kitchen",
    "air_conditioning": "air_conditioning",
    "late_checkin": "late_checkin",
}


def has_no_go(result: AccommodationResult, no_gos: list[str]) -> bool:
    risk_text = " ".join(result.risk_flags + result.reviews_summary.negative_patterns).lower()
    for no_go in no_gos:
        patterns = NO_GO_RISK_MAP.get(no_go, [no_go])
        if any(pattern.lower() in risk_text for pattern in patterns):
            return True
    return False


def matches_must_haves(result: AccommodationResult, must_haves: list[str]) -> bool:
    amenities = {item.lower() for item in result.amenities}

    for must_have in must_haves:
        normalized = MUST_HAVE_AMENITY_MAP.get(must_have, must_have).lower()
        if normalized == "free_cancellation":
            if result.policies.cancellation_category != CancellationCategory.free_cancellation:
                return False
            continue
        if normalized == "central_location":
            distance = result.location.distance_to_target_km
            if "central_location" not in amenities and (distance is None or distance > 1.5):
                return False
            continue
        if normalized not in amenities:
            return False
    return True


def filter_result(result: AccommodationResult, request: SearchRequest) -> bool:
    if not result.availability.available:
        return False

    if request.max_total_price is not None and result.price.total > request.max_total_price:
        return False

    if request.min_rating is not None:
        if result.rating.score is None or result.rating.score < request.min_rating:
            return False

    if request.accommodation_types:
        allowed = {item.lower() for item in request.accommodation_types}
        if not result.type or result.type.lower() not in allowed:
            return False

    if not matches_must_haves(result, request.must_haves):
        return False

    if has_no_go(result, request.no_gos):
        return False

    return True


def rating_component(result: AccommodationResult) -> float:
    score = result.rating.score or 0
    normalized = min(max(score / 10 * 100, 0), 100)
    count = result.rating.review_count or 0
    if count >= 500:
        confidence_bonus = 0
    elif count >= 100:
        confidence_bonus = -5
    elif count >= 20:
        confidence_bonus = -12
    else:
        confidence_bonus = -25
    return max(normalized + confidence_bonus, 0)


def location_component(result: AccommodationResult) -> float:
    distance = result.location.distance_to_target_km
    if distance is None:
        return 55
    if distance <= 0.5:
        return 100
    if distance <= 1.0:
        return 92
    if distance <= 2.0:
        return 78
    if distance <= 4.0:
        return 58
    return 35


def value_component(result: AccommodationResult, request: SearchRequest) -> float:
    if request.max_total_price is None:
        # Without a user budget, avoid overclaiming value. Use a neutral score.
        return 70
    ratio = result.price.total / request.max_total_price
    if ratio <= 0.75:
        return 100
    if ratio <= 0.90:
        return 85
    if ratio <= 1.0:
        return 70
    return 0


def cancellation_component(result: AccommodationResult) -> float:
    category = result.policies.cancellation_category
    if category == CancellationCategory.free_cancellation:
        return 100
    if category == CancellationCategory.partially_refundable:
        return 60
    if category == CancellationCategory.non_refundable:
        return 20
    return 45


def amenities_component(result: AccommodationResult, request: SearchRequest) -> float:
    if not request.nice_to_haves:
        return 75
    amenities = {item.lower() for item in result.amenities}
    hits = 0
    for item in request.nice_to_haves:
        normalized = MUST_HAVE_AMENITY_MAP.get(item, item).lower()
        if normalized in amenities:
            hits += 1
        elif normalized == "central_location" and (result.location.distance_to_target_km or 999) <= 1.5:
            hits += 1
    return min(100, 50 + (hits / len(request.nice_to_haves)) * 50)


def risk_component(result: AccommodationResult) -> float:
    risk_count = len(result.risk_flags)
    if risk_count == 0:
        return 100
    if risk_count == 1:
        return 82
    if risk_count == 2:
        return 65
    return 45


def calculate_score(result: AccommodationResult, request: SearchRequest) -> float:
    score = (
        rating_component(result) * 0.25
        + location_component(result) * 0.20
        + value_component(result, request) * 0.20
        + cancellation_component(result) * 0.15
        + amenities_component(result, request) * 0.10
        + risk_component(result) * 0.10
    )
    return round(score, 1)


def recommendation_reason(result: AccommodationResult, request: SearchRequest) -> str:
    parts = []
    if result.rating.score and result.rating.score >= 8.8:
        parts.append("starke Gästebewertung")
    if result.location.distance_to_target_km is not None and result.location.distance_to_target_km <= 1.5:
        parts.append("gute Lage")
    if result.policies.cancellation_category == CancellationCategory.free_cancellation:
        parts.append("flexible Storno-Option")
    if request.max_total_price and result.price.total <= request.max_total_price * 0.85:
        parts.append("gutes Preis-Leistungs-Verhältnis")

    if not parts:
        return "Solide Passung zu den Suchkriterien, aber Details vor Buchung prüfen."
    return "Empfohlen wegen " + ", ".join(parts) + "."


def sort_results(results: list[AccommodationResult], preference: SortPreference) -> list[AccommodationResult]:
    if preference == SortPreference.cheapest:
        return sorted(results, key=lambda item: (item.price.total, -(item.score or 0)))
    if preference == SortPreference.highest_rated:
        return sorted(results, key=lambda item: (-(item.rating.score or 0), item.price.total))
    if preference == SortPreference.most_flexible:
        return sorted(
            results,
            key=lambda item: (
                item.policies.cancellation_category != CancellationCategory.free_cancellation,
                item.price.total,
            ),
        )
    if preference == SortPreference.best_location:
        return sorted(results, key=lambda item: (item.location.distance_to_target_km or 999, -(item.score or 0)))
    return sorted(results, key=lambda item: (-(item.score or 0), item.price.total))
