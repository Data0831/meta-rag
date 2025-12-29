import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from src.services.search_service import SearchService
from src.tool.ANSI import print_red
import json

DEFAULT_LIMIT = 5
SEMANTIC_RATIO = 1.0
ENABLE_LLM_SEARCH = True
FORCE_MANUAL_RATIO = False
# SIMILAR_THRESHOLD is a mock threshold for UI display, not for actual filtering.
SIMILAR_THRESHOLD = 0.81
ENABLE_RERANK = True


def test_search(query: str):
    print("\n" + "=" * 80)
    print(f"Testing Query: {query}")
    print("=" * 80 + "\n")
    service = SearchService()
    try:
        results = service.search(
            query,
            limit=DEFAULT_LIMIT,
            semantic_ratio=SEMANTIC_RATIO,
            enable_llm=ENABLE_LLM_SEARCH,
            manual_semantic_ratio=FORCE_MANUAL_RATIO,
            enable_rerank=ENABLE_RERANK,
            fall_back=False,
        )
        status = results.get("status")
        if status == "failed":
            print_red("\n[SEARCH FAILED]", bold=True)
            print_red(f"  Error: {results.get('error', 'Unknown error')}")
            print_red(f"  Stage: {results.get('stage', 'Unknown stage')}")
            return results
        print("\n[Intent Parsed]")
        intent = results["intent"]
        print(
            json.dumps(
                {"intent": intent, "status": status}, indent=2, ensure_ascii=False
            )
        )
        final_ratio = results.get("final_semantic_ratio", SEMANTIC_RATIO)
        keyword_weight = 1 - final_ratio
        print(f"  Final Semantic Ratio: {final_ratio:.2f}")
        print(f"    ├─ Keyword Weight:  {keyword_weight:.2f}")
        print(f"    └─ Semantic Weight: {final_ratio:.2f}")
        filters = intent.get("filters", {})
        print(f"\n[Result Limit] Used: {DEFAULT_LIMIT}")
        print("\n" + "=" * 80)
        print(f"[Search Results] Found {len(results['results'])} documents")
        for idx, doc in enumerate(results["results"], 1):
            score = doc.get("_rankingScore", 0)
            rerank_score = doc.get("_rerank_score", 0)
            score_pass = score >= SIMILAR_THRESHOLD
            has_keyword = doc.get("has_keyword", "N/A")
            print(f"\n[{idx}] {doc.get('title', 'No Title')}")
            print(f"{'─' * 80}")
            print(f"  score_pass:       {str(score_pass).lower()}")
            print(f"  has_keyword:   {has_keyword}")
            print(f"  year_month:    {doc.get('year_month', 'N/A')}")
            print(f"  Ranking Score: {score:.4f}")
            print(f"  Rerank Score:  {rerank_score:.4f}")
            print(f"  Link: {doc.get('link', 'N/A')}")
            print(f"  heading_Link: {doc.get('heading_link', 'N/A')}")
        return results
    except Exception as e:
        print_red(f"\n[ERROR] {type(e).__name__}: {e}", bold=True)
        import traceback

        traceback.print_exc()
        return None


def main():
    test_queries = [
        # "2025 年 4 月份價格相關公告",
        # "與競爭對手 gemini 相關資，"，
        # "windows 11 相關公告"
        "windows 11 server 漏洞"
    ]
    for query in test_queries:
        test_search(query)
    print("\n" + "=" * 80)
    print("Test Suite Completed")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        custom_query = " ".join(sys.argv[1:])
        test_search(custom_query)
    else:
        main()
