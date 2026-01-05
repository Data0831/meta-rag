import os
import json
import sys
import datetime
from typing import Type, TypeVar, List, Dict, Any
from openai import AzureOpenAI, APIError, APIStatusError
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from src.tool.ANSI import print_red
from src.log.logManager import LogManager

load_dotenv()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        endpoint: str = None,
        api_key: str = None,
        model: str = None,
        api_version: str = None,
    ):
        self.endpoint = endpoint or os.getenv(
            "AZURE_ENDPOINT", "https://royaoaieus.openai.azure.com/"
        )
        self.api_key = api_key or os.getenv("PROXY_API_KEY")
        self.model = model or os.getenv("AZURE_DEPLOYMENT", "gpt-4o-mini")
        self.api_version = api_version or os.getenv(
            "AZURE_API_VERSION", "2024-12-01-preview"
        )

        print(
            f"✓ Initializing LLMClient (Azure) with endpoint={self.endpoint}, model={self.model}\n"
        )

        if not self.api_key:
            print_red("Warning: PROXY_API_KEY not found in environment variables.")

        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    def _add_additional_properties(self, schema: dict) -> dict:
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                schema["additionalProperties"] = False
                if "properties" in schema:
                    schema["required"] = list(schema["properties"].keys())
            for key, value in schema.items():
                schema[key] = self._add_additional_properties(value)
        elif isinstance(schema, list):
            return [self._add_additional_properties(item) for item in schema]
        return schema

    def _log_request(
        self,
        messages: list,
        response_content: str,
        temperature: float,
        response_format: dict,
        model: str,
    ):
        LogManager.log_client(
            messages=messages,
            response_content=response_content,
            temperature=temperature,
            response_format=response_format,
            model=model or self.model,
        )

    def call_gemini(
        self,
        messages: list,
        temperature: float = 0.0,
        response_format: dict = None,
        model: str = None,
    ) -> str:
        response_content = None
        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                stream=False,
                response_format=response_format,
            )
            response_content = response.choices[0].message.content
        except Exception as e:
            print_red(f"Error calling LLM: {e}")
            response_content = None

        self._log_request(
            messages, response_content, temperature, response_format, model
        )

        return response_content

    def call_with_schema(
        self,
        messages: list,
        response_model: Type[T],
        temperature: float = 0.0,
        model: str = None,
        max_retries: int = 1,
    ) -> Dict[str, Any]:
        schema = response_model.model_json_schema()
        schema_name = response_model.__name__

        schema = self._add_additional_properties(schema)

        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        }

        for attempt in range(max_retries + 1):
            try:
                response_text = self.call_gemini(
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                    model=model,
                )

                if not response_text:
                    print_red(f"Empty response from LLM (attempt {attempt + 1})")
                    continue

                clean_text = response_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                # Normalize full-width brackets to half-width to ensure citations are correctly formatted
                clean_text = clean_text.replace("【", "[").replace("】", "]")

                data = json.loads(clean_text)
                validated = response_model.model_validate(data)

                print(f"✓ Schema 驗證成功 ({schema_name})")
                return {"status": "success", "result": validated}

            except json.JSONDecodeError as e:
                print_red(f"JSON 解析錯誤 (attempt {attempt + 1}): {e}")
                print_red(f"Raw text: {response_text[:200]}...")
            except ValidationError as e:
                print_red(f"Pydantic 驗證錯誤 (attempt {attempt + 1}): {e}")
            except Exception as e:
                print_red(f"未預期的錯誤 (attempt {attempt + 1}): {e}")

            if attempt < max_retries:
                print(f"重試中... ({attempt + 1}/{max_retries})")

        print_red(f"✗ Schema 驗證失敗，已達最大重試次數")
        return {
            "status": "failed",
            "error": f"LLM schema validation failed after {max_retries + 1} attempts",
            "stage": "llm_schema_validation",
        }


if __name__ == "__main__":
    client = LLMClient()
    response = client.call_gemini(
        [{"role": "user", "content": "Hello, are you working?"}]
    )
    print("Response:", response)
