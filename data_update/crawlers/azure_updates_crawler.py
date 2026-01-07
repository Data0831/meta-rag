import requests
import re
import html
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class AzureUpdatesCrawler(BaseCrawler):
    """
    Azure Updates 爬蟲 (Modified Version)

    修改記錄：
    1. main_title 改為與 title 相同。
    2. JSON 欄位 workspace 改名為 website。
    """

    def __init__(self):
        super().__init__()

        # 1. 設定
        self.azure_updates_page = "https://azure.microsoft.com/zh-tw/updates/"
        self.api_url_base = (
            "https://www.microsoft.com/releasecommunications/api/v2/azure"
        )
        self.page_size = 200

        # 🔥 [修改 1] 將識別名稱變數改為 website_name
        # self.website_name = "Azure Updates"

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Referer": self.azure_updates_page,
            "Origin": "https://www.microsoft.com",
        }

    @property
    def source_name(self) -> str:
        return "azure_updates"

    def run(self) -> List[Dict]:
        print(f"🚀 [{self.source_name}] 啟動 Azure Updates 爬蟲...")

        try:
            # 1. 抓取所有資料
            raw_items = self._fetch_all()

            final_chunks = []
            chunked_count = 0

            # 2. 處理每一篇文章
            for item in raw_items:
                base_chunk_content = self._build_content(item)

                # 使用 UnifiedTokenSplitter 進行切塊
                split_texts = self.token_splitter.split_text(base_chunk_content)

                if len(split_texts) > 1:
                    chunked_count += 1

                # 封裝結果
                item_id = self._safe_str(item.get("id"))
                link = self._build_link(item_id)

                # 取得標題
                title = self._safe_str(item.get("title"))

                # 🔥 [修改 2] main_title 現在比照 title (內容一致)
                main_title = title

                year_month = self._format_year_month(
                    self._safe_str(item.get("modified"))
                )

                for text_part in split_texts:
                    chunk_obj = {
                        # 🔥 [修改 3] 欄位名稱改為 website
                        # "website": self.website_name,
                        "website": WebsiteKey.AZURE_UPDATES,
                        "title": title,
                        "link": link,
                        "heading_link": link,
                        "content": text_part,
                        "main_title": main_title,
                        "year_month": year_month,
                    }
                    final_chunks.append(chunk_obj)

            print(
                f"✅ [{self.source_name}] 處理完成: 原文 {len(raw_items)} 篇 -> 切分後 {len(final_chunks)} 塊"
            )

            return final_chunks

        except Exception as e:
            print(f"❌ [{self.source_name}] 執行發生錯誤: {e}")
            return []

    # =========================
    # 網路請求與基礎轉換
    # =========================

    def _fetch_all(self) -> List[Dict[str, Any]]:
        session = requests.Session()
        session.headers.update(self.headers)
        try:
            session.get(self.azure_updates_page, timeout=30)
        except:
            pass

        all_items = []
        next_url = f"{self.api_url_base}?$count=true&includeFacets=true&top={self.page_size}&orderby=modified%20desc"

        page_count = 0
        while next_url:
            page_count += 1
            print(f"    📄 Page {page_count}...")
            try:
                resp = session.get(next_url, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("value") or []

                if not isinstance(items, list):
                    break

                all_items.extend(items)
                next_url = data.get("@odata.nextLink")
            except Exception as e:
                print(f"    ❌ Error on page {page_count}: {e}")
                break
        return all_items

    # =========================
    # HTML 轉 Markdown 與 Metadata 組合
    # =========================

    def _build_content(self, item: Dict[str, Any]) -> str:
        # Metadata
        meta_top = []
        products = item.get("products") or []
        status = self._safe_str(item.get("status"))
        availabilities = item.get("availabilities") or []

        if products:
            meta_top.append(f"**Products**: {', '.join(products)}")
        if status:
            meta_top.append(f"**Status**: {status}")
        if availabilities:
            parts = []
            for a in availabilities:
                ring = self._safe_str(a.get("ring"))
                year = a.get("year")
                month = self._safe_str(a.get("month"))
                ym = f"{month} {year}" if year and month else ""
                if ring and ym:
                    parts.append(f"{ring}: {ym}")
            if parts:
                meta_top.append(f"**Availabilities**: {'; '.join(parts)}")

        # Body
        body_md = self._html_to_markdown(self._safe_str(item.get("description")))

        # Bottom Metadata
        meta_bottom = []
        item_id = self._safe_str(item.get("id"))
        product_categories = item.get("productCategories") or []
        tags = item.get("tags") or []
        created = self._format_date(self._safe_str(item.get("created")))
        modified = self._format_date(self._safe_str(item.get("modified")))

        if item_id:
            meta_bottom.append(f"**Azure ID**: {item_id}")
        if product_categories:
            meta_bottom.append(
                f"**Product Categories**: {', '.join(product_categories)}"
            )
        if tags:
            meta_bottom.append(f"**Update Types**: {', '.join(tags)}")
        if created:
            meta_bottom.append(f"**Added to roadmap**: {created}")
        if modified:
            meta_bottom.append(f"**Last modified**: {modified}")

        parts = [
            p
            for p in ["\n".join(meta_top), body_md, "\n".join(meta_bottom)]
            if p.strip()
        ]
        return "\n\n".join(parts)

    def _html_to_markdown(self, html_text: str) -> str:
        if not html_text:
            return ""
        text = html.unescape(html_text)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

        # 表格處理
        def repl_table(m):
            t = m.group(1)
            t = re.sub(
                r"<td[^>]*>(.*?)</td>", r"\1\t", t, flags=re.DOTALL | re.IGNORECASE
            )
            t = re.sub(
                r"<th[^>]*>(.*?)</th>", r"\1\t", t, flags=re.DOTALL | re.IGNORECASE
            )
            t = re.sub(r"</t[rd]>\s*<t[rd][^>]*>", "\t", t, flags=re.IGNORECASE)
            t = re.sub(r"<tr[^>]*>\s*", "", t, flags=re.IGNORECASE)
            t = re.sub(r"</tr>", "\n", t, flags=re.IGNORECASE)
            return t

        text = re.sub(
            r"<table[^>]*>(.*?)</table>",
            repl_table,
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # 連結與列表處理
        text = re.sub(
            r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            lambda m: f"[{m.group(2).strip()}]({m.group(1).strip()})",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"<li[^>]*>(.*?)</li>",
            lambda m: f"- {re.sub(r'<[^>]+>', '', m.group(1)).strip()}\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"<p[^>]*>(.*?)</p>",
            lambda m: f"{re.sub(r'<[^>]+>', '', m.group(1)).strip()}\n\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # 清除剩餘 HTML
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\r", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # =========================
    # Helpers
    # =========================

    def _safe_str(self, v: Any) -> str:
        return str(v).strip() if v is not None else ""

    def _format_date(self, d: str) -> str:
        if not d:
            return ""
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except:
            return re.sub(r"[^\d-].*", "", d)[:10]

    def _format_year_month(self, d: str) -> str:
        if not d:
            return ""
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%Y-%m")
        except:
            return re.sub(r"[^\d-].*", "", d)[:7]

    def _build_link(self, i: str) -> str:
        return f"https://azure.microsoft.com/updates/{i}/" if i else ""
