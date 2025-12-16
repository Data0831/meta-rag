import os
import sys
import json
import argparse
from typing import List
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.schemas import AnnouncementDoc
from src.vector_utils import create_enriched_text, get_embedding
from src.db_adapter_sqlite import insert_documents as insert_sqlite, init_db
from src.db_adapter_qdrant import upsert_documents as insert_qdrant, init_collection
from src.pipeline.etl import ETLPipeline

load_dotenv()

PROCESSED_DATA_PATH = os.path.join("data", "processed", "processed.json")


def load_processed_data() -> List[AnnouncementDoc]:
    """
    Load processed data from JSON and convert to AnnouncementDoc objects.
    """
    if not os.path.exists(PROCESSED_DATA_PATH):
        print(
            f"Processed data not found at {PROCESSED_DATA_PATH}. Please run ETL first."
        )
        return []

    with open(PROCESSED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for item in data:
        try:
            doc = AnnouncementDoc.model_validate(item)
            docs.append(doc)
        except Exception as e:
            print(f"Error validation doc: {e}")

    print(f"Loaded {len(docs)} documents from {PROCESSED_DATA_PATH}")
    return docs


def run_ingestion():
    """
    Main ingestion flow:
    1. Load processed data (assuming ETL is done for now, or trigger it).
    2. Generate Embeddings.
    3. Save to SQLite (Hybrid).
    4. Save to Qdrant (Hybrid).
    """

    # 1. Load Data
    docs = load_processed_data()
    if not docs:
        print("No documents to ingest. Exiting.")
        # Optional: Trigger ETL here if we wanted fully automated flow from raw
        # etl = ETLPipeline()
        # etl.run()
        # docs = load_processed_data()
        return

    # 2. Vector Enrichment
    print("Generating embeddings...")
    vectors = []

    # Process in batches to avoid memory issues or for progress tracking
    # But for 141 docs, we can do it in memory or loop

    valid_docs = []

    for doc in docs:
        text = create_enriched_text(doc)
        print(text)
        input("Press Enter to continue...")
        # vector = get_embedding(text, model="bge-m3")

        # if vector:
        #     vectors.append(vector)
        #     valid_docs.append(doc)
        # else:
        #     print(f"Failed to generate embedding for doc {doc.uuid}")

    print(f"Generated {len(vectors)} vectors.")

    # 3. SQLite Storage
    print("Initializing SQLite...")
    init_db()
    insert_sqlite(valid_docs)

    # 4. Qdrant Storage
    print("Initializing Qdrant...")
    init_collection(vector_size=1024)  # Ensure dim matches bge-m3
    insert_qdrant(valid_docs, vectors)

    print("Ingestion complete.")


def main():
    parser = argparse.ArgumentParser(description="Microsoft Announcement RAG CLI")
    parser.add_argument("mode", choices=["ingest", "chat"], help="Operation mode")

    args = parser.parse_args()

    if args.mode == "ingest":
        run_ingestion()
    elif args.mode == "chat":
        print("Chat mode not implemented yet.")


if __name__ == "__main__":
    main()
