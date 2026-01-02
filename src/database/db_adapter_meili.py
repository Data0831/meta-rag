"""
Meilisearch Database Adapter
Unified search engine for hybrid search (keyword + semantic + filters)
"""

import meilisearch
from typing import List, Dict, Any, Optional
from src.schema.schemas import AnnouncementDoc
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
                     e.g., "year_month IN ['2025-11']"
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
            hits = results["hits"]

            # Manually sort by _rankingScore in descending order
            # This ensures hybrid search results are properly ranked by their final score
            # (fixes issue where keyword results appear before higher-scored semantic results)
            if hits and "_rankingScore" in hits[0]:
                hits.sort(key=lambda x: x.get("_rankingScore", 0), reverse=True)

            return hits

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


def build_meili_filter(intent) -> Optional[str]:
    """
    Convert SearchIntent to Meilisearch filter syntax.

    Args:
        intent: SearchIntent object with filter fields

    Returns:
        Filter string in Meilisearch syntax, or None if no filters

    Examples:
        - year_month=['2025-12'] -> "year_month IN ['2025-12']"
        - workspaces=['General'] -> "workspace IN ['General']"
        - Combined -> "year_month IN ['2025-12'] AND workspace IN ['General']"
    """
    conditions = []

    if intent.year_month:
        months_str = ", ".join([f"'{m}'" for m in intent.year_month])
        conditions.append(f"year_month IN [{months_str}]")

    if intent.links:
        links_str = ", ".join([f"'{l}'" for l in intent.links])
        conditions.append(f"link IN [{links_str}]")

    if intent.workspaces:
        workspace_str = ", ".join([f"'{w}'" for w in intent.workspaces])
        conditions.append(f"workspace IN [{workspace_str}]")

    if hasattr(intent, "websites") and intent.websites:
        # 將列表轉成 Meilisearch 的 IN 語法: website IN ['azure', 'partner']
        sites_str = ", ".join([f"'{s}'" for s in intent.websites])
        conditions.append(f"website IN [{sites_str}]")

    return " AND ".join(conditions) if conditions else None


def transform_doc_for_meilisearch(
    doc: AnnouncementDoc, embedding_vector: List[float]
) -> Dict[str, Any]:
    """
    Transform AnnouncementDoc to Meilisearch document format.

    Args:
        doc: AnnouncementDoc object (simplified schema)
        embedding_vector: Embedding vector for the document

    Returns:
        Dictionary in Meilisearch format with _vectors field
    """
    # Serialize doc to dict
    doc_dict = doc.model_dump() if hasattr(doc, "model_dump") else doc.dict()

    # Generate a unique ID from link + title
    # Since link might not be unique (e.g. multiple sections), we combine it with title
    import hashlib

    doc_id = hashlib.md5((doc.link + doc.title).encode()).hexdigest()

    return {
        "id": doc_id,  # Generated ID from link
        "link": doc.link,
        "year_month": doc.year_month,  # YYYY-MM format (note: hyphen to match DB)
        "workspace": doc.workspace,  # e.g., General, Security
        "title": doc.title,
        "content": doc.content,  # Original content for display
        "cleaned_content": doc.cleaned_content,  # Cleaned content for search
        "_vectors": {"default": embedding_vector},  # Vector for hybrid search
    }
