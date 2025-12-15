from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import date


class ImpactLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Category(str, Enum):
    PRICING = "Pricing"
    SECURITY = "Security"
    FEATURE_UPDATE = "Feature Update"
    COMPLIANCE = "Compliance"
    RETIREMENT = "Retirement"
    GENERAL = "General"


class AnnouncementMetadata(BaseModel):
    meta_date_effective: Optional[date] = Field(
        None, description="Policy effective date"
    )
    meta_products: List[str] = Field(
        default_factory=list, description="Related products"
    )
    meta_category: Optional[Category] = Field(None, description="Announcement category")
    meta_audience: List[str] = Field(
        default_factory=list, description="Target audience"
    )
    meta_impact_level: Optional[ImpactLevel] = Field(None, description="Impact level")
    meta_action_deadline: Optional[date] = Field(None, description="Action deadline")
    meta_summary: Optional[str] = Field(
        None, description="Summary in Traditional Chinese"
    )
    meta_change_type: Optional[str] = Field(
        None, description="Type of change e.g. Deprecation"
    )
    meta_date_announced: Optional[date] = Field(
        None, description="Announcement publication date"
    )


class AnnouncementDoc(BaseModel):
    uuid: str = Field(..., description="Unique identifier")
    month: str = Field(..., description="Month of the announcement e.g. 2025-12")
    title: str = Field(..., description="Announcement title")
    link: Optional[str] = Field(None, description="Source URL")
    original_content: str = Field(..., description="Original raw content")

    # Metadata fields flattened or nested - adhering to the spec's flat structure illustration
    # but using the Metadata class as a container might be cleaner.
    # However, for flat storage in SQLite, mixing them is fine.
    # Let's include the metadata object directly to be Pythonic,
    # and we can flatten it for SQLite storage later.
    metadata: AnnouncementMetadata = Field(..., description="Extracted metadata")
