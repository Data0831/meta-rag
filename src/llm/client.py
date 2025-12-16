import os
import json
from typing import Type, TypeVar, List
from openai import OpenAI, APIError, APIStatusError
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

# Load environment variables
load_dotenv()

# Import model list from config
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config import GEMINI_MODELS

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        """
        Initialize the LLM Client.

        Args:
            base_url: The URL of the local Gemini-to-OpenAI proxy.
                      Defaults to "http://localhost:8000/openai/v1".
            api_key: The access token for the proxy (defined in .env ALLOWED_TOKENS).
            model: The Gemini model name to use (e.g., "gemini-1.5-flash").
        """
        self.base_url = base_url or os.getenv(
            "PROXY_BASE_URL", "http://localhost:8000/openai/v1"
        )
        # Using PROXY_API_KEY to distinguish from actual OpenAI key if needed, or stick to a convention
        # The user request implies reading from env.
        self.api_key = api_key or os.getenv("PROXY_API_KEY", "sk-mysecrettoken123")
        self.model = model or os.getenv("PROXY_MODEL_NAME", "gemini-2.5-flash")

        print(
            f"Initializing LLMClient with base_url={self.base_url}, model={self.model}"
        )

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def call_gemini(
        self,
        messages: list,
        temperature: float = 0.0,
        response_format: dict = None,
        model: str = None,
    ) -> str:
        """
        Send a request to the Gemini model via the local proxy.

        Args:
            messages: A list of message dictionaries (role, content).
            temperature: Sampling temperature.
            response_format: Optional dict, e.g., {"type": "json_object"}
            model: Optional model name override.

        Returns:
            The content of the response message.
        """
        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                stream=False,
                response_format=response_format,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None

    def call_with_schema(
        self,
        messages: list,
        response_model: Type[T],
        temperature: float = 0.0,
        model: str = None,
        max_retries: int = 2,
    ) -> T | None:
        """
        呼叫 LLM 並使用 Pydantic Schema 驗證輸出。

        Args:
            messages: 訊息列表 (role, content)。
            response_model: Pydantic BaseModel 類別（例如 BatchMetaExtraction）。
            temperature: 採樣溫度。
            model: 可選的模型名稱覆寫。
            max_retries: 驗證失敗時的最大重試次數。

        Returns:
            驗證後的 Pydantic 模型實例，或 None（如果失敗）。
        """
        # 生成 JSON Schema
        schema = response_model.model_json_schema()
        schema_name = response_model.__name__

        # 構建 OpenAI 格式的 response_format
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        }

        for attempt in range(max_retries + 1):
            try:
                # 呼叫 LLM
                response_text = self.call_gemini(
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                    model=model,
                )

                if not response_text:
                    print(f"Empty response from LLM (attempt {attempt + 1})")
                    continue

                # 清理可能的 Markdown code blocks
                clean_text = response_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                # 解析並驗證 JSON
                data = json.loads(clean_text)
                validated = response_model.model_validate(data)

                print(f"✓ Schema 驗證成功 ({schema_name})")
                return validated

            except json.JSONDecodeError as e:
                print(f"JSON 解析錯誤 (attempt {attempt + 1}): {e}")
                print(f"Raw text: {response_text[:200]}...")
            except ValidationError as e:
                print(f"Pydantic 驗證錯誤 (attempt {attempt + 1}): {e}")
            except Exception as e:
                print(f"未預期的錯誤 (attempt {attempt + 1}): {e}")

            if attempt < max_retries:
                print(f"重試中... ({attempt + 1}/{max_retries})")

        print(f"✗ Schema 驗證失敗，已達最大重試次數")
        return None


if __name__ == "__main__":
    # Simple connection test
    client = LLMClient()
    response = client.call_gemini(
        [{"role": "user", "content": "Hello, are you working?"}]
    )
    print("Response:", response)
