import os
import asyncio
from typing import List, Dict, Any, Union
import ollama
from collections import deque
from dotenv import load_dotenv
from src.log.logManager import LogManager
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)


async def get_embeddings_batch(
    texts: List[str],
    model: str = "bge-m3",
    sub_batch_size: int = 20,
    max_concurrency: int = 4,
    force_gpu: bool = True,
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    """
    Generate embeddings for a list of texts using sub-batching and high concurrency.
    Includes retry logic: if a batch fails, it's decomposed into individual items
    and added back to the queue to isolate the error.
    """
    if not texts:
        return []

    async_client = ollama.AsyncClient(host=OLLAMA_HOST)
    results = [None] * len(texts)

    # Task queue: (start_index, list_of_texts, current_retry_count)
    # Use sub_batch_size to initial partition
    chunks = [
        (i, texts[i : i + sub_batch_size], 0)
        for i in range(0, len(texts), sub_batch_size)
    ]
    task_queue = deque(chunks)

    # Semaphore to control concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_task(start_idx: int, chunk_texts: List[str], retry_count: int):
        async with semaphore:
            try:
                cleaned_texts = [t.replace("\n", " ") for t in chunk_texts]
                response = await async_client.embed(
                    model=model,
                    input=cleaned_texts,
                    options={
                        "num_ctx": 8192,
                        "num_gpu": 999 if force_gpu else 0,
                    },
                )

                embeddings = getattr(response, "embeddings", [])
                if not embeddings and isinstance(response, dict):
                    embeddings = response.get("embeddings", [])

                for i, emb in enumerate(embeddings):
                    if i < len(chunk_texts):
                        idx = start_idx + i
                        results[idx] = {"status": "success", "result": emb}

                # Completion check
                for i in range(len(chunk_texts)):
                    if results[start_idx + i] is None:
                        results[start_idx + i] = {
                            "status": "failed",
                            "error": "No embedding returned",
                            "stage": "embedding_generation",
                        }
            except Exception as e:
                # If chunk has multiple items, split them to find the culprit
                if len(chunk_texts) > 1:
                    for i, t in enumerate(chunk_texts):
                        task_queue.append((start_idx + i, [t], retry_count))
                    return

                # If single item failed or max retries
                if retry_count < max_retries:
                    task_queue.append((start_idx, chunk_texts, retry_count + 1))
                else:
                    # Final failure after max retries
                    t = chunk_texts[0]
                    text_preview = t[:50].replace("\n", " ")
                    error_msg = f"Embedding Failed at Index [{start_idx}] | Text: {text_preview}... | Error: {str(e)}"

                    logger.error(error_msg)

                    results[start_idx] = {
                        "status": "failed",
                        "error": str(e),
                        "text_preview": t[:100],
                        "stage": "embedding_generation",
                    }
                    LogManager.log_embedding(
                        text=t, error=str(e), model=model, index=start_idx
                    )

    # Run loop until queue is empty
    while task_queue:
        active_tasks = []
        # Pull up to max_concurrency items from the queue
        for _ in range(min(len(task_queue), max_concurrency)):
            idx, batch_txt, retries = task_queue.popleft()
            active_tasks.append(process_task(idx, batch_txt, retries))

        if active_tasks:
            await asyncio.gather(*active_tasks)

    return results


def get_embedding(text: str, model: str = "bge-m3") -> Dict[str, Any]:
    """
    Original sync function for compatibility.
    """
    try:
        text = text.replace("\n", " ")

        response = ollama_client.embeddings(
            model=model,
            prompt=text,
            options={"num_ctx": 8192},
        )
        return {"status": "success", "result": response["embedding"]}
    except Exception as e:
        error_info = {
            "status": "failed",
            "error": f"Error generating embedding from {OLLAMA_HOST}: {str(e)}",
            "stage": "embedding_generation",
        }
        LogManager.log_embedding(text=text, error=str(e), model=model)
        return error_info
