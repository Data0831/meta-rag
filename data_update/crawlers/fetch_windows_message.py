import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from config.config import WebsiteKey

# 引入父類別 (若找不到則使用 dummy object 方便單獨測試)
try:
    from .base import BaseCrawler
except ImportError:

    class BaseCrawler:
        def __init__(self):
            # 假設 utils 在同層或子目錄，供測試用
            try:
                from core.shared_splitter import UnifiedTokenSplitter

                self.token_splitter = UnifiedTokenSplitter()
            except ImportError:
                print("Warning: Shared Splitter not found for standalone test.")


# ==========================================
# CONFIG (全域設定)
# ==========================================
MAIN_LINK = (
    "https://learn.microsoft.com/zh-tw/windows/release-health/windows-message-center"
)
REMOVE_LINK = "https://learn.microsoft.com/zh-tw/windows/release-health/"
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ==========================================
# PART 1: 目錄結構爬蟲
# ==========================================
class TocCrawler:
    def run(self):
        """執行目錄爬取，回傳連結集合 (Set)"""
        print(f"--- [Step 1] 開始爬取目錄: {MAIN_LINK} ---")

        toc_data = []
        links = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            page.goto(MAIN_LINK, timeout=60000)

            try:
                # 等待目錄載入
                page.wait_for_selector("ul.tree.table-of-contents", timeout=15000)

                # 遞迴展開
                self._expand_all(page)

                # 解析結構
                root_tree = page.query_selector("ul.tree.table-of-contents")
                if root_tree:
                    toc_data = self._parse_tree(root_tree)

                # 提取連結
                all_links_list = []
                self._extract_links_recursive(toc_data, all_links_list)

                # 轉為 Set 並過濾
                links = set([item["url"] for item in all_links_list if item.get("url")])
                if REMOVE_LINK in links:
                    links.remove(REMOVE_LINK)

            except Exception as e:
                print(f"[Error] 目錄爬取失敗: {e}")
            finally:
                browser.close()

        print(f"--- 目錄爬取完成，共找到 {len(links)} 個連結 ---")
        return links

    def _expand_all(self, page):
        """持續尋找並展開未展開的項目"""
        iteration = 0
        while iteration < 100:
            expandable_items = page.query_selector_all(
                'li.tree-item[aria-expanded="false"]'
            )
            if not expandable_items:
                break
            for item in expandable_items:
                try:
                    expander = item.query_selector("span.tree-expander")
                    if expander:
                        expander.click()
                        time.sleep(0.05)
                except:
                    pass
            time.sleep(0.5)
            iteration += 1

    def _parse_tree(self, parent, level=1):
        """解析 DOM 樹狀結構"""
        items = []
        children = parent.query_selector_all(":scope > li")
        for child in children:
            item_data = {}
            link = child.query_selector("a.tree-item")
            if link:
                item_data = {
                    "title": link.inner_text().strip(),
                    "url": link.get_attribute("href"),
                    "type": "link",
                    "level": level,
                }
            else:
                expander = child.query_selector("span.tree-expander")
                if expander:
                    item_data = {
                        "title": expander.inner_text().strip(),
                        "type": "expandable",
                        "level": level,
                    }
            sub_tree = child.query_selector("ul.tree-group")
            if sub_tree:
                item_data["children"] = self._parse_tree(sub_tree, level + 1)
            if item_data:
                items.append(item_data)
        return items

    def _extract_links_recursive(self, items, out_list):
        for item in items:
            if item.get("type") == "link" and item.get("url"):
                out_list.append({"title": item["title"], "url": item["url"]})
            if "children" in item:
                self._extract_links_recursive(item["children"], out_list)


# ==========================================
# PART 2: 頁面內容爬蟲
# ==========================================
class PageContentScraper:
    def run(self, links_set):
        """接收連結列表，執行迴圈爬取"""
        if not links_set:
            return []
        links_list = list(links_set)
        total = len(links_list)
        results = []

        print(f"--- [Step 2] 開始爬取內容，共 {total} 頁 ---")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(user_agent=USER_AGENT)
            for i, link in enumerate(links_list):
                print(f"[{i+1}/{total}] Processing: {link}")
                try:
                    page = context.new_page()
                    page.goto(link, wait_until="domcontentloaded", timeout=60000)

                    self._wait_for_hydration(page)

                    html = page.content()
                    sections = self._extract_sections(html, link)

                    if sections:
                        results.extend(sections)

                    page.close()
                    time.sleep(1)
                except Exception as e:
                    print(f"    [Error] {link}: {e}")
            browser.close()
        return results

    def _wait_for_hydration(self, page):
        """等待 JS 生成 ID"""
        try:
            page.wait_for_selector(".heading-wrapper", state="attached", timeout=5000)
        except:
            try:
                page.wait_for_function(
                    "() => { const h = document.querySelector('h2'); return h && h.hasAttribute('id'); }",
                    timeout=2000,
                )
            except:
                pass
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except:
            pass

    def _extract_sections(self, html_content, base_url):
        """解析 HTML 為 Markdown Sections"""
        soup = BeautifulSoup(html_content, "html.parser")
        article_header = soup.find(id="article-header")
        parent = (
            article_header.parent
            if article_header
            else (
                soup.find("div", class_="content")
                or soup.find("main")
                or soup.find("article")
            )
        )

        if not parent:
            return []

        # 移除無用標籤
        for tag_name in ["script", "style", "meta", "link", "button"]:
            for tag in parent.find_all(tag_name):
                tag.decompose()
        for tag in parent.find_all("a", class_="anchor-link"):
            tag.decompose()

        all_elements = [e for e in parent.descendants if hasattr(e, "name") and e.name]
        start_index = -1
        for i, el in enumerate(all_elements):
            if self._is_header(el):
                start_index = i
                break

        if start_index == -1:
            return [
                {
                    "id": "main",
                    "title": soup.title.string if soup.title else "Main",
                    "link": base_url.split("#")[0],
                    "heading_link": base_url,
                    "content": self._to_md(parent, base_url.split("#")[0]),
                    "main_title": soup.title.string if soup.title else "Main",
                }
            ]

        sections = []
        curr_node = all_elements[start_index]
        curr_id = curr_node.get("id")
        curr_title = curr_node.get_text(strip=True)
        page_main_title = curr_title
        curr_blocks = []
        processed = {curr_node}

        for i in range(start_index + 1, len(all_elements)):
            node = all_elements[i]
            if node in processed or self._is_child_of(node, processed):
                continue

            if self._is_header(node):
                self._append_section(
                    sections,
                    curr_id,
                    curr_title,
                    base_url,
                    curr_blocks,
                    page_main_title,
                )
                curr_blocks = []
                curr_node = node
                curr_id = node.get("id")
                curr_title = node.get_text(strip=True)
                processed.add(node)
            else:
                if self._has_inner_header(node):
                    continue
                if node.name in ["br", "hr"]:
                    continue

                text = self._to_md(node, base_url)
                if text.strip():
                    curr_blocks.append(text)
                    processed.add(node)

        if curr_blocks:
            self._append_section(
                sections, curr_id, curr_title, base_url, curr_blocks, page_main_title
            )

        return sections

    def _append_section(
        self, sections, curr_id, curr_title, base_url, curr_blocks, page_main_title
    ):
        content = "\n\n".join(curr_blocks)
        if len(content) > 3000:
            split_sections = self._try_split_by_details(
                content, curr_id, base_url, page_main_title, curr_title
            )
            if split_sections:
                sections.extend(split_sections)
                return

        sections.append(
            {
                "id": curr_id,
                "title": curr_title,
                "link": base_url.split("#")[0],
                "heading_link": f"{base_url}#{curr_id}",
                "content": content,
                "main_title": page_main_title,
            }
        )

    def _try_split_by_details(
        self, content, parent_id, base_url, page_main_title, parent_title
    ):
        """嘗試解析並分割含有 details 的長內容"""
        if "<details>" not in content or "<summary>" not in content:
            return None
        try:
            soup = BeautifulSoup(content, "html.parser")
            details_list = soup.find_all("details")
            valid_details = [
                d
                for d in details_list
                if d.find("summary") and d.find("summary").find("strong")
            ]
            if not valid_details:
                return None

            new_sections = []
            buffer = []
            part_index = 0

            for element in soup.contents:
                if element in valid_details:
                    if buffer:
                        text_content = "".join([str(e) for e in buffer]).strip()
                        if text_content:
                            new_sections.append(
                                {
                                    "id": f"{parent_id}_part_{part_index}",
                                    "title": (
                                        parent_title
                                        if part_index == 0
                                        else f"{parent_title} (Part {part_index})"
                                    ),
                                    "link": base_url.split("#")[0],
                                    "heading_link": f"{base_url}#{parent_id}",
                                    "content": text_content,
                                    "main_title": page_main_title,
                                }
                            )
                            part_index += 1
                        buffer = []

                    summary = element.find("summary")
                    strong = summary.find("strong")
                    title = strong.get_text(strip=True)

                    detail_content_soup = BeautifulSoup(
                        str(element), "html.parser"
                    ).details
                    if detail_content_soup.summary:
                        detail_content_soup.summary.decompose()

                    inner_html = detail_content_soup.decode_contents().strip()
                    section_content = md(inner_html, heading_style="ATX")

                    new_sections.append(
                        {
                            "id": f"{parent_id}_detail_{part_index}",
                            "title": title,
                            "link": base_url.split("#")[0],
                            "heading_link": f"{base_url}#{parent_id}",
                            "content": section_content,
                            "main_title": page_main_title,
                        }
                    )
                    part_index += 1
                else:
                    buffer.append(element)

            if buffer:
                text_content = "".join([str(e) for e in buffer]).strip()
                if text_content:
                    new_sections.append(
                        {
                            "id": f"{parent_id}_part_{part_index}",
                            "title": "Summary" if part_index > 0 else "Main",
                            "link": base_url.split("#")[0],
                            "heading_link": f"{base_url}#{parent_id}",
                            "content": text_content,
                            "main_title": page_main_title,
                        }
                    )
            return new_sections
        except:
            return None

    def _is_header(self, tag):
        return (
            tag.name in ["h1", "h2", "h3", "h4"]
            and tag.get("id")
            and tag.parent.name == "div"
        )

    def _has_inner_header(self, tag):
        for child in tag.descendants:
            if hasattr(child, "name") and self._is_header(child):
                return True
        return False

    def _is_child_of(self, node, processed_set):
        for p in processed_set:
            if node in p.descendants:
                return True
        return False

    def _to_md(self, tag, base_url=None):
        if not tag:
            return ""
        if base_url and hasattr(tag, "find_all"):
            for a in tag.find_all("a", href=True):
                a["href"] = urljoin(base_url, a["href"])
            for img in tag.find_all("img", src=True):
                img["src"] = urljoin(base_url, img["src"])
        if tag.name == "details":
            return str(tag)
        return md(str(tag), heading_style="ATX")


# ==========================================
# PART 3: 內容處理 (日期與整合切塊)
# ==========================================
class ContentProcessor:
    def clean_content(self, item):
        title = item.get("title", "")
        # 移除不需要的標題頁面
        if title in [
            "回報 Windows 更新問題",
            "需要 Windows Update 的協助嗎？",
            "以您的語言瀏覽本網站",
        ]:
            return None

        content = item.get("content", "")
        # 移除制式文字
        remove_str = """意見反應\n\n為我建立此文章的摘要\n\n## 本文內容\n\n1. [已知問題](#已知問題)\n2. [問題詳細資料](#問題詳細資料)\n3. [回報 Windows 更新問題](#回報-windows-更新問題)\n4. [需要 Windows Update 的協助嗎？](#需要-windows-update-的協助嗎)\n5. [以您的語言瀏覽本網站](#以您的語言瀏覽本網站)\n\n"""
        if remove_str in content:
            content = content.replace(remove_str, "")

        item["content"] = content
        return item

    def run(self, raw_data, splitter):
        """
        :param raw_data: 爬取的原始資料
        :param splitter: 來自 BaseCrawler 的 token_splitter 實例
        """
        now = datetime.now(timezone(timedelta(hours=8)))
        current_year = now.year
        current_month = now.month
        output_data = []

        for item in raw_data:
            item = self.clean_content(item)
            if item is None:
                continue
            original_content = item.get("content", "")

            # --- 日期提取邏輯 ---
            pattern1 = r"(\d{4})-(\d{1,2})"
            pattern2 = r"(\d{4})\s*年\s*(\d{1,2})\s*月"
            dates = []
            for match in re.finditer(pattern1, original_content):
                dates.append((int(match.group(1)), int(match.group(2))))
            for match in re.finditer(pattern2, original_content):
                dates.append((int(match.group(1)), int(match.group(2))))

            valid_dates = [
                d
                for d in dates
                if 1 <= d[1] <= 12
                and (
                    d[0] < current_year
                    or (d[0] == current_year and d[1] <= current_month)
                )
            ]

            max_date_str = ""
            if valid_dates:
                valid_dates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                max_date_str = f"{valid_dates[0][0]}-{valid_dates[0][1]:02d}"

            # --- 切塊邏輯 (使用 UnifiedTokenSplitter) ---
            # 這裡會自動處理 Token 上限 (1500) 與重疊 (300)
            chunks = splitter.split_text(original_content)

            for content_chunk in chunks:
                if len(content_chunk) < 30:
                    continue  # 過濾過短內容

                new_item = item.copy()
                new_item["content"] = content_chunk
                new_item["year_month"] = max_date_str

                # 🔥 [關鍵修改] 更新 website 欄位
                new_item["website"] = WebsiteKey.WINDOWS_MESSAGE_CENTER

                output_data.append(new_item)

        return output_data


# ==========================================
# 整合類別：WindowsCrawler (繼承 BaseCrawler)
# ==========================================
class WindowsCrawler(BaseCrawler):
    """
    Windows Message Center 爬蟲 (Integrated Version)
    """

    def __init__(self):
        # 呼叫父類別初始化 (會建立 self.token_splitter)
        super().__init__()

    @property
    def source_name(self):
        return "windows_message_center"

    def run(self):
        print(f"🚀 [{self.source_name}] 啟動 Windows Release 爬蟲 (Integrated)...")

        # 1. 爬取目錄
        toc = TocCrawler()
        links = toc.run()

        # 2. 爬取內容
        scraper = PageContentScraper()
        raw_data = scraper.run(links)

        # 3. 後處理 (使用繼承來的 self.token_splitter)
        if raw_data:
            print("--- [Step 3] 開始後處理 (日期與 Token 分割) ---")
            processor = ContentProcessor()
            final_results = processor.run(raw_data, self.token_splitter)

            print(f"✅ 處理完成，共產生 {len(final_results)} 個區塊")
            return final_results
        else:
            print("--- 無資料 ---")
            return []


# 僅供單獨測試用
if __name__ == "__main__":
    crawler = WindowsCrawler()
    result = crawler.run()
    # 寫入檔案檢查 (Optional)
    # with open("windows_message_final.json", "w", encoding="utf-8") as f:
    #     json.dump(result, f, ensure_ascii=False, indent=2)
