import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.search_service import SearchService
from src.schema.schemas import SearchIntent, SearchFilters, Category, ImpactLevel


class TestMustHaveKeywords(unittest.TestCase):

    @patch("src.services.search_service.LLMClient")
    @patch("src.services.search_service.MeiliAdapter")
    @patch("src.services.search_service.vector_utils")
    def test_must_have_keywords_boosting(
        self, mock_vector_utils, mock_meili_adapter, mock_llm_client
    ):
        """
        Test that must_have_keywords are correctly appended 3 times to the keyword_query
        """
        # Setup mocks
        mock_adapter_instance = MagicMock()
        mock_meili_adapter.return_value = mock_adapter_instance

        mock_llm_instance = MagicMock()
        mock_llm_client.return_value = mock_llm_instance

        # Define the intent returned by the LLM
        mock_intent = SearchIntent(
            filters=SearchFilters(),
            keyword_query="GEMINI 競爭對手",
            semantic_query="GEMINI 競爭對手",
            must_have_keywords=["GEMINI"],
            recommended_semantic_ratio=0.5,
        )

        mock_llm_instance.call_with_schema.return_value = mock_intent

        # Initialize service
        service = SearchService()

        # Execute search
        service.search("與 GEMINI 競爭對手相關展品")

        # Verify the search call to Meilisearch adapter
        # We expect the keyword_query to be modified

        # The expected query string should be: "GEMINI 競爭對手 GEMINI GEMINI GEMINI"
        # The original query was "GEMINI 競爭對手"
        # The code appends: ' '.join(['GEMINI', 'GEMINI', 'GEMINI'])

        expected_query = "GEMINI 競爭對手 GEMINI GEMINI GEMINI"

        # Get the arguments called on search
        call_args = mock_adapter_instance.search.call_args
        self.assertIsNotNone(call_args, "MeiliAdapter.search was not called")

        kwargs = call_args.kwargs
        actual_query = kwargs.get("query")

        print(f"\nExpected Query: '{expected_query}'")
        print(f"Actual Query:   '{actual_query}'")

        self.assertEqual(actual_query, expected_query)

    @patch("src.services.search_service.LLMClient")
    @patch("src.services.search_service.MeiliAdapter")
    @patch("src.services.search_service.vector_utils")
    def test_multiple_must_have_keywords(
        self, mock_vector_utils, mock_meili_adapter, mock_llm_client
    ):
        """
        Test multiple must_have_keywords
        """
        # Setup mocks
        mock_adapter_instance = MagicMock()
        mock_meili_adapter.return_value = mock_adapter_instance

        mock_llm_instance = MagicMock()
        mock_llm_client.return_value = mock_llm_instance

        # Define the intent
        mock_intent = SearchIntent(
            filters=SearchFilters(),
            keyword_query="Azure Security",
            semantic_query="Azure Security",
            must_have_keywords=["Azure", "Security"],
            recommended_semantic_ratio=0.5,
        )

        mock_llm_instance.call_with_schema.return_value = mock_intent

        # Initialize service
        service = SearchService()

        # Execute search
        service.search("Azure Security issues")

        # Expected: "Azure Security Azure Azure Azure Security Security Security"
        # order depends on implementation, but likely appends [Azure, Azure, Azure, Security, Security, Security]
        # Actually the code does:
        # for kw in intent.must_have_keywords:
        #     boosted_keywords.extend([kw] * 3)
        # So yes: Azure Azure Azure Security Security Security

        expected_query = "Azure Security Azure Azure Azure Security Security Security"

        call_args = mock_adapter_instance.search.call_args
        kwargs = call_args.kwargs
        actual_query = kwargs.get("query")

        print(f"\nExpected Query: '{expected_query}'")
        print(f"Actual Query:   '{actual_query}'")

        self.assertEqual(actual_query, expected_query)


if __name__ == "__main__":
    unittest.main()
