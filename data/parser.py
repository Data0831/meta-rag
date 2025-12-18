import json
from typing import List, Dict, Any
from pathlib import Path
import re


def clean_content(content: str) -> str:
    """
    Clean the content by removing noise and keeping key information.

    Cleaning steps:
    1. Remove URLs (http/https)
    2. Remove Markdown links (keep anchor text)
    3. Remove template Markdown headers (#### 現已推出, etc.)
    4. Remove metadata fields (日期, 工作區, 受影響的群體)
    """
    if not content:
        return ""

    text = content

    # 1. Remove URLs
    text = re.sub(r'https?://\S+', '', text)

    # 2. Remove Markdown links but keep anchor text
    text = re.sub(r'\[(.*?)\]\([^)]*?\)', r'\1', text)

    # 3. Remove template Markdown headers (multiline mode)
    text = re.sub(r'^#{3,6}\s*(現已推出|即將到來的事項|提醒|後續步驟)\s*$', '', text, flags=re.MULTILINE)

    # 4. Remove metadata field lines
    text = re.sub(r'^\*\s*\*\*日期\*\*[：:].*\r?\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\s*\*\*工作區\*\*[：:].*\r?\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\s*\*\*受影響的群體\*\*[：:].*\r?\n?', '', text, flags=re.MULTILINE)

    # 5. Clean up excessive whitespace and newlines
    text = re.sub(r'\n{3,}', '\n\n', text)  # Replace 3+ newlines with 2
    text = text.strip()

    return text


def extract_metadata_from_content(content: str) -> Dict[str, str]:
    """
    Extract metadata from content markdown.
    Looks for patterns like:
    * **日期**：2025年12月10日
    * **工作區**：一般
    """
    metadata = {"announced": "", "workspace": ""}

    # Extract date (日期)
    date_pattern = r"\*\s*\*\*日期\*\*[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日"
    date_match = re.search(date_pattern, content)
    if date_match:
        month = date_match.group(2).zfill(2)
        day = date_match.group(3).zfill(2)
        metadata["announced"] = f"{month}-{day}"

    # Extract workspace (工作區)
    workspace_pattern = r"\*\s*\*\*工作區\*\*[：:]\s*(.+?)(?:\n|\*|$)"
    workspace_match = re.search(workspace_pattern, content)
    if workspace_match:
        workspace = workspace_match.group(1).strip()
        # Map Chinese to English
        workspace_map = {
            "一般": "General",
            "通用": "General",
        }
        metadata["workspace"] = workspace_map.get(workspace, workspace)

    return metadata


def convert_month_to_numeric(month_str: str) -> str:
    """
    Convert month string like '2025-december' to '2025-12'
    """
    month_map = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }

    parts = month_str.split("-")
    if len(parts) == 2:
        year = parts[0]
        month_name = parts[1].lower()
        month_num = month_map.get(month_name, "00")
        return f"{year}-{month_num}"

    return month_str


def parse_json_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses the raw JSON file containing announcements.
    Expected input format:
    {
        "2025-december": [
            { "title": "...", "link": "...", "content": "..." },
            ...
        ],
        ...
    }

    Returns output format:
    [
        {
            "link": "...",
            "year-month": "2025-12",
            "Announced": "12-10",
            "Workspace": "General",
            "title": "...",
            "content": "..."
        },
        ...
    ]
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

    parsed_items = []

    # Iterate over each month and its list of items
    if isinstance(data, dict):
        for month_key, items in data.items():
            if not isinstance(items, list):
                continue

            # Convert month key to year-month format
            year_month = convert_month_to_numeric(month_key)

            for item in items:
                # Basic validation
                if not isinstance(item, dict):
                    continue

                # Extract fields
                title = item.get("title", "").strip()
                content = item.get("content", "").strip()
                link = item.get("link", "").strip()

                # Extract metadata from content
                metadata = extract_metadata_from_content(content)

                # Clean content for better search/RAG performance
                cleaned = clean_content(content)

                # Build output document
                parsed_doc = {
                    "link": link,
                    "year-month": year_month,
                    "Workspace": metadata["workspace"],
                    "title": title,
                    "content": content,  # Keep original content
                    "cleaned_content": cleaned,  # Add cleaned version
                }

                parsed_items.append(parsed_doc)

    return parsed_items


if __name__ == "__main__":
    # Test execution
    data_path = Path("data/page.json")

    if not data_path.exists():
        print(
            f"Warning: {data_path} does not exist. Please place 'page.example.json' in 'data/' folder."
        )
    else:
        docs = parse_json_data(str(data_path))
        print(f"Successfully parsed {len(docs)} documents.")

        if len(docs) > 0:
            print("\nSample doc:")
            print(json.dumps(docs[0], indent=4, ensure_ascii=False))

        # Save to parse.json
        output_path = Path("data/parse.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=4, ensure_ascii=False)
        print(f"\nSaved parsed data to {output_path}")
