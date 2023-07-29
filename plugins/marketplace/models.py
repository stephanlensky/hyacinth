from pydantic import BaseModel

from hyacinth.models import BaseListing, BaseSearchParams


class MarketplaceListing(BaseListing):
    title: str


class MarketplaceCategory(BaseModel):
    id: str
    name: str
    seo_url: str | None
    parent_id: str | None = None


class MarketplaceSearchParams(BaseSearchParams):
    location: str  # URL part - can be id or vanity url
    category: str | None  # URL part - can be id or seo url
