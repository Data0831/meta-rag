"""
ETL Pipeline - Main Orchestrator

Coordinates batch processing, error handling, and file merging.
"""

import json
import os
import sys
import glob
from typing import List

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import local modules
from src.llm.client import LLMClient
from src.pipeline.error_handler import ErrorHandler
from src.pipeline.batch_processor import BatchProcessor


class ETLPipeline:
    """ETL Pipeline 主控制器"""

    def __init__(
        self,
        input_dir: str = "data/split",
        output_dir: str = "data/processed",
        log_dir: str = "data/process_log",
    ):
        self.input_dir = input_dir
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
        batch_files.sort(
            key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
        )

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

    def run(self, interactive: bool = True):
        """
        Run the pipeline on all files in data/split.

        Args:
            interactive: If True, ask user about retrying errors
        """
        files = glob.glob(os.path.join(self.input_dir, "*.json"))
        print(f"Found {len(files)} files in {self.input_dir}\n")

        # Process all files
        success_count = 0
        for file in files:
            if self.batch_processor.process_file(file):
                success_count += 1

        # Summary
        print("\n" + "=" * 60)
        print("ETL Pipeline 處理完成")
        print("=" * 60)
        print(f"成功: {success_count}/{len(files)} 批次")
        print(f"失敗: {len(self.error_handler.failed_batches)}/{len(files)} 批次")

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
            print("\n✓ 所有批次處理成功，無錯誤發生")
            # Only merge if no errors
            self.merge_processed_files()


def main():
    """主程式進入點"""
    pipeline = ETLPipeline()
    pipeline.run(interactive=True)

    # 如果有錯誤，處理用戶選擇
    if pipeline.error_handler.has_errors():
        print("\n請選擇如何處理失敗的批次:")
        print("1. 重試所有失敗的批次")
        print("2. 將錯誤寫入 errorlist.json 並結束")

        choice = input("\n請輸入選項 (1 或 2): ").strip()

        if choice == "1":
            pipeline.retry_failed_batches()

            # 重試後再次檢查
            if not pipeline.error_handler.has_errors():
                print("\n開始合併處理完成的檔案...")
                pipeline.merge_processed_files()
            else:
                print("\n重試後仍有錯誤，將錯誤寫入 errorlist.json")
                pipeline.error_handler.save_error_list()
        else:
            pipeline.error_handler.save_error_list()


if __name__ == "__main__":
    main()
