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
    meta_summary_segmented: Optional[str] = Field(
        None, description="Segmented summary for better keyword search (jieba)"
    )
    meta_change_type: Optional[str] = Field(
        None, description="Type of change e.g. Deprecation"
    )
    meta_date_announced: Optional[date] = Field(
        None, description="Announcement publication date"
    )


class AnnouncementDoc(BaseModel):
    id: str = Field(..., description="Unique identifier")
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


# LLM Extraction Schemas (用於批量 ETL)
class MetadataExtraction(BaseModel):
    """單個公告的 Metadata 提取結果（LLM 輸出格式）"""

    id: str = Field(..., description="Original ID from input")
    meta_date_effective: Optional[str] = Field(
        None, description="Policy effective date (YYYY-MM-DD)"
    )
    meta_date_announced: Optional[str] = Field(
        None, description="Announcement publication date (YYYY-MM-DD)"
    )
    meta_products: List[str] = Field(
        default_factory=list, description="Related products (English names)"
    )
    meta_audience: List[str] = Field(
        default_factory=list, description="Target audience roles"
    )
    meta_category: Optional[str] = Field(
        None,
        description="One of: Pricing, Security, Feature Update, Compliance, Retirement, General",
    )
    meta_impact_level: Optional[str] = Field(
        None, description="Impact level: High, Medium, or Low"
    )
    meta_action_deadline: Optional[str] = Field(
        None, description="Action deadline (YYYY-MM-DD)"
    )
    meta_summary: Optional[str] = Field(
        None, description="Concise summary in Traditional Chinese"
    )
    meta_change_type: Optional[str] = Field(
        None, description="Type of change (e.g., Deprecation, New Feature)"
    )


class BatchMetaExtraction(BaseModel):
    """批量 Metadata 提取的完整回應格式"""

    results: List[MetadataExtraction] = Field(
        ..., min_length=1, max_length=10, description="List of extracted metadata"
    )


class SearchFilters(BaseModel):
    """Search filters extracted from user query (STRICT filters only)"""

    months: List[str] = Field(
        default_factory=list,
        description="List of months (YYYY-MM format). For ranges like 'past 3 months', include all months.",
    )
    category: Optional[Category] = Field(None, description="Category")
    impact_level: Optional[ImpactLevel] = Field(None, description="Impact Level")


class SearchIntent(BaseModel):
    """Structured search intent parsed from user query"""

    filters: SearchFilters = Field(..., description="Strict filters to apply")
    keyword_query: str = Field(..., description="Optimized keyword query for FTS")
    semantic_query: str = Field(
        ..., description="Optimized semantic query for Vector DB"
    )
    boost_keywords: List[str] = Field(
        default_factory=list,
        description="Soft-match keywords (e.g., product names) to boost relevance, not filter",
    )
    limit: Optional[int] = Field(None, description="Max results to return")
    recommended_semantic_ratio: Optional[float] = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Recommended weight for semantic search (0.0=pure keyword, 1.0=pure semantic, 0.5=balanced)",
    )
