import os
from dotenv import load_dotenv

load_dotenv()

# Base directories
DATA_DIR = "data"
DATABASE_DIR = "database"

# Data subdirectories
DATA_JSON = os.path.join(DATA_DIR, "data.json")

# Meilisearch Settings
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://localhost:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "masterKey")
MEILISEARCH_INDEX = "announcements_v4"
## search.js init config
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 20
SCORE_PASS_THRESHOLD = 0.81
DEFAULT_SEMANTIC_RATIO = 0.5
ENABLE_LLM = True
MANUAL_SEMANTIC_RATIO = False
ENABLE_KEYWORD_WEIGHT_RERANK = True

# ============================================================================
# Backend-only Configuration (not exposed to frontend)
# ============================================================================
PRE_SEARCH_LIMIT = 50
NO_HIT_PENALTY_FACTOR = 0.15
KEYWORD_HIT_BOOST_FACTOR = 0.60


def get_score_min_threshold():
    return max(0, SCORE_PASS_THRESHOLD - 0.2)


FALLBACK_RESULT_COUNT = 2
