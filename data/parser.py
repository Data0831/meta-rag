import json
from typing import List, Dict, Any
from pathlib import Path
import re

FILES_NEED_TO_BE_PROCESSED = [
    "fetch_result/partner_center_announcements.json",
    "fetch_result/windows_message_center.json",
    "fetch_result/m365_roadmap.json",
    "fetch_result/powerbi_blog.json",
]

OUTPUT_FILE = "data.json"


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
    text = re.sub(r"https?://\S+", "", text)

    # 2. Remove Markdown links but keep anchor text
    text = re.sub(r"\[(.*?)\]\([^)]*?\)", r"\1", text)

    # 3. Remove template Markdown headers (multiline mode)
    text = re.sub(
        r"^#{3,6}\s*(現已推出|即將到來的事項|提醒|後續步驟)\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )

    # 4. Remove metadata field lines
    text = re.sub(r"^\*\s*\*\*日期\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\s*\*\*工作區\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE)
    text = re.sub(
        r"^\*\s*\*\*受影響的群體\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE
    )

    # 5. Clean up excessive whitespace and newlines
    text = re.sub(r"\n{3,}", "\n\n", text)  # Replace 3+ newlines with 2
    text = text.strip()

    return text


def process_files():
    """
    Process the files defined in FILES_NEED_TO_BE_PROCESSED.
    1. Read each file.
    2. Check required fields (link, year_month, title, content).
    3. Truncate content if > 3000 chars.
    4. Clean content.
    5. Aggregate and save to parse.json.
    """
    base_dir = Path(__file__).parent
    output_path = base_dir / OUTPUT_FILE
    aggregated_data = []

    print(f"Processing files: {FILES_NEED_TO_BE_PROCESSED}")

    for filename in FILES_NEED_TO_BE_PROCESSED:
        file_path = base_dir / filename
        if not file_path.exists():
            print(f"Warning: File {filename} not found. Skipping.")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {filename}: {e}")
            continue

        # Ensure data is a list
        if not isinstance(data, list):
            print(f"Warning: Data in {filename} is not a list. Skipping.")
            continue

        for item in data:
            # Helper to check required fields
            if not all(
                key in item for key in ["link", "year_month", "title", "content"]
            ):
                # Skip items missing required fields
                continue

            # Process Content
            raw_content = item["content"]

            # 1. Truncate if > 3000
            if len(raw_content) > 3000:
                raw_content = raw_content[:3000]

            # 2. Clean content
            cleaned_content = clean_content(raw_content)

            # Extract Year from year_month (assuming YYYY-MM format)
            year_month = item["year_month"]
            year = year_month.split("-")[0] if "-" in year_month else year_month[:4]

            # Update existing item to preserve other keys
            item["year"] = year
            item["content"] = raw_content
            item["cleaned_content"] = cleaned_content

            aggregated_data.append(item)

    # Save aggregated data
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(aggregated_data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {len(aggregated_data)} items to {output_path}")
    except Exception as e:
        print(f"Error saving output file: {e}")


if __name__ == "__main__":
    process_files()
