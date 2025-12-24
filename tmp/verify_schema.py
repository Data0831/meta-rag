import sys
sys.path.insert(0, r'F:\projects\meta-rag')

from src.schema.schemas import SearchIntent
import json

schema = SearchIntent.model_json_schema()
print("Generated JSON Schema:")
print(json.dumps(schema, indent=2))

print("\n" + "="*50)
if "$defs" in schema:
    print("WARNING: Schema contains $defs")
else:
    print("✓ Schema does NOT contain $defs")

if "$ref" in json.dumps(schema):
    print("WARNING: Schema contains $ref")
else:
    print("✓ Schema does NOT contain $ref")

print("\n" + "="*50)
print("\nTesting SearchIntent creation:")
intent = SearchIntent(
    year_month=["2025-12"],
    workspaces=["General"],
    keyword_query="test query",
    semantic_query="test semantic query",
)
print("✓ SearchIntent created successfully")
print(f"  year_month: {intent.year_month}")
print(f"  workspaces: {intent.workspaces}")
