from typing import List, Optional
from pydantic import BaseModel, Field


class AnnouncementDoc(BaseModel):
    """
    Simplified announcement document schema.
    """

    link: str = Field(..., description="Source URL")
    year_month: str = Field(
        ..., alias="year_month", description="Year and month e.g. 2025-12"
    )
    workspace: str = Field(
        ..., alias="Workspace", description="Workspace category e.g. General"
    )
    title: str = Field(..., description="Announcement title")
    content: str = Field(..., description="Original content")
    cleaned_content: str = Field(
        ..., description="Cleaned content for search and embedding"
    )

    class Config:
        populate_by_name = True


class SearchIntent(BaseModel):
    """Structured search intent parsed from user query"""

    year_month: List[str] = Field(
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
        None,
        ge=0.0,
        le=1.0,
        description="Recommended weight for semantic search (0.0=pure keyword, 1.0=pure semantic, 0.5=balanced)",
    )
