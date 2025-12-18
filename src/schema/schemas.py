from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import date


# Simplified schema matching parse.example.json format
class AnnouncementDoc(BaseModel):
    """
    Simplified announcement document schema.
    Matches the new parse.json format without complex metadata.
    """
    link: str = Field(..., description="Source URL")
    year_month: str = Field(..., alias="year-month", description="Year and month e.g. 2025-12")
    workspace: str = Field(..., alias="Workspace", description="Workspace category e.g. General")
    title: str = Field(..., description="Announcement title")
    content: str = Field(..., description="Original content")
    cleaned_content: str = Field(..., description="Cleaned content for search and embedding")

    class Config:
        populate_by_name = True  # Allow field population by alias or name


# Legacy schemas - kept for backward compatibility if needed
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


class LegacyAnnouncementDoc(BaseModel):
    """Legacy schema with complex metadata - deprecated"""
    id: str = Field(..., description="Unique identifier")
    month: str = Field(..., description="Month of the announcement e.g. 2025-12")
    title: str = Field(..., description="Announcement title")
    link: Optional[str] = Field(None, description="Source URL")
    original_content: str = Field(..., description="Original raw content")
    content_clean: Optional[str] = Field(
        None,
        description="Cleaned content with URLs removed/simplified (used for search and embedding)"
    )
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

    year_months: List[str] = Field(
        default_factory=list,
        description="List of year-months (YYYY-MM format). For ranges like 'past 3 months', include all months.",
    )
    links: List[str] = Field(
        default_factory=list,
        description="List of source URLs to filter by.",
    )
    workspaces: List[str] = Field(
        default_factory=list,
        description="List of workspaces to filter by e.g. General, Security",
    )
    # Legacy filters - kept for backward compatibility
    category: Optional[Category] = Field(None, description="Category (legacy)")
    impact_level: Optional[ImpactLevel] = Field(None, description="Impact Level (legacy)")


class SearchIntent(BaseModel):
    """Structured search intent parsed from user query"""

    filters: SearchFilters = Field(..., description="Strict filters to apply")
    keyword_query: str = Field(..., description="Optimized keyword query for FTS")
    semantic_query: str = Field(
        ..., description="Optimized semantic query for Vector DB"
    )
    must_have_keywords: List[str] = Field(
        default_factory=list,
        description="Critical keywords that MUST be present in the document (enforces exact match/presence)",
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
