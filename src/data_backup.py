"""
JARVIS-lite: 1-Click Backup & JSON/CSV Data Exporter (Phase 7)

Provides:
1. Complete SQLite database snapshot export to JSON.
2. Placement applications export to CSV.
3. Study roadmap & topic mastery export to CSV.
4. Timestamped backups in backups/ directory.
"""

import sys
import csv
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "assistant.db"
BACKUP_DIR = BASE_DIR / "backups"


def get_connection():
    return sqlite3.connect(DB_PATH)


def export_database_to_json() -> str:
    """Exports all tables into a single timestamped JSON backup."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = BACKUP_DIR / f"jarvis_backup_{timestamp}.json"

    conn = get_connection()
    cur = conn.cursor()

    # Discover all user tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]

    backup_data = {
        "timestamp": datetime.now().isoformat(),
        "database": "assistant.db",
        "tables": {}
    }

    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]

        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()

        backup_data["tables"][table] = [dict(zip(cols, row)) for row in rows]

    conn.close()

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2)

    return str(out_file)


def export_applications_to_csv() -> str:
    """Exports all placement applications to CSV."""
    BACKUP_DIR.mkdir(exist_ok=True)
    out_file = BACKUP_DIR / "placement_applications.csv"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, company, role, stage, result, notes, applied_date
        FROM applications
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Company", "Role", "Stage", "Result", "Notes", "Applied Date"])
        writer.writerows(rows)

    return str(out_file)


def export_study_topics_to_csv() -> str:
    """Exports all subjects and topics to CSV."""
    BACKUP_DIR.mkdir(exist_ok=True)
    out_file = BACKUP_DIR / "study_roadmap.csv"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT subjects.name, topics.topic_name, topics.status, topics.last_touched_date
        FROM topics
        JOIN subjects ON topics.subject_id = subjects.id
        ORDER BY subjects.name, topics.id
    """)
    rows = cur.fetchall()
    conn.close()

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Subject", "Topic Name", "Status", "Last Touched"])
        writer.writerows(rows)

    return str(out_file)
