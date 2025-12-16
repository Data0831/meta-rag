import os
import sys
import json
from typing import List
from dotenv import load_dotenv

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import PROCESSED_OUTPUT
from src.schema.schemas import AnnouncementDoc
from src.database.db_adapter_qdrant import reset_collection, upsert_documents
from src.database.db_adapter_sqlite import reset_db, insert_documents
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
    print("\n--- Clearing Data ---")
    print("Clearing Qdrant collection...")
    reset_collection()
    print("Clearing SQLite database...")
    reset_db()
    print("All cleared.")


def process_and_write():
    print("\n--- Processing and Writing Data ---")
    docs = load_processed_data()
    if not docs:
        print("No documents to process.")
        return

    print(f"Loaded {len(docs)} documents.")

    # 1. Generate Embeddings
    print("Generating embeddings (this may take a while)...")
    vectors = []
    valid_docs = []

    for i, doc in enumerate(docs):
        text = create_enriched_text(doc)
        vector = get_embedding(text)
        if vector:
            vectors.append(vector)
            valid_docs.append(doc)
        else:
            print(f"Failed to generate embedding for doc {doc.uuid}")

        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(docs)}")

    if not valid_docs:
        print("No valid documents with embeddings to insert.")
        return

    # 2. Insert into SQLite
    print("Inserting into SQLite...")
    insert_documents(valid_docs)

    # 3. Insert into Qdrant
    print("Inserting into Qdrant...")
    upsert_documents(valid_docs, vectors)

    print("Done.")


def main():
    while True:
        choice = (
            str(
                input(
                    """
        1. Clear all (Qdrant & SQLite)
        2. Process and Write (Load processed.json -> Embed -> Write to DBs)
        Q. Quit
        input your choice like 1 or Q:
        """
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
            return
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
