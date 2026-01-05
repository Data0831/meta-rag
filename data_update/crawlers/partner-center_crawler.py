import requests
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse
import datetime
import time
import re
import copy
from sentence_transformers import SentenceTransformer, util
from langchain_text_splitters import MarkdownHeaderTextSplitter
# 引入父類別
try:
    from .base import BaseCrawler
except ImportError:
    # 測試用 Mock
    class BaseCrawler:
        def __init__(self):
            try:
                from core.shared_splitter import UnifiedTokenSplitter 
                self.token_splitter = UnifiedTokenSplitter()
            except: pass

class PartnerCenterCrawler(BaseCrawler):
    """
    Microsoft Partner Center 公告爬蟲 (Integrated Version)
    
    整合特性：
    1. 架構統一：繼承 BaseCrawler，使用 UnifiedTokenSplitter 進行切塊。
    2. V33 核心保留：保留 AI 語意定位 (sentence-transformers) 與 DOM 結構回溯。
    3. 欄位優化：新增 website 欄位，保留 workspace 動態抓取。
    """

    def __init__(self):
        # 🔥 [修改 1] 初始化父類別，取得 self.token_splitter
        super().__init__()

        # 1. 基礎設定
        self.base_url = "https://learn.microsoft.com/zh-tw/partner-center/announcements/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 🔥 [修改 2] 設定固定欄位 website
        self.website_name = "partner_center_announcements"
        
        # 2. V33 邏輯常數
        self.VALID_HEADERS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        
        # 3. 初始化 AI 模型
        print(f"🚀 [{self.source_name}] 初始化 AI 模型 (sentence-transformers)...")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # 4. 初始化結構切分工具 (Token 切分工具已由 BaseCrawler 提供)
        # 這裡只保留 MarkdownHeaderTextSplitter 用於第一層結構拆解
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")],
            strip_headers=False 
        )

    @property
    def source_name(self):
        return "partner_center_announcements"

    # =========================================================================
    # 日期解析邏輯
    # =========================================================================
    def _parse_smart_date(self, date_text, url):
        """嘗試解析日期，失敗則從 URL 提取，最後才用當前時間"""
        if date_text:
            text = date_text.strip()
            formats = [
                "%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y", "%Y 年 %m 月 %d 日"
            ]
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(text, fmt)
                    return dt.strftime("%Y-%m")
                except ValueError:
                    continue
        
        try:
            match = re.search(r'/(\d{4})-([a-zA-Z]+)', url)
            if match:
                year = match.group(1)
                month_str = match.group(2)
                try:
                    dt = datetime.datetime.strptime(f"{year}-{month_str}", "%Y-%B")
                    return dt.strftime("%Y-%m")
                except ValueError:
                    pass
        except Exception:
            pass

        return datetime.datetime.now().strftime("%Y-%m")

    # =========================================================================
    # V33 核心邏輯 (保持原樣 - DOM 處理, AI 比對, 回溯機制)
    # =========================================================================
    def _process_images_in_node(self, node, base_url):
        if not node: return node
        for a_tag in list(node.find_all('a')):
            img = a_tag.find('img')
            if img:
                src = a_tag.get('href') or img.get('src')
                alt = img.get('alt', '')
                if src:
                    abs_src = urljoin(base_url, src)
                    marker = f" ||IMG_START||![{alt}]({abs_src})||IMG_END|| "
                    a_tag.replace_with(marker)
        for img in list(node.find_all('img')):
            src = img.get('src')
            alt = img.get('alt', '')
            if src:
                abs_src = urljoin(base_url, src)
                marker = f" ||IMG_START||![{alt}]({abs_src})||IMG_END|| "
                img.replace_with(marker)
        return node

    def _process_links_in_node(self, node, base_url):
        if not node: return node
        all_links = list(node.find_all('a'))
        for a_tag in all_links:
            href = a_tag.get('href')
            text = a_tag.get_text(separator=" ", strip=True)
            if href and text:
                abs_url = urljoin(base_url, href)
                link_markdown = f" [{text}]({abs_url}) "
                a_tag.replace_with(link_markdown)
        return node

    def _get_smart_text(self, node):
        if not node: return ""
        temp_node = copy.copy(node)
        for br in temp_node.find_all('br'):
            br.replace_with("||LINE_BREAK||")
        
        text = temp_node.get_text(separator=" ", strip=True)
        text = text.replace("||LINE_BREAK||", "\n")
        text = text.replace("||IMG_START||", "\n\n")
        text = text.replace("||IMG_END||", "\n\n")
        
        lines = []
        for line in text.split('\n'):
            clean_line = re.sub(r'\s+', ' ', line).strip()
            if clean_line: lines.append(clean_line)
        return "\n".join(lines)

    def _extract_rich_content(self, node, base_url):
        if not node: return ""
        processed = copy.copy(node)
        processed = self._process_images_in_node(processed, base_url)
        processed = self._process_links_in_node(processed, base_url)
        return self._get_smart_text(processed)

    def _process_table_to_markdown(self, table_node, base_url):
        trs = table_node.find_all('tr')
        if not trs: return ""
        markdown_lines = []
        headers = []
        first_row = trs[0]
        cols = first_row.find_all(['th', 'td'])
        
        for col in cols:
            text = self._extract_rich_content(col, base_url).replace('\n', '<br>')
            headers.append(text)
        if not headers: return ""

        markdown_lines.append("| " + " | ".join(headers) + " |")
        markdown_lines.append("| " + " | ".join(['---'] * len(headers)) + " |")

        for tr in trs[1:]:
            cells = []
            tds = tr.find_all(['td', 'th'])
            for i in range(len(headers)):
                if i < len(tds):
                    text = self._extract_rich_content(tds[i], base_url).replace('\n', '<br>')
                    cells.append(text)
                else:
                    cells.append("")
            markdown_lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(markdown_lines)

    def _format_node_to_markdown(self, node, base_url):
        if not node: return ""
        if isinstance(node, NavigableString):
            text = str(node).strip()
            return text if text else ""

        if node.name in self.VALID_HEADERS:
            level = int(node.name[1])
            text = node.get_text(strip=True)
            return f"\n{'#' * level} {text}"
        
        elif node.name in ['ul', 'ol']:
            list_items = []
            for li in node.find_all('li', recursive=False):
                item_text = self._extract_rich_content(li, base_url)
                list_items.append(f"- {item_text}")
            return "\n".join(list_items)

        elif node.name == 'table':
            return "\n" + self._process_table_to_markdown(node, base_url) + "\n"
        
        elif node.name == 'img':
            src = node.get('src')
            alt = node.get('alt', '')
            if src:
                abs_src = urljoin(base_url, src)
                return f"\n![{alt}]({abs_src})\n"
            return ""

        else:
            block_tags = ['p', 'div', 'ul', 'ol', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'section', 'article']
            has_block_children = False
            for child in node.children:
                if child.name in block_tags:
                    has_block_children = True
                    break
            
            if has_block_children:
                results = []
                for child in node.children:
                    res = self._format_node_to_markdown(child, base_url)
                    if res and res.strip():
                        results.append(res)
                return "\n\n".join(results)
            else:
                return self._extract_rich_content(node, base_url)

    def _get_real_start_after_marker(self, marker_node):
        if not marker_node: return None
        curr = marker_node.next_sibling
        while curr:
            if curr.name and curr.name != 'hr': return curr
            if isinstance(curr, NavigableString) and str(curr).strip(): return curr
            curr = curr.next_sibling
        return None

    def _backtrack_to_main_header(self, start_node):
        current = start_node
        original_start = start_node
        max_steps = 100 
        for _ in range(max_steps):
            prev = current.previous_sibling
            if prev is None: return current
            if prev.name == 'hr': 
                real_start = self._get_real_start_after_marker(prev)
                return real_start if real_start else original_start 
            current = prev
        return original_start

    def _get_content_semantic(self, url, target_title):
        try:
            time.sleep(1)
            parsed_url_obj = urlparse(url)
            base_url_no_fragment = f"{parsed_url_obj.scheme}://{parsed_url_obj.netloc}{parsed_url_obj.path}"
            fragment_id = parsed_url_obj.fragment
            
            response = requests.get(base_url_no_fragment, headers=self.headers)
            if response.status_code != 200: return None

            try:
                html = response.content.decode('utf-8')
            except:
                html = response.content.decode('big5', errors='ignore')

            soup = BeautifulSoup(html, "html.parser")
            main_content = soup.find("main") or soup.find("div", class_="content")
            if not main_content: return None

            found_node = None
            
            if fragment_id:
                anchor = main_content.find(id=fragment_id) or main_content.find("a", attrs={"name": fragment_id})
                if anchor:
                    if anchor.name in self.VALID_HEADERS:
                        found_node = anchor
                    else:
                        curr = anchor
                        for _ in range(15):
                            if curr is None: break
                            curr = curr.next_sibling
                            if curr and curr.name in self.VALID_HEADERS:
                                found_node = curr
                                break

            if not found_node:
                candidates = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                candidate_texts = [c.get_text(strip=True) for c in candidates]
                
                if candidate_texts:
                    target_embedding = self.embedding_model.encode(target_title, convert_to_tensor=True)
                    candidate_embeddings = self.embedding_model.encode(candidate_texts, convert_to_tensor=True)
                    
                    cosine_scores = util.cos_sim(target_embedding, candidate_embeddings)[0]
                    best_score_idx = cosine_scores.argmax().item()
                    best_score = cosine_scores[best_score_idx].item()
                    
                    if best_score > 0.4:
                        found_node = candidates[best_score_idx]

            if not found_node: return None

            start_header = self._backtrack_to_main_header(found_node)

            text_parts = []
            text_parts.append(self._format_node_to_markdown(start_header, base_url_no_fragment))
            
            current_node = start_header
            for sibling in current_node.next_siblings:
                if sibling is None: continue
                if sibling.name == 'hr': break
                if sibling.name is None:
                    txt = str(sibling).strip()
                    if txt: text_parts.append(txt)
                    continue
                if sibling.name == 'nav' or 'page-action-bar' in sibling.get('class', []): continue
                
                formatted_text = self._format_node_to_markdown(sibling, base_url_no_fragment)
                if formatted_text and formatted_text.strip():
                    text_parts.append(formatted_text)

            return "\n\n".join(text_parts)

        except Exception as e:
            print(f"❌ [{self.source_name}] Error in semantic fetch: {e}")
            return None

    # =========================================================================
    # 切塊邏輯 (整合 BaseCrawler 工具)
    # =========================================================================
    def _resolve_nearest_title(self, metadata, main_title):
        if "H3" in metadata: return metadata["H3"]
        if "H2" in metadata: return metadata["H2"]
        if "H1" in metadata: return metadata["H1"]
        return main_title

    def _split_markdown_into_chunks(self, full_markdown, main_title, date_str, link, workspace):
        final_chunks = []
        year_month = self._parse_smart_date(date_str, link)

        # 確保有 H1 大標題 (使用 main_title)
        if not full_markdown.strip().startswith("#"):
            full_markdown = f"# {main_title}\n\n{full_markdown}"

        # 1. 結構化切分 (LangChain)
        semantic_docs = self.markdown_splitter.split_text(full_markdown)
        
        for doc in semantic_docs:
            chunk_content = doc.page_content.strip()
            metadata = doc.metadata 
            
            if not chunk_content or set(chunk_content) <= {'#', ' ', '\n', '\t'}:
                continue
            
            # 🔥 [修改 3] 使用 BaseCrawler 提供的 token_splitter 進行長度控制
            # split_text 內部會自動判斷長度並遞迴切分
            sub_chunks = self.token_splitter.split_text(chunk_content)
            
            # 解析最近的標題 (Title)
            chunk_title = self._resolve_nearest_title(metadata, main_title)

            for sub_chunk in sub_chunks:
                if not sub_chunk.strip(): continue

                chunk_obj = {
                    "website": self.website_name,   # 🔥 [修改 4] 固定 website
                    "workspace": workspace,         # 🔥 [修改 5] 保留動態 workspace (Referrals, General...)
                    "link": link,
                    "heading_link": link,
                    "year_month": year_month,
                    "main_title": main_title,       # 🔥 [修改 6] 文章大標題
                    "title": chunk_title,           # 🔥 [修改 7] 章節小標題
                    "content": sub_chunk
                }
                final_chunks.append(chunk_obj)
        return final_chunks

    # =========================================================================
    # 執行入口
    # =========================================================================
    def run(self):
        print(f"🚀 [{self.source_name}] 啟動爬蟲 (V33 Integrated)...")
        all_final_dataset = []

        try:
            response = requests.get(self.base_url, headers=self.headers)
            try:
                html_text = response.content.decode('utf-8')
            except:
                html_text = response.content.decode('big5', errors='ignore')
                
            soup = BeautifulSoup(html_text, "html.parser")
            main_content = soup.find("main")
            tables = main_content.find_all("table") if main_content else []
            
            total_processed = 0

            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) == 3:
                        # 從表格提取 workspace 與 main_title
                        workspace = cells[0].get_text(strip=True)
                        link_cell = cells[1]
                        main_title = link_cell.get_text(strip=True)
                        a_tag = link_cell.find("a")
                        date_text = cells[2].get_text(strip=True)

                        if a_tag and a_tag.get("href"):
                            full_url = urljoin(self.base_url, a_tag.get("href"))
                            print(f"  [{total_processed + 1}] 解析: [{workspace}] {main_title}")
                            
                            # 使用 AI 語意定位抓取內文
                            markdown_content = self._get_content_semantic(full_url, main_title)
                            
                            if markdown_content:
                                # 傳入 main_title 與 workspace 進行封裝
                                chunks = self._split_markdown_into_chunks(
                                    markdown_content, 
                                    main_title, 
                                    date_text, 
                                    full_url, 
                                    workspace
                                )
                                print(f"    -> 產生 {len(chunks)} 個切塊 (Date: {chunks[0]['year_month']})")
                                all_final_dataset.extend(chunks)
                                total_processed += 1
                            else:
                                print("    ⚠️ 抓取失敗或無內容")
                            
                            time.sleep(1)

        except Exception as e:
            print(f"❌ [{self.source_name}] 發生錯誤: {e}")

        print(f"✅ [{self.source_name}] 完成。總切塊數: {len(all_final_dataset)}")
        return all_final_dataset