import ollama
import asyncio


async def test():
    print(f"Has AsyncClient: {hasattr(ollama, 'AsyncClient')}")
    if hasattr(ollama, "AsyncClient"):
        client = ollama.AsyncClient()
        print(f"Has embed: {hasattr(client, 'embed')}")
        print(f"Has embeddings: {hasattr(client, 'embeddings')}")


if __name__ == "__main__":
    asyncio.run(test())
