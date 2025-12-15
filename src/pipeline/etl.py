import json
import os
import glob
from typing import List, Dict, Any
from datetime import datetime
import uuid

# Import local modules
from src.llm.client import LLMClient
from src.llm.prompts import SYSTEM_PROMPT
from src.models.schemas import AnnouncementDoc, AnnouncementMetadata


class ETLPipeline:
    def __init__(
        self, input_dir: str = "data/split", output_dir: str = "data/processed"
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.llm_client = LLMClient()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def load_batch(self, file_path: str) -> List[Dict[str, Any]]:
        """Load a single batch file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse strict JSON from LLM response, handling potential markdown code blocks."""
        if not response_text:
            return []

        clean_text = response_text.strip()

        # Remove markdown code blocks if present
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Raw Text: {response_text[:100]}...")  # Print first 100 chars
            return []

    def merge_data(
        self, raw_items: List[Dict[str, Any]], metadata_items: List[Dict[str, Any]]
    ) -> List[AnnouncementDoc]:
        """Merge raw items with extracted metadata."""
        merged_docs = []

        # Create a lookup for metadata by ID if possible, but assuming order is preserved as per prompt
        # If lengths match, zip them.

        if len(raw_items) != len(metadata_items):
            print(
                f"Warning: Batch size mismatch! Raw: {len(raw_items)}, Meta: {len(metadata_items)}"
            )
            # Fallback logic could be added here, but for now we proceed safely with min length

        for raw, meta in zip(raw_items, metadata_items):
            # Generate UUID if not present
            doc_uuid = raw.get("id") or str(uuid.uuid4())

            # Construct Metadata object
            try:
                metadata_obj = AnnouncementMetadata(
                    meta_date_effective=meta.get("meta_date_effective"),
                    meta_products=meta.get("meta_products", []),
                    meta_category=meta.get("meta_category"),
                    meta_audience=meta.get("meta_audience", []),
                    meta_impact_level=meta.get("meta_impact_level"),
                    meta_action_deadline=meta.get("meta_action_deadline"),
                    meta_summary=meta.get("meta_summary"),
                    meta_change_type=meta.get("meta_change_type"),
                    meta_date_announced=meta.get("meta_date_announced"),
                )

                # Construct Document object
                doc = AnnouncementDoc(
                    uuid=str(doc_uuid),
                    month=raw.get("month", "Unknown"),
                    title=raw.get("title", ""),
                    link=raw.get("link"),
                    original_content=raw.get("content", ""),
                    metadata=metadata_obj,
                )
                merged_docs.append(doc)
            except Exception as e:
                print(f"Error merging item {doc_uuid}: {e}")

        return merged_docs

    def process_file(self, file_path: str):
        """Process a single file through the ETL pipeline."""
        print(f"Processing {file_path}...")

        # 1. Load Data
        raw_batch = self.load_batch(file_path)
        if not raw_batch:
            print("Empty batch, skipping.")
            return

        # 2. Prepare Prompt
        if not SYSTEM_PROMPT:
            print(
                "WARNING: SYSTEM_PROMPT is empty in src/prompts.py. Please fill it before running."
            )
            return

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(raw_batch, ensure_ascii=False)},
        ]

        # 3. Call LLM
        response_text = self.llm_client.call_gemini(messages)
        if not response_text:
            print("No response from LLM.")
            return

        # 4. Parse Response
        metadata_batch = self.parse_llm_response(response_text)
        if not metadata_batch:
            print("Failed to parse metadata.")
            return

        # 5. Merge
        docs = self.merge_data(raw_batch, metadata_batch)

        # 6. Save
        filename = os.path.basename(file_path)
        output_path = os.path.join(self.output_dir, filename)

        # Convert Pydantic models to dicts for JSON serialization
        docs_json = [doc.dict(mode="json") for doc in docs]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(docs_json, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(docs)} documents to {output_path}")

    def run(self):
        """Run the pipeline on all files in data/split."""
        files = glob.glob(os.path.join(self.input_dir, "*.json"))
        print(f"Found {len(files)} files in {self.input_dir}")

        for file in files:
            self.process_file(file)


if __name__ == "__main__":
    pipeline = ETLPipeline()
    pipeline.run()
