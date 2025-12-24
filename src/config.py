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
DATA_JSON = os.path.join(DATA_DIR, "data.json")

# Meilisearch Settings
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://localhost:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "masterKey")
MEILISEARCH_INDEX = "announcements_v2"
## search.js init config
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.81
DEFAULT_SEMANTIC_RATIO = 0.5
# TODO: Consider making this dynamic (e.g., limit * 1.2) in the future
PRE_SEARCH_LIMIT = 24

# Legacy FilePath dict for backward compatibility
FilePath = {
    "page": PAGE_JSON,
    "ETL_log": os.path.join(LOG_DIR, "log.json"),
    "processed_dir": PROCESSED_DIR,
    "log_dir": LOG_DIR,
}
