import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "assistant.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

tables = cursor.fetchall()

print("Tables in assistant.db:")
for table in tables:
    print(f"  ✓ {table[0]}")

connection.close()