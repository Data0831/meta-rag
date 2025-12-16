"""
SQLite Database Inspection Tool
Display tables and their contents from announcements.db
"""
import sqlite3
import os
from typing import List, Tuple

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "announcements.db")


def get_tables(cursor: sqlite3.Cursor) -> List[str]:
    """Get all table names from the database"""
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]


def get_table_info(cursor: sqlite3.Cursor, table_name: str) -> List[Tuple]:
    """Get column information for a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def get_row_count(cursor: sqlite3.Cursor, table_name: str) -> int:
    """Get the number of rows in a table"""
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def display_table_data(cursor: sqlite3.Cursor, table_name: str, limit: int = 5):
    """Display sample data from a table"""
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    rows = cursor.fetchall()

    if not rows:
        print("  (No data)")
        return

    # Get column names
    columns = [description[0] for description in cursor.description]

    # Calculate column widths
    col_widths = [len(col) for col in columns]
    for row in rows:
        for i, val in enumerate(row):
            val_str = str(val) if val is not None else "NULL"
            # Truncate long strings
            if len(val_str) > 50:
                val_str = val_str[:47] + "..."
            col_widths[i] = max(col_widths[i], len(val_str))

    # Print header
    header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
    print(f"  {header}")
    print(f"  {'-' * len(header)}")

    # Print rows
    for row in rows:
        row_str = " | ".join(
            str(val).ljust(col_widths[i])[:col_widths[i]] if val is not None else "NULL".ljust(col_widths[i])
            for i, val in enumerate(row)
        )
        print(f"  {row_str}")


def main():
    """Main function to display database information"""
    print("=" * 80)
    print("SQLite Database Inspector")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print()

    if not os.path.exists(DB_PATH):
        print("❌ Database file does not exist!")
        return

    # Get file size
    file_size = os.path.getsize(DB_PATH)
    print(f"File Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
    print()

    # Connect to database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all tables
        tables = get_tables(cursor)

        if not tables:
            print("⚠️  No tables found in database (database is empty)")
            return

        print(f"📊 Found {len(tables)} table(s)")
        print("=" * 80)
        print()

        # Display information for each table
        for table_name in tables:
            print(f"📋 Table: {table_name}")
            print("-" * 80)

            # Get row count
            row_count = get_row_count(cursor, table_name)
            print(f"  Rows: {row_count:,}")
            print()

            # Get column info
            columns_info = get_table_info(cursor, table_name)
            print("  Columns:")
            for col in columns_info:
                col_id, col_name, col_type, not_null, default, pk = col
                pk_marker = " (PRIMARY KEY)" if pk else ""
                null_marker = " NOT NULL" if not_null else ""
                print(f"    - {col_name}: {col_type}{null_marker}{pk_marker}")
            print()

            # Display sample data
            if row_count > 0:
                print(f"  Sample Data (first 5 rows):")
                display_table_data(cursor, table_name, limit=5)
            else:
                print("  (No data to display)")

            print()
            print()

        conn.close()

    except sqlite3.Error as e:
        print(f"❌ SQLite Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
