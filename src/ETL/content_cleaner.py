"""
Content Cleaner - Comprehensive Text Preprocessing
Removes URLs, boilerplate headers, metadata fields, and noise from content
to improve search quality and embedding effectiveness.
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


def remove_markdown_headings(text: str, remove_all_h3_plus: bool = False) -> str:
    """
    Remove boilerplate markdown headings from content.

    Args:
        text: Input text with markdown headings
        remove_all_h3_plus: If True, removes ALL h3+ headings (###, ####, etc.)
                           If False, only removes known boilerplate headings

    Returns:
        Text with specified headings removed

    Examples:
        >>> remove_markdown_headings("#### 現已推出\\n內容")
        "內容"
    """
    if remove_all_h3_plus:
        # Aggressive: Remove all h3+ headings (### and deeper)
        text = re.sub(r'^#{3,6}\s+.*$', '', text, flags=re.MULTILINE)
    else:
        # Conservative: Only remove known boilerplate headings
        boilerplate_patterns = [
            r'^#{3,6}\s*現已推出\s*$',
            r'^#{3,6}\s*即將到來的事項\s*$',
            r'^#{3,6}\s*提醒\s*$',
            r'^#{3,6}\s*後續步驟\s*$',
            r'^#{3,6}\s*重要資訊\s*$',
            r'^#{3,6}\s*重要事項\s*$',
            r'^#{3,6}\s*Note\s*$',
            r'^#{3,6}\s*Important\s*$',
        ]
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)

    return text


def remove_metadata_fields(text: str) -> str:
    """
    Remove metadata field headers (Date, Workspace, Affected audience, etc.)
    These should be extracted to metadata instead of staying in content.

    Args:
        text: Input text containing metadata fields

    Returns:
        Text with metadata field lines removed

    Examples:
        >>> remove_metadata_fields("**日期：** 2024-03-15\\n內容")
        "內容"
    """
    # Pattern matches:
    # - ** 日期 ：** value  (with various spacing)
    # - 日期： value
    # - Date: value
    # - *Workspace:* value
    metadata_patterns = [
        r'^\*?\*?\s*日期\s*[：:]\s*.*$',
        r'^\*?\*?\s*工作區\s*[：:]\s*.*$',
        r'^\*?\*?\s*受影響的群體\s*[：:]\s*.*$',
        r'^\*?\*?\s*Date\s*[：:]\s*.*$',
        r'^\*?\*?\s*Workspace\s*[：:]\s*.*$',
        r'^\*?\*?\s*Affected audience\s*[：:]\s*.*$',
        r'^\*?\*?\s*Announced\s*[：:]\s*.*$',
    ]

    for pattern in metadata_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)

    return text


def remove_announced_prefix(text: str) -> str:
    """
    Remove "Announced" prefix or standalone lines.

    Args:
        text: Input text

    Returns:
        Text with "Announced" removed

    Examples:
        >>> remove_announced_prefix("Announced March 2024\\nSome content")
        "Some content"
    """
    # Remove lines starting with "Announced"
    text = re.sub(r'^Announced.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

    # Remove inline "Announced:" patterns
    text = re.sub(r'\bAnnounced\s*[：:]\s*', '', text, flags=re.IGNORECASE)

    return text


def clean_content_comprehensive(
    text: str,
    remove_urls: bool = True,
    remove_headings: bool = True,
    remove_metadata: bool = True,
    remove_announced: bool = True,
    aggressive_heading_removal: bool = False
) -> str:
    """
    Comprehensive content cleaning pipeline combining all strategies.

    Processing order:
    1. Remove metadata field lines (Date, Workspace, etc.)
    2. Remove boilerplate markdown headings
    3. Remove "Announced" prefixes
    4. Remove URLs and markdown links
    5. Clean up whitespace

    Args:
        text: Raw text content
        remove_urls: Remove URLs and simplify markdown links
        remove_headings: Remove boilerplate markdown headings
        remove_metadata: Remove metadata field lines
        remove_announced: Remove "Announced" prefixes
        aggressive_heading_removal: Remove ALL h3+ headings (not just boilerplate)

    Returns:
        Cleaned text ready for embedding/search

    Examples:
        >>> text = "#### 現已推出\\n**日期：** 2024-03-15\\n詳見 [文檔](https://example.com)\\n內容"
        >>> clean_content_comprehensive(text)
        "詳見 文檔 內容"
    """
    # Step 1: Remove metadata fields first (they're usually at the top)
    if remove_metadata:
        text = remove_metadata_fields(text)

    # Step 2: Remove boilerplate headings
    if remove_headings:
        text = remove_markdown_headings(text, remove_all_h3_plus=aggressive_heading_removal)

    # Step 3: Remove "Announced" prefixes
    if remove_announced:
        text = remove_announced_prefix(text)

    # Step 4: Remove URLs and clean markdown links
    if remove_urls:
        text = clean_urls_from_content(text, preserve_anchor_text=True, replacement_token="")

    # Step 5: Final cleanup - normalize whitespace
    # Remove multiple blank lines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Remove leading/trailing whitespace per line
    text = '\n'.join(line.strip() for line in text.split('\n'))
    # Remove multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    # Final trim
    text = text.strip()

    return text


# Recommended default for this use case
clean_content_for_search = clean_content_comprehensive


if __name__ == "__main__":
    # Test cases for comprehensive cleaning
    test_cases = [
        # Test 1: URL cleaning
        "詳見 [Azure 定價頁面](https://azure.microsoft.com/pricing/) 了解更多資訊。",

        # Test 2: Standalone URL
        "請訪問 https://learn.microsoft.com 查看文檔。",

        # Test 3: Boilerplate headings
        "#### 現已推出\n新功能已經發布\n#### 提醒\n請注意更新",

        # Test 4: Metadata fields
        "**日期：** 2024-03-15\n**工作區：** Azure\n**受影響的群體：** 所有用戶\n重要內容在這裡",

        # Test 5: Announced prefix
        "Announced March 2024\n此功能將於下月推出",

        # Test 6: Comprehensive test (everything combined)
        """#### 現已推出
**日期：** March 15, 2024
**工作區：** Microsoft 365
Announced: March 2024

我們很高興宣布新功能。詳見 [官方文檔](https://docs.microsoft.com/feature) 了解更多。
請訪問 https://support.microsoft.com 獲取支援。

#### 後續步驟
請按照以下步驟操作。""",
    ]

    print("=" * 80)
    print("Content Cleaner - Comprehensive Test Suite")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"[Test {i}]")
        print(f"{'='*80}")
        print(f"原始內容:\n{test}")
        print(f"\n{'-'*80}")
        print(f"清理後 (comprehensive):\n{clean_content_comprehensive(test)}")
        print(f"\n{'-'*80}")

    # Detailed component tests
    print(f"\n\n{'='*80}")
    print("Component-level Tests")
    print("=" * 80)

    print("\n[A] Markdown Heading Removal:")
    heading_test = "#### 現已推出\n#### 即將到來的事項\n#### 自訂標題\n內容"
    print(f"原始: {heading_test}")
    print(f"保守模式: {remove_markdown_headings(heading_test, remove_all_h3_plus=False)}")
    print(f"激進模式: {remove_markdown_headings(heading_test, remove_all_h3_plus=True)}")

    print("\n[B] Metadata Field Removal:")
    metadata_test = "**日期：** 2024-03-15\n**工作區：** Azure\n實際內容"
    print(f"原始: {metadata_test}")
    print(f"清理: {remove_metadata_fields(metadata_test)}")

    print("\n[C] Announced Removal:")
    announced_test = "Announced: March 2024\nAnnounced March\n功能說明"
    print(f"原始: {announced_test}")
    print(f"清理: {remove_announced_prefix(announced_test)}")

    print("\n" + "=" * 80)