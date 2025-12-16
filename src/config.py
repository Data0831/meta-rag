import os

# Base directories
DATA_DIR = "data"
DATABASE_DIR = "database"

# Data subdirectories
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
LOG_DIR = os.path.join(DATA_DIR, "process_log")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
LLM_DIR = os.path.join(DATA_DIR, "llm")

# Input/Output files
PAGE_JSON = os.path.join(DATA_DIR, "page.json")
PAGE_EXAMPLE_JSON = os.path.join(DATA_DIR, "page.example.json")
PARSE_JSON = os.path.join(DATA_DIR, "parse.json")

# Processed output files
PROCESSED_OUTPUT = os.path.join(PROCESSED_DIR, "processed.json")
ERROR_LIST_OUTPUT = os.path.join(DATA_DIR, "errorlist.json")

# Database files
SQLITE_DB = os.path.join(DATABASE_DIR, "announcements.db")
QDRANT_STORAGE = os.path.join(DATABASE_DIR, "qdrant_storage")

# Legacy FilePath dict for backward compatibility
FilePath = {
    "page": PAGE_JSON,
    "ETL_log": os.path.join(LOG_DIR, "log.json"),
    "processed_dir": PROCESSED_DIR,
    "log_dir": LOG_DIR,
}
