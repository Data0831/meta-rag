import re
from typing import List, Dict, Any, Optional
from src.config import (
    RERANK_FULL_MATCH_BOOST,
    RERANK_PARTIAL_MATCH_FACTOR,
    RERANK_NO_MATCH_PENALTY,
    RERANK_TITLE_WEIGHT,
)


class ResultReranker:
    def __init__(self, search_results: List[Dict[str, Any]], target_keywords: Optional[List[str]]):
        self.results = search_results
        self.keywords = [k.lower().strip() for k in target_keywords] if target_keywords else []

    def _check_match(self, text: str, keyword: str) -> bool:
        if not text or not keyword:
            return False

        text = text.lower()
        try:
            if re.match(r'^[a-zA-Z0-9\.\-]+$', keyword):
                pattern = r'(?<![\w\.\-])' + re.escape(keyword) + r'(?![\w\.\-])'
            else:
                return keyword in text

            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return keyword in text

    def _calculate_boost(self, original_score: float, hit_ratio: float) -> float:
        if hit_ratio == 1.0:
            return original_score * RERANK_FULL_MATCH_BOOST

        elif hit_ratio > 0:
            return original_score * (1.0 + (hit_ratio * RERANK_PARTIAL_MATCH_FACTOR))

        else:
            return original_score * RERANK_NO_MATCH_PENALTY

    def rerank(self, top_k: Optional[int] = None, enable_rerank: bool = True) -> List[Dict[str, Any]]:
        if not self.results:
            return self.results

        if not enable_rerank:
            for doc in self.results:
                original_score = doc.get('_rankingScore', 1.0)
                doc['_rerank_score'] = original_score
                doc['_hit_ratio'] = "unknown"
                doc['has_keyword'] = "unknown"
            self.results.sort(key=lambda x: x['_rerank_score'], reverse=True)
            return self.results[:top_k] if top_k else self.results

        total_keywords = len(self.keywords)

        if not self.keywords:
            for doc in self.results:
                original_score = doc.get('_rankingScore', 1.0)
                doc['_rerank_score'] = original_score * RERANK_NO_MATCH_PENALTY
                doc['_hit_ratio'] = 0
                doc['has_keyword'] = "0/0"
            self.results.sort(key=lambda x: x['_rerank_score'], reverse=True)
            return self.results[:top_k] if top_k else self.results

        reranked_docs = []

        for doc in self.results:
            content_text = (doc.get('content', '') or "")
            title_text = (doc.get('title', '') or "")

            hits = 0
            matched_keywords_count = 0
            for kw in self.keywords:
                title_match = self._check_match(title_text, kw)
                content_match = self._check_match(content_text, kw)

                if title_match:
                    hits += RERANK_TITLE_WEIGHT
                    matched_keywords_count += 1
                elif content_match:
                    hits += 1.0
                    matched_keywords_count += 1

            max_possible_hits = len(self.keywords)
            hit_ratio = min(hits / max_possible_hits, 1.0) if max_possible_hits > 0 else 0

            original_score = doc.get('_rankingScore', 1.0)
            new_score = self._calculate_boost(original_score, hit_ratio)

            doc['_rerank_score'] = new_score
            doc['_hit_ratio'] = hit_ratio
            doc['has_keyword'] = f"{matched_keywords_count}/{total_keywords}"
            reranked_docs.append(doc)

        reranked_docs.sort(key=lambda x: x['_rerank_score'], reverse=True)

        return reranked_docs[:top_k] if top_k else reranked_docs
