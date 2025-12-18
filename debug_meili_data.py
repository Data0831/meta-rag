import sys
from pathlib import Path
import json

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.db_adapter_meili import MeiliAdapter
from src.config import MEILISEARCH_HOST, MEILISEARCH_API_KEY, MEILISEARCH_INDEX

def inspect_data():
    adapter = MeiliAdapter(host=MEILISEARCH_HOST, api_key=MEILISEARCH_API_KEY, collection_name=MEILISEARCH_INDEX)
    
    print(f"Connected to index: {MEILISEARCH_INDEX}")
    
    # Get 1 document to check schema
    results = adapter.index.get_documents({'limit': 1})
    
    if results.results:
        doc = results.results[0]
        print("\n[Sample Document]")
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        
        # Check specific fields
        print(f"\nMonth format: '{doc.get('month')}'")
        print(f"Metadata keys: {list(doc.get('metadata', {}).keys())}")
    else:
        print("Index is empty!")

if __name__ == "__main__":
    inspect_data()
