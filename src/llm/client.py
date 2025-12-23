import os
import json
import sys
from typing import Type, TypeVar, List
from openai import AzureOpenAI, APIError, APIStatusError
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

# Load environment variables
load_dotenv()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, endpoint: str = None, api_key: str = None, model: str = None, api_version: str = None):
        """
        Initialize the LLM Client using Azure OpenAI.

        Args:
            endpoint: The Azure Endpoint URL.
            api_key: The Azure API Key.
            model: The deployment name (e.g., "gpt-4o-mini").
            api_version: The API version to use.
        """
        # Defaults based on test2.py and user request
        self.endpoint = endpoint or os.getenv("AZURE_ENDPOINT", "https://royaoaieus.openai.azure.com/")
        self.api_key = api_key or os.getenv("PROXY_API_KEY")
        self.model = model or os.getenv("AZURE_DEPLOYMENT", "gpt-4o-mini")
        self.api_version = api_version or os.getenv("AZURE_API_VERSION", "2024-12-01-preview")

        print(
            f"Initializing LLMClient (Azure) with endpoint={self.endpoint}, model={self.model}"
        )
        
        if not self.api_key:
             print("Warning: PROXY_API_KEY not found in environment variables.")

        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )

    def call_gemini(
        self,
        messages: list,
        temperature: float = 0.0,
        response_format: dict = None,
        model: str = None,
    ) -> str:
        """
        Send a request to the Azure OpenAI model.
        (Method name kept as call_gemini for backward compatibility)

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
        max_retries: int = 0,
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

        for attempt in range(max_retries):
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