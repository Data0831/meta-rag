import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Database files (Legacy - will be removed)
SQLITE_DB = os.path.join(DATABASE_DIR, "announcements.db")
QDRANT_STORAGE = os.path.join(DATABASE_DIR, "qdrant_storage")

# Meilisearch Settings
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://localhost:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "masterKey")
MEILISEARCH_INDEX = "announcements"
## search.js init config
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.81
DEFAULT_SEMANTIC_RATIO = 0.5

# ETL Settings
DEFAULT_BATCH_SIZE = 10  # Number of documents to process per batch

# LLM Model Settings
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

# Legacy FilePath dict for backward compatibility
FilePath = {
    "page": PAGE_JSON,
    "ETL_log": os.path.join(LOG_DIR, "log.json"),
    "processed_dir": PROCESSED_DIR,
    "log_dir": LOG_DIR,
}
