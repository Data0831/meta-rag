import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
import markdown
from bs4 import BeautifulSoup
import tiktoken

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataParser:
    """
    Parser for processing crawled Microsoft announcement data.
    """

    def __init__(self, files_to_process: List[str], output_file: str):
        self.files_to_process = files_to_process
        self.output_file = output_file
        self.base_dir = Path(__file__).parent
        try:
            self.enc = tiktoken.encoding_for_model("gpt-4o-mini")
        except Exception:
            self.enc = tiktoken.get_encoding("cl100k_base")

    def clean_content(self, content: str) -> str:
        if not content:
            return ""

        text = content

        # 1. Remove URLs (preserve original functionality)
        text = re.sub(r"https?://\S+", "", text)

        # 2. Remove metadata field lines before markdown conversion
        text = re.sub(r"^\*\s*\*\*日期\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE)
        text = re.sub(
            r"^\*\s*\*\*工作區\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE
        )
        text = re.sub(
            r"^\*\s*\*\*受影響的群體\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE
        )

        # 3. Remove template Markdown headers
        text = re.sub(
            r"^#{3,6}\s*(現已推出|即將到來的事項|提醒|後續步驟)\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )

        # 4. Remove images ![alt](url) before markdown conversion
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

        # 5. Remove horizontal lines
        text = re.sub(r"^(\*{3,}|-{3,}|_{3,})\s*$", "", text, flags=re.MULTILINE)

        # 6. Convert markdown to HTML, then extract plain text
        html = markdown.markdown(text, extensions=["tables"])
        soup = BeautifulSoup(html, "html.parser")
        plain_text = soup.get_text()

        # 7. Clean up whitespace: replace multiple spaces with single space
        plain_text = re.sub(r" +", " ", plain_text)

        # 8. Replace newlines with space (preserve semantic separation)
        plain_text = re.sub(r"\n+", " ", plain_text)

        # 9. Final cleanup: remove leading/trailing whitespace
        plain_text = plain_text.strip()

        return plain_text

    def process_files(self):
        """
        Process the files defined in self.files_to_process.
        """
        output_path = self.base_dir / self.output_file
        aggregated_data = []

        logger.info(f"Processing files: {self.files_to_process}")

        for filename in self.files_to_process:
            file_path = self.base_dir / filename
            if not file_path.exists():
                logger.warning(f"File {filename} not found. Skipping.")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {filename}: {e}")
                continue

            # Ensure data is a list
            if not isinstance(data, list):
                logger.warning(f"Data in {filename} is not a list. Skipping.")
                continue

            for item in data:
                # Helper to check required fields
                if not all(
                    key in item for key in ["link", "year_month", "title", "content"]
                ):
                    # Skip items missing required fields
                    continue

                # Use process_item to clean and supplement fields
                processed_item = self.process_item(item)
                aggregated_data.append(processed_item)

        # Save aggregated data
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(aggregated_data, f, ensure_ascii=False, indent=4)
            logger.info(
                f"Successfully saved {len(aggregated_data)} items to {output_path}"
            )
        except Exception as e:
            logger.error(f"Error saving output file: {e}")

    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """供外部呼叫：清洗單筆資料並補齊欄位"""
        raw_content = item.get("content", "")

        # # 1. 截斷
        # if len(raw_content) > 3000:
        #     raw_content = raw_content[:3000]

        # 2. 清洗 (呼叫既有的 clean_content)
        cleaned_content = self.clean_content(raw_content)

        # 3. 處理年份
        year_month = item.get("year_month", "")
        year = year_month.split("-")[0] if "-" in year_month else year_month[:4]

        # 更新欄位
        item["year"] = year
        item["content"] = raw_content
        item["cleaned_content"] = json.dumps(cleaned_content, ensure_ascii=False)
        item["token"] = len(self.enc.encode(raw_content))
        item["update_time"] = datetime.now().strftime("%Y-%m-%d-%H-%M")

        return item


if __name__ == "__main__":
    FILES_TO_PROCESS = [
        # "fetch_result/partner_center_announcements.json",
        # "fetch_result/windows_message_center.json",
        # "fetch_result/m365_roadmap.json",
        # "fetch_result/powerbi_blog.json",
        # "sync_output/data.json"
        "data.json"
    ]
    OUTPUT_FILE = "data.json"

    parser = DataParser(files_to_process=FILES_TO_PROCESS, output_file=OUTPUT_FILE)
    parser.process_files()
