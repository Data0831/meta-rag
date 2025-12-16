"""
Meilisearch Database Adapter
Unified search engine for hybrid search (keyword + semantic + filters)
"""

import meilisearch
from typing import List, Dict, Any, Optional
from src.schema.schemas import AnnouncementDoc, SearchFilters
from src.meilisearch_config import (
    RANKING_RULES,
    FILTERABLE_ATTRIBUTES,
    SEARCHABLE_ATTRIBUTES,
    EMBEDDING_CONFIG,
    DEFAULT_SEMANTIC_RATIO,
)
import json


class MeiliAdapter:
    """
    Meilisearch Adapter for unified hybrid search.
    Handles both keyword search (with fuzzy matching) and semantic vector search.
    """

    def __init__(
        self,
        host: str = "http://localhost:7700",
        api_key: str = "masterKey",
        collection_name: str = "announcements",
    ):
        self.client = meilisearch.Client(host, api_key)
        self.collection_name = collection_name
        self.index = self.client.index(collection_name)
        self._configure_index()

    def _configure_index(self):
        """
        Configure the Meilisearch index with filterable attributes and vector search.
        This is called during initialization to ensure the index is properly configured.
        """
        try:
            # 1. Set filterable attributes (required for filtering)
            self.index.update_filterable_attributes(FILTERABLE_ATTRIBUTES)

            # 2. Set searchable attributes (for keyword search)
            self.index.update_searchable_attributes(SEARCHABLE_ATTRIBUTES)

            # 3. Enable vector search (Hybrid Search)
            self.index.update_embedders({"default": EMBEDDING_CONFIG})

            # 4. Set ranking rules to balance keyword and semantic search
            # Meilisearch uses these rules to determine the order of results
            self.index.update_ranking_rules(RANKING_RULES)

            print(
                f"✓ Meilisearch index '{self.collection_name}' configured successfully."
            )

        except Exception as e:
            print(f"Warning: Error configuring Meilisearch index: {e}")
            print("Index may need manual configuration via Meilisearch dashboard.")

    def upsert_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Upsert documents into Meilisearch.

        Expected document format:
        {
            "id": "id-string",
            "title": "...",
            "content": "...",
            "month": "YYYY-monthname",
            "link": "...",
            "metadata": {
                "meta_category": "...",
                "meta_impact_level": "...",
                ...
            },
            "_vectors": {
                "default": [0.1, 0.2, ...]  # 1024-dim vector
            }
        }

        Args:
            documents: List of document dictionaries with _vectors field
        """
        if not documents:
            print("No documents to upsert.")
            return

        try:
            # Meilisearch add_documents performs upsert automatically (based on 'id' field)
            task_info = self.index.add_documents(documents, primary_key="id")
            print(f"✓ Upserted {len(documents)} documents to Meilisearch.")
            print(f"  Task UID: {task_info.task_uid}")

        except Exception as e:
            print(f"Error upserting documents to Meilisearch: {e}")
            raise

    def search(
        self,
        query: str,
        vector: Optional[List[float]] = None,
        filters: Optional[str] = None,
        limit: int = 20,
        semantic_ratio: float = DEFAULT_SEMANTIC_RATIO,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search on Meilisearch.

        Args:
            query: Keyword query string
            vector: Query embedding vector (optional, for semantic search)
            filters: Filter expression in Meilisearch syntax
                     e.g., "month IN ['2025-november'] AND metadata.meta_category = 'Security'"
            limit: Maximum number of results to return
            semantic_ratio: Weight for semantic search (0.0 = pure keyword, 1.0 = pure semantic)
                            Default 0.5 means equal weight for keyword and semantic

        Returns:
            List of matching documents with scores and highlights
        """
        search_params = {
            "limit": limit,
            "attributesToRetrieve": ["*"],  # Return all fields
            "showRankingScore": True,  # Include ranking scores
            "showRankingScoreDetails": True,  # Include score breakdown
        }

        # Add filter if provided
        if filters:
            search_params["filter"] = filters

        # Add hybrid search if vector is provided
        if vector:
            search_params["hybrid"] = {
                "semanticRatio": semantic_ratio,
                "embedder": "default",
            }
            search_params["vector"] = vector

        try:
            results = self.index.search(query, search_params)
            return results["hits"]

        except Exception as e:
            print(f"Meilisearch search error: {e}")
            return []

    def reset_index(self) -> None:
        """
        Delete all documents from the index.
        This is useful for re-indexing from scratch.
        """
        try:
            task_info = self.index.delete_all_documents()
            print(f"✓ Deleted all documents from '{self.collection_name}'.")
            print(f"  Task UID: {task_info.task_uid}")

        except Exception as e:
            print(f"Error resetting Meilisearch index: {e}")
            raise

    def get_documents_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch full documents by a list of IDs.

        Args:
            ids: List of document IDs (ids)

        Returns:
            List of document dictionaries
        """
        if not ids:
            return []

        try:
            # Meilisearch doesn't have a built-in batch get by IDs
            # We use a filter to get documents by IDs
            # Note: This may not be the most efficient way for large lists
            id_filter = " OR ".join([f'id = "{doc_id}"' for doc_id in ids])

            results = self.index.search(
                "",  # Empty query
                {
                    "filter": id_filter,
                    "limit": len(ids),
                    "attributesToRetrieve": ["*"],
                },
            )

            return results["hits"]

        except Exception as e:
            print(f"Error fetching documents by IDs: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Meilisearch index.

        Returns:
            Dictionary with index statistics
        """
        try:
            stats = self.index.get_stats()
            # Convert Pydantic model to dict if needed
            if hasattr(stats, "model_dump"):
                return stats.model_dump()
            elif hasattr(stats, "dict"):
                return stats.dict()
            return stats

        except Exception as e:
            print(f"Error getting index stats: {e}")
            return {}


def build_meili_filter(filters: SearchFilters) -> Optional[str]:
    """
    Convert SearchFilters to Meilisearch filter syntax.

    Args:
        filters: SearchFilters object

    Returns:
        Filter string in Meilisearch syntax, or None if no filters

    Examples:
        - months=['2025-11'] -> "month IN ['2025-11']"
        - category='Security' -> "metadata.meta_category = 'Security'"
        - Combined -> "month IN ['2025-11'] AND metadata.meta_category = 'Security'"
    """
    conditions = []

    # Month filters (OR condition for multiple months)
    if filters.months:
        months_str = ", ".join([f"'{m}'" for m in filters.months])
        conditions.append(f"month IN [{months_str}]")

    # Category filter
    if filters.category:
        cat_val = (
            filters.category.value
            if hasattr(filters.category, "value")
            else filters.category
        )
        conditions.append(f"metadata.meta_category = '{cat_val}'")

    # Impact level filter
    if filters.impact_level:
        impact_val = (
            filters.impact_level.value
            if hasattr(filters.impact_level, "value")
            else filters.impact_level
        )
        conditions.append(f"metadata.meta_impact_level = '{impact_val}'")

    return " AND ".join(conditions) if conditions else None


def transform_doc_for_meilisearch(
    doc: AnnouncementDoc, embedding_vector: List[float]
) -> Dict[str, Any]:
    """
    Transform AnnouncementDoc to Meilisearch document format.

    Args:
        doc: AnnouncementDoc object
        embedding_vector: Embedding vector for the document

    Returns:
        Dictionary in Meilisearch format with _vectors field
    """
    meta = doc.metadata

    # Serialize metadata to dict
    metadata_dict = meta.model_dump() if hasattr(meta, "model_dump") else meta.dict()

    # Convert dates to strings for JSON compatibility
    for date_field in [
        "meta_date_effective",
        "meta_action_deadline",
        "meta_date_announced",
    ]:
        if metadata_dict.get(date_field):
            metadata_dict[date_field] = str(metadata_dict[date_field])

    # Convert enums to strings
    if metadata_dict.get("meta_category"):
        metadata_dict["meta_category"] = (
            metadata_dict["meta_category"].value
            if hasattr(metadata_dict["meta_category"], "value")
            else metadata_dict["meta_category"]
        )

    if metadata_dict.get("meta_impact_level"):
        metadata_dict["meta_impact_level"] = (
            metadata_dict["meta_impact_level"].value
            if hasattr(metadata_dict["meta_impact_level"], "value")
            else metadata_dict["meta_impact_level"]
        )

    return {
        "id": doc.id,  # Meilisearch requires 'id' field
        "title": doc.title,
        "content": doc.original_content,
        "month": doc.month,
        "link": doc.link,
        "metadata": metadata_dict,
        "_vectors": {"default": embedding_vector},  # Vector for hybrid search
    }
