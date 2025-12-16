"""
ETL Pipeline - Main Orchestrator
Coordinates batch processing, error handling, and file merging.
"""

import json
import os
import sys
import glob
from pathlib import Path
from typing import List

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
    PROCESSED_DIR,
    LOG_DIR,
    PROCESSED_OUTPUT,
    ERROR_LIST_OUTPUT,
)


class ETLPipeline:
    """ETL Pipeline 主控制器"""

    def __init__(
        self,
        input_file: str = PAGE_JSON,
        output_dir: str = PROCESSED_DIR,
        log_dir: str = LOG_DIR,
    ):
        self.input_file = input_file
        self.output_dir = output_dir
        # Initialize components
        self.llm_client = LLMClient()
        self.error_handler = ErrorHandler(log_dir=log_dir, output_dir=output_dir)
        self.batch_processor = BatchProcessor(
            llm_client=self.llm_client,
            error_handler=self.error_handler,
            output_dir=output_dir,
        )
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

    def clean_processed_files(self):
        """Clean all processed JSON files in the output directory."""
        for file in Path(self.output_dir).glob("*.json"):
            file.unlink()
            print(f"Deleted {file}")

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
        print(f"Successfully parsed {len(docs)} announcement documents.")
        return docs

    def genMetaData(self, interactive: bool = True):
        """
        Run the pipeline on the input file (page.json).
        Args:
            interactive: If True, ask user about retrying errors
        """
        print(f"Processing file: {self.input_file}\n")

        # Process the input file
        success = self.batch_processor.process_file(self.input_file)

        # Summary
        print("\n" + "=" * 60)
        print("ETL Pipeline 處理完成")
        print("=" * 60)
        print(f"成功: {1 if success else 0}/1 檔案")
        print(f"失敗: {0 if success else 1}/1 檔案")

        # Handle errors if any
        if self.error_handler.has_errors():
            self.error_handler.display_error_summary()
            if interactive:
                # 返回讓 main 處理用戶交互
                return
            else:
                # Non-interactive mode: 直接寫入 errorlist.json
                self.error_handler.save_error_list()
        else:
            print("\n✓ 處理成功，無錯誤發生")
            # Only merge if no errors
            self.merge_processed_files()

    def merge_processed_files(self, output_filename: str = "processed.json"):
        """Merge all processed separate JSON files into one."""
        json_files = glob.glob(os.path.join(self.output_dir, "*.json"))
        # Filter only numeric filenames to ensure we are merging the batches
        # and not merging the output file itself if it exists.
        batch_files = []
        for f in json_files:
            basename = os.path.basename(f)
            if basename == output_filename or basename == "errorlist.json":
                continue
            # Check if it looks like a batch file (digits.json)
            name_part = os.path.splitext(basename)[0]
            if name_part.isdigit():
                batch_files.append(f)
        # Sort numerically
        batch_files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
        all_docs = []
        print(f"Found {len(batch_files)} batch files to merge.")
        for file_path in batch_files:
            print(f"Merging {file_path}...")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                    if isinstance(docs, list):
                        all_docs.extend(docs)
                    else:
                        print(f"Warning: {file_path} is not a list. Skipping.")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        output_path = os.path.join(self.output_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_docs, f, ensure_ascii=False, indent=2)
        print(f"Successfully merged {len(all_docs)} documents into {output_path}")

    def retry_failed_batches(self):
        """重試所有失敗的批次"""
        if not self.error_handler.failed_batches:
            print("沒有需要重試的批次")
            return
        print("\n" + "=" * 60)
        print("開始重試失敗的批次...")
        print("=" * 60)
        # 複製失敗列表（避免在迭代時修改）
        batches_to_retry = self.error_handler.failed_batches.copy()
        # 清空錯誤記錄
        self.error_handler.clear_errors()
        for file_path in batches_to_retry:
            print(f"\n重試: {file_path}")
            self.batch_processor.process_file(file_path)
        # 檢查重試後是否還有錯誤
        if self.error_handler.has_errors():
            print("\n⚠ 重試後仍有部分批次失敗")
            self.error_handler.display_error_summary()
        else:
            print("\n✓ 所有批次重試成功!")
