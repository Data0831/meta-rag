import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from services.search_service import SearchService


def main():
    service = SearchService()

    query = "三個月內「AI 雲合作夥伴計劃」相關公告"
    print(f"Searching for: '{query}'\n")

    # Search with limit 7
    response = service.search(query, limit=7, semantic_ratio=0.5)

    # Display search intent and filters
    intent = response.get("intent", {})
    print("=" * 80)
    print("SEARCH INTENT & FILTERS")
    print("=" * 80)
    print(f"Keyword Query: {intent.get('keyword_query', 'N/A')}")
    print(f"Semantic Query: {intent.get('semantic_query', 'N/A')}")
    print(f"Semantic Ratio: {intent.get('recommended_semantic_ratio', 0.5):.2f}")
    print(f"Limit: {intent.get('limit', 7)}")

    filters = intent.get("filters", {})
    print(f"\nFilters:")
    print(f"  - Months: {filters.get('months', [])}")
    print(f"  - Category: {filters.get('category', 'None')}")
    print(f"  - Impact Level: {filters.get('impact_level', 'None')}")
    print("=" * 80)
    print()

    results = response["results"]
    print(f"Found {len(results)} results.\n")

    last_score = 1.1  # Scores are 0-1
    is_sorted = True

    for i, res in enumerate(results):
        score = res.get("_rankingScore", 0)
        details = res.get("_rankingScoreDetails", {})

        # Determine Type
        has_words = "words" in details
        has_vector = "vectorSort" in details or "semantic" in details

        match_type = "Unknown"
        if has_words and has_vector:
            match_type = "Hybrid  "
        elif has_words:
            match_type = "Keyword "
        elif has_vector:
            match_type = "Semantic"

        title = res.get("title", "No title")
        link = res.get("link", "No link")

        print(f"Result {i+1:2}: Score={score:.6f} | Type={match_type}")
        print(f"  Title: {title}")
        print(f"  Link: {link}")

        if score > last_score:
            print(f"  ❌ ERROR: Order violation! {score:.6f} > {last_score:.6f}")
            is_sorted = False
        last_score = score
        print()  # Add blank line for readability

    if is_sorted:
        print("\n✅ Results are properly sorted by ranking score.")
    else:
        print("\n❌ Results are NOT sorted by ranking score.")


if __name__ == "__main__":
    main()
