import os
from typing import List
import ollama
from dotenv import load_dotenv
from src.schema.schemas import AnnouncementMetadata, AnnouncementDoc
from uuid import uuid4
from datetime import date
import sys

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
            options={"num_ctx": 8192},  # Enforce num_ctx as specified
        )
        return response["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []


if __name__ == "__main__":
    from src.schema.schemas import AnnouncementMetadata, AnnouncementDoc
    from uuid import uuid4
    from datetime import date

    # Create a dummy AnnouncementMetadata
    dummy_metadata = AnnouncementMetadata(
        meta_date_announced=date(2023, 1, 15),
        meta_date_effective=date(2023, 2, 1),
        meta_products=["Microsoft Teams", "Microsoft 365"],
        meta_category="Feature Update",
        meta_audience=["Enterprise", "Small Business"],
        meta_impact_level="Medium",
        meta_summary="New features for Microsoft Teams and Microsoft 365.",
        meta_change_type="New Feature",
    )

    # Create a dummy AnnouncementDoc
    dummy_doc = AnnouncementDoc(
        uuid=str(uuid4()),
        month="2023-01",
        title="Introducing New Collaboration Features in Teams",
        original_content="Microsoft is rolling out new features to enhance collaboration in Microsoft Teams and Microsoft 365.",
        metadata=dummy_metadata,
    )

    print("--- Testing create_enriched_text ---")
    enriched_text = create_enriched_text(dummy_doc) * 10
    print(len(enriched_text))
    print("\n--- Testing get_embedding ---")

    # You might need to have Ollama running with 'bge-m3' model pulled
    # For example: ollama pull bge-m3

    embedding = get_embedding(enriched_text)
    if embedding:
        print(f"Successfully generated embedding. Length: {len(embedding)}")
        # print(f"First 5 elements: {embedding[:5]}...") # Uncomment to see part of the embedding
    else:
        print("Failed to generate embedding.")
