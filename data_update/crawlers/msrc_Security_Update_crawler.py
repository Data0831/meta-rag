import time
import re
import os
import sys
import random
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from markdownify import markdownify as md_converter
from datetime import datetime, timedelta

# ==========================================
# 1. 路徑設定：確保能引用 ../core/shared_splitter.py
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__)) # 取得 crawlers 資料夾路徑
parent_dir = os.path.dirname(current_dir)                # 取得 Microsoft_QA 資料夾路徑
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 嘗試匯入 UnifiedTokenSplitter
try:
    from core.shared_splitter import UnifiedTokenSplitter
except ImportError:
    print("❌ [Error] 無法匯入 UnifiedTokenSplitter，請確認 core/shared_splitter.py 是否存在。")
    # 這裡不強制退出，避免 IDE 檢查報錯，但執行時若無此檔會失敗
    UnifiedTokenSplitter = None 

# 保留 curl_cffi 用於繞過 WAF
from curl_cffi import requests

# 嘗試引用 BaseCrawler，若無則繼承 object
try:
    from .base import BaseCrawler
except ImportError:
    BaseCrawler = object

class MSRCGuideLocalCsvCrawler(BaseCrawler):
    """
    MSRC Update Guide 爬蟲 (本地 CSV 版)
    整合自動路徑偵測與 UnifiedTokenSplitter
    """

    def __init__(self, csv_file_path=None):
        """
        Args:
            csv_file_path (str, optional): CSV 路徑。
            若排程器未提供參數 (None)，程式會自動鎖定同目錄下的 'MSRC_Request.csv'。
        """
        # ==========================================
        # 2. CSV 路徑智慧判斷 (絕對路徑解決方案)
        # ==========================================
        # 取得這支程式 (msrc_spider.py) 所在的絕對資料夾路徑
        # 例如: C:\Users\2512050\Desktop\Microsoft_QA\crawlers
        current_crawler_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 組合出預設 CSV 的絕對路徑
        default_absolute_path = os.path.join(current_crawler_dir, "MSRC_Request.csv")

        if csv_file_path is None:
            # 情況 A: 排程器沒傳參數 -> 使用預設絕對路徑
            self.csv_file_path = default_absolute_path
            print(f"  🔧 未指定 CSV 路徑，自動鎖定: {self.csv_file_path}")
        else:
            # 情況 B: 有傳參數 -> 檢查有效性
            if os.path.exists(csv_file_path):
                self.csv_file_path = csv_file_path
            elif os.path.exists(default_absolute_path):
                # 參數路徑無效，但預設路徑有效 -> 自動修正
                print(f"  ⚠️ 指定路徑 '{csv_file_path}' 無效，自動切換至預設路徑: {default_absolute_path}")
                self.csv_file_path = default_absolute_path
            else:
                # 都找不到 -> 保留原值讓後面噴錯
                self.csv_file_path = csv_file_path

        self.base_url = "https://msrc.microsoft.com"
        
        # 設定下載目錄 (使用絕對路徑)
        self.download_dir = os.path.join(current_crawler_dir, "downloads")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        self.impersonate_list = [
            "chrome110", "chrome119", "chrome120", 
            "edge99", "edge101", 
            "safari15_5"
        ]
        
        self.target_chunk_size = 1500
        self.overlap_size = 300
        self._init_tools()

    @property
    def source_name(self):
        return "msrc_kb_article"

    def _init_tools(self):
        """
        初始化 UnifiedTokenSplitter
        """
        if UnifiedTokenSplitter:
            print("  🔧 Initializing UnifiedTokenSplitter with tolerance=200...")
            self.text_splitter = UnifiedTokenSplitter(
                model_name="gpt-4o",
                chunk_size=self.target_chunk_size,
                overlap=self.overlap_size,
                tolerance=200  # 🔥 容許值：總長 1700 以內不切分
            )
        else:
            raise ImportError("UnifiedTokenSplitter not loaded.")

    def _create_single_shot_session(self):
        """建立一次性 Session"""
        browser_ver = random.choice(self.impersonate_list)
        session = requests.Session(impersonate=browser_ver)
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://msrc.microsoft.com/",
            "Connection": "close" 
        })
        return session

    def _fetch_and_parse_article(self, url):
        """抓取單篇文章"""
        session = None
        try:
            session = self._create_single_shot_session()
            response = session.get(url, timeout=30)
            
            if response.status_code == 403: return "403_FORBIDDEN"
            if response.status_code == 404: return "404_NOT_FOUND"
            if response.status_code != 200:
                print(f"    ❌ HTTP Error {response.status_code}")
                return None

            html_content = response.text
            if "Access Denied" in html_content or "Request is blocked" in html_content:
                return "BLOCKED_CONTENT"

            soup = BeautifulSoup(html_content, 'html.parser')
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            title = title.split(" - Microsoft")[0]

            # 嘗試定位主要內容區塊
            content_div = soup.find('div', id='main') or \
                          soup.find('main') or \
                          soup.find('article') or \
                          soup.find('div', class_='support-content') or \
                          soup.find('div', class_='article-content') or \
                          soup.find('div', class_='ocpArticleContent') or \
                          soup.find('div', id='sup-article-content')
            
            if content_div:
                junk_selectors = ["script", "style", "nav", "footer", "button", ".no-print", ".sup-metablock", "#sup-article-feedback", ".wafer-cookie-banner"]
                for selector in junk_selectors:
                    for tag in content_div.select(selector): tag.extract()

                for a_tag in content_div.find_all('a', href=True):
                    if a_tag['href'].startswith('/'):
                        a_tag['href'] = urljoin(self.base_url, a_tag['href'])

                markdown_content = md_converter(str(content_div), heading_style="ATX")
                markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
                return {"title": title, "content": markdown_content}
            
            return None

        except Exception as e:
            error_str = str(e).lower()
            if "curl" in error_str or "connection" in error_str or "failed to connect" in error_str:
                return "CONNECTION_ERROR"
            print(f"    ❌ Generic Error: {e}")
            return None
        finally:
            if session: session.close()

    def _extract_date(self, text):
        if not text: return None
        match_chi = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
        if match_chi:
            y, m, d = match_chi.groups()
            return f"{y}-{int(m):02d}-{int(d):02d}"
        match_eng = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', text, re.IGNORECASE)
        if match_eng:
            try:
                dt_obj = datetime.strptime(match_eng.group(0), "%B %d, %Y")
                return dt_obj.strftime("%Y-%m-%d")
            except ValueError: pass
        match_simple = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
        if match_simple:
            y, m, d = match_simple.groups()
            return f"{y}-{int(m):02d}-{int(d):02d}"
        return None

    def _create_chunks(self, kb_id, link, content_data, csv_date=None):
        """
        切塊邏輯
        :param csv_date: 從 CSV 傳入的 Release Date (格式 YYYY-MM-DD)，若有則優先使用
        """
        chunks = []
        raw_content = content_data['content']
        page_title = content_data['title']
        main_title = f"KB{kb_id}: {page_title}"
        
        # 🔥 [修改部分] Year-Month 邏輯
        # 1. 優先使用 CSV 提供的日期
        if csv_date:
            # csv_date 格式為 '2025-01-15'，只取前 7 碼 => '2025-01'
            year_month_val = str(csv_date)[:7]
        else:
            # 2. 備援：解析網頁標題或內文
            extracted_date = self._extract_date(page_title)
            if not extracted_date:
                extracted_date = self._extract_date(raw_content[:500])
            
            # 如果有抓到日期 (YYYY-MM-DD)，只取前 7 碼 (YYYY-MM)
            if extracted_date:
                year_month_val = extracted_date[:7]
            else:
                year_month_val = "KB-Article"
        
        full_text = f"# {main_title}\n\n" + raw_content
        
        # 使用 UnifiedTokenSplitter (含 tolerance)
        chunks_text = self.text_splitter.split_text(full_text)
        
        for chunk_content in chunks_text:
            chunk_obj = {
                "website": "MSRC Update Guide",
                "link": link,
                "heading_link": link,
                "year_month": year_month_val,  # 這裡現在是 YYYY-MM
                "main_title": main_title,
                "title": f"Details for KB{kb_id}",
                "content": chunk_content,
                "kb_id": kb_id
            }
            chunks.append(chunk_obj)
        return chunks

    def run(self):
        print(f"🚀 [MSRCGuideLocalCrawler] Starting Scraper (Local CSV Mode)...")
        all_final_dataset = []

        csv_path = self.csv_file_path
        if not os.path.exists(csv_path): 
            print(f"  🛑 CSV file not found at: {csv_path}")
            # 再做一次最後確認，印出絕對路徑幫助除錯
            print(f"  (Checking Absolute Path: {os.path.abspath(csv_path)})")
            return []

        print(f"  📖 Processing CSV: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            
            # 檢查基本欄位
            required_cols = ['Article', 'Article (Link)']
            if not all(col in df.columns for col in required_cols):
                print(f"  🛑 Missing columns. Expected {required_cols}. Found: {df.columns.tolist()}")
                return []
            
            # 🔥 [修改部分] 欄位處理
            cols_to_keep = ['Article', 'Article (Link)']
            if 'Release Date' in df.columns:
                cols_to_keep.append('Release Date')
            
            df_filtered = df[cols_to_keep].copy()
            df_filtered['Article'] = df_filtered['Article'].astype(str).str.strip()
            df_filtered['Article (Link)'] = df_filtered['Article (Link)'].astype(str).str.strip()
            
            # 處理 Release Date：轉為標準 YYYY-MM-DD 字串
            if 'Release Date' in df_filtered.columns:
                df_filtered['Release Date'] = pd.to_datetime(
                    df_filtered['Release Date'], errors='coerce'
                ).dt.strftime('%Y-%m-%d')
                # 將 NaT (空值) 轉為 None
                df_filtered['Release Date'] = df_filtered['Release Date'].replace({float('nan'): None})

            # 篩選純數字 KB ID
            df_filtered = df_filtered[df_filtered['Article'].str.match(r'^\d+$')].drop_duplicates()
            
            if df_filtered.empty: 
                print("  ⚠️ No valid articles found in CSV after filtering.")
                return []

        except Exception as e:
            print(f"  🛑 CSV Error: {e}")
            return []

        print(f"  🕷️ Starting crawl for {len(df_filtered)} articles...")
        
        total = len(df_filtered)
        count = 0

        for index, row in df_filtered.iterrows():
            count += 1
            kb_id = row['Article']
            link = row['Article (Link)']
            
            # 🔥 [修改部分] 取得日期
            release_date = row.get('Release Date')

            if not link.startswith("http"): link = urljoin(self.base_url, link)

            print(f"  Processing [{count}/{total}]: KB{kb_id} ...")

            max_retries = 5
            retry_count = 0
            success = False
            base_wait_time = 30

            while retry_count <= max_retries and not success:
                content_data = self._fetch_and_parse_article(link)

                if content_data in ["403_FORBIDDEN", "BLOCKED_CONTENT", "CONNECTION_ERROR"]:
                    retry_count += 1
                    wait_time = base_wait_time * retry_count
                    print(f"    ⛔ Blocked/Error ({content_data})! Sleeping for {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if content_data == "404_NOT_FOUND":
                    print("    ⚠️ Page not found (404). Skipping.")
                    success = True 
                    break

                if content_data and isinstance(content_data, dict):
                    # 🔥 [修改部分] 傳入 csv_date
                    chunks = self._create_chunks(kb_id, link, content_data, csv_date=release_date)
                    print(f"    ✅ Success | {len(chunks)} chunks")
                    all_final_dataset.extend(chunks)
                    success = True
                else:
                    print("    ⚠️ Content Empty. Retrying...")
                    retry_count += 1
                    time.sleep(5)

            sleep_time = random.uniform(10, 20)
            print(f"    ☕ Resting ({sleep_time:.1f}s)...")
            time.sleep(sleep_time)

            if count % 3 == 0:
                print(f"    🛑 [Deep Cooling] Batch of 3 done. Sleeping 120s...")
                time.sleep(120)

        print(f"✅ Execution Complete. Total Chunks: {len(all_final_dataset)}")
        return all_final_dataset

if __name__ == "__main__":
    # 測試區：當直接執行此腳本時 (非透過 Scheduler)
    # 不傳參數，測試自動路徑抓取功能
    crawler = MSRCGuideLocalCsvCrawler()
    data = crawler.run()
    
    if data:
        df_result = pd.DataFrame(data)
        output_file = f"crawled_results_{int(time.time())}.csv"
        df_result.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"結果已儲存至: {output_file}")