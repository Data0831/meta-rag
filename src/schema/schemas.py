from typing import List, Optional
from pydantic import BaseModel, Field


class AnnouncementDoc(BaseModel):
    """
    Simplified announcement document schema.
    """

    id: str = Field(..., description="Unique document ID")
    link: str = Field(..., description="Source URL")
    year: str = Field(..., description="Year e.g. 2025")
    year_month: str = Field(
        ..., alias="year_month", description="Year and month e.g. 2025-12"
    )
    workspace: Optional[str] = Field(
        None, alias="Workspace", description="Workspace category e.g. General"
    )
    title: str = Field(..., description="Announcement title")
    main_title: str = Field(..., description="Main title of the page")
    heading_link: str = Field(..., description="Link with hash fragment")
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
    year: List[str] = Field(
        default_factory=list,
        description="List of years (YYYY format). Only use when user specifies a year without a specific month.",
    )
    links: List[str] = Field(
        default_factory=list,
        description="List of source URLs to filter by.",
    )
    keyword_query: str = Field(..., description="Optimized keyword query for FTS")
    semantic_query: str = Field(
        ..., description="Optimized semantic query for Vector DB"
    )
    must_have_keywords: List[str] = Field(
        default_factory=list,
        description="Critical keywords that MUST be present in the document (enforces exact match/presence)",
    )
    limit: Optional[int] = Field(None, description="Max results to return")
    recommended_semantic_ratio: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Recommended weight for semantic search (0.0=pure keyword, 1.0=pure semantic, 0.5=balanced)",
    )
