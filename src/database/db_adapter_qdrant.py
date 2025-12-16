import os
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter, 
    FieldCondition, 
    MatchValue, 
    MatchAny
)
from src.schema.schemas import AnnouncementDoc, SearchFilters
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
# API Key if needed (usually for cloud)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

COLLECTION_NAME = "announcements"
# Embedding size for bge-m3 is 1024
VECTOR_SIZE = 1024


def get_client():
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def init_collection(
    collection_name: str = COLLECTION_NAME, vector_size: int = VECTOR_SIZE
):
    """
    Initialize Qdrant collection.
    """
    client = get_client()
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection: {collection_name} with dim={vector_size}")
    else:
        print(f"Qdrant collection {collection_name} already exists.")


def reset_collection(collection_name: str = COLLECTION_NAME):
    """
    Delete and re-create Qdrant collection.
    """
    client = get_client()
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
        print(f"Deleted collection: {collection_name}")
    init_collection(collection_name)


def upsert_documents(
    docs: List[AnnouncementDoc],
    vectors: List[List[float]],
    collection_name: str = COLLECTION_NAME,
):
    """
    Upsert documents and their vectors into Qdrant.
    """
    client = get_client()

    points = []
    for doc, vector in zip(docs, vectors):
        # Prepare payload from metadata
        meta = doc.metadata
        payload = meta.model_dump() if hasattr(meta, "model_dump") else meta.dict()

        # Add basic info to payload for convenicence
        payload["uuid"] = doc.uuid
        payload["month"] = doc.month
        payload["title"] = doc.title

        # Serialize Dates for JSON compatibility
        if payload.get("meta_date_effective"):
            payload["meta_date_effective"] = str(payload["meta_date_effective"])
        if payload.get("meta_action_deadline"):
            payload["meta_action_deadline"] = str(payload["meta_action_deadline"])
        if payload.get("meta_date_announced"):
            payload["meta_date_announced"] = str(payload["meta_date_announced"])
        if payload.get("meta_impact_level"):
            payload["meta_impact_level"] = str(
                payload["meta_impact_level"].value
                if hasattr(payload["meta_impact_level"], "value")
                else payload["meta_impact_level"]
            )
        if payload.get("meta_category"):
            payload["meta_category"] = str(
                payload["meta_category"].value
                if hasattr(payload["meta_category"], "value")
                else payload["meta_category"]
            )

        points.append(PointStruct(id=doc.uuid, vector=vector, payload=payload))

    if points:
        client.upsert(collection_name=collection_name, points=points)
        print(f"Upserted {len(points)} points into Qdrant.")


def search_semantic(
    query_vector: List[float], 
    filters: Optional[SearchFilters] = None, 
    limit: int = 20,
    collection_name: str = COLLECTION_NAME
) -> List[Dict[str, Any]]:
    """
    Perform vector search on Qdrant with optional filters.
    """
    client = get_client()
    
    query_filter = None
    if filters:
        conditions = []
        
        if filters.month:
            conditions.append(
                FieldCondition(key="month", match=MatchValue(value=filters.month))
            )
        
        if filters.category:
            cat_val = filters.category.value if hasattr(filters.category, 'value') else filters.category
            conditions.append(
                FieldCondition(key="meta_category", match=MatchValue(value=cat_val))
            )
            
        if filters.impact_level:
            impact_val = filters.impact_level.value if hasattr(filters.impact_level, 'value') else filters.impact_level
            conditions.append(
                FieldCondition(key="meta_impact_level", match=MatchValue(value=impact_val))
            )
            
        if filters.products:
            # Check if ANY of the requested products match ANY of the meta_products list in payload
            # Qdrant match_any checks if payload field value (which can be list) contains any of the provided values.
            # But wait, meta_products is a list in payload. 'match_any' checks if the field value is one of the provided values.
            # If the field is a list, 'match_any' checks intersection?
            # Documentation says: "MatchAny - filter for keyword field. Matches if field value is one of the given values."
            # If field is array, it matches if at least one element equals to one of the values.
            conditions.append(
                FieldCondition(key="meta_products", match=MatchAny(any=filters.products))
            )
            
        if conditions:
            query_filter = Filter(must=conditions)

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True
    ).points
    
    # Format output
    return [
        {"uuid": hit.id, "score": hit.score, "payload": hit.payload}
        for hit in results
    ]
