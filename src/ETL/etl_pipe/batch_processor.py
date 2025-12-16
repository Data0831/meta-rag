"""
Batch Processor Module

Handles in-memory batch processing including:
- LLM metadata extraction
- Data merging
- Model switching on errors
"""

import json
import os
import sys
import time
import uuid
from typing import List, Dict, Any, Optional
from openai import APIStatusError

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
from src.config import GEMINI_MODELS


class BatchProcessor:
    """處理記憶體中批次資料的 ETL 流程，支援模型自動切換"""

    def __init__(
        self,
        llm_client: LLMClient,
        error_handler: ErrorHandler,
    ):
        self.llm_client = llm_client
        self.error_handler = error_handler

        # Model switching configuration
        self.available_models = GEMINI_MODELS.copy()
        self.current_model_index = 0

        # Set initial model from llm_client
        if hasattr(llm_client, "model") and llm_client.model in self.available_models:
            self.current_model_index = self.available_models.index(llm_client.model)

    def get_next_model(self) -> Optional[str]:
        """切換到下一個可用的 model"""
        self.current_model_index += 1
        if self.current_model_index >= len(self.available_models):
            return None  # 所有 model 都試過了

        next_model = self.available_models[self.current_model_index]
        print(f"🔄 切換到下一個 model: {next_model}")
        return next_model

    def reset_model_index(self):
        """重置 model index 到初始值（用於新的 batch）"""
        initial_model = (
            self.llm_client.model
            if hasattr(self.llm_client, "model")
            else self.available_models[0]
        )
        if initial_model in self.available_models:
            self.current_model_index = self.available_models.index(initial_model)
        else:
            self.current_model_index = 0

    def prepare_llm_input(
        self, raw_batch: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """準備 LLM 輸入資料（標準化欄位）"""
        llm_input = []
        for idx, item in enumerate(raw_batch):
            llm_item = {
                "id": item.get("id") or str(idx),
                "month": item.get("month"),
                "title": item.get("title"),
                "content": item.get("original_content") or item.get("content", ""),
            }
            llm_input.append(llm_item)
        return llm_input

    def extract_metadata(
        self, llm_input: List[Dict[str, Any]]
    ) -> Optional[BatchMetaExtraction]:
        """呼叫 LLM 提取 metadata，支援模型自動切換"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(llm_input, ensure_ascii=False)},
        ]

        # 使用當前 model 嘗試
        current_model = self.available_models[self.current_model_index]

        # 安全機制：最多嘗試所有可用 model 一次
        max_attempts = len(self.available_models)
        attempt_count = 0

        while attempt_count < max_attempts:
            attempt_count += 1

            try:
                print(
                    f"📡 使用 model: {current_model} (嘗試 {attempt_count}/{max_attempts})"
                )
                batch_result = self.llm_client.call_with_schema(
                    messages=messages,
                    response_model=BatchMetaExtraction,
                    model=current_model,
                )

                if batch_result:
                    return batch_result

                # 如果返回 None（驗證失敗），不切換 model，直接返回 None
                return None

            except APIStatusError as e:
                # 檢查是否為 429 或 500 錯誤
                if e.status_code in [429, 500]:
                    print(f"⚠ 遇到 {e.status_code} 錯誤: {e.message}")

                    # 嘗試切換到下一個 model
                    next_model = self.get_next_model()
                    if next_model is None:
                        print(f"✗ 所有 model 都已嘗試，放棄處理")
                        return None

                    current_model = next_model
                    print(f"⏳ 等待 3 秒後切換...")
                    time.sleep(3)  # 切換前等待，避免立即再次觸發 rate limit
                    continue
                else:
                    # 其他錯誤直接拋出
                    print(f"✗ API 錯誤 ({e.status_code}): {e.message}")
                    raise

            except Exception as e:
                # 其他例外直接拋出
                print(f"✗ 未預期的錯誤: {e}")
                raise

        # 安全退出：如果超過最大嘗試次數
        print(f"✗ 已達最大嘗試次數 ({max_attempts})，放棄處理")
        return None

    def merge_data(
        self, raw_items: List[Dict[str, Any]], metadata_items: List[MetadataExtraction]
    ) -> List[AnnouncementDoc]:
        """Merge raw items with extracted metadata (Pydantic objects)."""
        merged_docs = []

        # Create a lookup for metadata by ID (ID 是 id 或索引)
        metadata_by_id = {meta.id: meta for meta in metadata_items}

        for idx, raw in enumerate(raw_items):
            # 找出對應的 metadata (使用 id 或索引)
            lookup_id = raw.get("id") or str(idx)
            meta = metadata_by_id.get(lookup_id)

            if not meta:
                print(f"Warning: No metadata found for ID {lookup_id}, skipping.")
                continue

            # 使用原始的 id 或生成新的
            doc_id = raw.get("id") or str(uuid.uuid4())

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
                    id=doc_id,
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

    def process_batch(
        self, raw_batch: List[Dict[str, Any]], batch_index: int
    ) -> Optional[List[AnnouncementDoc]]:
        """
        Process a single batch through the ETL pipeline.

        Args:
            raw_batch: List of raw announcement documents
            batch_index: Index of the batch for logging purposes

        Returns:
            List of processed AnnouncementDoc objects if successful, None if error occurred
        """
        print(f"Processing batch {batch_index} ({len(raw_batch)} items)...")
        llm_input = None
        ids = []

        try:
            # 1. Validate batch
            if not raw_batch:
                print("Empty batch, skipping.")
                return []  # Empty is not an error

            # Extract ids for error tracking
            ids = [item.get("id") or str(idx) for idx, item in enumerate(raw_batch)]

            # Reset model index for new batch
            self.reset_model_index()

            # 2. Check SYSTEM_PROMPT
            if not SYSTEM_PROMPT:
                error_msg = "SYSTEM_PROMPT is empty in src/llm/metadata_prompts.py"
                print(f"WARNING: {error_msg}")
                self.error_handler.log_error(
                    batch_file=f"batch_{batch_index}",
                    ids=ids,
                    error_type="ConfigError",
                    error_message=error_msg,
                )
                return None

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
                    batch_file=f"batch_{batch_index}",
                    ids=ids,
                    error_type="LLMValidationError",
                    error_message=error_msg,
                    llm_input=llm_input,
                    llm_response=None,
                )
                return None

            # 5. Merge Data
            metadata_batch = batch_result.results
            docs = self.merge_data(raw_batch, metadata_batch)

            if len(docs) == 0:
                error_msg = (
                    f"Merge failed: No documents produced (expected {len(raw_batch)})"
                )
                print(f"✗ {error_msg}")
                self.error_handler.log_error(
                    batch_file=f"batch_{batch_index}",
                    ids=ids,
                    error_type="MergeError",
                    error_message=error_msg,
                    llm_input=llm_input,
                    llm_response=json.dumps(
                        [m.model_dump() for m in metadata_batch], ensure_ascii=False
                    ),
                )
                return None

            # 6. Rate limit protection
            time.sleep(1)
            print(f"✓ Batch {batch_index} processed successfully ({len(docs)} docs)")
            return docs

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"✗ {error_msg}")
            self.error_handler.log_error(
                batch_file=f"batch_{batch_index}",
                ids=ids,
                error_type="UnexpectedError",
                error_message=error_msg,
                llm_input=llm_input,
                llm_response=None,
            )
            return None
