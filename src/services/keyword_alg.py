import re
from typing import List, Dict, Any, Optional
from src.config import (
    NO_HIT_PENALTY_FACTOR,
    KEYWORD_HIT_BOOST_FACTOR,
)


class ResultReranker:
    def __init__(
        self, search_results: List[Dict[str, Any]], target_keywords: Optional[List[str]]
    ):
        self.results = search_results
        self.keywords = (
            [k.lower().strip() for k in target_keywords] if target_keywords else []
        )

    def _normalize(self, text: str) -> str:
        return text.lower().replace(" ", "").replace("-", "")

    def _check_match(self, text: str, keyword: str) -> bool:
        if not text or not keyword:
            return False

        norm_text = self._normalize(text)
        norm_keyword = self._normalize(keyword)

        return norm_keyword in norm_text

    def _calculate_score(self, original_score: float, hit_ratio: float) -> float:
        # Formula: Final = Original * (1 - P * (1 - R)) + B * R * (1 - Original)
        # P = NO_HIT_PENALTY_FACTOR (e.g., 0.25)
        # B = KEYWORD_HIT_BOOST_FACTOR (e.g., 0.55)

        # 1. Apply Penalty for missing keywords
        # If Ratio=1, penalty_term=1 (No penalty). If Ratio=0, penalty_term = 1 - P.
        penalty_multiplier = 1.0 - (NO_HIT_PENALTY_FACTOR * (1.0 - hit_ratio))
        penalized_score = original_score * penalty_multiplier

        # 2. Apply Boost for matching keywords (fill the gap to 1.0)
        # We add a fraction of the remaining distance to 1.0
        gap_to_1 = 1.0 - original_score
        boost_amount = KEYWORD_HIT_BOOST_FACTOR * hit_ratio * gap_to_1

        final_score = penalized_score + boost_amount

        return min(max(final_score, 0.0), 1.0)

    def rerank(
        self, top_k: Optional[int] = None, enable_keyword_weight_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        if not self.results:
            return self.results

        # Default values for all docs
        for doc in self.results:
            if "_rerank_score" not in doc:
                original_score = doc.get("_rankingScore", 1.0)
                doc["_rerank_score"] = original_score
                doc["_hit_ratio"] = 0.0
                doc["has_keyword"] = "0/0"

        if not enable_keyword_weight_rerank:
            for doc in self.results:
                original_score = doc.get("_rankingScore", 1.0)
                doc["_rerank_score"] = original_score
                doc["_hit_ratio"] = "disabled"
                doc["has_keyword"] = "disabled"
            self.results.sort(key=lambda x: x["_rerank_score"], reverse=True)
            return self.results[:top_k] if top_k else self.results

        # Deduplicate keywords to avoid counting the same concept multiple times
        unique_keywords = []
        for kw in self.keywords:
            if kw not in unique_keywords:
                unique_keywords.append(kw)

        total_keywords = len(unique_keywords)

        if not unique_keywords:
            # If no keywords provided, just return original results sorted by ranking score
            self.results.sort(key=lambda x: x.get("_rankingScore", 1.0), reverse=True)
            return self.results[:top_k] if top_k else self.results

        reranked_docs = []

        for doc in self.results:
            content_text = doc.get("content", "") or ""
            title_text = doc.get("title", "") or ""

            matched_keywords_count = 0
            for kw in unique_keywords:
                # Check if keyword exists in title or content
                if self._check_match(title_text, kw) or self._check_match(
                    content_text, kw
                ):
                    matched_keywords_count += 1

            # User suggested formula: matched / total
            hit_ratio = (
                matched_keywords_count / total_keywords if total_keywords > 0 else 0
            )

            original_score = doc.get("_rankingScore", 1.0)
            # Ensure original score is within 0-1 for the formula to work predictably
            original_score = min(max(original_score, 0.0), 1.0)

            new_score = self._calculate_score(original_score, hit_ratio)

            doc["_rerank_score"] = new_score
            doc["_hit_ratio"] = hit_ratio
            doc["has_keyword"] = f"{matched_keywords_count}/{total_keywords}"
            reranked_docs.append(doc)

        reranked_docs.sort(key=lambda x: x["_rerank_score"], reverse=True)

        return reranked_docs[:top_k] if top_k else reranked_docs
