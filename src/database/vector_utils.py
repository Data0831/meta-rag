import os
from typing import List
import ollama
from dotenv import load_dotenv

load_dotenv()

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)


def get_embedding(text: str, model: str = "bge-m3") -> List[float]:
    """
    Generates embedding for the given text using Ollama API.
    Uses OLLAMA_HOST environment variable for remote Ollama servers.
    """
    try:
        # Replacing newlines for consistency with common practices.
        text = text.replace("\n", " ")

        response = ollama_client.embeddings(
            model=model,
            prompt=text,
            options={"num_ctx": 8192},  # Enforce num_ctx as specified
        )
        return response["embedding"]
    except Exception as e:
        print(f"Error generating embedding from {OLLAMA_HOST}: {e}")
        return []


if __name__ == "__main__":
    # Test embedding generation
    test_text = "這是一個測試文本，用於生成向量嵌入。Microsoft Azure 雲端服務提供強大的計算能力。"

    print("--- Testing get_embedding ---")
    print(f"Test text: {test_text}")

    # You might need to have Ollama running with 'bge-m3' model pulled
    # For example: ollama pull bge-m3

    embedding = get_embedding(test_text)
    if embedding:
        print(f"✅ Successfully generated embedding")
        print(f"   Dimension: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
    else:
        print("❌ Failed to generate embedding")
