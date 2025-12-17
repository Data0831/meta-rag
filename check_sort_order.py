import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from services.search_service import SearchService


def main():
    service = SearchService()

    query = "三個月內「AI 雲合作夥伴計劃」相關公告"
    print(f"Searching for: '{query}'")

    # Search with limit 10
    response = service.search(query, limit=10, semantic_ratio=0.5)

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

        print(f"Result {i+1:2}: Score={score:.6f} | Type={match_type} | ID={res['id']}")

        if score > last_score:
            print(f"  ❌ ERROR: Order violation! {score:.6f} > {last_score:.6f}")
            is_sorted = False
        last_score = score

    if is_sorted:
        print("\n✅ Results are properly sorted by ranking score.")
    else:
        print("\n❌ Results are NOT sorted by ranking score.")


if __name__ == "__main__":
    main()
