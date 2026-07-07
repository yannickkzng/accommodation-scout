from math import radians, sin, cos, sqrt, atan2

from rapidfuzz import fuzz

from app.models import AccommodationResult, ProviderOption


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c


def maybe_same_property(a: AccommodationResult, b: AccommodationResult) -> bool:
    name_similarity = fuzz.token_sort_ratio(a.name.lower(), b.name.lower())
    address_similarity = 0
    if a.location.address and b.location.address:
        address_similarity = fuzz.token_sort_ratio(a.location.address.lower(), b.location.address.lower())

    geo_close = False
    if None not in (a.location.lat, a.location.lng, b.location.lat, b.location.lng):
        geo_close = distance_km(a.location.lat, a.location.lng, b.location.lat, b.location.lng) < 0.15

    return name_similarity >= 88 or (name_similarity >= 75 and (address_similarity >= 75 or geo_close))


def merge_provider_options(target: AccommodationResult, duplicate: AccommodationResult) -> AccommodationResult:
    options = target.provider_options or [
        ProviderOption(
            provider=target.provider,
            total_price=target.price.total,
            currency=target.price.currency,
            cancellation_category=target.policies.cancellation_category,
            cancellation=target.policies.cancellation,
            payment=target.policies.payment,
            booking_url=target.booking_url,
            room_name=target.availability.room_name,
        )
    ]

    duplicate_options = duplicate.provider_options or [
        ProviderOption(
            provider=duplicate.provider,
            total_price=duplicate.price.total,
            currency=duplicate.price.currency,
            cancellation_category=duplicate.policies.cancellation_category,
            cancellation=duplicate.policies.cancellation,
            payment=duplicate.policies.payment,
            booking_url=duplicate.booking_url,
            room_name=duplicate.availability.room_name,
        )
    ]

    existing_keys = {(item.provider, item.total_price, item.booking_url) for item in options}
    for option in duplicate_options:
        key = (option.provider, option.total_price, option.booking_url)
        if key not in existing_keys:
            options.append(option)

    target.provider_options = sorted(options, key=lambda item: item.total_price)

    # Keep the best factual price as the headline price.
    cheapest = target.provider_options[0]
    target.price.total = cheapest.total_price
    target.booking_url = cheapest.booking_url or target.booking_url
    target.provider = target.provider + "+" + duplicate.provider if duplicate.provider not in target.provider else target.provider

    target.risk_flags = sorted(set(target.risk_flags + duplicate.risk_flags))
    target.amenities = sorted(set(target.amenities + duplicate.amenities))
    return target


def dedupe_results(results: list[AccommodationResult]) -> list[AccommodationResult]:
    deduped: list[AccommodationResult] = []
    for result in results:
        matched = False
        for idx, existing in enumerate(deduped):
            if maybe_same_property(existing, result):
                deduped[idx] = merge_provider_options(existing, result)
                matched = True
                break
        if not matched:
            deduped.append(result)
    return deduped
