import json
import os
from pathlib import Path
from math import ceil
from src.ingestion.parser import parse_json_data


def split_and_save_batches(input_file: str, output_dir: str, batch_size: int = 5):
    """
    Reads the processed data, splits it into batches, and saves them as separate JSON files.
    """
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Parse data using existing ingestion logic
    # This returns a list of dictionaries (validated against AnnouncementDoc)
    print(f"Reading data from {input_file}...")
    all_docs = parse_json_data(input_file)

    if not all_docs:
        print("No documents found to split.")
        return

    total_docs = len(all_docs)
    num_batches = ceil(total_docs / batch_size)

    print(
        f"Found {total_docs} documents. Splitting into {num_batches} batches of size {batch_size}."
    )

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = start_idx + batch_size
        batch = all_docs[start_idx:end_idx]

        # Define output filename: 1.json, 2.json, ...
        filename = f"{i + 1}.json"
        output_path = os.path.join(output_dir, filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)

        print(f"Saved batch {i+1} to {output_path} ({len(batch)} items)")


if __name__ == "__main__":
    # Define paths
    INPUT_FILE = "data/result.json"
    OUTPUT_DIR = "data/split"

    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(
            f"Error: {INPUT_FILE} not found. Please ensure data is in 'data/' directory."
        )
    else:
        split_and_save_batches(INPUT_FILE, OUTPUT_DIR)
