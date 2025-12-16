from sqlite_utils import Database
from src.schema.schemas import AnnouncementDoc
from typing import List
import json
import os

DB_PATH = os.path.join("database", "announcements.db")


def init_db(db_path: str = DB_PATH):
    """
    Initialize the SQLite database and enable FTS5.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    db = Database(db_path)

    if "announcements" not in db.table_names():
        # Create table
        db["announcements"].create(
            {
                "uuid": str,
                "month": str,
                "title": str,
                "content": str,
                "products": str,  # Storing as JSON string
                "impact_level": str,
                "date_effective": str,
                "metadata_json": str,  # Full metadata dump
            },
            pk="uuid",
        )

        # Enable FTS on title and content
        # python-sqlite-utils handles creating the virtual table and triggers
        db["announcements"].enable_fts(["title", "content"], create_triggers=True)
        print(f"Initialized SQLite database at {db_path} with FTS enabled.")


def reset_db(db_path: str = DB_PATH):
    """
    Delete and re-initialize the SQLite database.
    """
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Removed database file: {db_path}")
        except Exception as e:
            print(f"Error removing database file: {e}")
    init_db(db_path)


def insert_documents(docs: List[AnnouncementDoc], db_path: str = DB_PATH):
    """
    Upsert documents into the SQLite database.
    """
    db = Database(db_path)

    # Ensure table exists
    if "announcements" not in db.table_names():
        init_db(db_path)

    records = []
    for doc in docs:
        meta = doc.metadata

        # Handle date serialization
        date_eff = (
            meta.meta_date_effective.isoformat() if meta.meta_date_effective else None
        )

        record = {
            "uuid": doc.uuid,
            "month": doc.month,
            "title": doc.title,
            "content": doc.original_content,
            "products": json.dumps(meta.meta_products, ensure_ascii=False),
            "impact_level": (
                meta.meta_impact_level.value if meta.meta_impact_level else None
            ),
            "date_effective": date_eff,
            # Handle Pydantic model dump compatibility
            "metadata_json": (
                meta.model_dump_json()
                if hasattr(meta, "model_dump_json")
                else meta.json()
            ),
        }
        records.append(record)

    # Batch upsert
    db["announcements"].upsert_all(records, pk="uuid")
    print(f"Upserted {len(records)} documents into SQLite.")
