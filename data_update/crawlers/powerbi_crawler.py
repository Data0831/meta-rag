import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md_converter
from urllib.parse import urljoin
import time
import re
# 移除不必要的 RecursiveCharacterTextSplitter，保留 MarkdownHeaderTextSplitter 用於結構切分
from langchain_text_splitters import MarkdownHeaderTextSplitter

try:
    from .base import BaseCrawler
except ImportError:
    # 僅供單獨測試用，實際上應確保 BaseCrawler 存在並包含 token_splitter
    class BaseCrawler:
        def __init__(self):
            # 模擬 BaseCrawler 的行為 (若您的 base.py 尚未更新，請略過此段)
            from core.shared_splitter import UnifiedTokenSplitter 
            self.token_splitter = UnifiedTokenSplitter()

class PowerBICrawler(BaseCrawler):
    """
    Power BI 部落格爬蟲 (Integrated Version)
    使用 MarkdownHeaderTextSplitter 進行結構切分，
    並使用 BaseCrawler 的 token_splitter 進行長度強制切分。
    """

    def __init__(self):
        # 🔥 [修改 1] 初始化父類別，取得 self.token_splitter
        super().__init__()
        
        # 1. 初始化全域設定
        self.base_url = "https://powerbi.microsoft.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.years_to_scrape = [2025]
        
        # 2. 切塊參數 (僅用於結構切分前的判斷，實際切分由 splitter 控制)
        self.target_chunk_size = 1500 

        # 3. 初始化工具
        self._init_tools()

    @property
    def source_name(self):
        return "powerbi_blog"
    
    def _init_tools(self):
        """
        🔥 [修改 2] 簡化初始化
        不再需要 tiktoken 或 overflow_splitter，因為 BaseCrawler 已經準備好了 token_splitter
        """
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")],
            strip_headers=False 
        )

    # 移除了 _count_tokens 方法，改用 self.token_splitter.count_tokens

    def _get_soup(self, url, retries=3):
        # ... (保持原樣，省略以節省篇幅) ...
        for attempt in range(1, retries + 1):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                if response.status_code == 200:
                    return BeautifulSoup(response.text, 'html.parser')
                elif response.status_code == 404:
                    return None
                else:
                    time.sleep(2)
            except Exception:
                if attempt < retries: time.sleep(attempt * 2)
        return None

    def _parse_and_clean_article(self, article_url):
        # ... (保持原樣，省略以節省篇幅) ...
        soup = self._get_soup(article_url)
        if not soup: return None
        
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        ignore_titles = ["Microsoft Power BI Blog", "Archives", "Page not found"]
        if any(ignore.lower() in title.lower() for ignore in ignore_titles): return None

        content_div = soup.find('div', class_='entry-content') or soup.find('article')
        
        if content_div:
            junk_selectors = [".share-buttons", ".social-share", ".related-posts", "script", "style", ".uhf-footer"]
            for selector in junk_selectors:
                for tag in content_div.select(selector): tag.extract()

            nav_keywords = ["ANNOUNCEMENTS", "DEVELOPERS", "FEATURES", "POWER BI", "LEARN MORE"]
            for nav_link in content_div.find_all('a'):
                if nav_link.get_text(strip=True).upper() in nav_keywords:
                    nav_link.extract()

            for header in content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                if not header.get_text(strip=True):
                    header.decompose()

            for block in content_div.find_all(['p', 'div', 'br', 'li', 'blockquote']):
                block.insert_after("\n")
            
            for a_tag in content_div.find_all('a', href=True):
                if a_tag['href'].startswith('/'):
                    a_tag['href'] = urljoin(self.base_url, a_tag['href'])

            markdown_content = md_converter(str(content_div), heading_style="ATX")
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
            
            return {"title": title, "content": markdown_content}
        return None

    def _resolve_nearest_title(self, metadata, main_title):
        if "H3" in metadata: return metadata["H3"]
        if "H2" in metadata: return metadata["H2"]
        if "H1" in metadata: return metadata["H1"]
        return main_title

    def _split_markdown_into_chunks(self, article_data, year_month, link):
        final_chunks = []
        
        title = article_data['title'].strip()
        raw_content = article_data['content'].strip()
        first_line = raw_content.split('\n')[0].strip()
        
        if first_line.startswith("#") and title.lower() in first_line.lower():
            full_markdown = raw_content
        else:
            full_markdown = f"# {title}\n\n{raw_content}"

        # 1. 結構化切分 (Structure Split) - 這是 PowerBI 爬蟲特有的邏輯，保留
        semantic_docs = self.markdown_splitter.split_text(full_markdown)
        
        for doc in semantic_docs:
            chunk_content = doc.page_content.strip()
            metadata = doc.metadata 
            
            if not chunk_content or set(chunk_content) <= {'#', ' ', '\n', '\t'}:
                continue
                
            # 🔥 [修改 3] 使用共用 Splitter 進行長度檢查與切分
            # 這裡不需再判斷 if/else，直接呼叫 split_text
            # 因為 split_text 內部會檢查：如果不超過長度，它會直接回傳 [text]
            
            sub_chunk_texts = self.token_splitter.split_text(chunk_content)
            
            chunk_title = self._resolve_nearest_title(metadata, title)

            # 遍歷切分後的文字塊，補上 Metadata
            for text_part in sub_chunk_texts:
                if not text_part.strip(): continue

                chunk_obj = {
                    "website": "PowerBI Blog",
                    "link": link,
                    "heading_link": link,
                    "year_month": year_month,
                    "main_title": title,
                    "title": chunk_title,
                    "content": text_part # 填入處理好的文字
                }
                final_chunks.append(chunk_obj)
                
        return final_chunks

    def run(self):
        # ... (保持原樣，省略以節省篇幅) ...
        print(f"🚀 [PowerBICrawler] Starting Scraper (Integrated with UnifiedTokenSplitter)...")
        all_final_dataset = []

        for year in self.years_to_scrape:
            print(f"\n****** Processing Year: {year} ******")
            
            for month in range(12, 0, -1):
                month_str = f"{year}-{month:02d}"
                print(f"\n=== Processing Month: {month_str} ===")
                
                page = 1
                while True:
                    soup = None
                    if page == 1:
                        url = f"{self.base_url}/en-us/blog/{year}/{month:02d}/"
                        soup = self._get_soup(url)
                    else:
                        url_v1 = f"{self.base_url}/en-us/blog/{year}/{month:02d}/?page={page}"
                        soup = self._get_soup(url_v1)
                        if not (soup and soup.find_all(['h2', 'h3'], class_=lambda x: x != 'widget-title')):
                            url_v2 = f"{self.base_url}/en-us/blog/{year}/{month:02d}/page/{page}/"
                            soup = self._get_soup(url_v2)
                            if not (soup and soup.find_all(['h2', 'h3'], class_=lambda x: x != 'widget-title')): 
                                soup = None

                    if not soup:
                        if page > 1: print(f"  Month {month_str} finished (End of pages).")
                        break

                    article_headers = soup.find_all(['h2', 'h3'])
                    if not article_headers: break

                    article_links = []
                    for h_tag in article_headers:
                        a_tag = h_tag.find('a')
                        if a_tag and 'href' in a_tag.attrs:
                            link = a_tag['href']
                            if "/blog/" in link:
                                if "microsoft.com" not in link: link = urljoin(self.base_url, link)
                                if "/zh-tw/" in link: continue
                                if link.rstrip('/').endswith("/en-us/blog"): continue
                                if link not in article_links: article_links.append(link)

                    if not article_links: 
                        print(f"  No more new articles found at Page {page}.")
                        break
                    
                    print(f"  --> Page {page}: Found {len(article_links)} articles")

                    for link in article_links:
                        data = self._parse_and_clean_article(link)
                        if data:
                            chunks = self._split_markdown_into_chunks(data, month_str, link)
                            print(f"    Processing: {data['title'][:40]}... | 產生 {len(chunks)} 個切塊")
                            all_final_dataset.extend(chunks)
                        else:
                            print(f"    Skipped (Invalid): {link}")
                        time.sleep(1)

                    page += 1
                    time.sleep(1) 

        print("------------------------------------------------")
        print(f"✅ [PowerBICrawler] Execution Complete.")
        print(f"📊 Total Chunks Generated: {len(all_final_dataset)}")
        
        return all_final_dataset