import os
from dotenv import load_dotenv

load_dotenv()

# Application Version
APP_VERSION = "v0.0.2"

# API Password
ADMIN_TOKEN = "msanmsan001"

# Date Range Configuration
DATE_RANGE_MIN = "2023-01"

# Base directories
DATA_DIR = "data_update"
DATABASE_DIR = "database"
LOG_BASE_DIR = os.getenv("LOG_BASE_DIR")
if not LOG_BASE_DIR:
    if os.environ.get("WEBSITE_INSTANCE_ID"):
        LOG_BASE_DIR = "/home/LogFiles"
    else:
        LOG_BASE_DIR = "data_logs"

# Data subdirectories
DATA_JSON = os.path.join(DATA_DIR, "data.json")
ANNOUNCEMENT_JSON = os.path.join("src", "datas", "announcement.json")
WEBSITE_JSON = os.path.join("src", "datas", "website.json")

# Meilisearch Settings
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://localhost:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "masterKey")
# MEILISEARCH_INDEX = "announcements_v4"
MEILISEARCH_INDEX = "announcements_deploy"
MEILISEARCH_TIMEOUT = int(os.getenv("MEILISEARCH_TIMEOUT", 25))

# ============================================================================
# Frontend Configurable Variables (exposed via /api/config)
# ============================================================================
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 20
SCORE_PASS_THRESHOLD = 0.81
DEFAULT_SEMANTIC_RATIO = 0.5
ENABLE_LLM = True
MANUAL_SEMANTIC_RATIO = False
ENABLE_KEYWORD_WEIGHT_RERANK = True
MAX_SEARCH_INPUT_LENGTH = 100
MAX_CHAT_INPUT_LENGTH = 500

AVAILABLE_SOURCES = [
    {
        "value": "partner_center_announcements",
        "label": "Microsoft 合作夥伴中心公告",
        "default_checked": True,
    },
    {"value": "Azure Updates", "label": "Azure 更新", "default_checked": True},
    {"value": "M365 Roadmap", "label": "Microsoft 365 藍圖", "default_checked": True},
    {
        "value": "windows message center",
        "label": "Windows 訊息中心",
        "default_checked": True,
    },
    {"value": "PowerBI Blog", "label": "Power BI 部落格", "default_checked": True},
    {"value": "MSRC_blog", "label": "MSRC Blog", "default_checked": True},
]

# ============================================================================
# Backend-only Configuration (not exposed to frontend)
# ============================================================================
PRE_SEARCH_LIMIT = 50
NO_HIT_PENALTY_FACTOR = 0.15
KEYWORD_HIT_BOOST_FACTOR = 0.60

FALLBACK_RESULT_COUNT = 2
SEARCH_MAX_RETRIES = 1


def get_score_min_threshold():
    return max(0, SCORE_PASS_THRESHOLD - 0.2)
