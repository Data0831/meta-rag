import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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


if __name__ == "__main__":
    # Simple connection test
    client = LLMClient()
    response = client.call_gemini(
        [{"role": "user", "content": "Hello, are you working?"}]
    )
    print("Response:", response)
