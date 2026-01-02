"""
Flask Application Entry Point
Web interface for the Microsoft RAG system using Meilisearch
"""

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
)
from src.tool.ANSI import print_red
from src.services.rag_service import RAGService
from src.services.search_service import SearchService
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
    return jsonify(
        {
            "default_limit": DEFAULT_SEARCH_LIMIT,
            "max_limit": MAX_SEARCH_LIMIT,
            "default_similarity_threshold": SCORE_PASS_THRESHOLD,
            "default_semantic_ratio": DEFAULT_SEMANTIC_RATIO,
            "enable_llm": ENABLE_LLM,
            "manual_semantic_ratio": MANUAL_SEMANTIC_RATIO,
            "enable_rerank": ENABLE_KEYWORD_WEIGHT_RERANK,
        }
    )



@app.route("/api/collection_search", methods=["POST"])
def search():
    """
    Perform hybrid search using SearchService

    Request JSON:
    {
        "query": "user query string",
        "limit": 20,  // optional
        "semantic_ratio": 0.5  // optional, 0.0 to 1.0
    }

    Returns:
        JSON response with search results
    """
    try:
        print("\n" + "=" * 60)
        print("/api/collection_search called")

        data = request.get_json()
        print(f"Request data: {data}")

        if not data or "query" not in data:
            print("Missing 'query' field")
            return jsonify({"error": "Missing 'query' field in request body"}), 400

        query = data["query"]
        limit = data.get("limit", 20)
        semantic_ratio = data.get("semantic_ratio", 0.5)
        enable_llm = data.get("enable_llm", True)
        manual_semantic_ratio = data.get("manual_semantic_ratio", False)
        filters = data.get("filters", {}) # 預設是空字典
        selected_websites = filters.get("website", []) # 拿出 website 列表
        
    
        print(f"  Query: {query}")
        print(f"  Limit: {limit}")
        print(f"  Semantic Ratio: {semantic_ratio}")
        print(f"  Enable LLM: {enable_llm}")
        print(f"  Manual Semantic Ratio: {manual_semantic_ratio}")
        print(f"  Websites Filter: {selected_websites}")

        # Validate parameters
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return (
                jsonify(
                    {
                        "error": "Invalid 'limit' value. Must be integer between 1 and 100."
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

        # Perform search
        print("Initializing SearchService...")
        search_service = SearchService()

        print("Calling search_service.search()...")
        results = search_service.search(
            user_query=query,
            limit=limit,
            semantic_ratio=semantic_ratio,
            enable_llm=enable_llm,
            manual_semantic_ratio=manual_semantic_ratio,
            website_filters=selected_websites
        )

        print(f"Search completed. Results count: {len(results.get('results', []))}")
        print("=" * 60 + "\n")
        return jsonify(results)

    except Exception as e:
        print(f"ERROR in /api/collection_search: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback

        print(f"   Traceback:\n{traceback.format_exc()}")
        print("=" * 60 + "\n")
        return jsonify({"error": str(e)}), 500


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
        # 接收前端傳來的 Context (搜尋結果)
        provided_context = data.get("context", [])
        # 接收前端傳來的 History (對話紀錄)
        chat_history = data.get("history", [])
        print(f"  Message: {user_message}")
        print(f"  Context items: {len(provided_context)}")
        print(f"  History items: {len(chat_history)}")
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        # 初始化 RAG Service 並執行
        rag_service = RAGService()
        response = rag_service.chat(
            user_query=user_message,
            provided_context=provided_context,
            history=chat_history,
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

        if not query:
            return jsonify({"error": "Query is required"}), 400
        print(f"  Query: {query}")
        print(f"  Limit: {limit}")
        print(f"  Semantic Ratio: {semantic_ratio}")
        print(f"  Enable LLM: {enable_llm}")
        print(f"  Manual Semantic Ratio: {manual_semantic_ratio}")
        print(f"  Enable Rerank: {enable_keyword_weight_rerank}")
        print(f"  Start Date: {start_date}")
        print(f"  End Date: {end_date}")
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
            ):
                yield json.dumps(step, ensure_ascii=False) + "\n"

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

    app.run(debug=True, host="0.0.0.0", port=5001)
