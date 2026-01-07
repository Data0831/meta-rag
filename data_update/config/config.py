import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from src.config import AVAILABLE_SOURCES
from src.database.vector_config import *


class WebsiteKey:
    """網站來源鍵值配置"""

    PARTNER_CENTER = AVAILABLE_SOURCES[0]["value"]
    AZURE_UPDATES = AVAILABLE_SOURCES[1]["value"]
    M365_ROADMAP = AVAILABLE_SOURCES[2]["value"]
    WINDOWS_MESSAGE_CENTER = AVAILABLE_SOURCES[3]["value"]
    POWERBI_BLOG = AVAILABLE_SOURCES[4]["value"]
    MSRC_BLOG = AVAILABLE_SOURCES[5]["value"]


class TokenConfig:
    """Token 配置參數"""

    MODEL_NAME = "gpt-4o-mini"
    CHUNK_SIZE = 1500
    OVERLAP = 300
    TOLERANCE = 200


# HARDWARE_CONFIG = LOW_END_2C4T
HARDWARE_CONFIG = RTX_4050_6G
# HARDWARE_CONFIG = CPU_16C_64G
MEILISEARCH_INDEX = "announcements_2026_01_07" # 這邊要指定正確

class TimeConfig:
    """時間配置參數"""
    run_time = ["06:00"]
    loop_time = 360 # 360 秒 = 6 分鐘

# 測試輸出
if __name__ == "__main__":
    print("WebsiteKey.PARTNER_CENTER:", WebsiteKey.AZURE_UPDATES)
    print("TokenConfig.MODEL_NAME:", TokenConfig.MODEL_NAME)
    print("HARDWARE_CONFIG:", HARDWARE_CONFIG)
