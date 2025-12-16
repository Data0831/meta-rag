import os
import sys

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ETL.etl_pipe.etl import ETLPipeline


def etl_pipe():
    pipeline = ETLPipeline()
    pipeline.genMetaData(interactive=True)
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


def etl_retry_errorlist():
    """從 errorlist.json 讀取失敗的批次並重試"""
    import json

    ERROR_LIST_PATH = "data/errorlist.json"
    # 檢查 errorlist.json 是否存在
    if not os.path.exists(ERROR_LIST_PATH):
        print(f"Error: {ERROR_LIST_PATH} not found.")
        print("請先執行 ETL Pipeline 並產生 errorlist.json")
        return
    # 讀取 errorlist.json
    try:
        with open(ERROR_LIST_PATH, "r", encoding="utf-8") as f:
            error_data = json.load(f)
    except Exception as e:
        print(f"Error reading {ERROR_LIST_PATH}: {e}")
        return
    failed_batch_files = error_data.get("failed_batch_files", [])
    if not failed_batch_files:
        print("沒有需要重試的批次檔案")
        return
    print("\n" + "=" * 60)
    print(f"發現 {len(failed_batch_files)} 個失敗的批次需要重試")
    print("=" * 60)
    for batch_file in failed_batch_files:
        print(f"  - {batch_file}")
    # 詢問用戶是否繼續
    choice = input("\n是否繼續重試? (Y/N): ").strip().upper()
    if choice != "Y":
        print("取消重試")
        return
    # 創建 Pipeline 並重試
    pipeline = ETLPipeline()
    print("\n開始重試失敗的批次...")
    success_count = 0
    for batch_file in failed_batch_files:
        print(f"\n重試: {batch_file}")
        if pipeline.batch_processor.process_file(batch_file):
            success_count += 1
    # 顯示結果
    print("\n" + "=" * 60)
    print("重試完成")
    print("=" * 60)
    print(f"成功: {success_count}/{len(failed_batch_files)} 批次")
    print(
        f"失敗: {len(pipeline.error_handler.failed_batches)}/{len(failed_batch_files)} 批次"
    )
    # 處理結果
    if pipeline.error_handler.has_errors():
        print("\n⚠ 重試後仍有部分批次失敗")
        pipeline.error_handler.display_error_summary()
        print("\n請選擇:")
        print("1. 更新 errorlist.json (只保留仍然失敗的批次)")
        print("2. 不更新，保留原 errorlist.json")
        choice = input("\n請輸入選項 (1 或 2): ").strip()
        if choice == "1":
            pipeline.error_handler.save_error_list()
            print("已更新 errorlist.json")
    else:
        print("\n✓ 所有批次重試成功!")
        # 刪除 errorlist.json
        try:
            os.remove(ERROR_LIST_PATH)
            print(f"已刪除 {ERROR_LIST_PATH}")
        except Exception as e:
            print(f"Warning: 無法刪除 {ERROR_LIST_PATH}: {e}")
        # 合併處理完成的檔案
        print("\n開始合併處理完成的檔案...")
        pipeline.merge_processed_files()


def main():
    while True:
        choice = (
            str(
                input(
                    """
        1. split json
        2. etl pipe
        3. retry errorlist
        Q. quit
        input your choice like 1 or Q:
        """
                )
            )
            .strip()
            .upper()
        )
        if choice == "1":
            # split_json()
            pass
        elif choice == "2":
            etl_pipe()
        elif choice == "3":
            etl_retry_errorlist()
        elif choice == "Q":
            return
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
