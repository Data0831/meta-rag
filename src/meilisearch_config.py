"""
Meilisearch Configuration Settings
Centralized configuration for search parameters and ranking rules.
"""

# Default Semantic Ratio
# Controls the weight of vector search vs keyword search
# 0.0 = Pure keyword search (Fuzzy)
# 1.0 = Pure vector search (Semantic)
# 0.5 = Balanced Hybrid Search (Default)
DEFAULT_SEMANTIC_RATIO = 0.5

# Meilisearch Ranking Rules
# These rules determine the order of search results.
# The order in the list represents the priority of the rule.
# Reference: https://www.meilisearch.com/docs/learn/core_concepts/relevancy
RANKING_RULES = [
    "words",  # Prioritize documents containing more query terms
    "typo",  # Prioritize documents with fewer typos
    "proximity",  # Prioritize documents where query terms are closer together
    "attribute",  # Prioritize matches in more important attributes (e.g. title > content)
    "sort",  # Sort by custom sortable attributes (if requested in query)
    "exactness",  # Prioritize exact matches over fuzzy matches
]

# Filterable Attributes
# Attributes that can be used in the 'filter' parameter
FILTERABLE_ATTRIBUTES = [
    "month",
    "link",
]

# Searchable Attributes
# Attributes that are searched for keywords
# Order implies importance (e.g., matches in title are more important than in content)
SEARCHABLE_ATTRIBUTES = [
    "title",
    "metadata.meta_summary",
    # "metadata.meta_summary_segmented",
    "content_clean",  # Use cleaned content (URLs removed) for better search quality
]

# Embedding Configuration
EMBEDDING_CONFIG = {
    "source": "userProvided",  # We generate embeddings externally (BGE-M3)
    "dimensions": 1024,  # Dimension of BGE-M3 embeddings
}
