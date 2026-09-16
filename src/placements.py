"""
JARVIS-lite: Placement & Job Application Tracker (Phase 5 - Feature 3d)

Independent feature module managing job and internship applications:
- Independent table: applications (company, role, stage, applied_date, result, notes)
- Does not merge into the existing tasks table
- Full CRUD API with CLI and GUI integration
- Automatic table initialization (preserving frozen init_db.py)
"""

import sys
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
sys.path.insert(0, str(BASE_DIR / "src"))

from assistant import DB_PATH, get_connection

VALID_STAGES = [
    "Applied",
    "OA (Online Assessment)",
    "Technical Interview",
    "HR Interview",
    "Offer Received",
    "Rejected",
]

VALID_RESULTS = [
    "In Progress",
    "Selected",
    "Rejected",
    "Withdrawn",
]


# --------------------------------------------------
# Table Initialization
# --------------------------------------------------

def init_applications_table():
    """
    Creates the applications table if it does not exist.
    Maintains independence without modifying the frozen init_db.py file.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'Applied',
            applied_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            result TEXT NOT NULL DEFAULT 'In Progress',
            notes TEXT
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_company
        ON applications(company)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_applications_stage
        ON applications(stage)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT,
            round_type TEXT NOT NULL,
            question_text TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Medium',
            notes TEXT,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_company_questions_company
        ON company_questions(company)
    """)

    conn.commit()
    conn.close()


# Ensure table exists upon module import
init_applications_table()


# --------------------------------------------------
# Data Operations (CRUD)
# --------------------------------------------------

def add_application(company, role, stage="Applied", applied_date=None, result="In Progress", notes=""):
    """
    Adds a new job/internship application.
    """
    company = company.strip()
    role = role.strip()
    if not company or not role:
        raise ValueError("Company name and role cannot be empty.")

    if not applied_date:
        applied_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO applications (company, role, stage, applied_date, result, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (company, role, stage, applied_date, result, notes.strip()))

    app_id = cur.lastrowid
    conn.commit()
    conn.close()

    return app_id


def update_application_stage(app_id, new_stage, new_result=None, notes=None):
    """
    Updates the stage, result, or notes of an existing application.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, company, role, stage, result, notes FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Application ID {app_id} not found.")

    updated_result = new_result if new_result is not None else row[4]
    updated_notes = notes if notes is not None else row[5]

    # Auto-adjust result if stage implies final decision
    if new_stage == "Offer Received" and new_result is None:
        updated_result = "Selected"
    elif new_stage == "Rejected" and new_result is None:
        updated_result = "Rejected"

    cur.execute("""
        UPDATE applications
        SET stage = ?, result = ?, notes = ?
        WHERE id = ?
    """, (new_stage, updated_result, updated_notes, app_id))

    conn.commit()
    conn.close()


def get_applications(stage_filter=None, result_filter=None):
    """
    Returns list of applications with optional filtering.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT id, company, role, stage, applied_date, result, notes FROM applications"
    params = []
    conditions = []

    if stage_filter:
        conditions.append("stage = ?")
        params.append(stage_filter)

    if result_filter:
        conditions.append("result = ?")
        params.append(result_filter)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()

    return rows


def delete_application(app_id):
    """
    Deletes an application by ID.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_placement_summary():
    """
    Returns summary statistics for placement dashboard.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM applications")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications WHERE stage = 'Offer Received' OR result = 'Selected'")
    offers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications WHERE result = 'In Progress'")
    in_progress = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications WHERE stage LIKE '%Interview%'")
    interviews = cur.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "in_progress": in_progress,
        "interviews": interviews,
        "offers": offers,
    }


# --------------------------------------------------
# Kanban & Pipeline Promotion Helpers
# --------------------------------------------------

KANBAN_COLUMNS = [
    "Applied",
    "OA (Online Assessment)",
    "Technical Interview",
    "HR Interview",
    "Offer Received",
]


def get_kanban_data(company_filter: str = None):
    """Returns applications grouped by active Kanban stages, with optional company filtering."""
    conn = get_connection()
    cur = conn.cursor()
    if company_filter and company_filter.strip():
        cur.execute("""
            SELECT id, company, role, stage, applied_date, result, notes
            FROM applications
            WHERE LOWER(company) LIKE LOWER(?)
            ORDER BY id DESC
        """, (f"%{company_filter.strip()}%",))
    else:
        cur.execute("""
            SELECT id, company, role, stage, applied_date, result, notes
            FROM applications
            ORDER BY id DESC
        """)
    rows = cur.fetchall()
    conn.close()

    kanban = {col: [] for col in KANBAN_COLUMNS}
    kanban["Rejected / Other"] = []

    for r in rows:
        app = {
            "id": r[0],
            "company": r[1],
            "role": r[2],
            "stage": r[3],
            "applied_date": r[4],
            "result": r[5],
            "notes": r[6] or "",
        }
        if app["stage"] in kanban:
            kanban[app["stage"]].append(app)
        else:
            kanban["Rejected / Other"].append(app)

    return kanban


def promote_application(app_id: int):
    """Moves an application to the next logical stage."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT stage FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    current_stage = row[0]
    if current_stage in KANBAN_COLUMNS:
        idx = KANBAN_COLUMNS.index(current_stage)
        if idx < len(KANBAN_COLUMNS) - 1:
            next_stage = KANBAN_COLUMNS[idx + 1]
            cur.execute("UPDATE applications SET stage = ? WHERE id = ?", (next_stage, app_id))
            conn.commit()
            conn.close()
            return next_stage
    conn.close()
    return current_stage


def demote_application(app_id: int):
    """Moves an application to the previous stage."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT stage FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    current_stage = row[0]
    if current_stage in KANBAN_COLUMNS:
        idx = KANBAN_COLUMNS.index(current_stage)
        if idx > 0:
            prev_stage = KANBAN_COLUMNS[idx - 1]
            cur.execute("UPDATE applications SET stage = ? WHERE id = ?", (prev_stage, app_id))
            conn.commit()
            conn.close()
            return prev_stage
    conn.close()
    return current_stage


# --------------------------------------------------
# Company Question Vault
# --------------------------------------------------

def add_company_question(company: str, role: str, round_type: str, question_text: str, difficulty: str = "Medium", notes: str = ""):
    """Saves an actual question asked by a company during a placement round."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO company_questions (company, role, round_type, question_text, difficulty, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (company.strip(), role.strip(), round_type.strip(), question_text.strip(), difficulty.strip(), notes.strip()))
    conn.commit()
    q_id = cur.lastrowid
    conn.close()
    return q_id


def get_company_questions(company: str = None):
    """Fetches stored company interview questions."""
    conn = get_connection()
    cur = conn.cursor()
    if company:
        cur.execute("""
            SELECT id, company, role, round_type, question_text, difficulty, notes, created_date
            FROM company_questions
            WHERE LOWER(company) LIKE LOWER(?)
            ORDER BY id DESC
        """, (f"%{company.strip()}%",))
    else:
        cur.execute("""
            SELECT id, company, role, round_type, question_text, difficulty, notes, created_date
            FROM company_questions
            ORDER BY id DESC
        """)
    rows = cur.fetchall()
    conn.close()

    return [{
        "id": r[0],
        "company": r[1],
        "role": r[2],
        "round_type": r[3],
        "question_text": r[4],
        "difficulty": r[5],
        "notes": r[6],
        "created_date": r[7],
    } for r in rows]


def delete_company_question(q_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM company_questions WHERE id = ?", (q_id,))
    conn.commit()
    conn.close()


# --------------------------------------------------
# CLI Interface
# --------------------------------------------------

def print_applications_table():
    apps = get_applications()
    summary = get_placement_summary()

    print("\n==========================================================================")
    print("                      PLACEMENT APPLICATIONS TRACKER")
    print("==========================================================================")
    print(f"Total: {summary['total']} | Active: {summary['in_progress']} | Interviews: {summary['interviews']} | Offers: {summary['offers']}")
    print("-" * 74)

    if not apps:
        print("No job applications tracked yet.")
        print("=" * 74)
        return

    print(f"{'ID':<4} {'Company':<18} {'Role':<18} {'Stage':<18} {'Result':<12}")
    print("-" * 74)

    for app in apps:
        app_id, company, role, stage, applied_date, result, notes = app
        print(f"{app_id:<4} {company[:17]:<18} {role[:17]:<18} {stage[:17]:<18} {result[:11]:<12}")

    print("=" * 74 + "\n")


def placement_cli():
    while True:
        print("\n--- PLACEMENT TRACKER MENU ---")
        print("1. View all applications & stats")
        print("2. Add new application")
        print("3. Update application stage")
        print("4. Delete application")
        print("5. Return to main")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            print_applications_table()

        elif choice == "2":
            company = input("Company Name: ").strip()
            role = input("Role / Job Title: ").strip()
            if not company or not role:
                print("Company and Role cannot be empty.")
                continue

            print("\nSelect Stage:")
            for i, stg in enumerate(VALID_STAGES, 1):
                print(f"  {i}. {stg}")
            stg_idx = input("Stage (default 1: Applied): ").strip()
            stage = VALID_STAGES[int(stg_idx) - 1] if stg_idx.isdigit() and 1 <= int(stg_idx) <= len(VALID_STAGES) else "Applied"

            notes = input("Notes (optional): ").strip()
            app_id = add_application(company, role, stage=stage, notes=notes)
            print(f"✓ Application #{app_id} added successfully.")

        elif choice == "3":
            print_applications_table()
            app_id_str = input("Enter Application ID to update: ").strip()
            if not app_id_str.isdigit():
                print("Invalid ID.")
                continue

            print("\nSelect New Stage:")
            for i, stg in enumerate(VALID_STAGES, 1):
                print(f"  {i}. {stg}")
            stg_idx = input("Stage number: ").strip()
            if not (stg_idx.isdigit() and 1 <= int(stg_idx) <= len(VALID_STAGES)):
                print("Invalid stage choice.")
                continue

            new_stage = VALID_STAGES[int(stg_idx) - 1]
            notes = input("Update notes (or press Enter to keep current): ").strip()
            update_application_stage(int(app_id_str), new_stage, notes=notes if notes else None)
            print(f"✓ Application #{app_id_str} stage updated to '{new_stage}'.")

        elif choice == "4":
            app_id_str = input("Enter Application ID to delete: ").strip()
            if app_id_str.isdigit():
                delete_application(int(app_id_str))
                print(f"✓ Application #{app_id_str} deleted.")
            else:
                print("Invalid ID.")

        elif choice == "5":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_applications_table()
    else:
        placement_cli()
