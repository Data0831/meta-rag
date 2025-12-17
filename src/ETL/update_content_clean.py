"""
Quick Update Script - Add content_clean field to existing processed.json

This script updates existing processed.json to add the content_clean field
without re-running the entire ETL pipeline.

Usage:
    python src/ETL/update_content_clean.py
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import PROCESSED_OUTPUT
from src.ETL.content_cleaner import clean_content_for_search


def update_processed_json():
    """Update processed.json with content_clean field."""

    # Check if file exists
    if not os.path.exists(PROCESSED_OUTPUT):
        print(f"❌ Error: File not found at {PROCESSED_OUTPUT}")
        print("Please run the ETL pipeline first to generate processed.json")
        return False

    # Load existing data
    print(f"Loading data from {PROCESSED_OUTPUT}...")
    try:
        with open(PROCESSED_OUTPUT, 'r', encoding='utf-8') as f:
            docs = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON: {e}")
        return False

    if not isinstance(docs, list):
        print(f"❌ Error: Expected a list, got {type(docs)}")
        return False

    print(f"✓ Loaded {len(docs)} documents")

    # Update each document
    print("\nUpdating content_clean field...")
    updated_count = 0
    skipped_count = 0

    for i, doc in enumerate(docs):
        if 'original_content' not in doc:
            print(f"⚠ Warning: Document {i} missing 'original_content', skipping")
            skipped_count += 1
            continue

        # Clean the content
        original = doc['original_content']
        cleaned = clean_content_for_search(original)

        # Add or update content_clean field
        doc['content_clean'] = cleaned
        updated_count += 1

        # Show progress
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(docs)}...")

    print(f"\n✓ Updated {updated_count} documents")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} documents (missing original_content)")

    # Create backup
    backup_path = PROCESSED_OUTPUT + ".backup"
    print(f"\nCreating backup at {backup_path}...")
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        print("✓ Backup created")
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False

    # Save updated data
    print(f"\nSaving updated data to {PROCESSED_OUTPUT}...")
    try:
        with open(PROCESSED_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        print("✓ File updated successfully")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False

    # Show example
    if docs:
        print("\n" + "=" * 80)
        print("Example (First Document):")
        print("=" * 80)
        first_doc = docs[0]

        original = first_doc.get('original_content', '')
        cleaned = first_doc.get('content_clean', '')

        print(f"\nTitle: {first_doc.get('title', 'N/A')}")
        print(f"\nOriginal Content (first 200 chars):")
        print(f"  {original[:200]}...")
        print(f"\nCleaned Content (first 200 chars):")
        print(f"  {cleaned[:200]}...")

        # Stats
        url_count_estimate = original.count('http') + original.count('www.')
        print(f"\nStats:")
        print(f"  Original length: {len(original)} chars")
        print(f"  Cleaned length: {len(cleaned)} chars")
        print(f"  Reduced by: {len(original) - len(cleaned)} chars ({(1 - len(cleaned)/len(original))*100:.1f}%)")
        print(f"  Estimated URLs removed: ~{url_count_estimate}")

    print("\n" + "=" * 80)
    print("✓ Update Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review the example above to verify cleaning worked correctly")
    print("2. Run: python src/vectorPreprocessing.py")
    print("   - Choose option 1 to clear Meilisearch index")
    print("   - Choose option 2 to regenerate embeddings and write to Meilisearch")
    print("3. Test your search to verify improved results")

    return True


def main():
    """Main entry point."""
    print("=" * 80)
    print("Content Clean Field Update Script")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Load your existing processed.json")
    print("2. Add content_clean field (URLs removed) to each document")
    print("3. Create a backup before updating")
    print("4. Save the updated file")
    print("\n" + "=" * 80)

    response = input("\nDo you want to continue? (y/n): ").strip().lower()

    if response != 'y':
        print("Operation cancelled.")
        return

    success = update_processed_json()

    if success:
        print("\n✓ All done! Your processed.json has been updated.")
    else:
        print("\n❌ Update failed. Please check the error messages above.")
        print("Your original data should still be intact.")


if __name__ == "__main__":
    main()
