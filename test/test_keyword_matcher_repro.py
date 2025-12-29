import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.keyword_alg import ResultReranker


def test_matching():
    reranker = ResultReranker([], [])

    test_cases = [
        # (text, keyword, expected_match)
        ("This is an azure cloud service", "Azure -- cloud", True),
        ("Usage of Azure -- cloud computing", "azure cloud", True),
        ("Plain cloud", "cloud", True),
        ("Multi-cloud strategy", "multi cloud", True),
        ("multi cloud strategy", "Multi-cloud", True),
        ("Ignore case HERE", "here", True),
        (
            "Partial mismatch",
            "partly",
            False,
        ),
        ("Completely Different", "Azure", False),
    ]

    print(
        f"{'Text':<40} | {'Keyword':<20} | {'Match?':<10} | {'Expected':<10} | {'Status'}"
    )
    print("-" * 100)

    all_passed = True
    for text, keyword, expected in test_cases:
        # We need to test the _check_match method.
        # Since it is private/internal, we access it directly for unit testing purposes.
        # Ideally we would test public API, but Reranker takes a list of results.
        # This unit test on the internal method is more direct for this logic change.

        match = reranker._check_match(text, keyword)
        status = "PASS" if match == expected else "FAIL"
        if status == "FAIL":
            all_passed = False

        print(
            f"{text[:37]+'...':<40} | {keyword:<20} | {str(match):<10} | {str(expected):<10} | {status}"
        )

    if all_passed:
        print("\nAll test cases PASSED.")
    else:
        print("\nSome test cases FAILED.")


if __name__ == "__main__":
    test_matching()
