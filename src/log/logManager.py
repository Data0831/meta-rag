import os
import json
import datetime
from typing import Any, Dict
from src.config import LOG_BASE_DIR
from src.tool.ANSI import print_red


class LogManager:
    LOG_TYPES = {
        "client": "client",
        "search": "search",
        "chat": "chat",
        "feedback": "feedback"
    }

    @staticmethod
    def _ensure_log_dir(log_type: str) -> str:
        log_dir = os.path.join(LOG_BASE_DIR, log_type)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        return log_dir

    @staticmethod
    def _get_log_file_path(log_type: str) -> str:
        log_dir = LogManager._ensure_log_dir(log_type)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H")
        return os.path.join(log_dir, f"log_{timestamp}.json")

    @staticmethod
    def _write_log(log_type: str, log_entry: Dict[str, Any]):
        try:
            log_file = LogManager._get_log_file_path(log_type)
            logs = []

            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                        if not isinstance(logs, list):
                            logs = []
                except:
                    logs = []

            logs.append(log_entry)

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print_red(f"Warning: Failed to write {log_type} log: {e}")

    @staticmethod
    def log_client(
        messages: list,
        response_content: str,
        temperature: float,
        response_format: dict,
        model: str
    ):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": model,
            "temperature": temperature,
            "messages": messages,
            "response_format": response_format,
            "response": response_content,
        }
        LogManager._write_log("client", log_entry)

    @staticmethod
    def log_search(ip: str, headers: dict, request_data: dict, response_data: Any):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "endpoint": "/api/search",
            "ip": ip,
            "headers": headers,
            "request": request_data,
            "response": response_data,
        }
        LogManager._write_log("search", log_entry)

    @staticmethod
    def log_chat(ip: str, headers: dict, request_data: dict, response_data: Any):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "endpoint": "/api/chat",
            "ip": ip,
            "headers": headers,
            "request": request_data,
            "response": response_data,
        }
        LogManager._write_log("chat", log_entry)

    @staticmethod
    def log_feedback(ip: str, headers: dict, feedback_data: dict):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "endpoint": "/api/feedback",
            "ip": ip,
            "headers": headers,
            "feedback_type": feedback_data.get("feedback_type"),
            "query": feedback_data.get("query"),
            "search_params": feedback_data.get("search_params", {}),
        }
        LogManager._write_log("feedback", log_entry)
