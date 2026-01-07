import time
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from markdownify import markdownify as md_converter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from playwright.sync_api import sync_playwright

import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from config.config import WebsiteKey

# 引入父類別
try:
    from .base import BaseCrawler
except ImportError:

    class BaseCrawler:
        def __init__(self):
            try:
                from core.shared_splitter import UnifiedTokenSplitter

                self.token_splitter = UnifiedTokenSplitter()
            except:
                pass


class MSRCCrawler(BaseCrawler):
    """
    MSRC 部落格爬蟲 (Integrated Version)

    整合特性：
    1. 架構統一：繼承 BaseCrawler，使用 UnifiedTokenSplitter。
    2. 雙層切分：先切 Markdown 結構 (H1/H2/H3)，再切 Token，確保標題對應準確。
    3. Playwright 核心：保留 WAF 繞過與動態載入能力。
    4. 年份過濾：保留遇到 "/2024/" 即停止的邏輯。
    """

    def __init__(self):
        # 🔥 [修改 1] 初始化父類別，取得 self.token_splitter
        super().__init__()

        self.base_url = "https://www.microsoft.com"
        self.start_url = "https://www.microsoft.com/en-us/msrc/blog/category?cat=MSRC"

        # 🔥 [修改 2] 設定固定欄位 website
        # self.website_name = "MSRC_blog"

        # 初始化結構切分工具 (Token 切分工具已由 BaseCrawler 提供)
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")],
            strip_headers=False,
        )

    @property
    def source_name(self):
        return "msrc_blog"

    def _parse_and_clean_content(self, html_content, url):
        """
        解析 HTML 內容 (保持原樣)
        """
        if not html_content:
            return None
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. 抓取標題
        title_tag = (
            soup.find("h1")
            or soup.find("div", class_="post-title")
            or soup.find("title")
        )
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        title = title.split(" - Microsoft")[0]

        ignore_titles = [
            "Page not found",
            "Error",
            "Access Denied",
            "Microsoft",
            "Just a moment...",
        ]
        if any(x in title for x in ignore_titles):
            return None

        # 2. 抓取內容
        content_div = (
            soup.find("div", class_="entry-content")
            or soup.find("div", class_="post-content")
            or soup.find("main")
            or soup.find("article")
            or soup.find("div", id="main-content")
        )

        if content_div:
            # 移除雜訊
            junk_selectors = [
                ".share-buttons",
                ".social-share",
                ".related-posts",
                "script",
                "style",
                "noscript",
                ".uhf-footer",
                "#uhf-footer",
                ".global-footer",
                "[aria-label='Breadcrumb']",
                ".pagenav",
                ".row.text-center",
                "footer",
                "nav",
                ".wafer-cookie-banner",
            ]
            for selector in junk_selectors:
                for tag in content_div.select(selector):
                    tag.extract()

            nav_keywords = [
                "ANNOUNCEMENTS",
                "DEVELOPERS",
                "FEATURES",
                "LEARN MORE",
                "MSRC",
                "READ MORE",
            ]
            for nav_link in content_div.find_all("a"):
                if nav_link.get_text(strip=True).upper() in nav_keywords:
                    nav_link.extract()

            for header in content_div.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                if not header.get_text(strip=True):
                    header.decompose()

            for block in content_div.find_all(
                ["p", "div", "br", "li", "blockquote", "tr"]
            ):
                block.insert_after("\n")

            for a_tag in content_div.find_all("a", href=True):
                if a_tag["href"].startswith("/"):
                    a_tag["href"] = urljoin(self.base_url, a_tag["href"])

            markdown_content = md_converter(str(content_div), heading_style="ATX")
            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

            return {"title": title, "content": markdown_content}
        return None

    def _resolve_nearest_title(self, metadata, main_title):
        """解析最近的標題 (H3 > H2 > H1 > Main Title)"""
        if "H3" in metadata:
            return metadata["H3"]
        if "H2" in metadata:
            return metadata["H2"]
        if "H1" in metadata:
            return metadata["H1"]
        return main_title

    def _split_markdown_into_chunks(self, article_data, source_tag, link):
        """
        改用 MarkdownHeaderTextSplitter + TokenSplitter 進行雙層切分
        """
        final_chunks = []
        main_title = article_data["title"].strip()
        raw_content = article_data["content"].strip()

        if not raw_content:
            return []

        # 確保有 H1 大標題 (使用 main_title)
        if not raw_content.startswith("#"):
            raw_content = f"# {main_title}\n\n{raw_content}"

        # 1. 第一層：依照 Markdown 結構切分 (H1, H2, H3)
        semantic_docs = self.markdown_splitter.split_text(raw_content)

        for doc in semantic_docs:
            chunk_content = doc.page_content.strip()
            metadata = doc.metadata

            if not chunk_content or set(chunk_content) <= {"#", " ", "\n", "\t"}:
                continue

            # 2. 第二層：依照 Token 數量切分 (使用 BaseCrawler 工具)
            sub_chunks = self.token_splitter.split_text(chunk_content)

            # 解析最近的小標題
            chunk_title = self._resolve_nearest_title(metadata, main_title)

            for sub_chunk in sub_chunks:
                if not sub_chunk.strip():
                    continue

                chunk_obj = {
                    "website": WebsiteKey.MSRC_BLOG,  # 🔥 [修改 3] 固定 website 為 MSRC_blog
                    "link": link,
                    "heading_link": link,
                    "year_month": source_tag,
                    "main_title": main_title,  # 🔥 [修改 4] 文章大標題
                    "title": chunk_title,  # 🔥 [修改 5] 最近的章節小標題
                    "content": sub_chunk,
                }
                final_chunks.append(chunk_obj)

        return final_chunks

    def run(self):
        print(f"🚀 [{self.source_name}] Starting Playwright Scraper (Integrated)...")
        all_final_dataset = []

        # 啟動 Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            page_num = 1
            max_empty_pages = 2
            empty_page_count = 0
            stop_crawling = False

            while not stop_crawling:
                target_url = (
                    self.start_url
                    if page_num == 1
                    else f"{self.start_url}&page={page_num}"
                )
                print(f"\n=== Processing Page {page_num} ===")
                print(f"    URL: {target_url}")

                try:
                    # 1. 前往列表頁
                    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                    time.sleep(2)

                    if (
                        "Access Denied" in page.title()
                        or "Just a moment" in page.title()
                    ):
                        print("  ⚠️ WAF Challenge detected. Waiting for auto-solve...")
                        time.sleep(5)

                    html_content = page.content()
                    soup = BeautifulSoup(html_content, "html.parser")

                    # 2. 提取文章連結
                    all_links = soup.find_all("a", href=True)
                    article_links = []

                    for a_tag in all_links:
                        link = a_tag["href"]
                        if not link.startswith("http"):
                            link = urljoin(self.base_url, link)

                        if "/msrc/blog/" in link and re.search(r"/20\d{2}/", link):
                            if (
                                "category" not in link
                                and "feed" not in link
                                and "tag" not in link
                            ):
                                if link not in article_links:
                                    article_links.append(link)

                    if not article_links:
                        print(f"  ⚠️ Page {page_num} has no articles.")
                        empty_page_count += 1
                        if empty_page_count >= max_empty_pages:
                            print("  🛑 Reached limit of empty pages. Stopping.")
                            break
                    else:
                        empty_page_count = 0
                        print(
                            f"  --> Page {page_num}: Found {len(article_links)} potential articles"
                        )

                    # 3. 逐一處理文章
                    for link in article_links:

                        # 🛑 檢查年份：如果是 2024 文章，直接觸發停止
                        if "/2024/" in link:
                            print(f"  🛑 Found 2024 article: {link}")
                            print("  🛑 Stopping crawler as we reached older content.")
                            stop_crawling = True
                            break

                        print(f"    Fetching: {link}")
                        try:
                            # 訪問內頁
                            page.goto(
                                link, wait_until="domcontentloaded", timeout=45000
                            )
                            time.sleep(1)

                            article_html = page.content()
                            data = self._parse_and_clean_content(article_html, link)

                            if data:
                                date_match = re.search(r"/(\d{4})/(\d{2})/", link)
                                year_month_tag = (
                                    f"{date_match.group(1)}-{date_match.group(2)}"
                                    if date_match
                                    else "MSRC-Latest"
                                )

                                # 使用新的雙層切分邏輯
                                chunks = self._split_markdown_into_chunks(
                                    data, year_month_tag, link
                                )
                                print(
                                    f"    Processing: {data['title'][:40]}... | {len(chunks)} Chunks"
                                )
                                all_final_dataset.extend(chunks)
                            else:
                                print(f"    Skipped (No Content/Filtered)")

                        except Exception as e:
                            print(f"    Error processing link {link}: {e}")

                        time.sleep(1)

                    if stop_crawling:
                        break

                except Exception as e:
                    print(f"  🛑 Error on Page {page_num}: {e}")
                    break

                page_num += 1
                time.sleep(1)

            browser.close()

        print("------------------------------------------------")
        print(f"✅ [{self.source_name}] Execution Complete.")
        print(f"📊 Total Chunks Generated: {len(all_final_dataset)}")

        return all_final_dataset


if __name__ == "__main__":
    crawler = MSRCCrawler()
    # crawler.run()
