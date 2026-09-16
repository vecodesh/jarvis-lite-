import sqlite3
from pathlib import Path

# assistant.db will live in the database/ folder
DB_PATH = Path(__file__).parent / "assistant.db"


def create_database():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Subjects
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Topics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            topic_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'not_started'
                CHECK(status IN ('not_started', 'in_progress', 'done')),
            last_touched_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (subject_id)
                REFERENCES subjects(id)
                ON DELETE CASCADE,

            UNIQUE(subject_id, topic_name)
        )
    """)

    # Tasks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            category TEXT NOT NULL
                CHECK(category IN ('life_admin', 'placement', 'academic')),
            status TEXT NOT NULL DEFAULT 'pending',
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            due_date TEXT
        )
    """)

    # Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            raw_text TEXT NOT NULL,
            parsed_summary TEXT
        )
    """)

    # Indexes for future "stale" detection
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_topics_last_touched
        ON topics(last_touched_date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_due_date
        ON tasks(due_date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp
        ON logs(timestamp)
    """)

    connection.commit()
    connection.close()

    print(f"Database created successfully: {DB_PATH}")


if __name__ == "__main__":
    create_database()