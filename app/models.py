from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SortPreference(str, Enum):
    best_value = "best_value"
    cheapest = "cheapest"
    highest_rated = "highest_rated"
    most_flexible = "most_flexible"
    best_location = "best_location"


class CancellationCategory(str, Enum):
    free_cancellation = "free_cancellation"
    partially_refundable = "partially_refundable"
    non_refundable = "non_refundable"
    unknown = "unknown"


class Coordinates(BaseModel):
    lat: float | None = None
    lng: float | None = None


class SearchRequest(BaseModel):
    destination: str = Field(..., examples=["Florenz"])
    checkin: date = Field(..., examples=["2026-09-12"])
    checkout: date = Field(..., examples=["2026-09-16"])
    adults: int = Field(..., ge=1, examples=[2])
    children: int = Field(default=0, ge=0)
    rooms: int = Field(default=1, ge=1)
    max_total_price: float | None = Field(default=None, gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    min_rating: float | None = Field(default=None, ge=0, le=10)
    accommodation_types: list[str] = Field(default_factory=list, examples=[["hotel", "apartment"]])
    must_haves: list[str] = Field(default_factory=list, examples=[["free_cancellation", "central_location"]])
    nice_to_haves: list[str] = Field(default_factory=list, examples=[["breakfast", "parking"]])
    no_gos: list[str] = Field(default_factory=list, examples=[["noise_complaints", "high_deposit"]])
    sort_preference: SortPreference = SortPreference.best_value
    max_results: int = Field(default=7, ge=1, le=20)
    target_location: str | None = Field(default=None, examples=["Dom / Altstadt"])
    target_coordinates: Coordinates | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_dates(self):
        if self.checkout <= self.checkin:
            raise ValueError("checkout must be after checkin")
        return self


class Location(BaseModel):
    city: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    distance_to_target_km: float | None = None
    area_summary: str | None = None


class Availability(BaseModel):
    available: bool = True
    checkin: date
    checkout: date
    room_name: str | None = None
    remaining_rooms: int | None = None


class Price(BaseModel):
    currency: str = "EUR"
    total: float
    per_night: float
    taxes_included: bool | None = None
    fees_included: bool | None = None
    mandatory_extra_costs: float | None = None
    city_tax_note: str | None = None
    price_notes: list[str] = Field(default_factory=list)


class Rating(BaseModel):
    score: float | None = Field(default=None, ge=0, le=10)
    review_count: int | None = Field(default=None, ge=0)
    source: str | None = None
    category_scores: dict[str, float] = Field(default_factory=dict)


class Policies(BaseModel):
    cancellation_category: CancellationCategory = CancellationCategory.unknown
    cancellation: str | None = None
    free_until: datetime | None = None
    payment: str | None = None
    deposit: str | None = None
    checkin: str | None = None
    checkout: str | None = None
    house_rules: list[str] = Field(default_factory=list)


class ReviewSummary(BaseModel):
    positive_patterns: list[str] = Field(default_factory=list)
    negative_patterns: list[str] = Field(default_factory=list)
    review_risk_summary: str | None = None
    source: str | None = None


class ProviderOption(BaseModel):
    provider: str
    total_price: float
    currency: str = "EUR"
    cancellation_category: CancellationCategory = CancellationCategory.unknown
    cancellation: str | None = None
    payment: str | None = None
    booking_url: str | None = None
    room_name: str | None = None
    breakfast_included: bool | None = None
    notes: list[str] = Field(default_factory=list)


class AccommodationResult(BaseModel):
    id: str
    provider: str
    provider_property_id: str | None = None
    name: str
    type: str | None = None
    location: Location
    availability: Availability
    price: Price
    rating: Rating
    policies: Policies = Field(default_factory=Policies)
    reviews_summary: ReviewSummary = Field(default_factory=ReviewSummary)
    booking_url: str | None = None
    amenities: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    provider_options: list[ProviderOption] = Field(default_factory=list)
    score: float | None = None
    why_recommended: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class SearchSummary(BaseModel):
    destination: str
    checkin: date
    checkout: date
    guests: str
    rooms: int
    results_checked: int
    available_results: int
    returned_results: int
    currency: str
    price_last_checked: datetime
    notes: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    search_summary: SearchSummary
    results: list[AccommodationResult]
    relaxation_suggestions: list[str] = Field(default_factory=list)
