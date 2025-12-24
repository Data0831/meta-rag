
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.services.search_service import SearchService

def test_search():
    try:
        service = SearchService(show_init_messages=True)
        query = "2025 年 4 月份價格相關公告"
        print(f"\nTesting search with query: '{query}'")
        
        # Enable LLM to test the fix
        results = service.search(query, enable_llm=True)
        
        print("\nSearch completed successfully!")
        print(f"Intent: {results.get('intent')}")
        print(f"Number of results: {len(results.get('results', []))}")
        
        if 'llm_error' in results:
            print(f"LLM Error (if any): {results['llm_error']}")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search()
