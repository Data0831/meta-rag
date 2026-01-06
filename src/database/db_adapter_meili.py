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
from src.tool.ANSI import print_red


class MeiliAdapter:
    def __init__(self, host, api_key, collection_name):
        self.client = meilisearch.Client(host, api_key)
        self.collection_name = collection_name
        self.index = self.client.index(collection_name)
        self._configure_index()

    def _configure_index(self):
        try:
            self.index.update_filterable_attributes(FILTERABLE_ATTRIBUTES)
            self.index.update_searchable_attributes(SEARCHABLE_ATTRIBUTES)
            self.index.update_embedders({"default": EMBEDDING_CONFIG})
            self.index.update_ranking_rules(RANKING_RULES)
            print(
                f"✓ Meilisearch index '{self.collection_name}' configured successfully."
            )
        except Exception as e:
            print_red(f"Warning: Error configuring Meilisearch index: {e}")
            print_red("Index may need manual configuration via Meilisearch dashboard.")

    def upsert_documents(self, documents: List[Dict[str, Any]]) -> None:
        if not documents:
            print("No documents to upsert.")
            return
        try:
            task_info = self.index.add_documents(documents, primary_key="id")
            print(f"✓ Upserted {len(documents)} documents to Meilisearch.")
            print(f"  Task UID: {task_info.task_uid}")
        except Exception as e:
            print_red(f"Error upserting documents to Meilisearch: {e}")
            raise

    def search(
        self,
        query: str,
        vector: Optional[List[float]] = None,
        filters: Optional[str] = None,
        website: Optional[List[str]] = None,
        limit: int = 20,
        semantic_ratio: float = DEFAULT_SEMANTIC_RATIO,
    ) -> Dict[str, Any]:
        search_params = {
            "limit": limit,
            "attributesToRetrieve": ["*"],
            "showRankingScore": True,
            "showRankingScoreDetails": True,
        }
        # === 新增：處理網站過濾邏輯 ===
        final_filter = filters

        if website and len(website) > 0:
            # 建立網站過濾字串: website IN ["Azure Updates", "Partner Center"]
            site_list_str = ", ".join([f'"{w}"' for w in website])
            website_filter = f'website IN [{site_list_str}]'

            # 如果原本已經有 filters (例如年份)，就用 AND 連接
            if final_filter:
                final_filter = f"({final_filter}) AND {website_filter}"
            else:
                final_filter = website_filter
        
        if final_filter:
            search_params["filter"] = final_filter
        if vector:
            search_params["hybrid"] = {
                "semanticRatio": semantic_ratio,
                "embedder": "default",
            }
            search_params["vector"] = vector
        try:
            results = self.index.search(query, search_params)
            hits = results["hits"]
            if hits and "_rankingScore" in hits[0]:
                hits.sort(key=lambda x: x.get("_rankingScore", 0), reverse=True)
            return {"status": "success", "result": hits}
        except Exception as e:
            print_red(f"Meilisearch search error: {e}")
            return {
                "status": "failed",
                "error": f"Meilisearch search error: {str(e)}",
                "stage": "meilisearch_search",
            }

    def multi_search(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute multiple searches in a single HTTP request using Meilisearch multi-search.
        Args:
            queries: List of search parameters. Each dict must include 'indexUid' and 'q'.
        """
        try:
            # ensure indexUid is present in each query
            for q in queries:
                if "indexUid" not in q:
                    q["indexUid"] = self.collection_name

            results = self.client.multi_search(queries)
            return {"status": "success", "result": results}
        except Exception as e:
            print_red(f"Meilisearch multi-search error: {e}")
            return {
                "status": "failed",
                "error": f"Meilisearch multi-search error: {str(e)}",
                "stage": "meilisearch_multi_search",
            }

    def update_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Partially update documents in Meilisearch.
        Existing fields not present in the payload will be preserved.
        """
        if not documents:
            print("No documents to update.")
            return
        try:
            task_info = self.index.update_documents(documents, primary_key="id")
            print(f"✓ Updated {len(documents)} documents in Meilisearch.")
            print(f"  Task UID: {task_info.task_uid}")
        except Exception as e:
            print_red(f"Error updating documents in Meilisearch: {e}")
            raise

    def reset_index(self) -> None:
        try:
            task_info = self.index.delete_all_documents()
            print(f"✓ Deleted all documents from '{self.collection_name}'.")
            print(f"  Task UID: {task_info.task_uid}")
        except Exception as e:
            print_red(f"Error resetting Meilisearch index: {e}")
            raise

    def delete_documents_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        if not ids:
            return {"deleted": [], "not_found": []}
        try:
            existing_docs = self.get_documents_by_ids(ids)
            existing_ids = {doc["id"] for doc in existing_docs}
            not_found_ids = [doc_id for doc_id in ids if doc_id not in existing_ids]
            if existing_ids:
                task_info = self.index.delete_documents(list(existing_ids))
                print(f"✓ Deleted {len(existing_ids)} documents from Meilisearch.")
                print(f"  Task UID: {task_info.task_uid}")
            return {"deleted": existing_docs, "not_found": not_found_ids}
        except Exception as e:
            print_red(f"Error deleting documents by IDs: {e}")
            return {"deleted": [], "not_found": ids}

    def get_documents_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        try:
            ids_str = ", ".join([f'"{doc_id}"' for doc_id in ids])
            id_filter = f"id IN [{ids_str}]"
            results = self.index.search(
                "",
                {"filter": id_filter, "limit": len(ids), "attributesToRetrieve": ["*"]},
            )
            return results["hits"]
        except Exception as e:
            print_red(f"Error fetching documents by IDs: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        try:
            stats = self.index.get_stats()
            if hasattr(stats, "model_dump"):
                return stats.model_dump()
            elif hasattr(stats, "dict"):
                return stats.dict()
            return stats
        except Exception as e:
            print_red(f"Error getting index stats: {e}")
            return {}


def build_meili_filter(intent) -> Optional[str]:
    conditions = []
    if intent.year_month:
        months_str = ", ".join([f"'{m}'" for m in intent.year_month])
        conditions.append(f"year_month IN [{months_str}]")
    if intent.year:
        years_str = ", ".join([f"'{y}'" for y in intent.year])
        conditions.append(f"year IN [{years_str}]")
    if intent.links:
        links_str = ", ".join([f"'{l}'" for l in intent.links])
        conditions.append(f"link IN [{links_str}]")
    if hasattr(intent, "website") and intent.website:
        website_str = ", ".join([f"'{w}'" for w in intent.website])
        conditions.append(f"website IN [{website_str}]")

    return " AND ".join(conditions) if conditions else None


def transform_doc_for_meilisearch(
    doc: AnnouncementDoc, embedding_vector: List[float]
) -> Dict[str, Any]:
    doc_dict = transform_doc_metadata_only(doc)
    doc_dict["_vectors"] = {"default": embedding_vector}
    return doc_dict


def transform_doc_metadata_only(doc: AnnouncementDoc) -> Dict[str, Any]:
    return {
        "id": doc.id,
        "link": doc.link,
        "year_month": doc.year_month,
        "year": doc.year,
        "workspace": doc.workspace,
        "title": doc.title,
        "main_title": doc.main_title,
        "heading_link": doc.heading_link,
        "content": doc.content,
        "cleaned_content": doc.cleaned_content,
        "website": doc.website,
    }
