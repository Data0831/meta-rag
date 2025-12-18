"""
Test script for Phase 4 Hybrid Search Service
Tests Intent Parsing, Filters, and RRF Fusion
"""

# todo: limit 設定、keyword 加入 query
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.search_service import SearchService
import json


def test_search(query: str):
    """Test search with a given query"""
    print("\n" + "=" * 80)
    print(f"Testing Query: {query}")
    print("=" * 80)

    service = SearchService()

    try:
        # Use limit=5 as fallback if LLM doesn't specify
        results = service.search(query, limit=5)

        # Display intent with highlighting
        print("\n[Intent Parsed]")
        intent = results["intent"]
        print(json.dumps(intent, indent=2, ensure_ascii=False))

        # Highlight key search parameters
        print("\n" + "-" * 80)
        print("[Search Strategy]")
        print(f"  Keyword Query:  {intent.get('keyword_query', 'N/A')}")
        print(f"  Must Have Keywords: {intent.get('must_have_keywords', [])}")
        print(f"  Semantic Query: {intent.get('semantic_query', 'N/A')}")

        # Show semantic ratio with visual indicator
        semantic_ratio = intent.get("recommended_semantic_ratio", 0.5)
        keyword_weight = 1 - semantic_ratio
        print(f"\n  Semantic Ratio: {semantic_ratio:.2f}")
        print(
            f"    ├─ Keyword Weight:  {keyword_weight:.2f} {'█' * int(keyword_weight * 20)}"
        )
        print(
            f"    └─ Semantic Weight: {semantic_ratio:.2f} {'█' * int(semantic_ratio * 20)}"
        )

        # Show applied filters
        filters = intent["filters"]
        print(f"\n[Filters Applied]")
        if filters.get("year_month"):
            print(f"  Year_Month:  {filters['year_month']}")
        if not any(filters.values()):
            print(f"  (No filters)")
        if intent.get("limit"):
            print(f"\n[Result Limit] LLM specified: {intent['limit']}")
        else:
            print(f"\n[Result Limit] Using fallback: 5")

        # Display results
        print("\n" + "=" * 80)
        print(f"[Search Results] Found {len(results['results'])} documents")
        print("=" * 80)

        for idx, doc in enumerate(results["results"], 1):
            print(f"\n[{idx}] {doc.get('title', 'No Title')}")
            print(f"{'─' * 80}")
            print(f"  year_month:   {doc.get('year_month', 'N/A')}")
            print(f"  Workspace:    {doc.get('workspace', 'N/A')}")
            print(f"  Ranking Score: {doc.get('_rankingScore', 0):.4f}")

            # Display detailed score breakdown
            if "_rankingScoreDetails" in doc:
                details = doc["_rankingScoreDetails"]
                # print(f"\n  Score Breakdown:")
                # for key, value in details.items():
                #     if isinstance(value, dict):
                #         print(f"    {key}:")
                #         for sub_key, sub_value in value.items():
                #             print(f"      {sub_key}: {sub_value}")
                #     else:
                #         print(f"    {key}: {value}")

            print(f"\n  Link: {doc.get('link', 'N/A')}")

        return results

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run test cases"""
    print("\n" + "=" * 80)
    print("Hybrid Search Service - LLM Semantic Ratio Test Suite")
    print("=" * 80)

    # Test cases covering different semantic ratio scenarios
    test_queries = [
        # Keyword-heavy queries (expected ratio: 0.2-0.3)
        # "Azure OpenAI pricing",
        # "Copilot for Microsoft 365 更新",
        # Balanced queries (expected ratio: 0.4-0.5)
        # "三個月內「AI 雲合作夥伴計劃」相關公告",
        "2025 年 4 月份價格相關公告",
        # "「AI 雲合作夥伴計劃」相關公告",
        # "安全性最佳實踐",
        # # Semantic-heavy queries (expected ratio: 0.6-0.8)
        # "如何提升雲端安全",
        # "最近有什麼重要變更",
    ]

    for query in test_queries:
        test_search(query)

    print("\n" + "=" * 80)
    print("Test Suite Completed")
    print("=" * 80)


if __name__ == "__main__":
    # You can also test with a custom query
    if len(sys.argv) > 1:
        custom_query = " ".join(sys.argv[1:])
        test_search(custom_query)
    else:
        main()
