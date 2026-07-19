from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .models import ProviderProfileStatus, SubscriptionVisibilityStatus


class ProviderOnboarding(BaseModel):
    display_name: str = Field(min_length=2, max_length=180)
    business_name: str | None = Field(default=None, max_length=180)
    bio: str | None = Field(default=None, max_length=3000)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    base_address_id: UUID | None = None


class ProviderProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=180)
    business_name: str | None = Field(default=None, max_length=180)
    bio: str | None = Field(default=None, max_length=3000)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    base_address_id: UUID | None = None

    @model_validator(mode="after")
    def has_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class PortfolioItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(min_length=10, max_length=2000)
    position: int = Field(default=0, ge=0, le=100)


class PortfolioItemView(BaseModel):
    id: UUID
    title: str
    description: str
    position: int


class ProviderProfileView(BaseModel):
    id: UUID
    display_name: str
    slug: str
    business_name: str | None
    bio: str | None
    experience_years: int | None
    base_address_id: UUID | None
    profile_status: ProviderProfileStatus
    subscription_visibility_status: SubscriptionVisibilityStatus
    rating_average: float
    rating_count: int
    completed_services_count: int
    response_rate: float
    average_response_minutes: int | None
    profile_completeness: int
    is_identity_verified: bool
    is_paused: bool
    portfolio: list[PortfolioItemView]


class ProviderPauseRequest(BaseModel):
    paused: bool


class ProviderProfileNotFound(BaseModel):
    detail: str = "Provider profile not found"
