"""
測試 UnifiedTokenSplitter 切分效能與正確性
"""
import time
import sys
import os

# 添加專案路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.shared_splitter import UnifiedTokenSplitter


def generate_test_text(num_tokens: int = 50000) -> str:
    """生成測試用的長文本 (優化版)"""
    sample_paragraphs = [
        "這是一段測試文字，用於測試文本切分器的效能。\n",
        "The quick brown fox jumps over the lazy dog.\n",
        "人工智慧正在改變我們的生活方式，從日常消費到企業決策都有深遠影響。\n",
        "Machine learning algorithms can process large amounts of data efficiently.\n",
        "在這個數位時代，資料已成為最重要的資產之一。\n",
        "Natural language processing enables computers to understand human language.\n",
        "區塊鏈技術提供了一種去中心化的信任機制。\n",
        "Cloud computing has revolutionized how businesses deploy applications.\n\n",
    ]
    
    # 先計算一個 block 的 token 數，減少 count_tokens 呼叫次數
    splitter = UnifiedTokenSplitter()
    one_block = "".join(sample_paragraphs)
    tokens_per_block = splitter.count_tokens(one_block)
    
    # 計算需要多少個 block
    blocks_needed = (num_tokens // tokens_per_block) + 1
    
    # 一次性生成
    text = one_block * blocks_needed
    
    return text


def test_performance(text: str, chunk_size: int = 500, overlap: int = 100):
    """測試切分效能"""
    splitter = UnifiedTokenSplitter(
        chunk_size=chunk_size,
        overlap=overlap,
        debug=False
    )
    
    total_tokens = splitter.count_tokens(text)
    print(f"📊 測試文本: {len(text):,} 字元, {total_tokens:,} tokens")
    print(f"🔧 設定: chunk_size={chunk_size}, overlap={overlap}")
    print("-" * 50)
    
    # 計時
    start_time = time.perf_counter()
    chunks = splitter.split_text(text)
    end_time = time.perf_counter()
    
    elapsed = end_time - start_time
    
    print(f"✅ 切分完成!")
    print(f"   - 切分數量: {len(chunks)} 段")
    print(f"   - 耗時: {elapsed:.3f} 秒")
    print(f"   - 速度: {total_tokens / elapsed:,.0f} tokens/秒")
    
    return chunks, elapsed


def test_correctness(chunks: list, splitter: UnifiedTokenSplitter, chunk_size: int, tolerance: int):
    """驗證切分正確性"""
    print("\n📝 驗證切分結果...")
    
    all_valid = True
    for i, chunk in enumerate(chunks):
        token_count = splitter.count_tokens(chunk)
        
        # 檢查是否超過上限 (chunk_size + tolerance)
        max_allowed = chunk_size + tolerance
        if token_count > max_allowed:
            print(f"   ❌ Chunk {i+1}: {token_count} tokens > {max_allowed} (超過上限!)")
            all_valid = False
        
        # 檢查開頭是否為換行後開始（除了第一段）
        if i > 0:
            # 前一段結尾應該是換行
            prev_ends_with_newline = chunks[i-1].rstrip() != chunks[i-1]
            
    if all_valid:
        print("   ✅ 所有 chunk 都在容許範圍內")
    
    # 統計 token 分佈
    token_counts = [splitter.count_tokens(c) for c in chunks]
    avg_tokens = sum(token_counts) / len(token_counts)
    min_tokens = min(token_counts)
    max_tokens = max(token_counts)
    
    print(f"\n📈 Token 分佈統計:")
    print(f"   - 平均: {avg_tokens:.1f} tokens")
    print(f"   - 最小: {min_tokens} tokens")
    print(f"   - 最大: {max_tokens} tokens")
    
    return all_valid


def test_newline_alignment(chunks: list):
    """檢查換行對齊情況"""
    print("\n🔍 檢查換行對齊...")
    
    ends_with_newline = 0
    starts_with_newline = 0
    
    for i, chunk in enumerate(chunks):
        # 檢查原始 chunk（未 strip）是否以換行結尾
        # 注意：因為 split_text 會 strip，所以這裡改成檢查是否看起來像完整行
        if chunk.endswith('.') or chunk.endswith('。') or chunk.endswith('\n'):
            ends_with_newline += 1
    
    print(f"   - 結尾看起來完整的段落: {ends_with_newline}/{len(chunks)}")


def main():
    print("=" * 60)
    print("🧪 UnifiedTokenSplitter 效能測試")
    print("=" * 60)
    
    # 測試不同規模
    test_cases = [
        (10000, 500, 100),   # 1萬 tokens
        (50000, 500, 100),   # 5萬 tokens
        (50000, 500, 150),   # 5萬 tokens, 更大 overlap
    ]
    
    for num_tokens, chunk_size, overlap in test_cases:
        print(f"\n{'='*60}")
        print(f"📦 測試案例: {num_tokens:,} tokens, chunk={chunk_size}, overlap={overlap}")
        print("=" * 60)
        
        # 生成測試文本 (計時)
        print("⏳ 生成測試文本...")
        gen_start = time.perf_counter()
        text = generate_test_text(num_tokens)
        gen_elapsed = time.perf_counter() - gen_start
        print(f"   ✅ 文本生成耗時: {gen_elapsed:.3f} 秒")
        
        # 效能測試
        splitter = UnifiedTokenSplitter(chunk_size=chunk_size, overlap=overlap)
        chunks, elapsed = test_performance(text, chunk_size, overlap)
        
        # 正確性驗證
        test_correctness(chunks, splitter, chunk_size, splitter.tolerance)
        
        # 換行對齊檢查
        test_newline_alignment(chunks)
        
        # 顯示前幾個 chunk 的開頭和結尾
        print(f"\n📄 Chunk 範例 (前 3 個):")
        for i, chunk in enumerate(chunks[:3]):
            first_line = chunk.split('\n')[0][:50]
            last_line = chunk.split('\n')[-1][-50:]
            print(f"   Chunk {i+1}:")
            print(f"      開頭: {first_line}...")
            print(f"      結尾: ...{last_line}")


if __name__ == "__main__":
    main()
