from typing import List, Optional
from pydantic import BaseModel, Field


class AnnouncementDoc(BaseModel):
    """
    Simplified announcement document schema.
    """

    id: str = Field(..., description="Unique document ID")
    link: str = Field(..., description="Source URL")
    year: Optional[str] = Field(None, description="Year e.g. 2025")
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
    website: str = Field(..., min_length=1, description="Website source description")

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
    websites: List[str] = Field(
        default_factory=list,
        description="List of website source descriptions to filter by.",
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
    websites: List[str] = Field(
        default_factory=list,
        description="List of websites to filter by e.g. ['azure_update', 'partner_center']",
    )
    sub_queries: List[str] = Field(
        default_factory=list,
        description="List of 3-5 sub-queries (natural language) to broaden the search scope. Each should focus on a different aspect (e.g. specific product, specific issue type, broad intent).",
    )
    direction: str = Field(
        default="",
        description="Search direction or focus provided by previous search attempts to guide the next search.",
    )


class RetrySearchDecision(BaseModel):
    """Result from search evaluation to decide if retry is needed"""

    relevant: bool = Field(
        ...,
        description="Whether the current documents are enough to answer the user's query clearly.",
    )
    search_direction: str = Field(
        default="",
        description="If relevant=False, provide a specific direction or focus for the next search attempt (in Chinese).",
    )
    decision: str = Field(
        default="",
        description="Decision explanation in Chinese (10-20 characters).",
    )


class StructuredSummary(BaseModel):
    """Structured summary response with three parts"""

    brief_answer: str = Field(
        ...,
        description="Brief answer to the query (max 20 characters). Return '沒有參考資料' if no results, or '從內容搜索不到' if results exist but are irrelevant.",
    )
    detailed_answer: str = Field(
        default="",
        description="Detailed answer with citations using [index] (only use half-width square brackets, NO full-width brackets like 【1】). Empty if no results. If results are irrelevant, explain what the content is about and why it doesn't answer the question.",
    )
    general_summary: str = Field(
        default="",
        description="General summary of all search results (max 500 characters), independent of the query. Empty if no results.",
    )
