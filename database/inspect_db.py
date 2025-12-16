import os
import sys
from sqlite_utils import Database

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DB_PATH = os.path.join("database", "announcements.db")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        return

    db = Database(DB_PATH)
    
    if "announcements" not in db.table_names():
        print("Table 'announcements' does not exist.")
        return

    count = db["announcements"].count
    print(f"Total documents in SQLite: {count}")
    
    print("\n--- First 5 Documents ---")
    for row in db["announcements"].rows_where(limit=5):
        print(f"UUID: {row.get('uuid')}")
        print(f"Month: {row.get('month')}")
        print(f"Category: {row.get('category')}")
        print(f"Title: {row.get('title')}")
        print("-" * 20)

if __name__ == "__main__":
    main()

