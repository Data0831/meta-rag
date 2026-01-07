"""
測試腳本：比較原版 split_text 與優化版 split_text_optimized 的效能和結果
"""

import time
from shared_splitter import UnifiedTokenSplitter


def generate_test_text(length: int = 5000) -> str:
    """生成測試文本（中英混合）"""
    chinese_text = """
    人工智慧（Artificial Intelligence, AI）是電腦科學的一個分支，致力於創建能夠執行通常需要人類智慧的任務的系統。
    這些任務包括視覺感知、語音識別、決策制定和語言翻譯等。近年來，深度學習技術的突破使得AI在許多領域取得了顯著進展。
    
    機器學習是AI的核心技術之一。它使電腦系統能夠從數據中學習並改進，而無需明確編程。
    監督學習、非監督學習和強化學習是三種主要的機器學習方法。每種方法都有其獨特的應用場景和優勢。
    
    自然語言處理（NLP）是AI的另一個重要領域，專注於使電腦能夠理解、解釋和生成人類語言。
    現代NLP系統使用大型語言模型（LLM），如GPT、BERT等，這些模型在大量文本數據上進行訓練。
    
    電腦視覺技術使機器能夠從圖像或視頻中獲取有意義的資訊。卷積神經網絡（CNN）在圖像識別任務中表現出色。
    物體檢測、圖像分割和人臉識別是電腦視覺的常見應用。這些技術已廣泛應用於自動駕駛、醫療診斷等領域。
    """

    english_text = """
    Artificial Intelligence has revolutionized many industries. Machine learning algorithms can now 
    process vast amounts of data and identify patterns that humans might miss. Deep learning, 
    a subset of machine learning, uses neural networks with multiple layers to learn hierarchical 
    representations of data.
    
    Natural Language Processing enables computers to understand and generate human language. 
    Large Language Models have shown remarkable capabilities in tasks such as translation, 
    summarization, and question answering. These models are trained on billions of parameters 
    and can generate human-like text.
    
    Computer Vision allows machines to interpret visual information from the world. Convolutional 
    Neural Networks have achieved superhuman performance in image classification tasks. Object 
    detection and semantic segmentation are crucial for applications like autonomous vehicles.
    """

    # 混合中英文並重複到指定長度
    mixed_text = (chinese_text + "\n\n" + english_text) * (
        length // (len(chinese_text) + len(english_text)) + 1
    )
    return mixed_text[:length]


def test_splitter_performance():
    """測試並比較兩種切分方法的效能"""
    print("=" * 80)
    print("🧪 文本切分器效能測試")
    print("=" * 80)

    # 創建測試文本（不同長度）
    test_cases = [
        ("短文本", 1000),
        ("中等文本", 5000),
        ("長文本", 20000),
    ]

    for name, length in test_cases:
        print(f"\n{'='*80}")
        print(f"📝 測試案例: {name} ({length} 字元)")
        print(f"{'='*80}")

        test_text = generate_test_text(length)

        # 測試原版
        splitter = UnifiedTokenSplitter(
            chunk_size=1500, overlap=300, tolerance=200, debug=False
        )

        start_time = time.time()
        chunks_original = splitter.split_text(test_text)
        time_original = time.time() - start_time

        print(f"\n📊 原版 split_text:")
        print(f"   ⏱️  執行時間: {time_original:.4f} 秒")
        print(f"   📦 切分段數: {len(chunks_original)}")
        if chunks_original:
            tokens_per_chunk = [splitter.count_tokens(c) for c in chunks_original]
            print(
                f"   📏 Token 數範圍: {min(tokens_per_chunk)} - {max(tokens_per_chunk)}"
            )
            print(
                f"   📈 平均 Token 數: {sum(tokens_per_chunk) / len(tokens_per_chunk):.1f}"
            )

        # 測試優化版
        start_time = time.time()
        chunks_optimized = splitter.split_text_optimized(test_text)
        time_optimized = time.time() - start_time

        print(f"\n📊 優化版 split_text_optimized:")
        print(f"   ⏱️  執行時間: {time_optimized:.4f} 秒")
        print(f"   📦 切分段數: {len(chunks_optimized)}")
        if chunks_optimized:
            tokens_per_chunk = [splitter.count_tokens(c) for c in chunks_optimized]
            print(
                f"   📏 Token 數範圍: {min(tokens_per_chunk)} - {max(tokens_per_chunk)}"
            )
            print(
                f"   📈 平均 Token 數: {sum(tokens_per_chunk) / len(tokens_per_chunk):.1f}"
            )

        # 效能提升
        speedup = time_original / time_optimized if time_optimized > 0 else 0
        print(f"\n🚀 效能提升: {speedup:.2f}x 倍速")
        print(
            f"   ⏱️  時間節省: {(time_original - time_optimized):.4f} 秒 ({(1 - time_optimized/time_original)*100:.1f}%)"
        )

        # 檢查結果一致性
        if len(chunks_original) == len(chunks_optimized):
            print(f"   ✅ 切分段數一致")
        else:
            print(
                f"   ⚠️  切分段數不同 (原版: {len(chunks_original)}, 優化版: {len(chunks_optimized)})"
            )


def test_edge_cases():
    """測試邊界情況"""
    print("\n" + "=" * 80)
    print("🧪 邊界情況測試")
    print("=" * 80)

    splitter = UnifiedTokenSplitter(chunk_size=100, overlap=20, debug=True)

    test_cases = [
        ("空文本", ""),
        ("純空白", "   \n\n  \t  "),
        ("超短文本", "Hello, World!"),
        ("無標點長文本", "a" * 1000),
        ("純標點", "。！？，；：、" * 50),
    ]

    for name, text in test_cases:
        print(f"\n📝 測試: {name}")
        print(f"   文本長度: {len(text)} 字元")

        try:
            chunks = splitter.split_text_optimized(text)
            print(f"   ✅ 成功切分為 {len(chunks)} 段")
        except Exception as e:
            print(f"   ❌ 錯誤: {e}")


if __name__ == "__main__":
    # 執行效能測試
    test_splitter_performance()

    # 執行邊界測試
    test_edge_cases()

    print("\n" + "=" * 80)
    print("✅ 測試完成")
    print("=" * 80)
