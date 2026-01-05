import sys
from pathlib import Path
import unittest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.keyword_alg import ResultReranker


class TestKeywordReranker(unittest.TestCase):
    def test_calculate_hit_ratio_basic(self):
        """測試基本的命中比例計算"""
        results = [
            {
                "title": "Python Programming",
                "content": "Learn Python language",
                "_rankingScore": 0.5,
            },
            {
                "title": "Java Tutorial",
                "content": "Learn Java language",
                "_rankingScore": 0.5,
            },
        ]
        keywords = ["python"]
        reranker = ResultReranker(results, keywords)
        reranked = reranker.rerank()

        # 第一個文檔命中一個關鍵字 (1/1)
        self.assertEqual(reranked[0]["_hit_ratio"], 1.0)
        self.assertEqual(reranked[0]["has_keyword"], "1/1")

        # 第二個文檔沒命中 (0/1)
        self.assertEqual(reranked[1]["_hit_ratio"], 0.0)
        self.assertEqual(reranked[1]["has_keyword"], "0/1")

    def test_keyword_deduplication(self):
        """測試輸入重複關鍵字時，不會重複計分"""
        results = [
            {
                "title": "Gemini AI",
                "content": "Google Gemini details",
                "_rankingScore": 0.5,
            }
        ]
        # 輸入重複關鍵字 "gemini"
        keywords = ["gemini", "gemini", "AI"]
        reranker = ResultReranker(results, keywords)
        reranked = reranker.rerank()

        # 去重後總數應該是 2 ("gemini", "ai")
        # 命中兩個 (gemini, ai) -> 2/2 = 1.0
        self.assertEqual(reranked[0]["_hit_ratio"], 1.0)
        self.assertEqual(reranked[0]["has_keyword"], "2/2")

    def test_title_and_content_hit_once(self):
        """測試關鍵字同時出現在標題與內容時，只會計分一次"""
        results = [
            {
                "title": "Python Python",
                "content": "Python is everywhere",
                "_rankingScore": 0.5,
            }
        ]
        keywords = ["python"]
        reranker = ResultReranker(results, keywords)
        reranked = reranker.rerank()

        # 即使出現多次，也只算 1/1 = 1.0
        self.assertEqual(reranked[0]["_hit_ratio"], 1.0)
        self.assertEqual(reranked[0]["has_keyword"], "1/1")

    def test_multiple_keywords_partial_hit(self):
        """測試多個關鍵字的部分命中"""
        results = [
            {
                "title": "AI and Machine Learning",
                "content": "Cloud computing benefits",
                "_rankingScore": 0.5,
            }
        ]
        keywords = ["AI", "Cloud", "Azure"]
        reranker = ResultReranker(results, keywords)
        reranked = reranker.rerank()

        # 命中 AI 和 Cloud，沒命中 Azure -> 2/3 ≈ 0.6667
        self.assertAlmostEqual(reranked[0]["_hit_ratio"], 2 / 3)
        self.assertEqual(reranked[0]["has_keyword"], "2/3")

    def test_score_boosting_logic(self):
        """測試分數加權邏輯，確認命中越高分越高"""
        results = [
            {
                "id": 1,
                "title": "Full and Partial hit",
                "content": "Matches both keywords",
                "_rankingScore": 0.5,
            },
            {
                "id": 2,
                "title": "Only Partial hit",
                "content": "Matches one keyword",
                "_rankingScore": 0.5,
            },
            {"id": 3, "title": "None", "content": "No hit", "_rankingScore": 0.5},
        ]
        keywords = ["Full", "Partial"]
        reranker = ResultReranker(results, keywords)
        reranked = reranker.rerank()

        # 分數排序應為：1 > 2 > 3
        # Id 1: hit_ratio = 2/2 = 1.0
        # Id 2: hit_ratio = 1/2 = 0.5
        # Id 3: hit_ratio = 0/2 = 0.0

        # 確認分數差距
        self.assertEqual(reranked[0]["id"], 1)
        self.assertEqual(reranked[1]["id"], 2)
        self.assertEqual(reranked[2]["id"], 3)

        self.assertTrue(reranked[0]["_rerank_score"] > reranked[1]["_rerank_score"])
        self.assertTrue(reranked[1]["_rerank_score"] > reranked[2]["_rerank_score"])


if __name__ == "__main__":
    unittest.main()
