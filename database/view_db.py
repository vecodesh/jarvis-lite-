import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "assistant.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

print("\n=== SUBJECTS ===")

cursor.execute("""
    SELECT id, name, created_date
    FROM subjects
""")

for row in cursor.fetchall():
    print(row)


print("\n=== TOPICS ===")

cursor.execute("""
    SELECT
        topics.id,
        subjects.name,
        topics.topic_name,
        topics.status,
        topics.last_touched_date
    FROM topics
    JOIN subjects
        ON topics.subject_id = subjects.id
""")

for row in cursor.fetchall():
    print(row)


print("\n=== TASKS ===")

cursor.execute("""
    SELECT
        id,
        task_name,
        category,
        status,
        created_date,
        due_date
    FROM tasks
""")

for row in cursor.fetchall():
    print(row)


print("\n=== LOGS ===")

cursor.execute("""
    SELECT id, timestamp, raw_text, parsed_summary
    FROM logs
""")

for row in cursor.fetchall():
    print(row)


connection.close()