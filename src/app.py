"""
Flask Application Entry Point
Web interface for the Microsoft RAG system
"""
from flask import Flask, render_template, jsonify
from qdrant_client import QdrantClient
from qdrant_client.models import CollectionStatus
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance"""
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


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
def search():
    """Vector Search - Collections management page"""
    return render_template('vector_search.html')


@app.route('/compare')
def compare():
    """Compare page - placeholder for future implementation"""
    return render_template('collection_search.html')


@app.route('/collection/<collection_name>')
def collection_detail(collection_name: str):
    """Collection detail page - placeholder for future implementation"""
    # For now, redirect to collection_search with the collection name
    return render_template('collection_search.html', collection_name=collection_name)


# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/collections')
def get_collections():
    """
    Get all Qdrant collections with their metadata

    Returns:
        JSON response with collections list
    """
    try:
        client = get_qdrant_client()
        collections_response = client.get_collections()

        collections_data = []

        for collection in collections_response.collections:
            try:
                # Get detailed collection info
                collection_info = client.get_collection(collection.name)

                # Extract relevant information
                collection_data = {
                    "name": collection.name,
                    "status": collection_info.status.value if hasattr(collection_info.status, 'value') else str(collection_info.status),
                    "points_count": collection_info.points_count or 0,
                    "segments_count": collection_info.segments_count or 0,
                    "config": {
                        "params": {
                            "vectors": {},
                            "shard_number": collection_info.config.params.shard_number if collection_info.config else 1
                        },
                        "optimizer_config": None
                    }
                }

                # Handle vectors configuration
                if collection_info.config and collection_info.config.params:
                    vectors_config = collection_info.config.params.vectors

                    # Handle both named vectors (dict) and single vector config
                    if isinstance(vectors_config, dict):
                        # Named vectors (e.g., {"dense": {...}, "sparse": {...}})
                        vectors_dict = {}
                        for name, vector_params in vectors_config.items():
                            if hasattr(vector_params, 'size'):
                                # Dense vector
                                vectors_dict[name] = {
                                    "size": vector_params.size,
                                    "distance": vector_params.distance.value if hasattr(vector_params.distance, 'value') else str(vector_params.distance)
                                }
                            else:
                                # Sparse vector or other type
                                vectors_dict[name] = {
                                    "sparse": True
                                }
                        collection_data["config"]["params"]["vectors"] = vectors_dict
                    else:
                        # Single unnamed vector
                        if hasattr(vectors_config, 'size'):
                            collection_data["config"]["params"]["vectors"] = {
                                "size": vectors_config.size,
                                "distance": vectors_config.distance.value if hasattr(vectors_config.distance, 'value') else str(vectors_config.distance)
                            }

                # Add optimizer config if available
                if collection_info.config and hasattr(collection_info.config, 'optimizer_config'):
                    optimizer = collection_info.config.optimizer_config
                    if optimizer:
                        collection_data["config"]["optimizer_config"] = {
                            "deleted_threshold": optimizer.deleted_threshold if hasattr(optimizer, 'deleted_threshold') else None,
                            "vacuum_min_vector_number": optimizer.vacuum_min_vector_number if hasattr(optimizer, 'vacuum_min_vector_number') else None,
                            "default_segment_number": optimizer.default_segment_number if hasattr(optimizer, 'default_segment_number') else None
                        }

                collections_data.append(collection_data)

            except Exception as e:
                # If we can't get details for a specific collection, include it with error info
                collections_data.append({
                    "name": collection.name,
                    "error": str(e)
                })

        return jsonify({
            "collections": collections_data
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "collections": []
        }), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        client = get_qdrant_client()
        # Try to get collections to verify connection
        client.get_collections()
        return jsonify({
            "status": "healthy",
            "qdrant_url": QDRANT_URL
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
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Server will run on: http://localhost:5000")
    print("="*60)

    app.run(debug=True, host='0.0.0.0', port=5000)
