import tiktoken
from typing import List

class UnifiedTokenSplitter:
    def __init__(self, model_name: str = "gpt-4o", chunk_size: int = 1500, overlap: int = 300, tolerance: int = 200):
        """
        初始化參數：
        :param chunk_size: 目標切塊大小 (例如 1500)
        :param overlap: 重疊大小 (例如 300)
        :param tolerance: 🔥 [新增] 容許溢出的緩衝區 (例如 200)
                          如果剩餘 token 數 < chunk_size + tolerance，就不再切分。
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tolerance = tolerance  # 新增容許值
        
        try:
            self.enc = tiktoken.encoding_for_model(model_name)
        except:
            self.enc = tiktoken.get_encoding("cl100k_base")

        self.separators = ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", ";", "，", ","]

    def count_tokens(self, text: str) -> int:
        if not text: return 0
        return len(self.enc.encode(text))

    def split_text(self, text: str) -> List[str]:
        # 🔥 [修改 1] 頂層判斷：如果總長度在 (1500 + 200) 以內，直接回傳
        if self.count_tokens(text) <= (self.chunk_size + self.tolerance):
            return [text]

        chunks = []
        self._recursive_split(text, chunks)
        return chunks

    def _recursive_split(self, text: str, chunks: List[str]):
        # 🔥 [修改 2] 遞迴終止條件：包含容許值
        # 假設剩餘文字是 1600 tokens，因為 <= 1700，所以這裡就會停止遞迴，直接保留
        if self.count_tokens(text) <= (self.chunk_size + self.tolerance):
            if text.strip():
                chunks.append(text)
            return

        # --- 以下邏輯保持不變，負責處理真的太長的情況 ---
        
        token_integers = self.enc.encode(text)
        limit_tokens = token_integers[:self.chunk_size] # 這裡依然用 1500 來定位切點
        hard_limit_char_index = len(self.enc.decode(limit_tokens))

        best_split_index = -1
        for sep in self.separators:
            found_idx = text.rfind(sep, 0, hard_limit_char_index)
            if found_idx != -1:
                best_split_index = found_idx + len(sep)
                break
        
        if best_split_index == -1:
            best_split_index = hard_limit_char_index

        current_chunk = text[:best_split_index]
        chunks.append(current_chunk)

        overlap_token_count = min(self.overlap, len(limit_tokens))
        tokens_before_split = self.enc.encode(current_chunk)
        overlap_tokens_ids = tokens_before_split[-overlap_token_count:]
        overlap_char_len = len(self.enc.decode(overlap_tokens_ids))
        
        next_start_index = max(0, best_split_index - overlap_char_len)

        if next_start_index >= len(text) - 10: return 
        if next_start_index <= 0 and len(chunks) > 0: next_start_index = best_split_index 

        remaining_text = text[next_start_index:]
        self._recursive_split(remaining_text, chunks)