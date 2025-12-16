"""
Batch Processor Module

Handles individual batch processing including:
- Loading batch data
- LLM metadata extraction
- Data merging
- File output
"""

import json
import os
import sys
import time
import uuid as uuid_lib
from typing import List, Dict, Any, Optional

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.llm.client import LLMClient
from src.llm.metadata_prompts import SYSTEM_PROMPT
from src.schema.schemas import (
    AnnouncementDoc,
    AnnouncementMetadata,
    BatchMetaExtraction,
    MetadataExtraction,
)
from src.ETL.etl_pipe.error_handler import ErrorHandler


class BatchProcessor:
    """處理單個批次的 ETL 流程"""

    def __init__(
        self,
        llm_client: LLMClient,
        error_handler: ErrorHandler,
        output_dir: str = "data/processed",
    ):
        self.llm_client = llm_client
        self.error_handler = error_handler
        self.output_dir = output_dir

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def load_batch(self, file_path: str) -> List[Dict[str, Any]]:
        """Load a single batch file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def prepare_llm_input(
        self, raw_batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """準備 LLM 輸入資料（標準化欄位）"""
        llm_input = []
        for idx, item in enumerate(raw_batch):
            llm_item = {
                "id": item.get("uuid") or str(idx),
                "month": item.get("month"),
                "title": item.get("title"),
                "content": item.get("original_content") or item.get("content", ""),
            }
            llm_input.append(llm_item)
        return llm_input

    def extract_metadata(
        self, llm_input: List[Dict[str, Any]]
    ) -> Optional[BatchMetaExtraction]:
        """呼叫 LLM 提取 metadata"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(llm_input, ensure_ascii=False)},
        ]

        batch_result = self.llm_client.call_with_schema(
            messages=messages, response_model=BatchMetaExtraction
        )

        return batch_result

    def merge_data(
        self, raw_items: List[Dict[str, Any]], metadata_items: List[MetadataExtraction]
    ) -> List[AnnouncementDoc]:
        """Merge raw items with extracted metadata (Pydantic objects)."""
        merged_docs = []

        # Create a lookup for metadata by ID (ID 是 uuid 或索引)
        metadata_by_id = {meta.id: meta for meta in metadata_items}

        for idx, raw in enumerate(raw_items):
            # 找出對應的 metadata (使用 uuid 或索引)
            lookup_id = raw.get("uuid") or str(idx)
            meta = metadata_by_id.get(lookup_id)

            if not meta:
                print(f"Warning: No metadata found for ID {lookup_id}, skipping.")
                continue

            # 使用原始的 uuid 或生成新的
            doc_uuid = raw.get("uuid") or str(uuid_lib.uuid4())

            # Construct Metadata object from Pydantic MetadataExtraction
            try:
                metadata_obj = AnnouncementMetadata(
                    meta_date_effective=meta.meta_date_effective,
                    meta_products=meta.meta_products or [],
                    meta_category=meta.meta_category,
                    meta_audience=meta.meta_audience or [],
                    meta_impact_level=meta.meta_impact_level,
                    meta_action_deadline=meta.meta_action_deadline,
                    meta_summary=meta.meta_summary,
                    meta_change_type=meta.meta_change_type,
                    meta_date_announced=meta.meta_date_announced,
                )

                # Construct Document object
                doc = AnnouncementDoc(
                    uuid=doc_uuid,
                    month=raw.get("month", "Unknown"),
                    title=raw.get("title", ""),
                    link=raw.get("link"),
                    original_content=raw.get("original_content")
                    or raw.get("content", ""),
                    metadata=metadata_obj,
                )
                merged_docs.append(doc)
            except Exception as e:
                print(f"Error merging item {lookup_id}: {e}")

        return merged_docs

    def save_batch(self, docs: List[AnnouncementDoc], file_path: str):
        """儲存批次結果到檔案"""
        filename = os.path.basename(file_path)
        output_path = os.path.join(self.output_dir, filename)

        # Convert Pydantic models to dicts for JSON serialization
        docs_json = [doc.model_dump(mode="json") for doc in docs]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(docs_json, f, ensure_ascii=False, indent=2)

        print(f"✓ Saved {len(docs)} documents to {output_path}")

    def process_file(self, file_path: str) -> bool:
        """
        Process a single file through the ETL pipeline.

        Returns:
            True if successful, False if error occurred
        """
        print(f"Processing {file_path}...")
        llm_input = None
        uuids = []

        try:
            # 1. Load Data
            raw_batch = self.load_batch(file_path)
            if not raw_batch:
                print("Empty batch, skipping.")
                return True  # Empty is not an error

            # Extract UUIDs for error tracking
            uuids = [item.get("uuid") or str(idx) for idx, item in enumerate(raw_batch)]

            # 2. Check SYSTEM_PROMPT
            if not SYSTEM_PROMPT:
                error_msg = "SYSTEM_PROMPT is empty in src/prompts.py"
                print(f"WARNING: {error_msg}")
                self.error_handler.log_error(
                    batch_file=file_path,
                    uuids=uuids,
                    error_type="ConfigError",
                    error_message=error_msg,
                )
                return False

            # 3. Prepare LLM Input
            llm_input = self.prepare_llm_input(raw_batch)

            # 4. Extract Metadata via LLM
            batch_result = self.extract_metadata(llm_input)

            if not batch_result:
                error_msg = (
                    "Failed to get validated response from LLM (all retries exhausted)"
                )
                print(f"✗ {error_msg}")
                self.error_handler.log_error(
                    batch_file=file_path,
                    uuids=uuids,
                    error_type="LLMValidationError",
                    error_message=error_msg,
                    llm_input=llm_input,
                    llm_response=None,
                )
                return False

            # 5. Merge Data
            metadata_batch = batch_result.results
            docs = self.merge_data(raw_batch, metadata_batch)

            if len(docs) == 0:
                error_msg = (
                    f"Merge failed: No documents produced (expected {len(raw_batch)})"
                )
                print(f"✗ {error_msg}")
                self.error_handler.log_error(
                    batch_file=file_path,
                    uuids=uuids,
                    error_type="MergeError",
                    error_message=error_msg,
                    llm_input=llm_input,
                    llm_response=json.dumps(
                        [m.model_dump() for m in metadata_batch], ensure_ascii=False
                    ),
                )
                return False

            # 6. Save
            self.save_batch(docs, file_path)
            time.sleep(1)  # Rate limit protection
            return True

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"✗ {error_msg}")
            self.error_handler.log_error(
                batch_file=file_path,
                uuids=uuids,
                error_type="UnexpectedError",
                error_message=error_msg,
                llm_input=llm_input,
                llm_response=None,
            )
            return False
