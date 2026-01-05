import tiktoken
from typing import Union


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    計算給定字串的 token 數量。

    Args:
        text: 要計算的字串。
        model: 使用的模型名稱，預設為 "gpt-4o-mini"。

    Returns:
        token 數量。
    """
    if not text:
        return 0

    try:
        # 取得該模型的 encoding
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # 如果模型不支援，預設使用 cl100k_base (GPT-4, GPT-3.5-turbo 等)
        print(f"Warning: Model {model} not found, using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


if __name__ == "__main__":
    test_text = "Hello, world! 這是 token 計算測試。"
    token_count = count_tokens(test_text)
    print(f"Text: {test_text}")
    print(f"Token count: {token_count}")
