import tiktoken
from typing import List, Optional
from config.config import TokenConfig


class UnifiedTokenSplitter:
    def __init__(
        self,
        model_name: str = TokenConfig.MODEL_NAME,
        chunk_size: int = TokenConfig.CHUNK_SIZE,
        overlap: int = TokenConfig.OVERLAP,
        tolerance: int = TokenConfig.TOLERANCE,
        debug: bool = False,
    ):
        """
        高效能精準切分器：預先 tokenize + 換行優先切分。

        參數說明：
        :param model_name: 使用的模型名稱（用於選擇對應的 tokenizer）
        :param chunk_size: [目標大小] 每一段期望的 Token 數量限制。
        :param overlap: [重複區間] 相鄰兩段之間「重疊」的部分。
                        💡 下一段會從前一段結尾 ~overlap 範圍內的換行處開始。
        :param tolerance: [寬容緩衝] 如果最後一段只剩下一點點（Token 數 < chunk_size + tolerance），
                          就直接合併，不再切分，避免出現極短片段。
        :param debug: 是否啟用調試模式（輸出詳細日誌）
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tolerance = tolerance
        self.debug = debug

        # 改進異常處理：只捕獲特定異常
        try:
            self.enc = tiktoken.encoding_for_model(model_name)
        except (KeyError, ValueError) as e:
            if self.debug:
                print(
                    f"⚠️ 無法載入模型 {model_name} 的 tokenizer，使用預設 cl100k_base: {e}"
                )
            self.enc = tiktoken.get_encoding("cl100k_base")

        # 標點優先級：換行 > 句末標點 > 分號/冒號 > 逗號/頓號
        self.separators = [
            "\n\n",
            "\n",
            "\r\n",  # Windows 換行
            "。",
            "！",
            "？",
            "!",
            "?",
            "；",
            ";",
            "：",  # 中文冒號
            ":",  # 英文冒號
            "，",
            ",",
            "、",  # 中文頓號
        ]

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.enc.encode(text))

    def split_text(self, text: str) -> List[str]:
        """
        高效能文本切分：預先 tokenize + 換行優先切分。
        
        ⚡ 效能優化：
        - 預先 tokenize 一次 → O(n) 而非 O(n × chunks)
        
        💡 切分策略：
        - chunk 結尾盡量切在換行符
        - 下一個 chunk 的起點在「前一段結尾 ~ overlap 範圍內」的換行處
        - 找不到換行時才使用標點，再找不到才硬切

        :param text: 要切分的文本
        :return: 切分後的文本片段列表
        """
        if not text or not text.strip():
            return []

        # 一次性 tokenize 整個文本
        all_tokens = self.enc.encode(text)
        total_tokens = len(all_tokens)

        if self.debug:
            print(f"📊 文本總長度: {len(text)} 字元, {total_tokens} tokens")

        # 緩衝檢查：如果總長度在 (目標 + 寬容值) 內，直接回傳
        if total_tokens <= (self.chunk_size + self.tolerance):
            if self.debug:
                print(f"✅ 文本長度在容許範圍內，不需切分")
            return [text.strip()]

        chunks = []
        token_start = 0

        while token_start < total_tokens:
            remaining = total_tokens - token_start

            # 如果剩餘 tokens 不多，直接全包
            if remaining <= (self.chunk_size + self.tolerance):
                chunk_tokens = all_tokens[token_start:]
                chunk_text = self.enc.decode(chunk_tokens).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                    if self.debug:
                        print(f"✅ 最後一段 (tokens: {remaining}): {chunk_text[:50]}...")
                break

            # 取得硬性上限範圍的 tokens (chunk_size)
            token_end = min(token_start + self.chunk_size, total_tokens)
            chunk_tokens = all_tokens[token_start:token_end]
            chunk_text = self.enc.decode(chunk_tokens)

            # === 智慧尋找切割點（優先換行） ===
            # 在 chunk 尾端搜尋最佳切分位置
            search_char_range = min(len(chunk_text) // 4, 300)  # 搜尋範圍：最後 1/4 或 300 字元
            search_start_char = max(0, len(chunk_text) - search_char_range)
            snippet = chunk_text[search_start_char:]

            best_offset = len(chunk_text)  # 預設使用完整 chunk
            for sep in self.separators:
                found_idx = snippet.rfind(sep)
                if found_idx != -1:
                    best_offset = search_start_char + found_idx + len(sep)
                    break

            # 取得最終的 chunk 文本
            final_chunk_text = chunk_text[:best_offset].strip()
            if not final_chunk_text:
                # 如果 strip 後為空，使用完整 chunk
                final_chunk_text = chunk_text.strip()
                best_offset = len(chunk_text)

            if final_chunk_text:
                chunks.append(final_chunk_text)
                if self.debug:
                    chunk_token_count = len(self.enc.encode(final_chunk_text))
                    print(f"📝 Chunk {len(chunks)} (tokens: {chunk_token_count}): {final_chunk_text[:50]}...")

            # === 計算下一段的起始 token 位置（換行優先 overlap）===
            # 策略：在 chunk 結尾 ~ overlap 範圍內找換行，從那裡開始下一段
            
            # 計算這個 chunk 實際使用的 token 數
            final_chunk_tokens = self.enc.encode(final_chunk_text)
            actual_chunk_token_count = len(final_chunk_tokens)
            
            # overlap 區域
            overlap_token_count = min(self.overlap, actual_chunk_token_count)
            
            if overlap_token_count > 0:
                # 取得 overlap 區域的文字
                overlap_tokens = final_chunk_tokens[-overlap_token_count:]
                overlap_text = self.enc.decode(overlap_tokens)
                
                # 在 overlap 區域內找換行（從前往後找，這樣 overlap 會更大）
                newline_pos = overlap_text.find('\n')
                if newline_pos != -1:
                    # 找到換行，從換行後開始
                    # 計算換行前的 tokens 數
                    text_before_newline = overlap_text[:newline_pos + 1]
                    tokens_before_newline = len(self.enc.encode(text_before_newline))
                    # 下一段從 overlap 開始位置 + 換行前的 tokens 開始
                    skip_tokens = actual_chunk_token_count - overlap_token_count + tokens_before_newline
                    token_start = token_start + skip_tokens
                else:
                    # 沒找到換行，使用標準 overlap
                    token_start = token_start + actual_chunk_token_count - overlap_token_count
            else:
                token_start = token_start + actual_chunk_token_count

            # 安全檢查：確保有前進
            if token_start >= total_tokens:
                break
            # 防止無限循環
            if actual_chunk_token_count == 0:
                token_start += 1

        if self.debug:
            print(f"✅ 切分完成，共 {len(chunks)} 段")

        return chunks