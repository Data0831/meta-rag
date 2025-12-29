import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
DATA_DIR = "data"
DATABASE_DIR = "database"

# Data subdirectories
LOG_DIR = os.path.join(DATA_DIR, "process_log")
DATA_JSON = os.path.join(DATA_DIR, "data.json")

# Meilisearch Settings
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://localhost:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "masterKey")
MEILISEARCH_INDEX = "announcements_v2"

## search.js init config
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.81
DEFAULT_SEMANTIC_RATIO = 0.5
PRE_SEARCH_LIMIT = 50

RERANK_FULL_MATCH_BOOST = 2.5
RERANK_PARTIAL_MATCH_FACTOR = 0.5
RERANK_NO_MATCH_PENALTY = 0.81
RERANK_TITLE_WEIGHT = 1.5
