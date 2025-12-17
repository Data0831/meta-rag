"""
Content Cleaner - URL and Hyperlink Processing
Removes or simplifies URLs to improve search quality and embedding effectiveness.
"""

import re
from typing import Tuple, List


def extract_markdown_links(text: str) -> List[Tuple[str, str]]:
    """
    Extract markdown-style links [text](url) from content.

    Args:
        text: Input text containing markdown links

    Returns:
        List of (anchor_text, url) tuples
    """
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    matches = re.findall(pattern, text)
    return matches


def clean_urls_from_content(
    text: str,
    preserve_anchor_text: bool = True,
    replacement_token: str = ""
) -> str:
    """
    Remove or simplify URLs from content to improve search quality.

    Strategy:
    1. Extract markdown links [text](url) → keep "text" only
    2. Remove standalone URLs (http://..., https://...)
    3. Optionally replace with a token (e.g., "[連結]")

    Args:
        text: Input text with URLs
        preserve_anchor_text: If True, keep anchor text from markdown links
        replacement_token: Token to replace standalone URLs (empty = remove)

    Returns:
        Cleaned text with URLs removed/simplified

    Examples:
        >>> clean_urls_from_content("詳見 [Azure 定價](https://azure.com/pricing)")
        "詳見 Azure 定價"

        >>> clean_urls_from_content("網址：https://microsoft.com", replacement_token="[連結]")
        "網址：[連結]"
    """

    # Step 1: Handle markdown links [text](url)
    if preserve_anchor_text:
        # Replace [text](url) with just "text"
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    else:
        # Replace entire markdown link with replacement token
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', replacement_token, text)

    # Step 2: Remove standalone URLs
    # Match http://, https://, www. patterns
    url_pattern = r'https?://[^\s\u4e00-\u9fff]+|www\.[^\s\u4e00-\u9fff]+'
    text = re.sub(url_pattern, replacement_token, text)

    # Step 3: Clean up multiple spaces and whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def extract_domain_from_url(url: str) -> str:
    """
    Extract clean domain from URL for potential filtering/metadata.

    Args:
        url: Full URL string

    Returns:
        Domain name (e.g., "microsoft.com")

    Example:
        >>> extract_domain_from_url("https://learn.microsoft.com/azure/pricing")
        "learn.microsoft.com"
    """
    pattern = r'https?://([^/\s]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else ""


def clean_content_aggressive(text: str) -> str:
    """
    Aggressive cleaning for embedding generation.
    Removes URLs entirely without replacement tokens.

    Args:
        text: Input text

    Returns:
        Cleaned text suitable for embedding
    """
    return clean_urls_from_content(
        text,
        preserve_anchor_text=True,
        replacement_token=""
    )


def clean_content_conservative(text: str) -> str:
    """
    Conservative cleaning that preserves context markers.
    Replaces URLs with [連結] token.

    Args:
        text: Input text

    Returns:
        Cleaned text with link markers
    """
    return clean_urls_from_content(
        text,
        preserve_anchor_text=True,
        replacement_token=" [連結] "
    )


# Recommended default for this use case
clean_content_for_search = clean_content_aggressive


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "詳見 [Azure 定價頁面](https://azure.microsoft.com/pricing/) 了解更多資訊。",
        "請訪問 https://learn.microsoft.com 查看文檔。",
        "Microsoft 官網：www.microsoft.com 提供完整說明。",
        "[點擊這裡](https://example.com/very/long/path/to/resource) 下載文件。網址是 https://another.com/path。",
    ]

    print("=" * 60)
    print("Content Cleaner Test")
    print("=" * 60)

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}]")
        print(f"原始: {test}")
        print(f"清理: {clean_content_aggressive(test)}")
        print(f"保守: {clean_content_conservative(test)}")