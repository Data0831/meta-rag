"""
Test script for content_cleaner.py
Run this to verify URL cleaning before processing your actual data.
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ETL.content_cleaner import (
    clean_content_aggressive,
    clean_content_conservative,
    extract_markdown_links,
)


def test_url_cleaning():
    """Test various URL patterns found in Microsoft announcements."""

    test_cases = [
        {
            "name": "Markdown link with traditional Chinese",
            "input": "詳見 [Azure 定價頁面](https://azure.microsoft.com/pricing/) 了解更多資訊。",
            "expected_aggressive": "詳見 Azure 定價頁面 了解更多資訊。",
        },
        {
            "name": "Standalone HTTPS URL",
            "input": "請訪問 https://learn.microsoft.com/docs/azure 查看完整文檔。",
            "expected_aggressive": "請訪問 查看完整文檔。",
        },
        {
            "name": "Multiple links in one sentence",
            "input": "參考 [文檔A](https://link1.com) 和 [文檔B](https://link2.com) 獲取詳情。",
            "expected_aggressive": "參考 文檔A 和 文檔B 獲取詳情。",
        },
        {
            "name": "Mixed markdown and standalone URLs",
            "input": "[點擊這裡](https://example.com/path) 下載，或訪問 https://another.com/page",
            "expected_aggressive": "點擊這裡 下載，或訪問",
        },
        {
            "name": "www. style URLs",
            "input": "Microsoft 官網：www.microsoft.com 提供完整說明",
            "expected_aggressive": "Microsoft 官網： 提供完整說明",
        },
        {
            "name": "Content without URLs",
            "input": "這是一個沒有任何連結的純文本內容。",
            "expected_aggressive": "這是一個沒有任何連結的純文本內容。",
        },
    ]

    print("=" * 80)
    print("URL Cleaning Test Results")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test['name']}")
        print(f"原始內容：")
        print(f"  {test['input']}")

        aggressive_result = clean_content_aggressive(test['input'])
        conservative_result = clean_content_conservative(test['input'])

        print(f"\n清理結果 (Aggressive - 用於 Embedding):")
        print(f"  {aggressive_result}")

        print(f"\n清理結果 (Conservative - 保留標記):")
        print(f"  {conservative_result}")

        # Check if markdown links were extracted
        links = extract_markdown_links(test['input'])
        if links:
            print(f"\n提取的連結:")
            for anchor, url in links:
                print(f"  - 錨點文字: '{anchor}' → URL: {url}")

    print("\n" + "=" * 80)
    print("測試完成！")
    print("=" * 80)


def test_real_world_example():
    """Test with a realistic Microsoft announcement snippet."""

    real_content = """
Microsoft Sentinel 現在推出預購計畫（Committed tier），最高可省 73%！
詳情請參考 [定價頁面](https://azure.microsoft.com/pricing/details/microsoft-sentinel/)。

適用於：
- 所有 CSP 合作夥伴
- Direct Bill Partners

生效日期：2024 年 1 月 15 日

如需更多資訊，請訪問 https://learn.microsoft.com/sentinel/pricing
或聯繫您的 Microsoft 代表。完整文檔可在 www.microsoft.com/sentinel 查看。
"""

    print("\n" + "=" * 80)
    print("Real-World Example Test")
    print("=" * 80)
    print("\n原始內容:")
    print(real_content)

    cleaned = clean_content_aggressive(real_content)
    print("\n清理後 (用於搜索和 Embedding):")
    print(cleaned)

    print("\n" + "=" * 80)
    print(f"字數統計:")
    print(f"  原始: {len(real_content)} 字元")
    print(f"  清理後: {len(cleaned)} 字元")
    print(f"  減少: {len(real_content) - len(cleaned)} 字元 ({(1 - len(cleaned)/len(real_content))*100:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    # Run all tests
    test_url_cleaning()
    test_real_world_example()

    print("\n如果測試結果符合預期，您可以繼續處理實際資料。")
    print("\n使用方式:")
    print("1. 重新執行 ETL pipeline (dataPreprocessing.py)")
    print("2. 重新生成 embeddings (vectorPreprocessing.py)")
    print("3. 搜索時將使用清理後的 content_clean 欄位")
