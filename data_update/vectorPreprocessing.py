import os
import sys
import json
import asyncio
from typing import List, Optional
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import (
    DATA_JSON,
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
    MEILISEARCH_TIMEOUT,
)
from src.schema.schemas import AnnouncementDoc
from src.database.db_adapter_meili import (
    MeiliAdapter,
    transform_doc_for_meilisearch,
    transform_doc_metadata_only,
)
from src.database.vector_utils import get_embedding, get_embeddings_batch
from src.database.vector_config import RTX_4050_6G, CPU_16C_64G, LOW_END_2C4T
from src.tool.ANSI import print_red, print_green, print_yellow

load_dotenv()


class VectorPreProcessor:
    def __init__(
        self,
        host: str = MEILISEARCH_HOST,
        api_key: str = MEILISEARCH_API_KEY,
        index_name: str = MEILISEARCH_INDEX,
        data_json: str = DATA_JSON,
        remove_json: Optional[str] = None,
        metadata_batch_size: int = 100,
        vector_batch_size: int = 200,
        sub_batch_size: int = 10,
        max_concurrency: int = 10,
        force_gpu: bool = True,
        timeout: int = MEILISEARCH_TIMEOUT,
        final_retry_count: int = 3,
    ):
        self.host = host
        self.api_key = api_key
        # Use provided index_name or fallback to config
        self.index_name = index_name or "announcements"
        self.data_json = data_json
        self.remove_json = remove_json or os.path.join(
            os.path.dirname(__file__), "remove.json"
        )
        self.metadata_batch_size = metadata_batch_size
        self.vector_batch_size = vector_batch_size
        self.sub_batch_size = sub_batch_size
        self.max_concurrency = max_concurrency
        self.force_gpu = force_gpu
        self.final_retry_count = final_retry_count

        self.adapter = MeiliAdapter(
            host=self.host,
            api_key=self.api_key,
            collection_name=self.index_name,
            timeout=timeout,
        )

    def load_processed_data(self) -> List[AnnouncementDoc]:
        if not os.path.exists(self.data_json):
            print(f"File not found: {self.data_json}")
            return []

        try:
            with open(self.data_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return []

        docs = []
        if not isinstance(data, list):
            print(f"Error: Expected a list, got {type(data)}")
            return []

        for i, item in enumerate(data):
            try:
                docs.append(AnnouncementDoc(**item))
            except Exception as e:
                print(f"Error parsing document at index {i}: {e}")
        return docs

    def load_remove_list(self) -> List[str]:
        if not os.path.exists(self.remove_json):
            print_yellow(f"File not found: {self.remove_json}")
            return []
        try:
            with open(self.remove_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                print_red(
                    f"Error: Expected a list in {self.remove_json}, got {type(data)}"
                )
                return []
            return data
        except json.JSONDecodeError as e:
            print_red(f"Error decoding JSON from {self.remove_json}: {e}")
            return []

    def clear_all(self):
        print("\n--- Clearing Data ---")
        print(f"Clearing Meilisearch index '{self.index_name}'...")
        self.adapter.reset_index()
        print("✓ Meilisearch index cleared.")

    async def _process_and_sync_embeddings(self, docs: List[AnnouncementDoc]):
        """Helper to process a list of docs in batches, generating embeddings and syncing to Meili."""
        total = len(docs)
        failed_docs_info = (
            []
        )  # To collect failures: {'index': i, 'doc': doc, 'error': err}
        print(
            f"Generating embeddings and transforming documents (Batch size: {self.vector_batch_size})..."
        )

        for i in range(0, total, self.vector_batch_size):
            batch_docs = docs[i : i + self.vector_batch_size]
            texts = [doc.cleaned_content for doc in batch_docs]

            print(
                f"  Batch {i//self.vector_batch_size + 1}: Generating embeddings for {len(texts)} docs..."
            )

            embedding_results = await get_embeddings_batch(
                texts,
                sub_batch_size=self.sub_batch_size,
                max_concurrency=self.max_concurrency,
                force_gpu=self.force_gpu,
            )

            meili_docs = []
            for j, res in enumerate(embedding_results):
                doc = batch_docs[j]
                if res.get("status") == "success":
                    vector = res.get("result")
                    meili_doc = transform_doc_for_meilisearch(doc, vector)
                    meili_docs.append(meili_doc)
                else:
                    error_msg = res.get("error", "Unknown error")
                    # Collect for final retry
                    failed_docs_info.append(
                        {"index": i + j, "doc": doc, "error": error_msg}
                    )
                    print_yellow(
                        f"  ⚠ Failed to generate embedding for index {i+j}, added to final retry list."
                    )

            if meili_docs:
                print(
                    f"  Batch {i//self.vector_batch_size + 1}: Syncing {len(meili_docs)} docs to Meilisearch..."
                )
                self.adapter.upsert_documents(meili_docs)

            print(f"  Processed {min(i + self.vector_batch_size, total)}/{total}")

        # --- Final Retry Stage for Failed Items ---
        if failed_docs_info:
            print_yellow(
                f"\n--- Final Retry Stage: Retrying {len(failed_docs_info)} failed items (Max {self.final_retry_count} retries) ---"
            )

            for attempt in range(1, self.final_retry_count + 1):
                if not failed_docs_info:
                    break

                print(f"  Final Retry Attempt {attempt}/{self.final_retry_count}...")

                still_failed = []
                meili_docs = []

                for info in failed_docs_info:
                    # 移除內容中所有的特定標點符號與空白，以便重新嘗試 Embedding
                    chars_to_remove = ",. '’\"，。"
                    retry_content = info["doc"].cleaned_content.translate(
                        str.maketrans("", "", chars_to_remove)
                    )
                    res = get_embedding(retry_content)
                    if res.get("status") == "success":
                        vector = res.get("result")
                        meili_doc = transform_doc_for_meilisearch(info["doc"], vector)
                        meili_docs.append(meili_doc)
                    else:
                        info["error"] = res.get("error", "Unknown error")
                        still_failed.append(info)

                if meili_docs:
                    print_green(
                        f"    ✓ Recovered {len(meili_docs)} items in attempt {attempt}"
                    )
                    self.adapter.upsert_documents(meili_docs)

                failed_docs_info = still_failed

        # --- Final Error Table Display ---
        if failed_docs_info:
            print_red("\n" + "=" * 100)
            print_red(f"{'INDEX':<8} | {'ERROR':<30} | {'CONTENT SNIPPET':<100}")
            print_red("-" * 100)
            for info in failed_docs_info:
                idx = info["index"]
                orig_err = str(info["error"]).replace("\n", " ")
                err = (orig_err[:27] + "...") if len(orig_err) > 27 else orig_err

                orig_content = info["doc"].cleaned_content.replace("\n", " ")
                content = (
                    (orig_content[:47] + "...")
                    if len(orig_content) > 47
                    else orig_content
                )

                print_red(f"{idx:<8} | {err:<30} | {content:<50}")
            print_red("=" * 100 + "\n")

    async def async_process_and_write(self):
        print("\n--- Processing and Writing Data (Async Pipeline) ---")
        docs = self.load_processed_data()
        if not docs:
            print("No documents to process.")
            return

        print(f"Loaded {len(docs)} documents.")
        await self._process_and_sync_embeddings(docs)

        print("\n--- Index Statistics ---")
        stats = self.adapter.get_stats()
        if stats:
            print(f"  Total documents: {stats.get('numberOfDocuments', 'N/A')}")
            print(
                f"  Index status: {stats.get('isIndexing', False) and 'Indexing...' or 'Ready'}"
            )
        print("\n✓ Done.")

    def process_and_write(self):
        asyncio.run(self.async_process_and_write())

    def delete_by_ids(self):
        print("\n--- Deleting Documents by IDs ---")
        ids_to_remove = self.load_remove_list()
        if not ids_to_remove:
            print_yellow("No IDs to remove.")
            return
        print(f"Loaded {len(ids_to_remove)} IDs from {self.remove_json}")
        result = self.adapter.delete_documents_by_ids(ids_to_remove)
        deleted_docs = result.get("deleted", [])
        not_found_ids = result.get("not_found", [])
        if deleted_docs:
            print_green(f"\n✓ Successfully deleted {len(deleted_docs)} documents:")
            for doc in deleted_docs:
                print_green(f"  - ID: {doc['id']}, Title: {doc.get('title', 'N/A')}")
        if not_found_ids:
            print_yellow(f"\n⚠ {len(not_found_ids)} IDs not found in Meilisearch:")
            for doc_id in not_found_ids:
                print_yellow(f"  - ID: {doc_id}")

    async def async_add_new_documents(self):
        print("\n--- Adding New Documents (Async Pipeline) ---")
        docs = self.load_processed_data()
        if not docs:
            print_yellow("No documents to process.")
            return
        print(f"Loaded {len(docs)} documents from {self.data_json}")

        doc_ids = [doc.id for doc in docs]
        existing_docs = self.adapter.get_documents_by_ids(doc_ids)
        existing_ids = {doc["id"] for doc in existing_docs}
        new_docs = [doc for doc in docs if doc.id not in existing_ids]

        if not new_docs:
            print_yellow("No new documents to add (all already exist in Meilisearch).")
            return

        print(f"Found {len(new_docs)} new documents to add")
        if len(docs) - len(new_docs) > 0:
            print_yellow(f"Skipping {len(docs) - len(new_docs)} existing documents")

        await self._process_and_sync_embeddings(new_docs)
        print_green("\n✓ Successfully added documents.")

    def add_new_documents(self):
        asyncio.run(self.async_add_new_documents())

    def auto_sync(self):
        print("\n=== Auto Sync: Delete + Add ===")
        self.delete_by_ids()
        self.add_new_documents()
        print("\n✓ Auto sync completed.")

    def update_metadata_by_id(self):
        print("\n--- Updating Document Metadata by IDs (No Embedding change) ---")
        docs = self.load_processed_data()
        if not docs:
            print_yellow("No documents to process.")
            return
        print(f"Loaded {len(docs)} documents from {self.data_json}")

        meili_docs = []
        for i, doc in enumerate(docs):
            meili_doc = transform_doc_metadata_only(doc)
            meili_docs.append(meili_doc)

            if i == 0:
                print_yellow("\n[DEBUG] First document to be updated:")
                print_yellow(json.dumps(meili_doc, indent=2, ensure_ascii=False))

            if len(meili_docs) >= self.metadata_batch_size:
                print(f"  Updating batch of {len(meili_docs)} documents...")
                self.adapter.update_documents(meili_docs)
                meili_docs = []

        if meili_docs:
            print(f"  Updating final batch of {len(meili_docs)} documents...")
            self.adapter.update_documents(meili_docs)

        print_green("\n✓ Metadata update completed.")

    async def async_sync_from_files(
        self, upsert_path: str = None, delete_path: str = None
    ):
        """外部自動化介面：根據傳入的檔案路徑執行資料庫同步，成功後刪除原始檔案"""
        print("\n--- 🔗 Triggered by RAG Sync System ---")

        # 1. 執行刪除 (Delete Flow)
        if delete_path and os.path.exists(delete_path):
            print(f"📉 Processing delete list: {delete_path}")
            try:
                with open(delete_path, "r", encoding="utf-8") as f:
                    ids_to_remove = json.load(f)

                if ids_to_remove:
                    # 呼叫既有的 adapter 刪除功能
                    self.adapter.delete_documents_by_ids(ids_to_remove)
                    print_green(f"  ✓ Deleted {len(ids_to_remove)} docs.")

                    # 【新增】確認刪除動作成功沒報錯，才刪除實體檔案
                    f.close()  # 確保檔案釋放
                    os.remove(delete_path)
                    print_green(f"  🗑️  File removed: {delete_path}")
                else:
                    # 檔案是空的或是空List，也視為處理完畢，刪除之
                    print_yellow("  ⚠ Empty delete list, removing file.")
                    os.remove(delete_path)

            except Exception as e:
                print_red(f"  ❌ Error processing delete file: {e}")
                # 發生錯誤時，不執行 os.remove，檔案保留

        # 2. 執行新增/更新 (Upsert Flow)
        if upsert_path and os.path.exists(upsert_path):
            print(f"📈 Processing upsert list: {upsert_path}")
            try:
                with open(upsert_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                docs = []
                for item in data:
                    try:
                        # 轉換為 AnnouncementDoc 物件
                        docs.append(AnnouncementDoc(**item))
                    except Exception as e:
                        print_red(f"  ⚠ Skipped invalid doc: {e}")

                if docs:
                    # 呼叫既有的 Embedding 處理流程
                    await self._process_and_sync_embeddings(docs)
                    print_green(f"  ✓ Upserted {len(docs)} docs.")

                    # 【新增】確認 Embedding 與 Upsert 成功，才刪除實體檔案
                    f.close()  # 確保檔案釋放
                    os.remove(upsert_path)
                    print_green(f"  🗑️  File removed: {upsert_path}")
                else:
                    # 檔案內容無效，視為處理完畢，刪除之以免卡住
                    print_yellow("  ⚠ No valid docs found, removing file.")
                    os.remove(upsert_path)

            except Exception as e:
                print_red(f"  ❌ Error processing upsert file: {e}")
                # 發生錯誤時，不執行 os.remove，檔案保留

    def run_dynamic_sync(self, upsert_path: str = None, delete_path: str = None):
        """同步執行入口 (Wrapper)"""
        asyncio.run(self.async_sync_from_files(upsert_path, delete_path))


def main():
    print("=== Select Hardware Profile ===")
    print("1. RTX 4050 6GB VRAM")
    print("2. 16 Core CPU + 64GB RAM")
    print("3. LOW END 2C4T + 4GB RAM")
    hw_choice = input("Enter choice (1-3, default 1): ").strip()

    hw_config = RTX_4050_6G
    hw_name = "RTX 4050 6GB VRAM"
    if hw_choice == "2":
        hw_config = CPU_16C_64G
        hw_name = "16 Core CPU + 64GB RAM"
    elif hw_choice == "3":
        hw_config = LOW_END_2C4T
        hw_name = "LOW END 2C4T + 4GB RAM"

    processor = VectorPreProcessor(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        index_name=MEILISEARCH_INDEX,
        # index_name="announcements_test",
        data_json=DATA_JSON,
        metadata_batch_size=100,
        vector_batch_size=200,
        **hw_config,
    )

    while True:
        print("\n" + "=" * 40)
        print_red(f"HARDWARE PROFILE: {hw_name}")
        print_red(f"MEILISEARCH HOST: {os.getenv('MEILISEARCH_HOST', 'unknown')}")
        print_red(f"MEILISEARCH INDEX: {processor.index_name}")
        print_red(f"OLLAMA HOST: {os.getenv('OLLAMA_HOST', 'unknown')}")
        print("=" * 40)

        choice = (
            str(
                input(
                    """
        1. Clear Meilisearch index
        2. Process and Write (Load data.json -> Embed -> Write to Meilisearch)
        3. Auto Sync (Delete from remove.json -> Add new from data.json)
        4. Update Metadata by ID (Load data.json -> Partial Update -> No Embed)
        Q. Quit

        Enter your choice (1, 2, 3, 4, or Q): """
                )
            )
            .strip()
            .upper()
        )
        if choice in ["1", "2", "3", "4"]:
            confirm = (
                input(f"Confirm executing Option [{choice}]? (y/N): ").strip().lower()
            )
            if confirm != "y":
                print_yellow("Action cancelled by user.")
                continue

        if choice == "1":
            processor.clear_all()
        elif choice == "2":
            processor.process_and_write()
        elif choice == "3":
            processor.auto_sync()
        elif choice == "4":
            processor.update_metadata_by_id()
        elif choice == "Q":
            print("Exiting...")
            return
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
