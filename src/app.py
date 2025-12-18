"""
Flask Application Entry Point
Web interface for the Microsoft RAG system using Meilisearch
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request
import os
from dotenv import load_dotenv
from typing import Dict, Any

from src.database.db_adapter_meili import MeiliAdapter
from src.services.search_service import SearchService
from src.config import MEILISEARCH_HOST, MEILISEARCH_API_KEY, MEILISEARCH_INDEX

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
MEILISEARCH_HOST = os.getenv("MEILISEARCH_HOST", "http://localhost:7700")
MEILISEARCH_API_KEY = os.getenv("MEILISEARCH_API_KEY", "masterKey")


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
    """RAG LAB - Main page"""
    return render_template("index.html")


@app.route("/chat")
def chat():
    """Chat interface"""
    return render_template("chat.html")


@app.route("/search")
def search_page():
    """Search interface page"""
    return render_template("search.html")


@app.route("/vector_search")
def vector_search_page():
    """Vector search collections management page"""
    return render_template("vector_search.html")


@app.route("/collection/<collection_name>")
def collection_search(collection_name):
    """Collection-specific search interface"""
    return render_template("collection_search.html", collection_name=collection_name)


# ============================================================================
# API Routes
# ============================================================================


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
        print("🔍 /api/collection_search called")

        data = request.get_json()
        print(f"📥 Request data: {data}")

        if not data or "query" not in data:
            print("❌ Missing 'query' field")
            return jsonify({"error": "Missing 'query' field in request body"}), 400

        query = data["query"]
        limit = data.get("limit", 20)
        semantic_ratio = data.get("semantic_ratio", 0.5)
        enable_llm = data.get("enable_llm", True)

        print(f"  Query: {query}")
        print(f"  Limit: {limit}")
        print(f"  Semantic Ratio: {semantic_ratio}")
        print(f"  Enable LLM: {enable_llm}")

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
        print("🚀 Initializing SearchService...")
        search_service = SearchService()

        print("🔎 Calling search_service.search()...")
        results = search_service.search(
            user_query=query,
            limit=limit,
            semantic_ratio=semantic_ratio,
            enable_llm=enable_llm,
        )

        print(f"✅ Search completed. Results count: {len(results.get('results', []))}")
        print("=" * 60 + "\n")
        return jsonify(results)

    except Exception as e:
        print(f"❌ ERROR in /api/collection_search: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback

        print(f"   Traceback:\n{traceback.format_exc()}")
        print("=" * 60 + "\n")
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


@app.route("/api/collections")
def get_collections():
    """
    Get Meilisearch indexes/collections information
    Adapted to match Qdrant-style collection format for frontend compatibility

    Returns:
        JSON response with collections list
    """
    try:
        adapter = get_meili_adapter()
        stats = adapter.get_stats()

        # Adapt Meilisearch index info to Qdrant-style collection format
        collection = {
            "name": MEILISEARCH_INDEX,
            "status": "green",  # Assume green if we can fetch stats
            "points_count": stats.get("numberOfDocuments", 0),
            "segments_count": 1,  # Meilisearch doesn't have segments concept
            "config": {
                "params": {
                    "vectors": {
                        "default": {
                            "size": 1024,  # BGE-M3 dimension
                            "distance": "Cosine",
                        }
                    },
                    "shard_number": 1,
                },
                "optimizer_config": {
                    "indexing_threshold": stats.get("isIndexing", False)
                },
            },
        }

        return jsonify({"collections": [collection]})

    except Exception as e:
        # Return error collection if connection fails
        error_collection = {"name": MEILISEARCH_INDEX, "error": str(e)}
        return (
            jsonify({"collections": [error_collection]}),
            200,
        )  # Still return 200 to show error in UI


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
    print(f"Server will run on: http://localhost:5000")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=5000)
