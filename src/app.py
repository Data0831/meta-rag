"""
Flask Application Entry Point
Web interface for the Microsoft RAG system using Meilisearch
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request, redirect, url_for
import os
from dotenv import load_dotenv
from typing import Dict, Any

from src.database.db_adapter_meili import MeiliAdapter
from src.agents.srhSumAgent import SrhSumAgent


from src.config import (
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_SEMANTIC_RATIO,
    ENABLE_LLM,
    MANUAL_SEMANTIC_RATIO,
    ENABLE_KEYWORD_WEIGHT_RERANK,
)
from src.tool.ANSI import print_red

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
            "default_similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD,
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
            print_red("Missing 'query' field")
            return jsonify({"error": "Missing 'query' field in request body"}), 400

        query = data["query"]
        limit = data.get("limit", 20)
        semantic_ratio = data.get("semantic_ratio", 0.5)
        enable_llm = data.get("enable_llm", True)
        manual_semantic_ratio = data.get("manual_semantic_ratio", False)
        enable_keyword_weight_rerank = data.get("enable_keyword_weight_rerank", True)

        print(f"  Query: {query}")
        print(f"  Limit: {limit}")
        print(f"  Semantic Ratio: {semantic_ratio}")
        print(f"  Enable LLM: {enable_llm}")
        print(f"  Manual Semantic Ratio: {manual_semantic_ratio}")
        print(f"  Enable Rerank: {enable_keyword_weight_rerank}")

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
            enable_keyword_weight_rerank=enable_keyword_weight_rerank,
        )

        # Check if search failed
        if results.get("status") == "failed":
            error_msg = results.get("error", "Unknown error")
            stage = results.get("stage", "unknown")
            print_red(f"Search failed at stage '{stage}': {error_msg}")
            print("=" * 60 + "\n")

            # Return different HTTP status codes based on stage
            if stage in ["meilisearch", "embedding", "llm"]:
                status_code = 503  # Service Unavailable
            else:
                status_code = 500  # Internal Server Error

            return jsonify(results), status_code

        print(f"Search completed. Results count: {len(results.get('results', []))}")
        print("=" * 60 + "\n")
        return jsonify(results)

    except Exception as e:
        print_red(f"ERROR in /api/collection_search: {e}")
        print_red(f"   Error type: {type(e).__name__}")
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


@app.route("/api/summary", methods=["POST"])
def generate_summary():
    """
    API Route: Generate summary for search results
    處理前端傳來的摘要請求
    Request JSON: {
        "query": "user query string",
        "results": [ ... top 5 search results ... ]
    }
    """
    try:
        print("\n" + "=" * 60)
        print("/api/summary called")

        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        user_query = data.get("query", "")
        search_results = data.get("results", [])

        if not user_query:
            print("Missing 'query' field")
            return jsonify({"error": "Query is required"}), 400

        print(f"  Query: {user_query}")
        print(f"  Results to summarize: {len(search_results)}")

        # 初始化 Agent
        agent = SrhSumAgent()

        # 呼叫 Agent 生成摘要
        summary_text = agent.generate_summary(user_query, search_results)

        print("Summary generated")
        print("=" * 60 + "\n")

        return jsonify({"summary": summary_text})

    except Exception as e:
        print_red(f"Summary Endpoint Error: {e}")
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

    app.run(threaded=True, debug=True, host="0.0.0.0", port=port)
