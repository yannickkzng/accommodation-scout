from __future__ import annotations

import hashlib
import math
import time
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.models import (
    AccommodationResult,
    Availability,
    CancellationCategory,
    Location,
    Policies,
    Price,
    ProviderOption,
    Rating,
    ReviewSummary,
    SearchRequest,
)
from app.providers.base import AccommodationProvider, ProviderNotConfigured


# Small MVP geocoding fallback so the Custom GPT can search by city name without
# needing a separate maps/geocoding API. Add more places here as needed.
KNOWN_COORDINATES: dict[str, tuple[float, float]] = {
    "florenz": (43.7696, 11.2558),
    "firenze": (43.7696, 11.2558),
    "florence": (43.7696, 11.2558),
    "rom": (41.9028, 12.4964),
    "rome": (41.9028, 12.4964),
    "paris": (48.8566, 2.3522),
    "london": (51.5072, -0.1276),
    "barcelona": (41.3874, 2.1686),
    "madrid": (40.4168, -3.7038),
    "lissabon": (38.7223, -9.1393),
    "lisbon": (38.7223, -9.1393),
    "amsterdam": (52.3676, 4.9041),
    "hamburg": (53.5511, 9.9937),
    "berlin": (52.5200, 13.4050),
    "münchen": (48.1351, 11.5820),
    "munich": (48.1351, 11.5820),
    "kopenhagen": (55.6761, 12.5683),
    "copenhagen": (55.6761, 12.5683),
    "new york": (40.7128, -74.0060),
    "palma": (39.5696, 2.6502),
    "mallorca": (39.6953, 3.0176),
}

ACCOMMODATION_TYPE_MAP = {
    "hotel": ["HOTEL"],
    "hotels": ["HOTEL"],
    "apartment": ["APARTMENT", "APARTHOTEL"],
    "apartments": ["APARTMENT", "APARTHOTEL"],
    "ferienwohnung": ["APARTMENT", "APARTHOTEL"],
    "hostel": ["HOSTEL"],
    "villa": ["VILLA"],
}

BREAKFAST_BOARD_CODES = {"BB", "HB", "FB", "AI"}


class HotelbedsProvider(AccommodationProvider):
    name = "hotelbeds"

    def __init__(self) -> None:
        if not settings.hotelbeds_api_key or not settings.hotelbeds_secret:
            raise ProviderNotConfigured("Hotelbeds credentials are missing.")
        self.base_url = (settings.hotelbeds_base_url or "https://api.test.hotelbeds.com").rstrip("/")

    def _signature(self) -> str:
        timestamp = str(int(time.time()))
        raw = f"{settings.hotelbeds_api_key}{settings.hotelbeds_secret}{timestamp}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _headers(self) -> dict[str, str]:
        return {
            "Api-key": settings.hotelbeds_api_key or "",
            "X-Signature": self._signature(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
        }

    async def status(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.hotelbeds_timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/hotel-api/1.0/status",
                headers=self._headers(),
            )
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"raw": response.text}

    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        payload = self._availability_payload(request)

        async with httpx.AsyncClient(timeout=settings.hotelbeds_timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/hotel-api/1.0/hotels",
                headers=self._headers(),
                json=payload,
            )

        if response.status_code >= 400:
            detail = response.text[:800]
            raise RuntimeError(f"Hotelbeds HTTP {response.status_code}: {detail}")

        data = response.json()
        return self._normalize_availability(data, request)

    def _availability_payload(self, request: SearchRequest) -> dict[str, Any]:
        lat, lng = self._coordinates_for_request(request)

        payload: dict[str, Any] = {
            "stay": {
                "checkIn": request.checkin.isoformat(),
                "checkOut": request.checkout.isoformat(),
            },
            "occupancies": [
                {
                    "rooms": request.rooms,
                    "adults": request.adults,
                    "children": request.children,
                }
            ],
            "geolocation": {
                "latitude": lat,
                "longitude": lng,
                "radius": settings.hotelbeds_search_radius_km,
                "unit": "km",
            },
            "filter": {
                "maxHotels": settings.hotelbeds_max_hotels,
                "maxRatesPerRoom": settings.hotelbeds_max_rates_per_room,
            },
        }

        if request.max_total_price is not None:
            payload["filter"]["maxRate"] = request.max_total_price

        accommodations = self._hotelbeds_accommodation_types(request.accommodation_types)
        if accommodations:
            payload["accommodations"] = accommodations

        if request.min_rating is not None:
            # Hotelbeds review rating is commonly 1-5; our user-facing request uses 0-10.
            payload["reviews"] = [
                {
                    "type": "HOTELBEDS",
                    "minRate": max(1, min(5, round(request.min_rating / 2, 1))),
                    "minReviewCount": 1,
                }
            ]

        return payload

    def _coordinates_for_request(self, request: SearchRequest) -> tuple[float, float]:
        if request.target_coordinates and request.target_coordinates.lat is not None and request.target_coordinates.lng is not None:
            return request.target_coordinates.lat, request.target_coordinates.lng

        destination = request.destination.strip().lower()
        if destination in KNOWN_COORDINATES:
            return KNOWN_COORDINATES[destination]

        # Try a loose contains match, e.g. "Florenz Altstadt".
        for key, coords in KNOWN_COORDINATES.items():
            if key in destination:
                return coords

        raise ValueError(
            "No coordinates found for destination. Add it to KNOWN_COORDINATES in "
            "app/providers/hotelbeds.py or pass target_coordinates."
        )

    def _hotelbeds_accommodation_types(self, requested_types: list[str]) -> list[str]:
        values: list[str] = []
        for item in requested_types:
            values.extend(ACCOMMODATION_TYPE_MAP.get(item.lower(), []))
        return sorted(set(values))

    def _normalize_availability(self, data: dict[str, Any], request: SearchRequest) -> list[AccommodationResult]:
        hotels_container = data.get("hotels") or {}
        hotels = hotels_container.get("hotels") or []
        results: list[AccommodationResult] = []

        for hotel in hotels:
            selected = self._select_rate(hotel, request)
            if not selected:
                continue

            room, rate = selected
            result = self._result_from_hotel_rate(hotel, room, rate, request)
            results.append(result)

        return results

    def _select_rate(self, hotel: dict[str, Any], request: SearchRequest) -> tuple[dict[str, Any], dict[str, Any]] | None:
        candidates: list[tuple[dict[str, Any], dict[str, Any], float, CancellationCategory]] = []

        for room in hotel.get("rooms") or []:
            for rate in room.get("rates") or []:
                total = self._total_price(rate)
                if total is None:
                    continue
                category, _ = self._cancellation(rate, total)
                candidates.append((room, rate, total, category))

        if not candidates:
            return None

        must_be_flexible = "free_cancellation" in request.must_haves
        if must_be_flexible:
            flexible = [item for item in candidates if item[3] == CancellationCategory.free_cancellation]
            if flexible:
                candidates = flexible

        # Prefer actually bookable rates, then flexible rates, then lowest total price.
        def sort_key(item: tuple[dict[str, Any], dict[str, Any], float, CancellationCategory]) -> tuple[int, int, float]:
            _, rate, total, category = item
            recheck_penalty = 1 if str(rate.get("rateType", "")).upper() == "RECHECK" else 0
            cancellation_rank = {
                CancellationCategory.free_cancellation: 0,
                CancellationCategory.partially_refundable: 1,
                CancellationCategory.unknown: 2,
                CancellationCategory.non_refundable: 3,
            }[category]
            return (recheck_penalty, cancellation_rank, total)

        room, rate, _, _ = sorted(candidates, key=sort_key)[0]
        return room, rate

    def _result_from_hotel_rate(
        self,
        hotel: dict[str, Any],
        room: dict[str, Any],
        rate: dict[str, Any],
        request: SearchRequest,
    ) -> AccommodationResult:
        nights = max((request.checkout - request.checkin).days, 1)
        total_without_local_extras = self._base_price(rate) or self._total_price(rate) or 0.0
        mandatory_extra_costs = self._excluded_taxes(rate)
        total = total_without_local_extras + mandatory_extra_costs
        currency = hotel.get("currency") or rate.get("currency") or request.currency
        category, cancellation_text = self._cancellation(rate, total)
        free_until = self._free_until(rate)
        rating_score, review_count = self._rating(hotel)
        lat = self._float_or_none(hotel.get("latitude"))
        lng = self._float_or_none(hotel.get("longitude"))
        target_lat, target_lng = self._coordinates_for_request(request)
        distance = self._distance_km(lat, lng, target_lat, target_lng) if lat is not None and lng is not None else None

        amenities = self._amenities(rate, hotel, distance)
        risk_flags = self._risk_flags(rate, category, mandatory_extra_costs, review_count)
        comments = str(rate.get("rateComments") or "")
        if "deposit" in comments.lower():
            risk_flags.append("possible_deposit")

        price_notes = []
        city_tax_note = None
        if mandatory_extra_costs > 0:
            city_tax_note = f"Nicht alle lokalen Steuern/Gebühren sind im Rate-Preis enthalten: ca. {mandatory_extra_costs:.2f} {currency}."
            price_notes.append(city_tax_note)
        if str(rate.get("rateType", "")).upper() == "RECHECK":
            price_notes.append("Diese Rate hat rateType=RECHECK; vor einer echten Buchung sollte CheckRate ausgeführt werden.")

        payment = self._payment_text(rate)
        room_name = room.get("name") or room.get("code")
        hotel_name = hotel.get("name") or f"Hotelbeds Hotel {hotel.get('code')}"
        provider_id = str(hotel.get("code") or hotel_name)

        return AccommodationResult(
            id=f"hotelbeds:{provider_id}",
            provider="Hotelbeds",
            provider_property_id=provider_id,
            name=hotel_name,
            type=self._property_type(hotel, room),
            location=Location(
                city=hotel.get("destinationName"),
                address=None,
                lat=lat,
                lng=lng,
                distance_to_target_km=round(distance, 2) if distance is not None else None,
                area_summary=self._area_summary(hotel, distance),
            ),
            availability=Availability(
                available=True,
                checkin=request.checkin,
                checkout=request.checkout,
                room_name=room_name,
                remaining_rooms=rate.get("allotment"),
            ),
            price=Price(
                currency=currency,
                total=round(total, 2),
                per_night=round(total / nights, 2),
                taxes_included=self._taxes_all_included(rate),
                fees_included=self._taxes_all_included(rate),
                mandatory_extra_costs=round(mandatory_extra_costs, 2),
                city_tax_note=city_tax_note,
                price_notes=price_notes,
            ),
            rating=Rating(
                score=rating_score,
                review_count=review_count,
                source="Hotelbeds" if rating_score is not None else None,
            ),
            policies=Policies(
                cancellation_category=category,
                cancellation=cancellation_text,
                free_until=free_until,
                payment=payment,
                deposit="Nicht eindeutig aus Availability ersichtlich; RateComments/CheckRate vor Buchung prüfen.",
                checkin=None,
                checkout=None,
                house_rules=[comments] if comments else [],
            ),
            reviews_summary=ReviewSummary(
                positive_patterns=self._positive_patterns(hotel, rate, distance),
                negative_patterns=self._negative_patterns(rate, mandatory_extra_costs),
                review_risk_summary="Hotelbeds liefert hier strukturierte Verfügbarkeitsdaten; ausführliche Gästetexte sind im MVP noch nicht angebunden.",
                source="Hotelbeds",
            ),
            booking_url=None,
            amenities=amenities,
            risk_flags=risk_flags,
            provider_options=[
                ProviderOption(
                    provider="Hotelbeds",
                    total_price=round(total, 2),
                    currency=currency,
                    cancellation_category=category,
                    cancellation=cancellation_text,
                    payment=payment,
                    booking_url=None,
                    room_name=room_name,
                    breakfast_included=self._breakfast_included(rate),
                    notes=price_notes,
                )
            ],
            raw={"hotel": hotel, "room": room, "rate": rate},
        )

    def _base_price(self, rate: dict[str, Any]) -> float | None:
        for key in ("sellingRate", "net"):
            value = self._float_or_none(rate.get(key))
            if value is not None:
                return value
        return None

    def _total_price(self, rate: dict[str, Any]) -> float | None:
        base = self._base_price(rate)
        if base is None:
            return None
        return base + self._excluded_taxes(rate)

    def _excluded_taxes(self, rate: dict[str, Any]) -> float:
        taxes = (rate.get("taxes") or {}).get("taxes") or []
        total = 0.0
        for tax in taxes:
            if tax.get("included") is False:
                total += self._float_or_none(tax.get("clientAmount")) or self._float_or_none(tax.get("amount")) or 0.0
        return total

    def _taxes_all_included(self, rate: dict[str, Any]) -> bool | None:
        taxes = rate.get("taxes")
        if not taxes:
            return None
        return taxes.get("allIncluded")

    def _cancellation(self, rate: dict[str, Any], total: float) -> tuple[CancellationCategory, str]:
        promo_text = " ".join(str(item.get("name", "")) for item in rate.get("promotions") or []).lower()
        rate_class = str(rate.get("rateClass") or "").upper()
        if rate_class == "NRF" or "non-refundable" in promo_text or "non refundable" in promo_text:
            return CancellationCategory.non_refundable, "Nicht stornierbar laut Rate-Klasse/Promotion."

        policies = rate.get("cancellationPolicies") or []
        if not policies:
            return CancellationCategory.unknown, "Keine Stornierungsbedingungen in der Availability-Antwort gefunden."

        first = sorted(policies, key=lambda item: item.get("from", ""))[0]
        amount = self._float_or_none(first.get("amount")) or 0.0
        from_date = first.get("from")
        if amount >= total * 0.95:
            return CancellationCategory.free_cancellation, f"Kostenlos stornierbar bis {from_date}; danach vermutlich {amount:.2f} Gebühr."
        return CancellationCategory.partially_refundable, f"Teilweise stornierbar; erste Gebühr ca. {amount:.2f} ab {from_date}."

    def _free_until(self, rate: dict[str, Any]) -> datetime | None:
        policies = rate.get("cancellationPolicies") or []
        if not policies:
            return None
        value = sorted(policies, key=lambda item: item.get("from", ""))[0].get("from")
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _rating(self, hotel: dict[str, Any]) -> tuple[float | None, int | None]:
        reviews = hotel.get("reviews") or []
        if not reviews:
            return None, None
        review = reviews[0]
        raw_score = self._float_or_none(review.get("rate"))
        if raw_score is None:
            return None, review.get("reviewCount")
        # Hotelbeds reviews are often on a 1-5 scale. Our app uses 0-10.
        score = raw_score * 2 if raw_score <= 5 else raw_score
        return round(min(score, 10), 1), review.get("reviewCount")

    def _amenities(self, rate: dict[str, Any], hotel: dict[str, Any], distance: float | None) -> list[str]:
        amenities: set[str] = set()
        if self._breakfast_included(rate):
            amenities.add("breakfast")
        if distance is not None and distance <= 1.5:
            amenities.add("central_location")
        board_name = str(rate.get("boardName") or "").lower()
        if "all inclusive" in board_name:
            amenities.add("all_inclusive")
        if hotel.get("categoryName"):
            amenities.add(str(hotel["categoryName"]).lower().replace(" ", "_"))
        return sorted(amenities)

    def _breakfast_included(self, rate: dict[str, Any]) -> bool:
        board_code = str(rate.get("boardCode") or "").upper()
        board_name = str(rate.get("boardName") or "").lower()
        return board_code in BREAKFAST_BOARD_CODES or "breakfast" in board_name

    def _risk_flags(
        self,
        rate: dict[str, Any],
        cancellation_category: CancellationCategory,
        mandatory_extra_costs: float,
        review_count: int | None,
    ) -> list[str]:
        flags: list[str] = []
        if cancellation_category == CancellationCategory.non_refundable:
            flags.append("non_refundable")
        if str(rate.get("rateType", "")).upper() == "RECHECK":
            flags.append("rate_requires_recheck")
        if mandatory_extra_costs > 0:
            flags.append("local_taxes_not_included")
        if review_count is not None and review_count < 20:
            flags.append("low_review_count")
        flags.append("no_public_booking_link_hotelbeds_b2b")
        return flags

    def _payment_text(self, rate: dict[str, Any]) -> str | None:
        payment_type = str(rate.get("paymentType") or "")
        if payment_type == "AT_HOTEL":
            return "Zahlung im Hotel laut Hotelbeds-Rate."
        if payment_type == "AT_WEB":
            return "Zahlung über den Anbieter/Hotelbeds-Workflow laut Rate."
        return payment_type or None

    def _property_type(self, hotel: dict[str, Any], room: dict[str, Any]) -> str:
        text = " ".join(
            str(value or "")
            for value in [hotel.get("name"), hotel.get("categoryName"), room.get("name"), room.get("code")]
        ).lower()
        if "apartment" in text or "apart" in text or "apt" in text:
            return "apartment"
        if "hostel" in text:
            return "hostel"
        return "hotel"

    def _area_summary(self, hotel: dict[str, Any], distance: float | None) -> str:
        parts = []
        if hotel.get("zoneName"):
            parts.append(str(hotel["zoneName"]))
        if hotel.get("destinationName"):
            parts.append(str(hotel["destinationName"]))
        if distance is not None:
            parts.append(f"ca. {distance:.1f} km vom Suchzentrum entfernt")
        return ", ".join(parts) if parts else "Lage aus Hotelbeds-Koordinaten übernommen."

    def _positive_patterns(self, hotel: dict[str, Any], rate: dict[str, Any], distance: float | None) -> list[str]:
        patterns = ["Live-Verfügbarkeit über Hotelbeds gefunden"]
        if distance is not None and distance <= 1.5:
            patterns.append("zentrale Lage laut Koordinaten")
        if self._breakfast_included(rate):
            patterns.append("Verpflegung/Frühstück in der Rate enthalten")
        if hotel.get("categoryName"):
            patterns.append(str(hotel["categoryName"]))
        return patterns

    def _negative_patterns(self, rate: dict[str, Any], mandatory_extra_costs: float) -> list[str]:
        patterns = []
        if mandatory_extra_costs > 0:
            patterns.append("lokale Steuern/Gebühren möglicherweise zusätzlich zahlbar")
        if str(rate.get("rateType", "")).upper() == "RECHECK":
            patterns.append("Rate sollte vor Buchung erneut geprüft werden")
        if not patterns:
            patterns.append("keine ausführlichen Review-Texte im MVP verfügbar")
        return patterns

    def _float_or_none(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _distance_km(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c
