import json
from typing import List, Dict, Any
from pathlib import Path
import sys
import os
import uuid

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.schema.schemas import AnnouncementDoc, AnnouncementMetadata


def parse_json_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses the raw JSON file containing announcements.
    Expected format:
    {
        "2025-12": [
            { "title": "...", "link": "...", "content": "..." },
            ...
        ],
        ...
    }
    Returns a list of clean dictionaries with added 'month' field.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON - {e}")
        return []

    cleaned_items = []

    # Iterate over each month and its list of items
    # The structure is assumed to be Key (Month) -> List of Objects
    if isinstance(data, dict):
        for month, items in data.items():
            if not isinstance(items, list):
                continue

            for item in items:
                # Basic validation
                if not isinstance(item, dict):
                    continue

                # Extract fields
                title = item.get("title", "").strip()
                content = item.get("content", "").strip()
                link = item.get("link", "").strip()

                # We need a unique ID for the vector store and database.
                # Since we don't have one in the source, we generate a id.
                doc_id = str(uuid.uuid4())

                # Initialize empty metadata needed for schema validation later
                # Ensure it validates against our schema
                try:
                    doc = AnnouncementDoc(
                        id=doc_id,
                        month=month,
                        title=title,
                        link=link,
                        original_content=content,
                        metadata=AnnouncementMetadata(),
                    )
                    cleaned_items.append(doc.model_dump())
                except Exception as e:
                    print(f"Warning: Skipping item due to validation error: {e}")
                    continue

    return cleaned_items


if __name__ == "__main__":
    # Test execution
    data_path = Path("data/page.json")
    # If running from root, path is data/page.json
    # Adjust if running helper script directly
    if not data_path.exists():
        # Try absolute path if relative fails, or check common locations
        # For now, just print warning
        print(
            f"Warning: {data_path} does not exist. Please place 'page.json' in 'data/' folder."
        )
    else:
        docs = parse_json_data(str(data_path))
        print(f"Successfully parsed {len(docs)} documents.")
        if len(docs) > 0:
            print("Sample doc:", json.dumps(docs[0], indent=2, ensure_ascii=False))
