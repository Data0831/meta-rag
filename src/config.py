import os
from dotenv import load_dotenv

load_dotenv()

# Application Version
APP_VERSION = "v0.0.2"

# API Password
ADMIN_TOKEN = "msanmsan001"

# Date Range Configuration
DATE_RANGE_MIN = "2013-11" # Azure update 最小從 2013-11 開始

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
MEILISEARCH_INDEX = "announcements_2026_01_07"
MEILISEARCH_TIMEOUT = int(os.getenv("MEILISEARCH_TIMEOUT", 25))

# ============================================================================
# Frontend Configurable Variables (exposed via /api/config)
# ============================================================================
DEFAULT_SEARCH_LIMIT = 5  # 默認的搜索數量
MAX_SEARCH_LIMIT = 50  # 最大搜索數量
SCORE_PASS_THRESHOLD = 0.81  # 相關性門檻 (左側)
DEFAULT_SEMANTIC_RATIO = 0.5
ENABLE_LLM = True
MANUAL_SEMANTIC_RATIO = False
MAX_SEARCH_INPUT_LENGTH = 100
MAX_CHAT_INPUT_LENGTH = 500
MAX_CHAT_HISTORY = 40 # 最大對話歷史保留，如果超過就會截斷
LLM_TOKEN_LIMIT = 100000
SUMMARIZE_TOKEN_LIMIT = 80000  # 總結的 token 限制量，會影響總結使用的篇數
PROXY_MODEL_NAME = os.getenv("PROXY_MODEL_NAME", "")

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
    {"value": "MSRC Update Guide", "label": "MSRC Update Guide", "default_checked": True},
]


# ============================================================================
# Backend-only Configuration (not exposed to frontend)
# ============================================================================
def get_pre_search_limit(limit):
    return max(
        50, int(limit * 1.5 + 20)
    )  # 根據使用者選擇的篇數動態返回 > 的數量並進行現有演算法處理 (merge,key_alg, sort, multi_search)


RETRY_SEARCH_LIMIT_MULTIPLIER = (
    1.5  # 重試後的擴大範圍，也會影響上面的，假設 is_retry_search 為 true
)
NO_HIT_PENALTY_FACTOR = 0.15
KEYWORD_HIT_BOOST_FACTOR = 0.60
SEARCH_MAX_RETRIES = 1  # 重搜索的次數
