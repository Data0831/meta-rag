import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from src.llm.client import LLMClient


def test_llm_connection() -> None:
    print("=== Testing LLMClient Connection ===")

    client = LLMClient()

    response = client.call_gemini(
        messages=[{"role": "user", "content": "Hello, are you working?"}]
    )

    if response:
        print("✓ Connection successful!")
        print(f"Response: {response}")
    else:
        print("✗ Connection failed - no response received")


if __name__ == "__main__":
    test_llm_connection()
