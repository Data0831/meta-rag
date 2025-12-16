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
    PROCESSED_OUTPUT,
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
)
from src.schema.schemas import AnnouncementDoc
from src.database.db_adapter_meili import MeiliAdapter, transform_doc_for_meilisearch
from src.database.vector_utils import create_enriched_text, get_embedding

load_dotenv()


def load_processed_data() -> List[AnnouncementDoc]:
    if not os.path.exists(PROCESSED_OUTPUT):
        print(f"File not found: {PROCESSED_OUTPUT}")
        return []

    try:
        with open(PROCESSED_OUTPUT, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []

    docs = []
    # Handle list or dict wrapper
    if isinstance(data, dict) and "results" in data:
        items = data["results"]
    elif isinstance(data, list):
        items = data
    else:
        print("Unknown JSON structure. Expected list or dict with 'results' key.")
        return []

    for item in items:
        try:
            docs.append(AnnouncementDoc(**item))
        except Exception as e:
            print(f"Error parsing document: {e}")
            # print(f"Item: {item}") # Debug if needed
    return docs


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
    - Load processed.json
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
        # Generate enriched text for embedding
        text = create_enriched_text(doc)
        vector = get_embedding(text)

        if vector:
            # Transform to Meilisearch format
            meili_doc = transform_doc_for_meilisearch(doc, vector)
            meili_docs.append(meili_doc)
        else:
            print(f"⚠ Failed to generate embedding for doc {doc.id}")

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(docs)}")

    if not meili_docs:
        print("No valid documents with embeddings to insert.")
        return

    print(f"✓ Successfully prepared {len(meili_docs)} documents.")

    # 2. Upsert to Meilisearch
    print("Upserting documents to Meilisearch...")
    adapter.upsert_documents(meili_docs)

    # 3. Show index stats
    print("\n--- Index Statistics ---")
    stats = adapter.get_stats()
    if stats:
        print(f"  Total documents: {stats.get('numberOfDocuments', 'N/A')}")
        print(
            f"  Index status: {stats.get('isIndexing', False) and 'Indexing...' or 'Ready'}"
        )

    print("\n✓ Done.")


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
        2. Process and Write (Load processed.json -> Embed -> Write to Meilisearch)
        Q. Quit

        Enter your choice (1, 2, or Q): """
                )
            )
            .strip()
            .upper()
        )
        if choice == "1":
            clear_all()
        elif choice == "2":
            process_and_write()
        elif choice == "Q":
            print("Exiting...")
            return
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
