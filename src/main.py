import os
import json
import argparse
import sys
from typing import List

# Add the project root to sys.path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.models.schemas import AnnouncementDoc
from src import vector_utils
from src import db_adapter_sqlite
from src import db_adapter_qdrant

PROCESSED_DATA_PATH = os.path.join(project_root, "data", "processed", "processed.json")


def load_processed_data(file_path: str) -> List[AnnouncementDoc]:
    print(f"Reading from: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for item in data:
        # Pydantic validation
        docs.append(AnnouncementDoc(**item))
    return docs


def run_ingest_mode():
    print("Starting Ingestion Mode...")

    # 1. Load Data
    if not os.path.exists(PROCESSED_DATA_PATH):
        print(f"Error: Processed data not found at {PROCESSED_DATA_PATH}")
        return

    try:
        docs = load_processed_data(PROCESSED_DATA_PATH)
        print(f"Loaded {len(docs)} documents.")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # 2. Initialize Databases
    print("Initializing databases...")
    try:
        db_adapter_sqlite.init_db()
        db_adapter_qdrant.init_collection()
    except Exception as e:
        print(f"Error initializing databases: {e}")
        return

    # 3. Store in SQLite
    print("Writing to SQLite...")
    try:
        db_adapter_sqlite.insert_documents(docs)
    except Exception as e:
        print(f"Error writing to SQLite: {e}")
        return

    # 4. Generate Embeddings & Store in Qdrant
    print("Generating embeddings and writing to Qdrant...")

    valid_docs = []
    valid_vectors = []

    for i, doc in enumerate(docs):
        try:
            text = vector_utils.create_enriched_text(doc)
            vector = vector_utils.get_embedding(text)
            if vector:
                valid_docs.append(doc)
                valid_vectors.append(vector)
            else:
                print(f"Skipping doc {doc.uuid} due to empty embedding.")

            if (len(valid_vectors)) % 10 == 0 and len(valid_vectors) > 0:
                print(f"Generated {len(valid_vectors)} embeddings...", end="\r")
        except Exception as e:
            print(f"Error processing doc {doc.uuid}: {e}")

    print(f"\nGenerated total {len(valid_vectors)} embeddings.")

    if valid_docs:
        try:
            db_adapter_qdrant.upsert_documents(valid_docs, valid_vectors)
        except Exception as e:
            print(f"Error writing to Qdrant: {e}")

    print("Ingestion Complete!")


def main():
    parser = argparse.ArgumentParser(description="Microsoft Announcements RAG System")
    parser.add_argument(
        "--mode", choices=["ingest", "chat"], default="ingest", help="Operation mode"
    )
    args = parser.parse_args()

    if args.mode == "ingest":
        run_ingest_mode()
    elif args.mode == "chat":
        print("Chat mode not implemented yet (Phase 5).")


if __name__ == "__main__":
    main()
