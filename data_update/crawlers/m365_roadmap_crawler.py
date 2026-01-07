import requests
import re
from typing import Any, Dict, List, Optional, Tuple

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from config.config import WebsiteKey

# 引入父類別，若找不到則使用 dummy object (測試用)
try:
    from .base import BaseCrawler
except ImportError:

    class BaseCrawler:
        def __init__(self):
            # 假設 utils 在同層或子目錄
            try:
                from core.shared_splitter import UnifiedTokenSplitter

                self.token_splitter = UnifiedTokenSplitter()
            except ImportError:
                print("Warning: Shared Splitter not found.")


class M365RoadmapCrawler(BaseCrawler):
    """
    Microsoft 365 Roadmap 爬蟲 (Integrated Version)
    API: https://www.microsoft.com/releasecommunications/api/v1/m365
    """

    def __init__(self):
        # 🔥 [修改 1] 初始化父類別，繼承 self.token_splitter
        super().__init__()

        # 設定
        self.roadmap_page = "https://www.microsoft.com/zh-tw/microsoft-365/roadmap"
        self.api_url = "https://www.microsoft.com/releasecommunications/api/v1/m365"
        self.card_link_template = (
            "https://www.microsoft.com/zh-tw/microsoft-365/roadmap?id={id}"
        )

        self.website_name = "M365 Roadmap"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Referer": self.roadmap_page,
            "Origin": "https://www.microsoft.com",
        }

        self.month_map = {
            "January": "01",
            "February": "02",
            "March": "03",
            "April": "04",
            "May": "05",
            "June": "06",
            "July": "07",
            "August": "08",
            "September": "09",
            "October": "10",
            "November": "11",
            "December": "12",
        }

        # 狀態映射
        self.status_map = {
            "in development": "in_development",
            "rolling out": "rolling_out",
            "launched": "launched",
        }

        # 標題顯示名稱 (這裡保留 map 但主要邏輯會改用 item title)
        self.status_title_map = {
            "in_development": "In development",
            "rolling_out": "Rolling out",
            "launched": "Launched",
        }

    @property
    def source_name(self) -> str:
        # 這會決定最後存檔的檔名： data/m365_roadmap.json
        return "m365_roadmap"

    def run(self) -> List[Dict]:
        print(f"🚀 [{self.source_name}] Starting M365 Roadmap Scraper (Integrated)...")

        try:
            # 1. 抓取原始資料
            raw_data = self._fetch_all()
            print(f"    -> API 回傳 {len(raw_data)} 筆資料")

            # 2. 轉換與分組
            bucket = {
                "in_development": [],
                "rolling_out": [],
                "launched": [],
            }
            for it in raw_data:
                st = self.status_map.get(self._safe_status(it.get("status")))
                if st:
                    bucket[st].append(self._to_card(it))

            grouped_data = {}
            for st, cards in bucket.items():
                grouped_data[st] = self._group_by_month(cards)

            # 3. 扁平化 (Flatten) 為系統標準格式
            final_chunks = self._export_flat_list(grouped_data)

            print(f"✅ [{self.source_name}] Processed {len(final_chunks)} chunks.")
            return final_chunks

        except Exception as e:
            print(f"❌ [{self.source_name}] Error: {e}")
            return []

    # =========================
    # 內部邏輯方法
    # =========================
    def _fetch_all(self) -> List[Dict[str, Any]]:
        session = requests.Session()
        session.headers.update(self.headers)
        try:
            session.get(self.roadmap_page, timeout=10)  # warm-up
        except:
            pass

        r = session.get(self.api_url, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []
        return data

    def _safe_status(self, s: Any) -> str:
        return str(s or "").strip().lower()

    def _parse_month_key(self, s: str) -> Optional[str]:
        if not s:
            return None
        m = re.match(
            r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+CY(\d{4})$",
            str(s).strip(),
        )
        if not m:
            return None
        return f"{m.group(2)}-{self.month_map[m.group(1)]}"

    def _pick_tag_names(self, item: Dict[str, Any], path: Tuple[str, ...]) -> List[str]:
        cur: Any = item
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return []
            cur = cur[p]
        if not isinstance(cur, list):
            return []
        return [
            x.get("tagName", "")
            for x in cur
            if isinstance(x, dict) and x.get("tagName")
        ]

    def _to_card(self, item: Dict[str, Any]) -> Dict[str, Any]:
        card_id = item.get("id")
        link = self.card_link_template.format(id=card_id) if card_id is not None else ""
        return {
            "id": card_id,
            "link": link,
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "status": item.get("status", ""),
            "preview_available": item.get("publicPreviewDate", ""),
            "rollout_start": item.get("publicDisclosureAvailabilityDate", ""),
            "moreInfoLink": item.get("moreInfoLink"),
            "products": self._pick_tag_names(item, ("tagsContainer", "products")),
            "platforms": self._pick_tag_names(item, ("tagsContainer", "platforms")),
            "cloud_instances": self._pick_tag_names(
                item, ("tagsContainer", "cloudInstances")
            ),
            "release_phases": self._pick_tag_names(
                item, ("tagsContainer", "releasePhase")
            ),
            "added_to_roadmap": item.get("created", ""),
            "last_modified": item.get("modified", ""),
        }

    def _group_by_month(
        self, cards: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for c in cards:
            key = (
                self._parse_month_key(c.get("preview_available", ""))
                or self._parse_month_key(c.get("rollout_start", ""))
                or "unknown"
            )
            grouped.setdefault(key, []).append(c)

        for k in grouped:
            grouped[k].sort(
                key=lambda x: (x.get("preview_available", ""), x.get("title", ""))
            )

        return dict(sorted(grouped.items(), key=lambda x: (x[0] == "unknown", x[0])))

    def _export_flat_list(
        self, data: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> List[Dict[str, Any]]:
        """
        將分組資料轉為 DiffEngine 可吃的 Flat List (含切塊邏輯)
        """
        results: List[Dict[str, Any]] = []

        for status_key, months in data.items():
            # 原始狀態標題 (僅供參考)
            # status_title = self.status_title_map.get(status_key, "Microsoft 365 Roadmap")

            for year_month, items in months.items():
                for it in items:
                    parts: List[str] = []

                    # 內文組合
                    if it.get("description"):
                        parts.append(it["description"].strip())
                    if it.get("status"):
                        parts.append(f"Status: {it['status']}")
                    if it.get("preview_available"):
                        parts.append(f"Preview available: {it['preview_available']}")
                    if it.get("rollout_start"):
                        parts.append(f"Rollout start: {it['rollout_start']}")

                    # 標籤類
                    if it.get("cloud_instances"):
                        parts.append(
                            f"Cloud instances: {', '.join(it['cloud_instances'])}"
                        )
                    if it.get("release_phases"):
                        parts.append(
                            f"Release phases: {', '.join(it['release_phases'])}"
                        )
                    if it.get("products"):
                        parts.append(f"Products: {', '.join(it['products'])}")
                    if it.get("platforms"):
                        parts.append(f"Platforms: {', '.join(it['platforms'])}")

                    if it.get("moreInfoLink"):
                        parts.append(f"More info: {it['moreInfoLink']}")

                    content_str = "\n".join([p for p in parts if p]).strip()
                    link = it.get("link", "") or ""

                    # 取得標題
                    title = it.get("title", "") or ""

                    # 🔥 [修改 2] main_title 比照 title
                    main_title = title

                    # 🔥 [修改 3] 使用 token_splitter 進行切塊
                    split_texts = self.token_splitter.split_text(content_str)

                    for text_part in split_texts:
                        chunk = {
                            "website": WebsiteKey.M365_ROADMAP,
                            "title": title,
                            "link": link,
                            "heading_link": link,
                            "content": text_part,
                            "main_title": main_title,
                            "year_month": year_month,
                        }
                        results.append(chunk)

        return results
