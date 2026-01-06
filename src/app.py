import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    Response,
    stream_with_context,
)
import os
import json
from dotenv import load_dotenv
from typing import Dict, Any

from src.database.db_adapter_meili import MeiliAdapter
from src.agents.srhSumAgent import SrhSumAgent
from src.config import (
    APP_VERSION,
    ADMIN_TOKEN,
    ANNOUNCEMENT_JSON,
    DATE_RANGE_MIN,
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    SCORE_PASS_THRESHOLD,
    DEFAULT_SEMANTIC_RATIO,
    ENABLE_LLM,
    MANUAL_SEMANTIC_RATIO,
    ENABLE_KEYWORD_WEIGHT_RERANK,
    MAX_SEARCH_INPUT_LENGTH,
    MAX_CHAT_INPUT_LENGTH,
    WEBSITE_JSON,
    AVAILABLE_SOURCES,
    MEILISEARCH_TIMEOUT,
)
from src.tool.ANSI import print_red
from src.services.rag_service import RAGService
from src.log.logManager import LogManager

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)


def get_meili_adapter() -> MeiliAdapter:
    """Get Meilisearch adapter instance"""
    return MeiliAdapter(
        host=MEILISEARCH_HOST,
        api_key=MEILISEARCH_API_KEY,
        collection_name=MEILISEARCH_INDEX,
        timeout=MEILISEARCH_TIMEOUT,
    )


# ============================================================================
# Page Routes
# ============================================================================


@app.route("/")
def index():
    """Main page"""
    print("Rendering index page")
    return render_template("index.html")


# ============================================================================
# API Routes
# ============================================================================


@app.route("/api/config")
def get_config():
    """
    Get application configuration for frontend

    Returns:
        JSON response with config values
    """
    from datetime import datetime

    announcements = []
    websites = []

    announcement_path = os.path.join(str(project_root), ANNOUNCEMENT_JSON)
    website_path = os.path.join(str(project_root), WEBSITE_JSON)

    try:
        if os.path.exists(announcement_path):
            with open(announcement_path, "r", encoding="utf-8") as f:
                announcements = json.load(f)
    except Exception as e:
        print_red(f"Failed to load announcement.json: {e}")

    try:
        if os.path.exists(website_path):
            with open(website_path, "r", encoding="utf-8") as f:
                websites = json.load(f)
    except Exception as e:
        print_red(f"Failed to load website.json: {e}")

    date_range_max = datetime.now().strftime("%Y-%m")

    return jsonify(
        {
            "version": APP_VERSION,
            "default_limit": DEFAULT_SEARCH_LIMIT,
            "max_limit": MAX_SEARCH_LIMIT,
            "default_similarity_threshold": SCORE_PASS_THRESHOLD,
            "default_semantic_ratio": DEFAULT_SEMANTIC_RATIO,
            "enable_llm": ENABLE_LLM,
            "manual_semantic_ratio": MANUAL_SEMANTIC_RATIO,
            "enable_rerank": ENABLE_KEYWORD_WEIGHT_RERANK,
            "announcements": announcements,
            "websites": websites,
            "sources": AVAILABLE_SOURCES,
            "max_search_input_length": MAX_SEARCH_INPUT_LENGTH,
            "max_chat_input_length": MAX_CHAT_INPUT_LENGTH,
            "date_range_min": DATE_RANGE_MIN,
            "date_range_max": date_range_max,
        }
    )


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """
    RAG Chat Endpoint
    處理前端傳來的聊天請求，包含上下文與歷史紀錄
    Request JSON: {
        "message": "user question",
        "context": [...],
        "history": [...]
    }
    """
    try:
        print("\n" + "=" * 60)
        print("/api/chat called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        user_message = data.get("message", "")
        # --- [新增] 字數限制檢查 ---
        if len(user_message) > MAX_CHAT_INPUT_LENGTH:
            print(f"Refused: Input length {len(user_message)} exceeds limit.")
            return (
                jsonify(
                    {
                        "status": "failed",
                        "error_stage": "input_validation",
                        "error": f"Input length exceeds limit of {MAX_CHAT_INPUT_LENGTH} characters.",
                    }
                ),
                400,
            )

        # 接收前端傳來的 Context (搜尋結果)
        provided_context = data.get("context", [])
        # 接收前端傳來的 History (對話紀錄)
        chat_history = data.get("history", [])
        print(f"  Message: {user_message}")
        print(f"  Context items: {len(provided_context)}")
        print(f"  History items: {len(chat_history)}")
        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        client_ip = request.remote_addr
        request_headers = dict(request.headers)
        request_data = data.copy()

        rag_service = RAGService()
        response = rag_service.chat(
            user_query=user_message,
            provided_context=provided_context,
            history=chat_history,
        )

        LogManager.log_chat(
            ip=client_ip,
            headers=request_headers,
            request_data=request_data,
            response_data=response,
        )

        print("Chat response generated")
        print("=" * 60 + "\n")
        return jsonify(response)
    except Exception as e:
        print_red(f"RAG Endpoint Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/search", methods=["POST"])
def search_endpoint():
    """
    API Route: Search and generate summary (Streaming)
    處理前端傳來的搜尋請求，Agent 內部執行搜尋、檢查相關性、優化與摘要生成
    """
    try:
        print("\n" + "=" * 60)
        print("/api/search (Streaming) called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        query = data.get("query", "")
        limit = data.get("limit", DEFAULT_SEARCH_LIMIT)
        semantic_ratio = data.get("semantic_ratio", DEFAULT_SEMANTIC_RATIO)
        enable_llm = data.get("enable_llm", ENABLE_LLM)
        manual_semantic_ratio = data.get("manual_semantic_ratio", MANUAL_SEMANTIC_RATIO)
        enable_keyword_weight_rerank = data.get(
            "enable_keyword_weight_rerank", ENABLE_KEYWORD_WEIGHT_RERANK
        )
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        selected_website = data.get("selected_website", [])

        if not query:
            return jsonify({"error": "Query is required"}), 400

        if len(query) > MAX_SEARCH_INPUT_LENGTH:
            print(f"Refused: Query length {len(query)} exceeds limit.")
            return (
                jsonify(
                    {
                        "status": "failed",
                        "error_stage": "input_validation",
                        "error": f"Input length exceeds limit of {MAX_SEARCH_INPUT_LENGTH} characters.",
                    }
                ),
                400,
            )

        print(f"  Query: {query}")
        print(f"  Limit: {limit}")
        print(f"  Semantic Ratio: {semantic_ratio}")
        print(f"  Enable LLM: {enable_llm}")
        print(f"  Manual Semantic Ratio: {manual_semantic_ratio}")
        print(f"  Enable Rerank: {enable_keyword_weight_rerank}")
        print(f"  Start Date: {start_date}")
        print(f"  End Date: {end_date}")
        print(f"  Selected website: {selected_website}")
        # Validate parameters
        if not isinstance(limit, int) or limit < 1 or limit > MAX_SEARCH_LIMIT:
            return (
                jsonify(
                    {
                        "error": f"Invalid 'limit' value. Must be integer between 1 and {MAX_SEARCH_LIMIT}."
                    }
                ),
                400,
            )
        if (
            not isinstance(semantic_ratio, (int, float))
            or semantic_ratio < 0
            or semantic_ratio > 1
        ):
            return (
                jsonify(
                    {
                        "error": "Invalid 'semantic_ratio' value. Must be float between 0.0 and 1.0."
                    }
                ),
                400,
            )

        client_ip = request.remote_addr
        request_headers = dict(request.headers)
        request_data = data.copy()

        response_steps = []

        def generate():
            agent = SrhSumAgent()
            for step in agent.run(
                query=query,
                limit=limit,
                semantic_ratio=semantic_ratio,
                enable_llm=enable_llm,
                manual_semantic_ratio=manual_semantic_ratio,
                enable_keyword_weight_rerank=enable_keyword_weight_rerank,
                start_date=start_date,
                end_date=end_date,
                website=selected_website,
            ):
                response_steps.append(step)
                yield json.dumps(step, ensure_ascii=False) + "\n"

            LogManager.log_search(
                ip=client_ip,
                headers=request_headers,
                request_data=request_data,
                response_data=response_steps,
            )

        return Response(
            stream_with_context(generate()), mimetype="application/x-ndjson"
        )
    except Exception as e:
        print_red(f"Search Endpoint Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """
    Get Meilisearch index statistics

    Returns:
        JSON response with index stats
    """
    try:
        adapter = get_meili_adapter()
        stats = adapter.get_stats()
        return jsonify({"index_name": MEILISEARCH_INDEX, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    try:
        adapter = get_meili_adapter()
        stats = adapter.get_stats()
        return jsonify(
            {
                "status": "healthy",
                "meilisearch_host": MEILISEARCH_HOST,
                "index": MEILISEARCH_INDEX,
                "document_count": stats.get("numberOfDocuments", 0),
            }
        )
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route("/api/feedback", methods=["POST"])
def feedback_endpoint():
    """
    User Feedback Endpoint
    記錄用戶對搜尋結果摘要的反饋（讚/倒讚）
    Request JSON: {
        "feedback_type": "positive" | "negative",
        "query": "user query",
        "search_params": {...}
    }
    """
    try:
        print("\n" + "=" * 60)
        print("/api/feedback called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        feedback_type = data.get("feedback_type")
        if feedback_type not in ["positive", "negative"]:
            return jsonify({"error": "Invalid feedback_type"}), 400

        client_ip = request.remote_addr
        request_headers = dict(request.headers)

        LogManager.log_feedback(
            ip=client_ip, headers=request_headers, feedback_data=data
        )

        print(f"  Feedback Type: {feedback_type}")
        print(f"  Query: {data.get('query', 'N/A')}")
        print("Feedback logged successfully")
        print("=" * 60 + "\n")

        return jsonify({"status": "success"})

    except Exception as e:
        print_red(f"Feedback Endpoint Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Error Handlers
# ============================================================================


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Not Found", "message": str(e)}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


# ============================================================================
# Data Update API (Supports website and announcement)
# ============================================================================


@app.route("/api/admin/update-json/<target>", methods=["POST"])
def update_json_data(target):
    """
    通用遠端更新 API
    URL 範例: /api/admin/update-json/website 或 /api/admin/update-json/announcement
    """
    try:
        # 1. 驗證權限
        token = request.headers.get("X-Admin-Token")
        if token != ADMIN_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401

        # 2. 決定目標檔案路徑
        if target == "website":
            file_path = os.path.join(str(project_root), WEBSITE_JSON)
        elif target == "announcement":
            file_path = os.path.join(str(project_root), ANNOUNCEMENT_JSON)
        else:
            return jsonify({"error": f"Invalid target: {target}"}), 400

        # 3. 獲取 JSON 資料並驗證
        new_data = request.get_json()
        if not isinstance(new_data, list):
            return jsonify({"error": "Invalid format, must be a list"}), 400

        # 4. 寫入檔案
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)

        print(f"Successfully updated {target}.json via API")
        return jsonify({"status": "success", "message": f"{target}.json updated."})

    except Exception as e:
        print_red(f"Update API Error ({target}): {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Microsoft RAG System - Flask Web Server")
    print("=" * 60)
    print(f"Meilisearch Host: {MEILISEARCH_HOST}")
    print(f"Index Name: {MEILISEARCH_INDEX}")
    port = int(os.environ.get("PORT", 5000))
    print(f"Server will run on: http://0.0.0.0:{port}")
    print("=" * 60)

    # app.run(debug=False, host="0.0.0.0", port=5000)
    app.run(debug=True, host="0.0.0.0", port=5000)
