from abc import ABC, abstractmethod
from typing import List, Dict

# 引入您建立的共用切塊模組
# 假設 shared_splitter.py 與 base.py 位於同一目錄下
try:
    from ..core.shared_splitter import UnifiedTokenSplitter
except ImportError:
    # 備用路徑 (如果放在 utils 資料夾下)
    from core.shared_splitter import UnifiedTokenSplitter

class BaseCrawler(ABC):
    """所有爬蟲的父類別"""

    def __init__(self):
        """
        父類別建構子：負責初始化共用工具。
        """
        # 在這裡實例化一次，所有子類別都能透過 self.token_splitter 使用
        # 統一設定：Token 上限 1500，重疊 300
        print(f"🔧 [BaseCrawler] 初始化共用 Token 切塊工具...")
        self.token_splitter = UnifiedTokenSplitter(chunk_size=1500, overlap=300)

    @property
    @abstractmethod
    def source_name(self) -> str:
        """定義資料來源名稱 (將成為 json 檔名)"""
        pass

    @abstractmethod
    def run(self) -> List[Dict]:
        """
        執行爬取並切塊，回傳已切塊完成的列表。
        """
        pass