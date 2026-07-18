from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AddressCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    formatted_address: str = Field(min_length=5, max_length=500)
    street: str = Field(min_length=1, max_length=180)
    street_number: str = Field(min_length=1, max_length=30)
    unit: str | None = Field(default=None, max_length=50)
    city: str = Field(min_length=1, max_length=120)
    administrative_area: str | None = Field(default=None, max_length=120)
    province: str = Field(min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    country_code: str = Field(default="AR", min_length=2, max_length=2)
    google_place_id: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    formatted_address: str | None = Field(default=None, min_length=5, max_length=500)
    street: str | None = Field(default=None, min_length=1, max_length=180)
    street_number: str | None = Field(default=None, min_length=1, max_length=30)
    unit: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    administrative_area: str | None = Field(default=None, max_length=120)
    province: str | None = Field(default=None, min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    google_place_id: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_default: bool | None = None

    @model_validator(mode="after")
    def coordinates_are_paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        if "google_place_id" in self.model_fields_set and self.google_place_id is None:
            raise ValueError("google_place_id cannot be cleared")
        return self


class AddressView(BaseModel):
    id: UUID
    label: str
    formatted_address: str
    street: str
    street_number: str
    unit: str | None
    city: str
    administrative_area: str | None
    province: str
    postal_code: str | None
    country_code: str
    google_place_id: str
    latitude: float
    longitude: float
    is_default: bool
