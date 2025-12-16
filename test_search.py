"""
Test script for Phase 4 Hybrid Search Service
Tests Intent Parsing, Filters, and RRF Fusion
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.search_service import SearchService
import json


def test_search(query: str):
    """Test search with a given query"""
    print("\n" + "=" * 80)
    print(f"Testing Query: {query}")
    print("=" * 80)

    service = SearchService()

    try:
        results = service.search(query, limit=5)

        # Display intent
        print("\n[Intent Parsed]")
        print(json.dumps(results["intent"], indent=2, ensure_ascii=False))

        # Show applied filters
        filters = results["intent"]["filters"]
        if filters.get("months"):
            print(f"\n[Months Filter] {filters['months']}")
        if results["intent"].get("boost_keywords"):
            print(f"[Boost Keywords] {results['intent']['boost_keywords']}")

        # Display results
        print(f"\n[Results] Found {len(results['results'])} documents")
        for idx, doc in enumerate(results["results"], 1):
            print(f"\n{idx}. {doc.get('title', 'No Title')}")
            print(f"   id: {doc['id']}")
            print(f"   Month: {doc.get('month', 'N/A')}")
            print(f"   Category: {doc.get('category', 'N/A')}")
            print(f"   RRF Score: {doc.get('rrf_score', 0):.4f}")
            if "snippet" in doc:
                print(f"   Snippet: {doc['snippet'][:100]}...")

        return results

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run test cases"""
    print("\n" + "=" * 80)
    print("Phase 4 Hybrid Search Service - Test Suite")
    print("=" * 80)

    # Test cases
    test_queries = [
        "Show me security announcements",
        "三個月內「AI 雲合作夥伴計劃」相關公告",
        "Azure OpenAI pricing",
        "過去兩個月的高影響力安全公告",
        "2025年10月的 Copilot 更新",
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
