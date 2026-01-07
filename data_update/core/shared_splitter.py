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
        """
        統一的文本切分方法

        :param text: 要切分的文本
        :return: 切分後的文本片段列表
        """
        if not text or not text.strip():
            return []

        total_tokens = self.count_tokens(text)

        if self.debug:
            print(f"📊 文本總長度: {len(text)} 字元, {total_tokens} tokens")
            print(f"🔧 表格感知模式: {'啟用' if self.table_aware else '停用'}")

        # 緩衝檢查：如果總長度在 (目標 + 寬容值) 內，直接回傳
        if total_tokens <= (self.chunk_size + self.tolerance):
            if self.debug:
                print(f"✅ 文本長度在容許範圍內，不需切分")
            return [text.strip()]

        chunks = []
        char_start_idx = 0
        text_len = len(text)

        while char_start_idx < text_len:
            # 1. 估算當前片段的結束字元位置
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

            # 2. 定位「硬性上限」切割點 (根據 chunk_size)
            hard_limit_ids = remaining_tokens_ids[: self.chunk_size]
            hard_limit_text = self.enc.decode(hard_limit_ids)
            hard_limit_char_len = len(hard_limit_text)
            current_end_boundary = char_start_idx + hard_limit_char_len

            # 3. 智慧尋找切割點（標點符號）
            # 搜尋範圍動態調整為 chunk_size 的 1/4，最小為 chunk_size 的 1/20，但不超過實際文本長度的一半
            search_range = min(
                max(self.chunk_size // 20, self.chunk_size // 4),
                hard_limit_char_len // 2,
            )
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
                best_split_point = self._adjust_split_for_table(
                    text, char_start_idx, best_split_point, text_len
                )

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

    def _adjust_split_for_table(
        self, text: str, start_idx: int, split_point: int, text_len: int
    ) -> int:
        """
        調整切分點以避免在表格中間切斷

        :param text: 完整文本
        :param start_idx: 當前段落起始位置
        :param split_point: 建議的切分點
        :param text_len: 文本總長度
        :return: 調整後的切分點
        """
        # 檢查切分點附近是否有表格
        context_before = text[max(0, split_point - 200) : split_point]
        context_after = text[split_point : min(text_len, split_point + 200)]

        # 檢查切分點前後是否有表格行
        lines_before = context_before.split("\n")
        lines_after = context_after.split("\n")

        in_table = False
        if lines_before and self._is_table_row(lines_before[-1]):
            in_table = True
        if lines_after and self._is_table_row(lines_after[0]):
            in_table = True

        if not in_table:
            return split_point

        if self.debug:
            print(f"⚠️  偵測到表格，調整切分點...")

        # 向後找到表格結束
        table_end = split_point
        for i in range(split_point, min(text_len, split_point + 500)):
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
        adjusted_chunk = text[start_idx:table_end]
        adjusted_tokens = self.count_tokens(adjusted_chunk)

        if adjusted_tokens <= (self.chunk_size + self.tolerance):
            if self.debug:
                print(f"   ✅ 調整到表格結束 (tokens: {adjusted_tokens})")
            return table_end
        else:
            # 如果調整後太大，向前找表格開始
            table_start = start_idx
            for i in range(split_point - 1, start_idx, -1):
                if text[i] == "\n":
                    prev_line_end = i
                    prev_line_start = text.rfind("\n", start_idx, prev_line_end) + 1
                    prev_line = text[prev_line_start:prev_line_end]

                    if not self._is_table_row(prev_line):
                        table_start = prev_line_end + 1
                        break

            if self.debug:
                print(f"   ⚠️  表格太大，調整到表格開始")
            return table_start

    def split_text_optimized(self, text: str) -> List[str]:
        """
        優化版切分邏輯（向後兼容別名）

        注意：此方法現在直接調用 split_text，不再有獨立實現。
        原本的「優化」（基於 token 索引）已整合到主方法中。
        """
        return self.split_text(text)

    def split_text_table_aware(self, text: str) -> List[str]:
        """
        表格感知切分（向後兼容別名）

        注意：此方法現在直接調用 split_text 並啟用表格感知模式。
        """
        return self.split_text(text)
