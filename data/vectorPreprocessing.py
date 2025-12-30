import os
import sys
import json
from typing import List
from dotenv import load_dotenv

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import (
    DATA_JSON,
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
)
from src.schema.schemas import AnnouncementDoc
from src.database.db_adapter_meili import MeiliAdapter, transform_doc_for_meilisearch
from src.database.vector_utils import get_embedding
from src.tool.ANSI import print_red, print_green, print_yellow

load_dotenv()

REMOVE_JSON = os.path.join(os.path.dirname(__file__), "remove.json")
BATCH_SIZE = 100


def load_processed_data() -> List[AnnouncementDoc]:
    """
    Load processed data from parse.json.
    Expected format: Array of announcement objects.
    """
    if not os.path.exists(DATA_JSON):
        print(f"File not found: {DATA_JSON}")
        return []

    try:
        with open(DATA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []

    docs = []
    # New format expects a simple list
    if not isinstance(data, list):
        print(f"Error: Expected a list, got {type(data)}")
        return []

    for i, item in enumerate(data):
        try:
            docs.append(AnnouncementDoc(**item))
        except Exception as e:
            print(f"Error parsing document at index {i}: {e}")
            # print(f"Item: {item}")  # Debug output for troubleshooting
    return docs


def load_remove_list() -> List[str]:
    if not os.path.exists(REMOVE_JSON):
        print_yellow(f"File not found: {REMOVE_JSON}")
        return []
    try:
        with open(REMOVE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print_red(f"Error: Expected a list in {REMOVE_JSON}, got {type(data)}")
            return []
        return data
    except json.JSONDecodeError as e:
        print_red(f"Error decoding JSON from {REMOVE_JSON}: {e}")
        return []


def clear_all():
    """Clear all data from Meilisearch index."""
    print("\n--- Clearing Data ---")
    print("Clearing Meilisearch index...")
    adapter = MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
    )
    adapter.reset_index()
    print("✓ Meilisearch index cleared.")


def process_and_write():
    """
    Process documents and write to Meilisearch.
    - Load parse.json
    - Generate embeddings
    - Transform to Meilisearch format
    - Upsert to Meilisearch
    """
    print("\n--- Processing and Writing Data ---")
    docs = load_processed_data()
    if not docs:
        print("No documents to process.")
        return

    print(f"Loaded {len(docs)} documents.")

    # Initialize Meilisearch adapter
    adapter = MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
    )

    # 1. Generate Embeddings and Transform Documents
    print("Generating embeddings and transforming documents...")
    meili_docs = []

    for i, doc in enumerate(docs):
        text = doc.cleaned_content
        embedding_result = get_embedding(text)

        if embedding_result.get("status") == "success":
            vector = embedding_result.get("result")
            meili_doc = transform_doc_for_meilisearch(doc, vector)
            meili_docs.append(meili_doc)
        else:
            error_msg = embedding_result.get("error", "Unknown error")
            print(f"⚠ Failed to generate embedding for doc: {doc.title}")
            print(f"  Error: {error_msg}")

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(docs)}")

        # Batch upsert to save memory
        if len(meili_docs) >= BATCH_SIZE:
            print(f"  Sending batch of {len(meili_docs)} documents to Meilisearch...")
            adapter.upsert_documents(meili_docs)
            meili_docs = []

    # Final upsert for remaining documents
    if meili_docs:
        print(f"  Sending final batch of {len(meili_docs)} documents to Meilisearch...")
        adapter.upsert_documents(meili_docs)
    else:
        if not docs:
            print("No documents to process.")
            return

    # 3. Show index stats
    print("\n--- Index Statistics ---")
    stats = adapter.get_stats()
    if stats:
        print(f"  Total documents: {stats.get('numberOfDocuments', 'N/A')}")
        print(
            f"  Index status: {stats.get('isIndexing', False) and 'Indexing...' or 'Ready'}"
        )

    print("\n✓ Done.")


def delete_by_ids():
    print("\n--- Deleting Documents by IDs ---")
    ids_to_remove = load_remove_list()
    if not ids_to_remove:
        print_yellow("No IDs to remove.")
        return
    print(f"Loaded {len(ids_to_remove)} IDs from remove.json")
    adapter = MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
    )
    result = adapter.delete_documents_by_ids(ids_to_remove)
    deleted_docs = result.get("deleted", [])
    not_found_ids = result.get("not_found", [])
    if deleted_docs:
        print_green(f"\n✓ Successfully deleted {len(deleted_docs)} documents:")
        for doc in deleted_docs:
            print_green(f"  - ID: {doc['id']}, Title: {doc.get('title', 'N/A')}")
    if not_found_ids:
        print_yellow(f"\n⚠ {len(not_found_ids)} IDs not found in Meilisearch:")
        for doc_id in not_found_ids:
            print_yellow(f"  - ID: {doc_id}")


def add_new_documents():
    print("\n--- Adding New Documents ---")
    docs = load_processed_data()
    if not docs:
        print_yellow("No documents to process.")
        return
    print(f"Loaded {len(docs)} documents from data.json")
    adapter = MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
    )
    doc_ids = [doc.id for doc in docs]
    existing_docs = adapter.get_documents_by_ids(doc_ids)
    existing_ids = {doc["id"] for doc in existing_docs}
    new_docs = [doc for doc in docs if doc.id not in existing_ids]
    if not new_docs:
        print_yellow("No new documents to add (all already exist in Meilisearch).")
        return
    print(f"Found {len(new_docs)} new documents to add")
    if len(docs) - len(new_docs) > 0:
        print_yellow(f"Skipping {len(docs) - len(new_docs)} existing documents")
    print("Generating embeddings and transforming new documents...")
    meili_docs = []
    for i, doc in enumerate(new_docs):
        text = doc.cleaned_content
        embedding_result = get_embedding(text)
        if embedding_result.get("status") == "success":
            vector = embedding_result.get("result")
            meili_doc = transform_doc_for_meilisearch(doc, vector)
            meili_docs.append(meili_doc)
        else:
            error_msg = embedding_result.get("error", "Unknown error")
            print_red(f"⚠ Failed to generate embedding for doc: {doc.title}")
            print_red(f"  Error: {error_msg}")
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(new_docs)}")

        # Batch upsert to save memory
        if len(meili_docs) >= BATCH_SIZE:
            print(f"  Sending batch of {len(meili_docs)} documents to Meilisearch...")
            adapter.upsert_documents(meili_docs)
            meili_docs = []

    # Final upsert for remaining documents
    if meili_docs:
        print(f"  Sending final batch of {len(meili_docs)} documents to Meilisearch...")
        adapter.upsert_documents(meili_docs)
        print_green(f"\n✓ Successfully added documents.")
    else:
        print_yellow("No valid documents with embeddings to insert.")
        return


def auto_sync():
    print("\n=== Auto Sync: Delete + Add ===")
    delete_by_ids()
    add_new_documents()
    print("\n✓ Auto sync completed.")


def main():
    """
    Main entry point for vector preprocessing.
    Provides interactive menu for Meilisearch operations.
    """
    while True:
        choice = (
            str(
                input(
                    """
        === Meilisearch Vector Preprocessing ===
        1. Clear Meilisearch index
        2. Process and Write (Load parocessed.json -> Embed -> Write to Meilisearch)
        3. Auto Sync (Delete from remove.json -> Add new from data.json)
        Q. Quit

        Enter your choice (1, 2, 3, or Q): """
                )
            )
            .strip()
            .upper()
        )
        if choice == "1":
            clear_all()
        elif choice == "2":
            process_and_write()
        elif choice == "3":
            auto_sync()
        elif choice == "Q":
            print("Exiting...")
            return
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
