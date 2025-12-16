"""
ETL Pipeline - Main Orchestrator
Coordinates batch processing, error handling, and incremental storage.
"""

import json
import os
import sys
from typing import List, Dict, Any

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Import local modules
from src.llm.client import LLMClient
from src.ETL.etl_pipe.error_handler import ErrorHandler
from src.ETL.etl_pipe.batch_processor import BatchProcessor
from src.ETL.etl_pipe.parser import parse_json_data as parse_raw_json
from src.config import (
    PAGE_JSON,
    PARSE_JSON,
    PROCESSED_DIR,
    LOG_DIR,
    PROCESSED_OUTPUT,
    ERROR_LIST_OUTPUT,
    DEFAULT_BATCH_SIZE,
)


class ETLPipeline:
    """ETL Pipeline 主控制器"""

    def __init__(
        self,
        parsed_file: str = PARSE_JSON,
        processed_file: str = PROCESSED_OUTPUT,
        log_dir: str = LOG_DIR,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.parsed_file = parsed_file
        self.processed_file = processed_file
        self.batch_size = batch_size

        # Initialize components
        self.llm_client = LLMClient()
        self.error_handler = ErrorHandler(log_dir=log_dir, output_dir=PROCESSED_DIR)
        self.batch_processor = BatchProcessor(
            llm_client=self.llm_client,
            error_handler=self.error_handler,
        )

        # Ensure directories exist
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

    def parse_json_data(self, file_path: str = PAGE_JSON) -> List[dict]:
        """
        把 page.json 解析成 AnnouncementDoc 的 list
        Args:
            file_path: Path to the raw JSON file
        Returns:
            List of AnnouncementDoc dictionaries with UUID and empty metadata
        """
        print(f"Parsing raw data from {file_path}...")
        docs = parse_raw_json(file_path)
        with open(self.parsed_file, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        print(f"Successfully parsed {len(docs)} announcement documents.")
        return docs

    def clean(self):
        os.remove(self.processed_file)

    def load_parsed_data(self) -> List[Dict[str, Any]]:
        """
        Load parsed data from parse.json.

        Returns:
            List of parsed announcement documents
        """
        if not os.path.exists(self.parsed_file):
            print(f"Warning: {self.parsed_file} not found. Returning empty list.")
            return []

        with open(self.parsed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded {len(data)} documents from {self.parsed_file}")
            return data

    def load_processed_data(self) -> List[Dict[str, Any]]:
        """
        Load already processed data from processed.json.

        Returns:
            List of processed documents
        """
        if not os.path.exists(self.processed_file):
            print(f"No existing processed file found at {self.processed_file}")
            return []

        with open(self.processed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded {len(data)} already processed documents")
            return data

    def append_to_processed(self, new_docs: List[Dict[str, Any]]):
        """
        Append new documents to processed.json (incremental write).

        Args:
            new_docs: List of new documents to append
        """
        # Load existing data
        existing_docs = self.load_processed_data()

        # Merge with new docs
        all_docs = existing_docs + new_docs

        # Write back
        with open(self.processed_file, "w", encoding="utf-8") as f:
            json.dump(all_docs, f, ensure_ascii=False, indent=2)

        print(
            f"✓ Appended {len(new_docs)} documents to {self.processed_file} (total: {len(all_docs)})"
        )

    def genMetaData(self, interactive: bool = True):
        """
        Run the ETL pipeline: load parsed data, process in batches, append to processed.json.

        Args:
            interactive: If True, ask user about retrying errors
        """
        print("=" * 60)
        print("Starting ETL Pipeline")
        print("=" * 60)

        # 1. Load parsed data
        all_docs = self.load_parsed_data()
        if not all_docs:
            print("No parsed data found. Please run the parser first.")
            return

        # 2. Load already processed data to avoid duplicates
        processed_docs = self.load_processed_data()
        processed_uuids = {doc.get("uuid") for doc in processed_docs if doc.get("uuid")}

        # 3. Filter out already processed documents
        unprocessed_docs = [
            doc for doc in all_docs if doc.get("uuid") not in processed_uuids
        ]

        if not unprocessed_docs:
            print("\n✓ All documents have been processed already.")
            return

        print(f"\nTotal documents: {len(all_docs)}")
        print(f"Already processed: {len(processed_docs)}")
        print(f"To process: {len(unprocessed_docs)}")
        print(f"Batch size: {self.batch_size}\n")

        # 4. Process in batches
        total_batches = (len(unprocessed_docs) + self.batch_size - 1) // self.batch_size
        successful_batches = 0
        failed_batches = 0

        for i in range(0, len(unprocessed_docs), self.batch_size):
            batch = unprocessed_docs[i : i + self.batch_size]
            batch_index = i // self.batch_size + 1

            print(f"\n[Batch {batch_index}/{total_batches}]")

            # Process the batch
            result_docs = self.batch_processor.process_batch(batch, batch_index)

            if result_docs is not None:
                # Success: append to processed.json
                docs_dict = [doc.model_dump(mode="json") for doc in result_docs]
                self.append_to_processed(docs_dict)
                successful_batches += 1
            else:
                # Failed
                failed_batches += 1

        # 5. Summary
        print("\n" + "=" * 60)
        print("ETL Pipeline Summary")
        print("=" * 60)
        print(f"Successful batches: {successful_batches}/{total_batches}")
        print(f"Failed batches: {failed_batches}/{total_batches}")

        # Handle errors if any
        if self.error_handler.has_errors():
            self.error_handler.display_error_summary()
            if not interactive:
                self.error_handler.save_error_list()
        else:
            print("\n✓ All batches processed successfully!")

        print(f"\nProcessed data saved to: {self.processed_file}")
