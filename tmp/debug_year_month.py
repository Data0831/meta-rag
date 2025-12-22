"""
Debug script to check year_month filtering in Meilisearch
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.db_adapter_meili import MeiliAdapter
from src.config import MEILISEARCH_HOST, MEILISEARCH_API_KEY, MEILISEARCH_INDEX
import json

def main():
    print("=" * 80)
    print("Debugging year_month Filtering")
    print("=" * 80)

    # Initialize adapter
    adapter = MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
    )

    # 1. Get index stats
    print("\n[Index Stats]")
    stats = adapter.get_stats()
    print(f"  Total documents: {stats.get('numberOfDocuments', 0)}")

    # 2. Get all documents to see year_month values
    print("\n[Fetching all documents to check year_month values]")
    all_docs = adapter.index.search("", {"limit": 1000})

    year_months = set()
    for doc in all_docs['hits']:
        ym = doc.get('year_month')
        year_months.add(ym)

    print(f"  Found {len(year_months)} unique year_month values:")
    for ym in sorted(year_months):
        print(f"    - {ym}")

    # 3. Test different filter syntaxes
    test_cases = [
        # With backticks
        ("`year_month` IN ['2025-10', '2025-11', '2025-12']", "With backticks (current)"),
        # Without backticks
        ("year_month IN ['2025-10', '2025-11', '2025-12']", "Without backticks"),
        # Single value with backticks
        ("`year_month` = '2025-12'", "Single value with backticks"),
        # Single value without backticks
        ("year_month = '2025-12'", "Single value without backticks"),
    ]

    print("\n" + "=" * 80)
    print("[Testing Different Filter Syntaxes]")
    print("=" * 80)

    for filter_expr, description in test_cases:
        print(f"\n{description}:")
        print(f"  Filter: {filter_expr}")

        try:
            results = adapter.search(
                query="",
                filters=filter_expr,
                limit=5,
            )
            print(f"  ✅ Results found: {len(results)}")
            if results:
                print(f"     First result year_month: {results[0].get('year_month')}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("Debug completed")
    print("=" * 80)

if __name__ == "__main__":
    main()
