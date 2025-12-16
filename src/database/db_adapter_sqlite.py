from sqlite_utils import Database
from src.schema.schemas import AnnouncementDoc, SearchFilters
from typing import List, Dict, Any, Optional
import json
import os
from src.config import SQLITE_DB

DB_PATH = SQLITE_DB


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
                "category": str,
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
    Also removes WAL and SHM files if they exist.
    """
    # List of files to remove (main db + WAL mode files)
    files_to_remove = [
        db_path,
        f"{db_path}-wal",
        f"{db_path}-shm"
    ]

    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed file: {file_path}")
            except PermissionError:
                print(f"Permission denied: {file_path} (file may be in use)")
            except Exception as e:
                print(f"Error removing {file_path}: {e}")

    # Re-initialize the database
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
            "category": (
                meta.meta_category.value if meta.meta_category else None
            ),
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


def search_keyword(
    query: str, filters: Optional[SearchFilters] = None, limit: int = 20, db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Perform FTS5 search on SQLite with optional filters.
    Returns a list of dicts with 'uuid' and 'score' (rank).
    """
    db = Database(db_path)
    
    if "announcements" not in db.table_names():
        print("Table 'announcements' does not exist.")
        return []

    # Base query for FTS
    # We use the announcements_fts table implicitly via .search() method of sqlite-utils 
    # OR construct raw SQL for more control over hybrid filtering (WHERE + MATCH).
    
    # Using raw SQL to combine FTS match with standard column filtering efficiently
    # The standard pattern for sqlite FTS mixed with column filters is:
    # SELECT ..., rank FROM announcements WHERE announcements MATCH :query AND [filters] ORDER BY rank
    
    where_clauses = ["announcements_fts MATCH :query"]
    params = {"query": query}

    if filters:
        # Support multiple months (OR condition)
        if filters.months:
            if len(filters.months) == 1:
                where_clauses.append("month = :month")
                params["month"] = filters.months[0]
            else:
                # Multiple months: month IN (...)
                month_placeholders = ", ".join([f":month_{i}" for i in range(len(filters.months))])
                where_clauses.append(f"month IN ({month_placeholders})")
                for i, month in enumerate(filters.months):
                    params[f"month_{i}"] = month

        if filters.category:
            where_clauses.append("category = :category")
            params["category"] = filters.category.value if hasattr(filters.category, 'value') else filters.category

        if filters.impact_level:
            where_clauses.append("impact_level = :impact_level")
            params["impact_level"] = filters.impact_level.value if hasattr(filters.impact_level, 'value') else filters.impact_level

    where_str = " AND ".join(where_clauses)
    
    # We join with the FTS table to get the rank. 
    # sqlite-utils creates a view or we can just query the table directly if it's set up right.
    # Usually: select * from announcements where announcements match ...
    # But for ranking we specifically want the FTS table's hidden columns or matchinfo.
    # Simpler approach using sqlite-utils pythonic API if possible, but raw SQL is safer for FTS syntax.
    
    # Standard SQLite FTS query
    sql = f"""
        SELECT announcements.uuid, announcements.title, snippet(announcements_fts, -1, '<b>', '</b>', '...', 64) as snippet
        FROM announcements 
        JOIN announcements_fts ON announcements.rowid = announcements_fts.rowid 
        WHERE {where_str}
        ORDER BY rank
        LIMIT {limit}
    """
    
    try:
        results = list(db.query(sql, params))
        # Add a mock score based on order (since rank is hidden/internal usually lower is better in FTS5 default)
        # We can normalize rank to a score 0-1 if needed, but for RRF we just need rank order.
        # Let's return the rank index as score for now (1/(rank+k)).
        return results
    except Exception as e:
        print(f"SQLite Search Error: {e}")
        return []


def get_documents_by_uuids(uuids: List[str], db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Fetch full documents by a list of UUIDs.
    """
    db = Database(db_path)
    if not uuids:
        return []
    
    placeholders = ",".join(["?"] * len(uuids))
    sql = f"SELECT * FROM announcements WHERE uuid IN ({placeholders})"
    
    return list(db.query(sql, uuids))
