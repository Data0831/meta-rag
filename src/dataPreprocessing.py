import os
import sys

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ETL.etl_pipe.etl import ETLPipeline

etl_pipeline = ETLPipeline()


def parse_json_data():
    etl_pipeline.parse_json_data()


def etl_clean():
    etl_pipeline.clean()


def etl_genMetaData():
    etl_pipeline.genMetaData(interactive=True)


def etl_retry_errorlist():
    etl_pipeline.genMetaData(interactive=True)


def main():
    while True:
        choice = (
            str(
                input(
                    """
        0. parse_json_data (解析原始 json)
        1. 清除 processed (如果需要全部重新處理)
        2. etl genMetaData (送給 LLM 處理)
        3. retry (保留上次的 processed，重新處理失敗的批次)
        Q. quit
        input your choice like 1 or Q:
        """
                )
            )
            .strip()
            .upper()
        )
        if choice == "0":
            parse_json_data()
        elif choice == "1":
            etl_clean()
        elif choice == "2":
            etl_genMetaData()
        elif choice == "3":
            etl_retry_errorlist()
        elif choice == "Q":
            return
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
