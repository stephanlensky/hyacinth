from pydantic import BaseModel

from hyacinth.models import BaseListing, BaseSearchParams


class MarketplaceListing(BaseListing):
    title: str
    url: str
    body: str
    image_urls: list[str]
    thumbnail_url: str | None = None
    price: float
    city: str | None = None
    state: str | None = None
    latitude: float
    longitude: float


class MarketplaceCategory(BaseModel):
    id: str
    name: str
    seo_url: str | None
    parent_id: str | None = None


class MarketplaceSearchParams(BaseSearchParams):
    location: str  # URL part - can be id or vanity url
    category: str  # URL part - can be id or seo url
