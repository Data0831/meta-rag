import os
from typing import List
import ollama

load_dotenv()


def create_enriched_text(doc: AnnouncementDoc) -> str:
    """
    Constructs the synthetic context string for embedding.
    Format based on GEMINI.md:
    Title: {title}
    Impact Level: {meta_impact_level}
    Target Audience: {meta_audience}
    Products: {meta_products}
    Change Type: {meta_change_type}
    Summary: {meta_summary}
    Content: {original_content}
    """
    meta = doc.metadata

    # Handle list fields by joining them
    audience = ", ".join(meta.meta_audience) if meta.meta_audience else "None"
    products = ", ".join(meta.meta_products) if meta.meta_products else "None"

    # Handle enum/optional fields safely
    impact = meta.meta_impact_level.value if meta.meta_impact_level else "Unknown"
    change_type = meta.meta_change_type if meta.meta_change_type else "Unknown"
    summary = meta.meta_summary if meta.meta_summary else ""

    text = (
        f"Title: {doc.title}\n"
        f"Impact Level: {impact}\n"
        f"Target Audience: {audience}\n"
        f"Products: {products}\n"
        f"Change Type: {change_type}\n"
        f"Summary: {summary}\n"
        f"Content: {doc.original_content}"
    )
    return text


def get_embedding(text: str, model: str = "bge-m3") -> List[float]:
    """
    Generates embedding for the given text using Ollama API.
    """
    try:
        # Replacing newlines for consistency with common practices.
        text = text.replace("\n", " ")

        response = ollama.embeddings(
            model=model,
            prompt=text,
            options={
                "num_ctx": 8192  # Enforce num_ctx as specified
            }
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []
