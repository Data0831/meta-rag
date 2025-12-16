"""
Flask Application Entry Point
Web interface for the Microsoft RAG system using Meilisearch
"""
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
        collection_name=MEILISEARCH_INDEX
    )


# ============================================================================
# Page Routes
# ============================================================================

@app.route('/')
def index():
    """RAG LAB - Main page"""
    return render_template('index.html')


@app.route('/chat')
def chat():
    """Chat interface"""
    return render_template('chat.html')


@app.route('/search')
def search_page():
    """Search interface page"""
    return render_template('search.html')


# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/search', methods=['POST'])
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
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' field in request body"
            }), 400

        query = data['query']
        limit = data.get('limit', 20)
        semantic_ratio = data.get('semantic_ratio', 0.5)

        # Validate parameters
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return jsonify({
                "error": "Invalid 'limit' value. Must be integer between 1 and 100."
            }), 400

        if not isinstance(semantic_ratio, (int, float)) or semantic_ratio < 0 or semantic_ratio > 1:
            return jsonify({
                "error": "Invalid 'semantic_ratio' value. Must be float between 0.0 and 1.0."
            }), 400

        # Perform search
        search_service = SearchService()
        results = search_service.search(
            user_query=query,
            limit=limit,
            semantic_ratio=semantic_ratio
        )

        return jsonify(results)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """
    Get Meilisearch index statistics

    Returns:
        JSON response with index stats
    """
    try:
        adapter = get_meili_adapter()
        stats = adapter.get_stats()

        return jsonify({
            "index_name": MEILISEARCH_INDEX,
            "stats": stats
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        adapter = get_meili_adapter()
        stats = adapter.get_stats()

        return jsonify({
            "status": "healthy",
            "meilisearch_host": MEILISEARCH_HOST,
            "index": MEILISEARCH_INDEX,
            "document_count": stats.get('numberOfDocuments', 0)
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not Found",
        "message": str(e)
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e)
    }), 500


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print("="*60)
    print("Starting Microsoft RAG System - Flask Web Server")
    print("="*60)
    print(f"Meilisearch Host: {MEILISEARCH_HOST}")
    print(f"Index Name: {MEILISEARCH_INDEX}")
    print(f"Server will run on: http://localhost:5000")
    print("="*60)

    app.run(debug=True, host='0.0.0.0', port=5000)
