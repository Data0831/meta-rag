import time
import re
import os
import sys
import json
import random
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from markdownify import markdownify as md_converter
from datetime import datetime, timedelta

# ==========================================
# 0. 路徑與模組設定
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 嘗試匯入 UnifiedTokenSplitter
try:
    from core.shared_splitter import UnifiedTokenSplitter
except ImportError:
    print("❌ [Error] 無法匯入 UnifiedTokenSplitter，請確認路徑。")
    UnifiedTokenSplitter = None

from playwright.sync_api import sync_playwright
from curl_cffi import requests

try:
    from .base import BaseCrawler
except ImportError:
    BaseCrawler = object

class MSRCGuideCsvCrawler(BaseCrawler):
    """
    MSRC Update Guide 爬蟲 (針對使用者 HTML 修正版)
    """

    def __init__(self):
        self.base_url = "https://msrc.microsoft.com"
        self.guide_url = "https://msrc.microsoft.com/update-guide/"
        
        self.download_dir = os.path.join(current_dir, "downloads")
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
        if UnifiedTokenSplitter:
            print("  🔧 Initializing UnifiedTokenSplitter...")
            self.text_splitter = UnifiedTokenSplitter(
                model_name="gpt-4o",
                chunk_size=self.target_chunk_size,
                overlap=self.overlap_size,
                tolerance=200
            )
        else:
            raise ImportError("UnifiedTokenSplitter is missing.")

    def _apply_stealth(self, page):
        """Playwright 隱身術"""
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page.add_init_script("window.chrome = {runtime: {}};")
        page.add_init_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});")
        page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});")

    def _create_single_shot_session(self):
        """建立 curl_cffi Session"""
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

    def _download_latest_csv_by_date(self, days=7):
        """
        下載 CSV：根據使用者截圖修正 (解決日曆擋住 Ok 按鈕的問題)
        """
        print(f"  📥 [Phase 1] Navigating to MSRC to download CSV (Last {days} days)...")
        csv_path = None
        
        # 計算日期 (格式調整為 Jan 08, 2026 以符合網頁)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime("%b %d, %Y")
        end_str = end_date.strftime("%b %d, %Y")
        
        print(f"    📅 Target Range: {start_str} to {end_str}")

        with sync_playwright() as p:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(
                accept_downloads=True, 
                viewport={'width': 1920, 'height': 1200}, 
                locale='en-US' 
            )
            page = context.new_page()
            self._apply_stealth(page)

            try:
                page.goto(self.guide_url, wait_until="networkidle", timeout=60000)
                time.sleep(5) 

                # 1. 開啟日期選單
                try:
                    # 使用 Icon 過濾定位日期按鈕
                    date_picker_btn = page.locator("[data-automationid='splitbuttonprimary']").filter(
                        has=page.locator("[data-icon-name='Calendar']")
                    ).first
                    
                    if date_picker_btn.is_visible():
                        date_picker_btn.click()
                        time.sleep(1.5)

                        # 2. 定位輸入框 (根據您的 HTML 資訊，Placeholder 是一樣的)
                        date_inputs = page.get_by_placeholder("Select a date...")
                        
                        if date_inputs.count() >= 2:
                            # --- 設定 Start Date (第 1 個) ---
                            start_input = date_inputs.nth(0)
                            start_input.click()
                            start_input.fill(start_str)
                            print(f"    ⌨️ Input Start Date: {start_str}")
                            
                            # --- 設定 End Date (第 2 個) ---
                            end_input = date_inputs.nth(1)
                            end_input.click()
                            end_input.fill(end_str)
                            print(f"    ⌨️ Input End Date: {end_str}")
                            
                            # 按下 Enter 觸發日期確認
                            page.keyboard.press("Enter")
                            time.sleep(0.5)

                            # ==================================================
                            # 🔥 [關鍵修正] 關閉日曆彈窗，避免擋住 Ok 按鈕
                            # ==================================================
                            print("    🛡️ Attempting to close calendar popup...")
                            # 方法 A: 按 Esc
                            page.keyboard.press("Escape")
                            time.sleep(0.5)
                            
                            # 方法 B: 點擊上方標題文字 (Select date range) 強制失焦
                            # 這是最保險的做法，點擊空白處或標題
                            try:
                                page.get_by_text("Select date range", exact=True).first.click(force=True)
                            except:
                                # 如果找不到標題，點擊輸入框旁白的空白處 (body)
                                page.mouse.click(0, 0)
                            
                            time.sleep(1) # 等待日曆縮回去

                        else:
                            print("    ⚠️ Could not find date inputs.")

                        # 3. 點擊 OK (現在應該不會被擋住了)
                        ok_btn = page.get_by_role("button", name="Ok")
                        
                        if ok_btn.is_visible():
                            ok_btn.click()
                            print("    👉 Clicked 'Ok'")
                        else:
                            # 如果還是點不到，嘗試用 JS 強制點擊
                            print("    ⚠️ 'Ok' button not visible, trying force click...")
                            page.evaluate("document.querySelector('button[name=\"Ok\"]').click()")
                            
                        print("    ⏳ Waiting 5s for table refresh...")
                        time.sleep(5)
                    else:
                        print("    ⚠️ Date Picker button not found.")
                except Exception as e:
                    print(f"    ⚠️ Date setting failed: {e}")
                    # 截圖以便後續除錯
                    page.screenshot(path=os.path.join(self.download_dir, "error_date_click.png"))

                # 4. 觸發匯出 (Download CSV)
                export_btn = page.locator("button[aria-label='Download']").first
                if not export_btn.is_visible(): export_btn = page.get_by_text("Download").first
                
                if export_btn.is_visible():
                    export_btn.click()
                    time.sleep(2)
                    
                    try:
                        # 選擇 CSV 格式
                        csv_option = page.get_by_text("csv - Comma Separated Value", exact=False).first
                        if csv_option.is_visible(): csv_option.click()
                        
                        # 定位 Start 按鈕 (匯出確認視窗)
                        start_btn = page.get_by_role("button", name="Start").first
                        if not start_btn.is_visible(): start_btn = page.get_by_text("Start", exact=True).first
                        
                        if start_btn.is_visible():
                            # 檢查是否有資料 (按鈕是否 Disabled)
                            if start_btn.is_disabled():
                                print("    🛑 [Result] No data in range. 'Start' button is disabled.")
                                return None
                            
                            # 下載檔案
                            with page.expect_download(timeout=60000) as download_info:
                                start_btn.click()
                            
                            download = download_info.value
                            filename = f"msrc_kb_{int(time.time())}.csv"
                            save_path = os.path.join(self.download_dir, filename)
                            download.save_as(save_path)
                            print(f"    ✅ CSV Downloaded: {save_path}")
                            csv_path = save_path
                        else:
                            print("    ❌ 'Start' button not found.")
                    except Exception as e:
                        print(f"    ❌ Download interaction failed: {e}")
                else:
                    print("    ❌ Download (Export) button not found.")

            except Exception as e:
                print(f"  🛑 Browser Automation failed: {e}")
            finally:
                browser.close()
        return csv_path

    def _fetch_and_parse_article(self, url):
        """抓取並解析單篇文章"""
        session = None
        try:
            session = self._create_single_shot_session()
            response = session.get(url, timeout=30)
            
            if response.status_code == 403: return "403_FORBIDDEN"
            if response.status_code == 404: return "404_NOT_FOUND"
            if response.status_code != 200: return None

            html_content = response.text
            if "Access Denied" in html_content: return "BLOCKED_CONTENT"

            soup = BeautifulSoup(html_content, 'html.parser')
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            title = title.split(" - Microsoft")[0]

            content_div = soup.find('div', id='main') or soup.find('main') or soup.find('article')
            
            if content_div:
                for tag in content_div.select("script, style, nav, footer, button"): tag.extract()
                for a_tag in content_div.find_all('a', href=True):
                    if a_tag['href'].startswith('/'):
                        a_tag['href'] = urljoin(self.base_url, a_tag['href'])

                markdown_content = md_converter(str(content_div), heading_style="ATX")
                markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
                return {"title": title, "content": markdown_content}
            
            return None
        except Exception as e:
            return "CONNECTION_ERROR"
        finally:
            if session: session.close()

    def _extract_date(self, text):
        if not text: return None
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
        if match:
            y, m, d = match.groups()
            return f"{y}-{int(m):02d}-{int(d):02d}"
        return None

    def _create_chunks(self, kb_id, link, content_data):
        chunks = []
        raw_content = content_data['content']
        page_title = content_data['title']
        main_title = f"KB{kb_id}: {page_title}"
        
        extracted_date = self._extract_date(page_title)
        if not extracted_date:
            extracted_date = self._extract_date(raw_content[:500])
        year_month_val = extracted_date if extracted_date else "KB-Article"
        
        full_text = f"# {main_title}\n\n" + raw_content
        
        chunks_text = self.text_splitter.split_text(full_text)
        
        for chunk_content in chunks_text:
            chunk_obj = {
                "source": self.source_name,
                "link": link,
                "heading_link": link,
                "year_month": year_month_val,
                "main_title": main_title,
                "title": f"Details for KB{kb_id}",
                "content": chunk_content,
                "kb_id": kb_id
            }
            chunks.append(chunk_obj)
        return chunks

    def run(self):
        print(f"🚀 [MSRCGuideCrawler] Starting Scraper (Incremental Mode)...")
        
        # ==========================================
        # 🔥 [需求 3] 載入歷史資料 (State Rehydration)
        # ==========================================
        history_file_path = os.path.join(parent_dir, "data", f"{self.source_name}.json")
        history_data = []
        
        if os.path.exists(history_file_path):
            print(f"  📂 Loading history from: {history_file_path}")
            try:
                with open(history_file_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                print(f"  ✅ Loaded {len(history_data)} existing records.")
            except Exception as e:
                print(f"  ⚠️ Failed to load history: {e}")
        else:
            print("  🆕 No history file found. Treating as fresh run.")

        # 1. 下載最近 7 天的 CSV
        csv_path = self._download_latest_csv_by_date(days=7)
        
        # 若 Start 鍵失效 (None)，代表無資料，直接回傳舊資料
        if not csv_path:
            print("  💤 No new data found in the last 7 days. Returning history only.")
            return history_data

        # 2. 處理新資料
        new_chunks = []
        print(f"  📖 Processing CSV: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            if 'Article' in df.columns:
                df_filtered = df[df['Article'].astype(str).str.match(r'^\d+$')].drop_duplicates()
                print(f"  🕷️ Found {len(df_filtered)} new articles to crawl...")

                count = 0
                for index, row in df_filtered.iterrows():
                    count += 1
                    kb_id = str(row['Article']).strip()
                    link = row.get('Article (Link)', '')
                    if not link.startswith("http"): link = urljoin(self.base_url, link)
                    
                    print(f"  Processing [{count}/{len(df_filtered)}]: KB{kb_id} ...")
                    
                    # 執行重試邏輯
                    success = False
                    retry_count = 0
                    while retry_count < 3 and not success:
                        content_data = self._fetch_and_parse_article(link)
                        if content_data and isinstance(content_data, dict):
                            chunks = self._create_chunks(kb_id, link, content_data)
                            new_chunks.extend(chunks)
                            print(f"    ✅ Parsed {len(chunks)} chunks")
                            success = True
                        else:
                            retry_count += 1
                            time.sleep(2)

                    time.sleep(random.uniform(2, 5)) # 避免被擋
            else:
                print("  ⚠️ CSV format unexpected.")
        except Exception as e:
            print(f"  🛑 CSV Processing Error: {e}")

        # 3. 合併回傳
        print(f"  🔄 Merging: {len(history_data)} (History) + {len(new_chunks)} (New)")
        # 這裡簡單相加，重複的項目會在 Diff Engine 中被過濾掉 (因為 Hash ID 一樣)
        combined_dataset = history_data + new_chunks
        
        return combined_dataset

if __name__ == "__main__":
    crawler = MSRCGuideCsvCrawler()
    crawler.run()