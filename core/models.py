"""Portfolio data models and deterministic authorization rules."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class VisibilityTier(str, Enum):
    PUBLIC = "public"
    SIGNED_IN = "signed_in"
    SELECTED = "selected"
    OWNER_ONLY = "owner_only"


class PortfolioItem(BaseModel):
    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    repo_url: str | None = None
    demo_url: str | None = None
    screenshot_url: str | None = None
    visibility: VisibilityTier = VisibilityTier.PUBLIC
    allowed_visitors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_allowed_visitors(self) -> "PortfolioItem":
        self.allowed_visitors = sorted(
            {visitor.strip().lower() for visitor in self.allowed_visitors if visitor.strip()}
        )
        return self


class PortfolioStore(BaseModel):
    owner_name: str
    beagle_handle: str
    items: list[PortfolioItem] = Field(default_factory=list)


def filter_items_for_visitor(
    store: PortfolioStore,
    visitor_email: str | None = None,
    is_owner: bool = False,
) -> list[PortfolioItem]:
    """Return only records authorized for the current identity."""
    if is_owner:
        return list(store.items)

    normalized_email = visitor_email.strip().lower() if visitor_email else None
    allowed: list[PortfolioItem] = []
    for item in store.items:
        if item.visibility == VisibilityTier.PUBLIC:
            allowed.append(item)
        elif item.visibility == VisibilityTier.SIGNED_IN and normalized_email:
            allowed.append(item)
        elif (
            item.visibility == VisibilityTier.SELECTED
            and normalized_email
            and normalized_email in item.allowed_visitors
        ):
            allowed.append(item)
    return allowed

