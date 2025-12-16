"""Check month format in database"""
from sqlite_utils import Database

db = Database("database/announcements.db")
months = db.execute("SELECT DISTINCT month FROM announcements ORDER BY month").fetchall()

print("Current month formats in database:")
for (month,) in months:
    print(f"  - {month}")
