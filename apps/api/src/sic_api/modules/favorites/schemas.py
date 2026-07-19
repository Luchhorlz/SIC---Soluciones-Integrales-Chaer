from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FavoriteProviderView(BaseModel):
    id: UUID
    provider_slug: str
    display_name: str
    business_name: str | None
    rating_average: float
    rating_count: int
    is_identity_verified: bool
    created_at: datetime
