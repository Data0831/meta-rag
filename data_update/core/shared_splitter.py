import tiktoken
from typing import List, Optional


class UnifiedTokenSplitter:
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        chunk_size: int = 1500,
        overlap: int = 300,
        tolerance: int = 200,
        debug: bool = False,
        table_aware: bool = True,
    ):
        """
        混合版精準切分器：結合 Token 計數與智慧標點識別。

        參數說明：
        :param model_name: 使用的模型名稱（用於選擇對應的 tokenizer）
        :param chunk_size: [目標大小] 每一段期望的 Token 數量限制。
        :param overlap: [重複區間] 相鄰兩段之間「重疊」的部分。
                        💡 解釋：這不是 150/2 分在前後，而是「下一段的前 X 個字」會包含「前一段最後的 X 個字」。
                        較大的 overlap (如 300) 能讓 RAG 在檢索到片段時，保留更多上下文連貫性。
        :param tolerance: [寬容緩衝] 如果最後一段只剩下一點點（Token 數 < chunk_size + tolerance），
                          就直接合併，不再切分，避免出現極短片段。
        :param debug: 是否啟用調試模式（輸出詳細日誌）
        :param table_aware: 是否啟用表格感知模式（避免在表格 row 中間切斷）
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tolerance = tolerance
        self.debug = debug
        self.table_aware = table_aware

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
        # 擴展中文標點符號支援
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

    def _is_table_row(self, line: str) -> bool:
        """檢查是否為 Markdown 表格行"""
        stripped = line.strip()
        return (
            stripped.startswith("|")
            and stripped.endswith("|")
            and stripped.count("|") >= 2
        )

    def _find_table_boundary(
        self, text: str, start_pos: int, direction: str = "backward"
    ) -> int:
        """
        尋找表格邊界

        :param text: 完整文本
        :param start_pos: 起始位置
        :param direction: 'backward' 向前找表格開始，'forward' 向後找表格結束
        :return: 表格邊界位置
        """
        lines = (
            text[:start_pos].split("\n")
            if direction == "backward"
            else text[start_pos:].split("\n")
        )

        if direction == "backward":
            # 向前找：找到第一個非表格行
            for i in range(len(lines) - 1, -1, -1):
                if not self._is_table_row(lines[i]):
                    # 返回這個非表格行之後的位置
                    boundary = sum(len(lines[j]) + 1 for j in range(i + 1))  # +1 for \n
                    return boundary
            return 0  # 整個都是表格
        else:
            # 向後找：找到第一個非表格行
            for i, line in enumerate(lines):
                if not self._is_table_row(line):
                    # 返回這個非表格行之前的位置
                    boundary = start_pos + sum(len(lines[j]) + 1 for j in range(i))
                    return boundary
            return len(text)  # 整個都是表格

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.enc.encode(text))

    def split_text(self, text: str) -> List[str]:
        """主切分邏輯：改為迭代式，處理長文更穩定"""
        total_tokens = self.count_tokens(text)

        # 緩衝檢查：如果總長度在 (目標 + 寬容值) 內，直接回傳
        if total_tokens <= (self.chunk_size + self.tolerance):
            return [text.strip()] if text.strip() else []

        chunks = []
        start_char_idx = 0
        text_len = len(text)

        while start_char_idx < text_len:
            # 1. 估算當前片段的結束字元位置
            remaining_text = text[start_char_idx:]
            remaining_tokens_ids = self.enc.encode(remaining_text)

            # 如果剩下不長了，直接全包
            if len(remaining_tokens_ids) <= (self.chunk_size + self.tolerance):
                chunks.append(remaining_text.strip())
                break

            # 2. 定位「硬性上限」切割點 (根據 chunk_size)
            hard_limit_ids = remaining_tokens_ids[: self.chunk_size]
            hard_limit_char_len = len(self.enc.decode(hard_limit_ids))
            current_end_boundary = start_char_idx + hard_limit_char_len

            # 3. 智慧尋找「切割點」：在結尾附近找標點符號，讓切割更自然
            search_range = 150
            search_start = max(start_char_idx, current_end_boundary - search_range)
            snippet = text[search_start:current_end_boundary]

            best_split_point = current_end_boundary
            for sep in self.separators:
                found_idx = snippet.rfind(sep)
                if found_idx != -1:
                    best_split_point = search_start + found_idx + len(sep)
                    break

            current_chunk = text[start_char_idx:best_split_point].strip()
            if current_chunk:
                chunks.append(current_chunk)

            # 4. 計算「下一段」的起始點 (處理 Overlap)
            tokens_in_chunk = self.enc.encode(text[start_char_idx:best_split_point])
            overlap_token_count = min(self.overlap, len(tokens_in_chunk))
            overlap_ids = tokens_in_chunk[-overlap_token_count:]
            overlap_char_len = len(self.enc.decode(overlap_ids))

            theoretical_next_start = best_split_point - overlap_char_len

            # --- 智慧起始點尋找 (Smart Start) ---
            s_min = max(start_char_idx + 1, theoretical_next_start - 50)
            s_max = min(best_split_point - 1, theoretical_next_start + 50)

            best_next_start = theoretical_next_start
            if s_max > s_min:
                start_snippet = text[s_min:s_max]
                for sep in self.separators:
                    found_idx = start_snippet.find(sep)
                    if found_idx != -1:
                        best_next_start = s_min + found_idx + len(sep)
                        break

            # 防呆：避免原地踏步（增強版安全檢查）
            if best_next_start <= start_char_idx:
                # 確保至少前進一些距離，避免無限循環
                start_char_idx = max(best_split_point, start_char_idx + 1)
            else:
                start_char_idx = best_next_start

            # 額外安全檢查：如果下一個起始點超過文本長度，直接結束
            if start_char_idx >= text_len:
                break

        return chunks

    def split_text_optimized(self, text: str) -> List[str]:
        """
        優化版切分邏輯：使用快取機制減少重複編碼

        主要改進：
        1. 一次性編碼整個文本並快取
        2. 建立 token-char 映射表提高精度
        3. 減少重複的編碼/解碼操作
        4. 更安全的邊界檢查
        """
        if not text or not text.strip():
            return []

        # 一次性編碼整個文本（快取）
        all_token_ids = self.enc.encode(text)
        total_tokens = len(all_token_ids)

        if self.debug:
            print(f"📊 文本總長度: {len(text)} 字元, {total_tokens} tokens")

        # 緩衝檢查：如果總長度在 (目標 + 寬容值) 內，直接回傳
        if total_tokens <= (self.chunk_size + self.tolerance):
            if self.debug:
                print(f"✅ 文本長度在容許範圍內，不需切分")
            return [text.strip()]

        chunks = []
        token_start_idx = 0

        while token_start_idx < total_tokens:
            # 1. 計算當前 chunk 的 token 範圍
            token_end_idx = min(token_start_idx + self.chunk_size, total_tokens)

            # 如果剩餘 tokens 不多，直接全包
            remaining_tokens = total_tokens - token_start_idx
            if remaining_tokens <= (self.chunk_size + self.tolerance):
                chunk_token_ids = all_token_ids[token_start_idx:]
                chunk_text = self.enc.decode(chunk_token_ids).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                    if self.debug:
                        print(
                            f"✅ 最後一段 (tokens: {len(chunk_token_ids)}): {chunk_text[:50]}..."
                        )
                break

            # 2. 解碼當前 chunk
            chunk_token_ids = all_token_ids[token_start_idx:token_end_idx]
            chunk_text = self.enc.decode(chunk_token_ids)

            # 3. 智慧尋找切割點（在 chunk 末尾附近找標點）
            search_range = min(150, len(chunk_text) // 2)  # 動態調整搜尋範圍
            search_start = max(0, len(chunk_text) - search_range)
            snippet = chunk_text[search_start:]

            best_split_offset = len(chunk_text)  # 預設：整段
            for sep in self.separators:
                found_idx = snippet.rfind(sep)
                if found_idx != -1:
                    best_split_offset = search_start + found_idx + len(sep)
                    break

            # 切割文本
            final_chunk = chunk_text[:best_split_offset].strip()
            if final_chunk:
                chunks.append(final_chunk)
                if self.debug:
                    actual_tokens = self.count_tokens(final_chunk)
                    print(
                        f"📝 Chunk {len(chunks)} (tokens: {actual_tokens}): {final_chunk[:50]}..."
                    )

            # 4. 計算下一段的起始點（處理 overlap）
            # 重新編碼切割後的文本以獲得精確的 token 數
            final_chunk_tokens = self.enc.encode(final_chunk)
            overlap_token_count = min(self.overlap, len(final_chunk_tokens))

            # 記錄當前位置用於安全檢查
            prev_token_start = token_start_idx

            # 下一段從「當前段 - overlap」開始
            token_start_idx = (
                token_start_idx + len(final_chunk_tokens) - overlap_token_count
            )

            # 安全檢查：確保有前進
            if token_start_idx <= prev_token_start:
                token_start_idx = token_end_idx
                if self.debug:
                    print(f"⚠️ 偵測到可能的無限循環，強制前進")

        if self.debug:
            print(f"✅ 切分完成，共 {len(chunks)} 段")

        return chunks

    def split_text_table_aware(self, text: str) -> List[str]:
        """
        表格感知切分：確保不會在表格 row 中間切斷

        策略：
        1. 使用優化版切分邏輯
        2. 在切分點檢查是否位於表格內
        3. 如果在表格內，調整到表格邊界
        4. 保留表格標題和分隔線
        """
        if not text or not text.strip():
            return []

        # 一次性編碼整個文本（快取）
        all_token_ids = self.enc.encode(text)
        total_tokens = len(all_token_ids)

        if self.debug:
            print(f"📊 文本總長度: {len(text)} 字元, {total_tokens} tokens")

        # 緩衝檢查：如果總長度在 (目標 + 寬容值) 內，直接回傳
        if total_tokens <= (self.chunk_size + self.tolerance):
            if self.debug:
                print(f"✅ 文本長度在容許範圍內，不需切分")
            return [text.strip()]

        chunks = []
        char_start_idx = 0
        text_len = len(text)

        # 用於儲存表格標題和分隔線（如果需要重複使用）
        table_header_cache = {}

        while char_start_idx < text_len:
            # 1. 估算當前 chunk 的字元範圍（基於 token 數）
            remaining_text = text[char_start_idx:]
            remaining_tokens_ids = self.enc.encode(remaining_text)

            # 如果剩餘 tokens 不多，直接全包
            remaining_tokens = len(remaining_tokens_ids)
            if remaining_tokens <= (self.chunk_size + self.tolerance):
                chunk_text = remaining_text.strip()
                if chunk_text:
                    chunks.append(chunk_text)
                    if self.debug:
                        print(
                            f"✅ 最後一段 (tokens: {remaining_tokens}): {chunk_text[:50]}..."
                        )
                break

            # 2. 定位「硬性上限」切割點
            hard_limit_ids = remaining_tokens_ids[: self.chunk_size]
            hard_limit_text = self.enc.decode(hard_limit_ids)
            hard_limit_char_len = len(hard_limit_text)
            current_end_boundary = char_start_idx + hard_limit_char_len

            # 3. 智慧尋找切割點（標點符號）
            search_range = min(150, hard_limit_char_len // 2)
            search_start = max(char_start_idx, current_end_boundary - search_range)
            snippet = text[search_start:current_end_boundary]

            best_split_point = current_end_boundary
            for sep in self.separators:
                found_idx = snippet.rfind(sep)
                if found_idx != -1:
                    best_split_point = search_start + found_idx + len(sep)
                    break

            # 4. 表格感知調整
            if self.table_aware:
                # 檢查切分點附近是否有表格
                context_before = text[max(0, best_split_point - 200) : best_split_point]
                context_after = text[
                    best_split_point : min(text_len, best_split_point + 200)
                ]

                # 檢查切分點前後是否有表格行
                lines_before = context_before.split("\n")
                lines_after = context_after.split("\n")

                in_table = False
                if lines_before and self._is_table_row(lines_before[-1]):
                    in_table = True
                if lines_after and self._is_table_row(lines_after[0]):
                    in_table = True

                if in_table:
                    if self.debug:
                        print(f"⚠️  偵測到表格，調整切分點...")

                    # 向後找到表格結束
                    table_end = best_split_point
                    for i in range(
                        best_split_point, min(text_len, best_split_point + 500)
                    ):
                        if text[i] == "\n":
                            next_line_start = i + 1
                            next_line_end = text.find("\n", next_line_start)
                            if next_line_end == -1:
                                next_line_end = text_len
                            next_line = text[next_line_start:next_line_end]

                            if not self._is_table_row(next_line):
                                table_end = i + 1  # 在表格後的換行符之後切分
                                break

                    # 檢查調整後的大小是否可接受
                    adjusted_chunk = text[char_start_idx:table_end]
                    adjusted_tokens = self.count_tokens(adjusted_chunk)

                    if adjusted_tokens <= (self.chunk_size + self.tolerance):
                        best_split_point = table_end
                        if self.debug:
                            print(f"   ✅ 調整到表格結束 (tokens: {adjusted_tokens})")
                    else:
                        # 如果調整後太大，向前找表格開始
                        table_start = char_start_idx
                        for i in range(best_split_point - 1, char_start_idx, -1):
                            if text[i] == "\n":
                                prev_line_end = i
                                prev_line_start = (
                                    text.rfind("\n", char_start_idx, prev_line_end) + 1
                                )
                                prev_line = text[prev_line_start:prev_line_end]

                                if not self._is_table_row(prev_line):
                                    table_start = prev_line_end + 1
                                    break

                        best_split_point = table_start
                        if self.debug:
                            print(f"   ⚠️  表格太大，調整到表格開始")

            # 5. 提取當前 chunk
            current_chunk = text[char_start_idx:best_split_point].strip()
            if current_chunk:
                chunks.append(current_chunk)
                if self.debug:
                    actual_tokens = self.count_tokens(current_chunk)
                    print(
                        f"📝 Chunk {len(chunks)} (tokens: {actual_tokens}): {current_chunk[:50]}..."
                    )

            # 6. 計算下一段的起始點（處理 overlap）
            chunk_tokens = self.enc.encode(current_chunk)
            overlap_token_count = min(self.overlap, len(chunk_tokens))

            if overlap_token_count > 0:
                overlap_ids = chunk_tokens[-overlap_token_count:]
                overlap_text = self.enc.decode(overlap_ids)
                overlap_char_len = len(overlap_text)
                char_start_idx = best_split_point - overlap_char_len
            else:
                char_start_idx = best_split_point

            # 安全檢查：確保有前進
            if char_start_idx >= text_len:
                break

        if self.debug:
            print(f"✅ 切分完成，共 {len(chunks)} 段")

        return chunks
