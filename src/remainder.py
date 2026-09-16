import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------
# Database
# --------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "database" / "assistant.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# --------------------------------------------------
# Find stale topics
# --------------------------------------------------

def get_stale_topics(days=3):
    connection = get_connection()
    cursor = connection.cursor()

    cutoff_date = datetime.now() - timedelta(days=days)

    cursor.execute(
        """
        SELECT
            subjects.name,
            topics.topic_name,
            topics.status,
            topics.last_touched_date
        FROM topics
        JOIN subjects
            ON topics.subject_id = subjects.id
        WHERE topics.status != 'done'
          AND topics.last_touched_date < ?
        ORDER BY topics.last_touched_date ASC
        """,
        (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
    )

    results = cursor.fetchall()

    connection.close()

    return results


# --------------------------------------------------
# Find stale tasks
# --------------------------------------------------

def get_stale_tasks(days=3):
    connection = get_connection()
    cursor = connection.cursor()

    cutoff_date = datetime.now() - timedelta(days=days)

    cursor.execute(
        """
        SELECT
            task_name,
            category,
            status,
            created_date,
            due_date
        FROM tasks
        WHERE status != 'done'
          AND created_date < ?
        ORDER BY created_date ASC
        """,
        (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
    )

    results = cursor.fetchall()

    connection.close()

    return results


# --------------------------------------------------
# Calculate how many days old something is
# --------------------------------------------------

def days_old(date_string):
    date = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    difference = datetime.now() - date

    return difference.days


# --------------------------------------------------
# Print reminders
# --------------------------------------------------

def show_reminders():
    stale_topics = get_stale_topics(days=3)
    stale_tasks = get_stale_tasks(days=3)

    print("\n========================================")
    print("        JARVIS MEMORY CHECK")
    print("========================================")

    if not stale_topics and not stale_tasks:
        print("\n✓ Nothing important looks stale.")
        print("You're up to date!")

        return

    # --------------------------------------------------
    # Topics
    # --------------------------------------------------

    if stale_topics:
        print("\n📚 Topics you haven't touched:\n")

        for subject, topic, status, last_touched in stale_topics:

            age = days_old(last_touched)

            print(
                f"• {topic} ({subject}) "
                f"— {age} days ago"
            )

    # --------------------------------------------------
    # Tasks
    # --------------------------------------------------

    if stale_tasks:
        print("\n📋 Pending tasks:\n")

        for task, category, status, created_date, due_date in stale_tasks:

            age = days_old(created_date)

            print(
                f"• {task} "
                f"— pending for {age} days"
            )

    print("\n========================================")


# --------------------------------------------------
# Test
# --------------------------------------------------

if __name__ == "__main__":
    show_reminders()