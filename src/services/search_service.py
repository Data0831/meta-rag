import concurrent.futures
import json
from typing import List, Dict, Any, Optional
from src.llm.client import LLMClient
from src.llm.search_prompts import SEARCH_INTENT_PROMPT
from src.schema.schemas import SearchIntent, AnnouncementDoc, SearchFilters
from src.database import db_adapter_sqlite, db_adapter_qdrant, vector_utils

class SearchService:
    def __init__(self):
        self.llm_client = LLMClient()
        
    def parse_intent(self, user_query: str) -> Optional[SearchIntent]:
        """
        Convert user query into structured search intent using LLM.
        """
        # Construct prompt
        prompt = SEARCH_INTENT_PROMPT.format(user_query=user_query)
        
        messages = [
             {"role": "user", "content": prompt}
        ]
        
        # Use LLM with schema validation
        intent = self.llm_client.call_with_schema(
            messages=messages,
            response_model=SearchIntent,
            temperature=0.0
        )
        return intent

    def search(self, user_query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Perform hybrid search:
        1. Parse Intent (LLM)
        2. Parallel Search (SQLite FTS + Qdrant Vector)
        3. RRF Fusion
        4. Fetch Content
        """
        # 1. Parse Intent
        intent = self.parse_intent(user_query)
        if not intent:
            # Fallback if intent parsing fails
            print("Intent parsing failed. Fallback to basic keyword search.")
            intent = SearchIntent(
                filters=SearchFilters(), # Empty filters
                keyword_query=user_query,
                semantic_query=user_query, # Use original query as semantic query
                query=user_query # This field isn't in schema but might be useful? 
                                 # Wait, SearchIntent schema in schemas.py doesn't have 'query' field in my update?
                                 # Let's check schemas.py again.
            )
            
        # print(f"Parsed Intent: {intent.model_dump_json(indent=2)}")

        # 2. Parallel Search
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # SQLite Future
            future_sqlite = executor.submit(
                db_adapter_sqlite.search_keyword, 
                query=intent.keyword_query, 
                filters=intent.filters, 
                limit=limit
            )
            
            # Qdrant Future
            def qdrant_task():
                # Embedding
                embedding = vector_utils.get_embedding(intent.semantic_query)
                if not embedding:
                    print("Embedding generation failed.")
                    return []
                # Search
                return db_adapter_qdrant.search_semantic(
                    query_vector=embedding, 
                    filters=intent.filters, 
                    limit=limit
                )
            
            future_qdrant = executor.submit(qdrant_task)
            
            try:
                results_sqlite = future_sqlite.result()
            except Exception as e:
                print(f"SQLite search failed: {e}")
                results_sqlite = []
                
            try:
                results_qdrant = future_qdrant.result()
            except Exception as e:
                print(f"Qdrant search failed: {e}")
                results_qdrant = []

        # 3. RRF Fusion
        # RRF score = 1 / (k + rank)
        k = 60
        fused_scores = {} # uuid -> score
        
        # Process SQLite results
        for rank, item in enumerate(results_sqlite):
            uuid = item['uuid']
            fused_scores[uuid] = fused_scores.get(uuid, 0) + (1 / (k + rank + 1))
            
        # Process Qdrant results
        for rank, item in enumerate(results_qdrant):
            uuid = item['uuid']
            fused_scores[uuid] = fused_scores.get(uuid, 0) + (1 / (k + rank + 1))
            
        # Sort by score desc
        sorted_uuids = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        top_uuids = [u[0] for u in sorted_uuids[:limit]]
        
        # 4. Fetch Full Content
        if not top_uuids:
            return {"intent": intent.model_dump(), "results": []}

        docs = db_adapter_sqlite.get_documents_by_uuids(top_uuids)
        
        # Re-order docs to match sorted_uuids and inject scores
        doc_map = {d['uuid']: d for d in docs}
        ordered_docs = []
        for uuid in top_uuids:
            if uuid in doc_map:
                doc = doc_map[uuid]
                doc['rrf_score'] = fused_scores[uuid]
                
                # Also include snippets/payloads if available?
                # SQLite FTS returns snippet in 'snippet' column, but get_documents_by_uuids does SELECT *
                # We might want to merge snippets from results_sqlite if possible.
                # Find snippet from results_sqlite
                fts_hit = next((r for r in results_sqlite if r['uuid'] == uuid), None)
                if fts_hit and 'snippet' in fts_hit:
                    doc['snippet'] = fts_hit['snippet']
                
                ordered_docs.append(doc)

        return {
            "intent": intent.model_dump(),
            "results": ordered_docs
        }
