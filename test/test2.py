import os
import dotenv

dotenv.load_dotenv()
from openai import AzureOpenAI

endpoint = "https://royaoaieus.openai.azure.com/"
model_name = "gpt-4o-mini"
deployment = "gpt-4o-mini"
subscription_key = os.getenv("PROXY_API_KEY")
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "hi",
        },
    ],
    max_tokens=4096,
    temperature=1.0,
    top_p=1.0,
    model=deployment,
)

print(response.choices[0].message.content)
