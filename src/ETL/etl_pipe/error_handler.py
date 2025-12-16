"""
Error Handler Module

Handles error logging, tracking, and recovery for ETL pipeline.
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ErrorRecord:
    """記錄 ETL 處理錯誤的詳細資訊"""

    timestamp: str
    batch_file: str
    ids: List[str]  # 該批次中的所有 id
    error_type: str
    error_message: str
    llm_input: Optional[List[Dict[str, Any]]] = None
    llm_response: Optional[str] = None


class ErrorHandler:
    """管理 ETL Pipeline 的錯誤記錄與處理"""

    def __init__(
        self, log_dir: str = "data/process_log", output_dir: str = "data/processed"
    ):
        self.log_dir = log_dir
        self.output_dir = output_dir
        self.error_records: List[ErrorRecord] = []
        self.failed_batches: List[str] = []

        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)

    def log_error(
        self,
        batch_file: str,
        ids: List[str],
        error_type: str,
        error_message: str,
        llm_input: Optional[List[Dict[str, Any]]] = None,
        llm_response: Optional[str] = None,
    ):
        """記錄錯誤到 process_log"""
        timestamp = datetime.now().isoformat()

        error_record = ErrorRecord(
            timestamp=timestamp,
            batch_file=batch_file,
            ids=ids,
            error_type=error_type,
            error_message=error_message,
            llm_input=llm_input,
            llm_response=llm_response,
        )

        self.error_records.append(error_record)
        self.failed_batches.append(batch_file)

        # 寫入 process_log 檔案
        log_filename = f"{os.path.basename(batch_file)}.error.json"
        log_path = os.path.join(self.log_dir, log_filename)

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(asdict(error_record), f, ensure_ascii=False, indent=2)

        print(f"⚠ 錯誤已記錄至 {log_path}")

    def display_error_summary(self):
        """顯示錯誤摘要"""
        if not self.error_records:
            return

        print("\n" + "=" * 60)
        print("⚠ ETL 處理過程中發生錯誤")
        print("=" * 60)

        # 顯示錯誤摘要
        for i, error in enumerate(self.error_records, 1):
            print(f"\n錯誤 #{i}:")
            print(f"  檔案: {error.batch_file}")
            print(f"  類型: {error.error_type}")
            print(f"  訊息: {error.error_message}")
            print(f"  受影響的 id 數量: {len(error.ids)}")
            print(
                f"  詳細日誌: {self.log_dir}/{os.path.basename(error.batch_file)}.error.json"
            )

        # 收集所有失敗的 id
        all_failed_ids = []
        for error in self.error_records:
            all_failed_ids.extend(error.ids)

        print(f"\n總計失敗的項目數: {len(all_failed_ids)}")
        print(f"失敗的批次檔案數: {len(self.failed_batches)}")

    def save_error_list(self):
        """將失敗的 id 寫入 errorlist.json"""
        all_failed_ids = []
        for error in self.error_records:
            all_failed_ids.extend(error.ids)

        error_list_path = os.path.join(self.output_dir, "../errorlist.json")
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "total_failed_items": len(all_failed_ids),
            "total_failed_batches": len(self.failed_batches),
            "failed_ids": all_failed_ids,
            "failed_batch_files": self.failed_batches,
            "error_summary": [
                {
                    "batch_file": error.batch_file,
                    "error_type": error.error_type,
                    "error_message": error.error_message,
                    "affected_count": len(error.ids),
                }
                for error in self.error_records
            ],
        }

        with open(error_list_path, "w", encoding="utf-8") as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 錯誤清單已寫入: {error_list_path}")

    def clear_errors(self):
        """清空錯誤記錄（用於重試）"""
        self.error_records.clear()
        self.failed_batches.clear()

    def has_errors(self) -> bool:
        """檢查是否有錯誤記錄"""
        return len(self.error_records) > 0
