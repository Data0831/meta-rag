import sys
import json
import requests


from src.tool.ANSI import print_red

# Configuration
API_URL = "http://localhost:5000/api/search"
DEFAULT_LIMIT = 5
SEMANTIC_RATIO = 0.5
ENABLE_LLM = True
MANUAL_SEMANTIC_RATIO = False
ENABLE_KEYWORD_WEIGHT_RERANK = True


def test_api_search(query: str):
    print("\n" + "=" * 80)
    print(f"Testing API Search (Streaming): {query}")
    print("=" * 80 + "\n")

    payload = {
        "query": query,
        "limit": DEFAULT_LIMIT,
        "semantic_ratio": SEMANTIC_RATIO,
        "enable_llm": ENABLE_LLM,
        "manual_semantic_ratio": MANUAL_SEMANTIC_RATIO,
        "enable_keyword_weight_rerank": ENABLE_KEYWORD_WEIGHT_RERANK,
    }

    try:
        print(f"Sending POST request to {API_URL}...")
        with requests.post(API_URL, json=payload, stream=True) as response:
            if response.status_code != 200:
                print_red(f"Error: Server returned status code {response.status_code}")
                try:
                    print_red(f"Response: {response.json()}")
                except:
                    print_red(f"Response text: {response.text}")
                return

            print("Connected. Receiving stream...\n")

            final_summary = ""
            final_results = []

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    try:
                        step = json.loads(decoded_line)
                        stage = step.get("stage", "")
                        message = step.get("message", "")

                        if message:
                            print(f"[{stage.upper()}] {message}")

                        if stage == "complete":
                            final_summary = step.get("summary", "")
                            final_results = step.get("results", [])

                    except json.JSONDecodeError:
                        print(f"Received raw line: {decoded_line}")

        # Print Final Results similar to original test script
        print("\n" + "=" * 80)
        print("[Final Summary]")
        print(final_summary)
        print("\n" + "=" * 80)
        print(f"[Final Results Count] {len(final_results)}")

        if final_results:
            print("\n" + "=" * 80)
            print(f"[Search Results] Found {len(final_results)} documents")
            for idx, doc in enumerate(final_results, 1):
                score = doc.get("_rankingScore", 0)
                rerank_score = doc.get("_rerank_score", 0)
                # score_pass logic is server-side now, but we can assume logic matches if we care,
                # or just print what we get.
                has_keyword = doc.get("has_keyword", "N/A")

                print(f"\n[{idx}] {doc.get('title', 'No Title')}")
                print(f"\n[main_title] {doc.get('main_title', 'No Title')}")
                print(f"{'─' * 80}")
                # Note: score_pass is not explicitly returned in the document dictionary usually unless added by service.
                # We'll omit calculating it locally to avoid desync, or just check 'score' if needed.
                print(f"  has_keyword:   {has_keyword}")
                print(f"  year_month:    {doc.get('year_month', 'N/A')}")
                print(f"  Ranking Score: {score:.4f}")
                print(f"  Rerank Score:  {rerank_score:.4f}")
                print(f"  Link: {doc.get('link', 'N/A')}")
                print(f"  heading_Link: {doc.get('heading_link', 'N/A')}")
        else:
            print("\n[Search Results] No documents found.")

        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print_red(f"\n[ERROR] Could not connect to server at {API_URL}")
        print_red("Please ensure 'python src/app.py' is running.")
    except Exception as e:
        print_red(f"\n[ERROR] {type(e).__name__}: {e}")


def main():
    test_queries = [
        "競爭對手的最新消息",
    ]

    for query in test_queries:
        test_api_search(query)

    print("\n" + "=" * 80)
    print("Test Suite Completed")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        custom_query = " ".join(sys.argv[1:])
        test_api_search(custom_query)
    else:
        main()
