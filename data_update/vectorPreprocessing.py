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

    # --- Data Loading Helpers ---

    def _load_json(self, file_path: str, default_val=None) -> any:
        """Generic JSON loader with error handling."""
        if not os.path.exists(file_path):
            print_yellow(f"File not found: {file_path}")
            return default_val if default_val is not None else []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print_red(f"Error loading JSON from {file_path}: {e}")
            return default_val if default_val is not None else []

    def _parse_items_to_docs(self, data: List[dict]) -> List[AnnouncementDoc]:
        """Convert a list of dictionaries to AnnouncementDoc objects."""
        if not isinstance(data, list):
            print_red(f"Error: Expected a list of items, got {type(data)}")
            return []

        docs = []
        for i, item in enumerate(data):
            try:
                docs.append(AnnouncementDoc(**item))
            except Exception as e:
                print_red(f"Error parsing document at index {i}: {e}")
        return docs

    def load_processed_data(self) -> List[AnnouncementDoc]:
        """Public interface: Load and parse documents from the main data source."""
        data = self._load_json(self.data_json)
        return self._parse_items_to_docs(data)

    def load_remove_list(self) -> List[str]:
        """Public interface: Load ID list for removal."""
        return self._load_json(self.remove_json)

    # --- Core Pipeline logic ---

    def _display_error_report(self, failed_docs_info: List[dict]):
        """Prints a formatted table of documents that failed after all retries."""
        if not failed_docs_info:
            return

        print_red("\n" + "=" * 100)
        print_red(f"{'INDEX':<8} | {'ERROR':<30} | {'CONTENT SNIPPET':<100}")
        print_red("-" * 100)
        for info in failed_docs_info:
            idx = info.get("index", "N/A")
            orig_err = str(info.get("error", "Unknown")).replace("\n", " ")
            err = (orig_err[:27] + "...") if len(orig_err) > 27 else orig_err

            orig_content = info["doc"].cleaned_content.replace("\n", " ")
            content = (
                (orig_content[:47] + "...") if len(orig_content) > 47 else orig_content
            )
            print_red(f"{idx:<8} | {err:<30} | {content:<50}")
        print_red("=" * 100 + "\n")

    async def _handle_retry_logic(self, failed_docs_info: List[dict]) -> List[dict]:
        """Performs retries for documents that failed embedding generation."""
        if not failed_docs_info:
            return []

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
                # Remove specific punctuation and whitespace to try and recover
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

        return failed_docs_info

    async def _process_and_sync_embeddings(self, docs: List[AnnouncementDoc]):
        """Internal Pipeline: Batches docs, gets embeddings, and syncs to Meilisearch."""
        total = len(docs)
        failed_docs_info = []

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
                    meili_docs.append(transform_doc_for_meilisearch(doc, vector))
                else:
                    failed_docs_info.append(
                        {
                            "index": i + j,
                            "doc": doc,
                            "error": res.get("error", "Unknown error"),
                        }
                    )
                    print_yellow(
                        f"  ⚠ Failed embedding for index {i+j}, queued for retry."
                    )

            if meili_docs:
                print(
                    f"  Batch {i//self.vector_batch_size + 1}: Syncing {len(meili_docs)} docs to Meilisearch..."
                )
                self.adapter.upsert_documents(meili_docs)

            print(f"  Processed {min(i + self.vector_batch_size, total)}/{total}")

        # Final retry stage
        failed_docs_info = await self._handle_retry_logic(failed_docs_info)

        # Display final errors if any
        self._display_error_report(failed_docs_info)

    # --- Public API Methods ---

    def clear_all(self):
        """Reset the index."""
        print("\n--- Clearing Data ---")
        print(f"Clearing Meilisearch index '{self.index_name}'...")
        self.adapter.reset_index()
        print("✓ Meilisearch index cleared.")

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

        doc_ids = [doc.id for doc in docs]
        existing_docs = self.adapter.get_documents_by_ids(doc_ids)
        existing_ids = {doc["id"] for doc in existing_docs}
        new_docs = [doc for doc in docs if doc.id not in existing_ids]

        if not new_docs:
            print_yellow("No new documents to add (all already exist in Meilisearch).")
            return

        print(f"Found {len(new_docs)} new documents (out of {len(docs)})")
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
        """Triggered by RAG Sync System. Processes files and deletes them on success."""
        print("\n--- 🔗 Triggered by RAG Sync System ---")

        # 1. Delete Flow
        if delete_path and os.path.exists(delete_path):
            print(f"📉 Processing delete list: {delete_path}")
            ids_to_remove = self._load_json(delete_path)
            if ids_to_remove:
                try:
                    self.adapter.delete_documents_by_ids(ids_to_remove)
                    os.remove(delete_path)
                    print_green(
                        f"  ✓ Deleted {len(ids_to_remove)} docs and removed file."
                    )
                except Exception as e:
                    print_red(f"  ❌ Error deleting docs: {e}")
            else:
                os.remove(delete_path)
                print_yellow("  ⚠ Empty delete list, file removed.")

        # 2. Upsert Flow
        if upsert_path and os.path.exists(upsert_path):
            print(f"📈 Processing upsert list: {upsert_path}")
            raw_data = self._load_json(upsert_path)
            docs = self._parse_items_to_docs(raw_data)
            if docs:
                try:
                    await self._process_and_sync_embeddings(docs)
                    os.remove(upsert_path)
                    print_green(f"  ✓ Upserted {len(docs)} docs and removed file.")
                except Exception as e:
                    print_red(f"  ❌ Error upserting docs: {e}")
            else:
                os.remove(upsert_path)
                print_yellow("  ⚠ No valid docs found, file removed.")

    def run_dynamic_sync(self, upsert_path: str = None, delete_path: str = None):
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
        print_red(f"CONCURRENCY: {processor.max_concurrency}")
        print_red(f"BATCH SIZE: {processor.sub_batch_size}")
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
