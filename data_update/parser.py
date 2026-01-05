import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

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

    def clean_content(self, content: str) -> str:
        """
        Clean the content by removing noise and keeping key information.

        Cleaning steps:
        1. Remove URLs (http/https)
        2. Remove Markdown links (keep anchor text)
        3. Remove template Markdown headers (#### 現已推出, etc.)
        4. Remove metadata fields (日期, 工作區, 受影響的群體)
        """
        if not content:
            return ""

        text = content

        # 1. Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # 2. Remove Markdown links but keep anchor text
        text = re.sub(r"\[(.*?)\]\([^)]*?\)", r"\1", text)

        # 3. Remove template Markdown headers (multiline mode)
        text = re.sub(
            r"^#{3,6}\s*(現已推出|即將到來的事項|提醒|後續步驟)\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )

        # 4. Remove metadata field lines
        text = re.sub(r"^\*\s*\*\*日期\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE)
        text = re.sub(
            r"^\*\s*\*\*工作區\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE
        )
        text = re.sub(
            r"^\*\s*\*\*受影響的群體\*\*[：:].*\r?\n?", "", text, flags=re.MULTILINE
        )

        # 5. Clean up excessive whitespace and newlines
        text = re.sub(r"\n{3,}", "\n\n", text)  # Replace 3+ newlines with 2
        text = text.strip()

        return text

    def _get_website_tag(self, filename: str) -> str:
        """
        Determine the website tag based on the filename.
        """
        if "partner_center" in filename:
            return "partner_center"
        if "m365_roadmap" in filename:
            return "m365_roadmap"
        if "windows_message_center" in filename:
            return "windows_message_center"
        if "powerbi_blog" in filename:
            return "powerbi_blog"
        if "azure_update" in filename:
            return "azure_update"
        if "msrc_blog" in filename:
            return "msrc_blog"
        return "general"

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

            # 根據檔名決定 website tag
            current_website_tag = self._get_website_tag(filename)

            for item in data:
                # Helper to check required fields
                if not all(
                    key in item for key in ["link", "year_month", "title", "content"]
                ):
                    # Skip items missing required fields
                    continue

                # Process Content
                raw_content = item["content"]

                # 1. Truncate if > 3000
                if len(raw_content) > 3000:
                    raw_content = raw_content[:3000]

                # 2. Clean content
                cleaned_content = self.clean_content(raw_content)

                # Extract Year from year_month (assuming YYYY-MM format)
                year_month = item["year_month"]
                year = year_month.split("-")[0] if "-" in year_month else year_month[:4]

                # Update existing item to preserve other keys
                item["year"] = year
                item["content"] = raw_content
                item["cleaned_content"] = cleaned_content
                item["website"] = current_website_tag

                aggregated_data.append(item)

        # Save aggregated data
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(aggregated_data, f, ensure_ascii=False, indent=4)
            logger.info(
                f"Successfully saved {len(aggregated_data)} items to {output_path}"
            )
        except Exception as e:
            logger.error(f"Error saving output file: {e}")


if __name__ == "__main__":
    FILES_TO_PROCESS = [
        "fetch_result/partner_center_announcements.json",
        "fetch_result/windows_message_center.json",
        "fetch_result/m365_roadmap.json",
        "fetch_result/powerbi_blog.json",
    ]
    OUTPUT_FILE = "data.json"

    parser = DataParser(files_to_process=FILES_TO_PROCESS, output_file=OUTPUT_FILE)
    parser.process_files()
