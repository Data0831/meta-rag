import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from src.services.search_service import SearchService
from src.tool.ANSI import print_red
from src.config import (
    DEFAULT_SEARCH_LIMIT as DEFAULT_LIMIT,
    DEFAULT_SEMANTIC_RATIO as SEMANTIC_RATIO,
    DEFAULT_SIMILARITY_THRESHOLD as SIMILAR_THRESHOLD,
    ENABLE_LLM,
    MANUAL_SEMANTIC_RATIO,
    ENABLE_KEYWORD_WEIGHT_RERANK,
)
import json


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
            enable_llm=ENABLE_LLM,
            manual_semantic_ratio=MANUAL_SEMANTIC_RATIO,
            enable_rerank=ENABLE_KEYWORD_WEIGHT_RERANK,
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

        # Print Traces
        traces = results.get("traces", [])
        print("\n[Search Traces (Agentic Thinking)]")
        if traces:
            for t in traces:
                print(f"  ➤ {t}")
        else:
            print("  (No traces available)")

        filters = results.get(
            "meili_filter"
        )  # Intent object doesn't have meili_filter field directly often

        print(f"\n[Result Limit] Used: {DEFAULT_LIMIT}")
        print("\n" + "=" * 80)
        print(f"[Search Results] Found {len(results['results'])} documents")
        for idx, doc in enumerate(results["results"], 1):
            score = doc.get("_rankingScore", 0)
            rerank_score = doc.get("_rerank_score", 0)
            score_pass = score >= SIMILAR_THRESHOLD
            has_keyword = doc.get("has_keyword", "N/A")
            print(f"\n[{idx}] {doc.get('title', 'No Title')}")
            print(f"\n[main_title] {doc.get('main_title', 'No Title')}")
            print(f"{'─' * 80}")
            print(f"  score_pass:    {str(score_pass).lower()}")
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
        # "與競爭對手 gemini 相關資料"
        # "windows 11 相關公告"
        # "windows 11 server 漏洞"
        # "powerbi 近三個月更新"
        # "powerbi 近期更新"
        # "與 Gemini 相關資"
        # "123"
        "KB12453115"
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
