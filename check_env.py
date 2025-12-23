import os
from dotenv import load_dotenv

load_dotenv()

print("=== Environment Variables Check ===")
print(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT', 'NOT SET')}")
print(f"AZURE_OPENAI_KEY: {'SET (length: ' + str(len(os.getenv('AZURE_OPENAI_KEY', ''))) + ')' if os.getenv('AZURE_OPENAI_KEY') else 'NOT SET'}")
print(f"AZURE_DEPLOYMENT_NAME: {os.getenv('AZURE_DEPLOYMENT_NAME', 'NOT SET')}")
print(f"AZURE_API_VERSION: {os.getenv('AZURE_API_VERSION', 'NOT SET')}")
