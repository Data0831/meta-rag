import os
import sys
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import (
    DATA_JSON,
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
)
from src.schema.schemas import AnnouncementDoc
from src.database.db_adapter_meili import (
    MeiliAdapter,
    transform_doc_for_meilisearch,
)
from src.database.vector_utils import get_embedding
from src.tool.ANSI import print_red, print_green, print_yellow

load_dotenv()

REMOVE_JSON = os.path.join(current_dir, "remove.json")
QUERY_CHUNK_SIZE = 200  # Batch size for checking existence
DELETE_CHUNK_SIZE = 500  # Batch size for deletions
UPLOAD_BATCH_SIZE = 100  # Batch size for embedding and upload


def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def load_data() -> List[AnnouncementDoc]:
    """Load new data from data.json."""
    if not os.path.exists(DATA_JSON):
        print_yellow(f"No new data file found at: {DATA_JSON}")
        return []
    try:
        with open(DATA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        docs = []
        for i, item in enumerate(data):
            try:
                docs.append(AnnouncementDoc(**item))
            except Exception as e:
                print_red(f"Error parsing doc at index {i}: {e}")
        return docs
    except Exception as e:
        print_red(f"Failed to read {DATA_JSON}: {e}")
        return []


def load_remove_list() -> List[str]:
    """Load IDs to remove from remove.json."""
    if not os.path.exists(REMOVE_JSON):
        return []
    try:
        with open(REMOVE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print_red(f"Failed to read {REMOVE_JSON}: {e}")
        return []


def run_sync():
    """Main synchronization logic."""
    print_green("\n=== Running Synchronization Task ===")

    adapter = MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
    )

    # 1. Handle Deletions (Batching)
    ids_to_remove = load_remove_list()
    if ids_to_remove:
        print(f"Found {len(ids_to_remove)} IDs to remove...")
        for chunk in chunk_list(ids_to_remove, DELETE_CHUNK_SIZE):
            result = adapter.delete_documents_by_ids(chunk)
            deleted_count = len(result.get("deleted", []))
            if deleted_count > 0:
                print(f"  - Removed {deleted_count} documents.")
    else:
        print("No documents to remove today.")

    # 2. Handle Additions/Updates
    docs = load_data()
    if not docs:
        print_yellow("No new documents to process today.")
        return

    print(f"Loaded {len(docs)} documents from data.json.")

    # First pass: Check which IDs already exist in Meilisearch
    existing_ids = set()
    doc_ids = [doc.id for doc in docs]

    print("Checking for existing documents in Meilisearch...")
    for chunk in chunk_list(doc_ids, QUERY_CHUNK_SIZE):
        existing_batch = adapter.get_documents_by_ids(chunk)
        for doc_item in existing_batch:
            existing_ids.add(doc_item["id"])

    new_docs = [doc for doc in docs if doc.id not in existing_ids]

    if not new_docs:
        print_green("All current documents already exist. No updates needed.")
        return
    print(
        f"Generating embeddings and uploading {len(new_docs)} new/updated documents..."
    )

    # Second pass: Generate embeddings and upsert missing ones
    meili_docs = []
    for i, doc in enumerate(new_docs):
        text = doc.cleaned_content
        embedding_result = get_embedding(text)

        if embedding_result.get("status") == "success":
            vector = embedding_result.get("result")
            meili_doc = transform_doc_for_meilisearch(doc, vector)
            meili_docs.append(meili_doc)
        else:
            print_red(f"  ⚠ Failed embedding for: {doc.title[:30]}...")

        if len(meili_docs) >= UPLOAD_BATCH_SIZE:
            print(f"  Progress: {i + 1}/{len(new_docs)}")
            adapter.upsert_documents(meili_docs)
            meili_docs = []

    if meili_docs:
        adapter.upsert_documents(meili_docs)

    print_green(f"\n✓ Synchronization complete. Added/Updated: {len(new_docs)} docs.")


if __name__ == "__main__":
    run_sync()
