from datetime import datetime, time, timedelta

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
from app.providers.base import AccommodationProvider


class MockProvider(AccommodationProvider):
    name = "mock"

    async def search(self, request: SearchRequest) -> list[AccommodationResult]:
        nights = (request.checkout - request.checkin).days
        destination = request.destination
        free_until = datetime.combine(request.checkin - timedelta(days=5), time(23, 59))

        return [
            AccommodationResult(
                id="mock-palazzo-verde",
                provider=self.name,
                provider_property_id="mock-001",
                name=f"Palazzo Verde {destination}",
                type="hotel",
                location=Location(
                    city=destination,
                    address="Via Centrale 12",
                    lat=43.771,
                    lng=11.255,
                    distance_to_target_km=0.7,
                    area_summary="Sehr zentrale Lage, gut zu Fuß zu den wichtigsten Sehenswürdigkeiten.",
                ),
                availability=Availability(
                    available=True,
                    checkin=request.checkin,
                    checkout=request.checkout,
                    room_name="Classic Doppelzimmer",
                    remaining_rooms=2,
                ),
                price=Price(
                    currency=request.currency,
                    total=842.0,
                    per_night=round(842.0 / nights, 2),
                    taxes_included=True,
                    fees_included=True,
                    mandatory_extra_costs=0,
                    city_tax_note="City Tax kann vor Ort zusätzlich anfallen.",
                ),
                rating=Rating(score=8.9, review_count=1240, source="mock_reviews"),
                policies=Policies(
                    cancellation_category=CancellationCategory.free_cancellation,
                    cancellation="Kostenlos stornierbar bis 5 Tage vor Anreise.",
                    free_until=free_until,
                    payment="Zahlung vor Ort möglich; Kreditkarte zur Garantie erforderlich.",
                    deposit="Keine Kaution angegeben.",
                    checkin="15:00–22:00",
                    checkout="bis 11:00",
                ),
                reviews_summary=ReviewSummary(
                    positive_patterns=["zentrale Lage", "sehr sauber", "freundliches Personal"],
                    negative_patterns=["Zimmer eher klein", "gelegentlich Straßenlärm"],
                    review_risk_summary="Lärm wird erwähnt, wirkt aber nicht dominant.",
                    source="mock_reviews",
                ),
                amenities=["free_cancellation", "wifi", "air_conditioning", "central_location"],
                risk_flags=["some_noise_mentions"],
                booking_url="https://example.com/palazzo-verde",
                provider_options=[
                    ProviderOption(
                        provider="MockTravel",
                        total_price=842.0,
                        currency=request.currency,
                        cancellation_category=CancellationCategory.free_cancellation,
                        cancellation="Kostenlos stornierbar bis 5 Tage vor Anreise.",
                        booking_url="https://example.com/palazzo-verde",
                        room_name="Classic Doppelzimmer",
                    ),
                    ProviderOption(
                        provider="MockRooms",
                        total_price=819.0,
                        currency=request.currency,
                        cancellation_category=CancellationCategory.non_refundable,
                        cancellation="Nicht stornierbar.",
                        booking_url="https://example.com/palazzo-verde-cheap",
                        room_name="Classic Doppelzimmer",
                    ),
                ],
            ),
            AccommodationResult(
                id="mock-casa-luce",
                provider=self.name,
                provider_property_id="mock-002",
                name=f"Casa Luce Apartment {destination}",
                type="apartment",
                location=Location(
                    city=destination,
                    address="Borgo Tranquillo 4",
                    lat=43.775,
                    lng=11.248,
                    distance_to_target_km=1.6,
                    area_summary="Ruhige Wohnlage mit guter ÖPNV-Anbindung ins Zentrum.",
                ),
                availability=Availability(
                    available=True,
                    checkin=request.checkin,
                    checkout=request.checkout,
                    room_name="Apartment mit 1 Schlafzimmer",
                    remaining_rooms=1,
                ),
                price=Price(
                    currency=request.currency,
                    total=760.0,
                    per_night=round(760.0 / nights, 2),
                    taxes_included=True,
                    fees_included=True,
                    mandatory_extra_costs=45,
                    city_tax_note="City Tax kann vor Ort zusätzlich anfallen.",
                    price_notes=["Reinigungsgebühr im Gesamtpreis enthalten."],
                ),
                rating=Rating(score=9.1, review_count=320, source="mock_reviews"),
                policies=Policies(
                    cancellation_category=CancellationCategory.partially_refundable,
                    cancellation="Teilweise erstattbar; Details vor Buchung prüfen.",
                    payment="Vorauszahlung möglich.",
                    deposit="Kaution: 150 € möglich.",
                    checkin="16:00–20:00, später Check-in nach Absprache",
                    checkout="bis 10:00",
                    house_rules=["Keine Partys", "Nichtraucherunterkunft"],
                ),
                reviews_summary=ReviewSummary(
                    positive_patterns=["ruhige Lage", "gute Ausstattung", "sehr sauber"],
                    negative_patterns=["Check-in-Zeitfenster eng", "Kaution wird vereinzelt erwähnt"],
                    review_risk_summary="Gute Wahl, wenn eine Wohnung wichtiger ist als maximale Flexibilität.",
                    source="mock_reviews",
                ),
                amenities=["kitchen", "wifi", "quiet_location", "washing_machine"],
                risk_flags=["possible_deposit", "limited_checkin_window"],
                booking_url="https://example.com/casa-luce",
                provider_options=[
                    ProviderOption(
                        provider="MockStay",
                        total_price=760.0,
                        currency=request.currency,
                        cancellation_category=CancellationCategory.partially_refundable,
                        cancellation="Teilweise erstattbar.",
                        booking_url="https://example.com/casa-luce",
                        room_name="Apartment mit 1 Schlafzimmer",
                    )
                ],
            ),
            AccommodationResult(
                id="mock-grand-stazione",
                provider=self.name,
                provider_property_id="mock-003",
                name=f"Grand Hotel Stazione {destination}",
                type="hotel",
                location=Location(
                    city=destination,
                    address="Piazza Stazione 2",
                    lat=43.776,
                    lng=11.247,
                    distance_to_target_km=1.0,
                    area_summary="Sehr praktisch am Bahnhof gelegen, ideal für Anreise mit Zug.",
                ),
                availability=Availability(
                    available=True,
                    checkin=request.checkin,
                    checkout=request.checkout,
                    room_name="Standard Doppelzimmer",
                    remaining_rooms=4,
                ),
                price=Price(
                    currency=request.currency,
                    total=690.0,
                    per_night=round(690.0 / nights, 2),
                    taxes_included=False,
                    fees_included=True,
                    mandatory_extra_costs=0,
                    city_tax_note="Steuern/City Tax müssen vor Buchung geprüft werden.",
                ),
                rating=Rating(score=8.4, review_count=2200, source="mock_reviews"),
                policies=Policies(
                    cancellation_category=CancellationCategory.non_refundable,
                    cancellation="Nicht stornierbar bei günstigster Rate.",
                    payment="Sofortzahlung erforderlich.",
                    deposit="Keine Kaution angegeben.",
                    checkin="14:00–24:00",
                    checkout="bis 11:00",
                ),
                reviews_summary=ReviewSummary(
                    positive_patterns=["gute Verkehrsanbindung", "solides Preis-Leistungs-Verhältnis"],
                    negative_patterns=["teilweise laut", "Zimmer etwas älter"],
                    review_risk_summary="Preislich gut, aber schwächer bei Flexibilität und Ruhe.",
                    source="mock_reviews",
                ),
                amenities=["wifi", "late_checkin", "near_train_station"],
                risk_flags=["noise_complaints", "non_refundable"],
                booking_url="https://example.com/grand-stazione",
                provider_options=[
                    ProviderOption(
                        provider="MockTravel",
                        total_price=690.0,
                        currency=request.currency,
                        cancellation_category=CancellationCategory.non_refundable,
                        cancellation="Nicht stornierbar.",
                        booking_url="https://example.com/grand-stazione",
                        room_name="Standard Doppelzimmer",
                    )
                ],
            ),
        ]
