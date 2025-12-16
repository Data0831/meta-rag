import os
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from src.models.schemas import AnnouncementDoc
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
# API Key if needed (usually for cloud)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

COLLECTION_NAME = "announcements"
# Default embedding size for text-embedding-3-small is 1536
VECTOR_SIZE = 1536


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
