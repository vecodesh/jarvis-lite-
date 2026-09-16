"""
JARVIS-lite: 6:00 AM Stark Battle Plan & Evening Debrief Engine

Eliminates daily task paralysis by generating a strict 3-Target Daily Protocol:
1. Target 1 (DSA / Coding): One curated or high-frequency algorithm to solve.
2. Target 2 (CS Fundamentals): One stale topic (>3 days untouched) to revise.
3. Target 3 (Life / Admin / Placement): One high-priority pending task/deadline.

Includes:
- Target completion tracking (checkbox persistence).
- Evening Debrief generator with execution scoring (0-100%) and readiness bonus.
"""

import sys
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

import ollama

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "assistant.db"
MODEL = "llama3.1:8b"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_battle_plan_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_battle_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_date TEXT NOT NULL UNIQUE,
            target1_text TEXT NOT NULL,
            target1_done INTEGER NOT NULL DEFAULT 0,
            target2_text TEXT NOT NULL,
            target2_done INTEGER NOT NULL DEFAULT 0,
            target3_text TEXT NOT NULL,
            target3_done INTEGER NOT NULL DEFAULT 0,
            evening_debrief_text TEXT,
            execution_score INTEGER DEFAULT 0,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_battle_plan_table()


def _get_target1_coding() -> str:
    """Selects an algorithm target from coding submissions or curated catalogue."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT problem_title FROM coding_submissions")
    done_titles = [r[0].lower() for r in cur.fetchall()]
    conn.close()

    default_problems = [
        "Solve 'Two Sum' using O(N) Hash Map in Coding Arena",
        "Solve 'Valid Parentheses' using Stack in Coding Arena",
        "Solve 'Longest Substring Without Repeating Characters' (Sliding Window)",
        "Solve 'Merge Intervals' (Array Sorting & Merge)",
        "Implement 'Course Schedule' using Kahn's Topological Sort",
        "Implement 'LRU Cache' using Doubly Linked List & Hash Map",
        "Practice Binary Search on Rotated Sorted Array",
        "Implement Tree Level Order Traversal (BFS)",
    ]

    for p in default_problems:
        p_name = p.split("'")[1].lower() if "'" in p else p.lower()
        if p_name not in done_titles:
            return p

    return default_problems[0]


def _get_target2_stale_topic() -> str:
    """Selects an untouched CS topic from topics table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.topic_name, s.name,
               (julianday('now') - julianday(t.last_touched_date)) as days_stale
        FROM topics t
        JOIN subjects s ON t.subject_id = s.id
        ORDER BY days_stale DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        topic, subj, days = row
        d_val = int(days) if days else 0
        return f"Revise '{topic}' in {subj} ({d_val}d stale — flashcards or tutor)"

    return "Revise Operating Systems: Virtual Memory & Page Replacement algorithms"


def _get_target3_deliverable() -> str:
    """Selects a pending life or placement deliverable from tasks table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT task_name, category FROM tasks
        WHERE status != 'done'
        ORDER BY id ASC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        return f"Deliverable: {row[0]} [{row[1]}]"

    # Fallback to application OA check
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT company, role, stage FROM applications
        WHERE stage IN ('Applied', 'OA (Online Assessment)')
        LIMIT 1
    """)
    app_row = cur.fetchone()
    conn.close()

    if app_row:
        return f"Follow up / Check status for {app_row[0]} ({app_row[1]}) [{app_row[2]}]"

    return "Review and update resume profile with latest project bullet points"


def generate_daily_battle_plan(date_str: str = None) -> dict:
    """
    Generates or fetches today's 3-Target Battle Plan.
    """
    today = date_str or datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, plan_date, target1_text, target1_done,
               target2_text, target2_done, target3_text, target3_done,
               evening_debrief_text, execution_score
        FROM daily_battle_plans WHERE plan_date = ?
    """, (today,))
    row = cur.fetchone()

    if row:
        conn.close()
        return {
            "id": row[0],
            "plan_date": row[1],
            "target1": {"text": row[2], "done": bool(row[3])},
            "target2": {"text": row[4], "done": bool(row[5])},
            "target3": {"text": row[6], "done": bool(row[7])},
            "evening_debrief": row[8],
            "execution_score": row[9],
        }

    # Generate new plan for today
    t1 = _get_target1_coding()
    t2 = _get_target2_stale_topic()
    t3 = _get_target3_deliverable()

    cur.execute("""
        INSERT INTO daily_battle_plans
        (plan_date, target1_text, target2_text, target3_text, target1_done, target2_done, target3_done, execution_score)
        VALUES (?, ?, ?, ?, 0, 0, 0, 0)
    """, (today, t1, t2, t3))
    conn.commit()
    plan_id = cur.lastrowid
    conn.close()

    return {
        "id": plan_id,
        "plan_date": today,
        "target1": {"text": t1, "done": False},
        "target2": {"text": t2, "done": False},
        "target3": {"text": t3, "done": False},
        "evening_debrief": None,
        "execution_score": 0,
    }


def toggle_target_done(target_num: int, date_str: str = None) -> dict:
    """Toggles completion of target 1, 2, or 3."""
    today = date_str or datetime.now().strftime("%Y-%m-%d")
    plan = generate_daily_battle_plan(today)
    col = f"target{target_num}_done"
    curr_done = plan[f"target{target_num}"]["done"]
    new_done = 0 if curr_done else 1

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE daily_battle_plans SET {col} = ? WHERE plan_date = ?", (new_done, today))

    # Recalculate score
    cur.execute("""
        SELECT target1_done, target2_done, target3_done
        FROM daily_battle_plans WHERE plan_date = ?
    """, (today,))
    t1, t2, t3 = cur.fetchone()
    total_done = t1 + t2 + t3
    score = int((total_done / 3.0) * 100)
    cur.execute("UPDATE daily_battle_plans SET execution_score = ? WHERE plan_date = ?", (score, today))
    conn.commit()
    conn.close()

    return generate_daily_battle_plan(today)


def generate_evening_debrief(date_str: str = None) -> dict:
    """
    Compiles daily targets, computes execution score, and delivers an
    encouraging Tony Stark / JARVIS evening debrief.
    """
    today = date_str or datetime.now().strftime("%Y-%m-%d")
    plan = generate_daily_battle_plan(today)

    d1 = plan["target1"]["done"]
    d2 = plan["target2"]["done"]
    d3 = plan["target3"]["done"]
    completed_count = sum([d1, d2, d3])
    score = int((completed_count / 3.0) * 100)

    prompt = (
        f"You are JARVIS, Tony Stark's personal AI assistant holding the user accountable.\n\n"
        f"DAILY EXECUTION REPORT FOR {today}:\n"
        f"- Target 1 (Coding): {plan['target1']['text']} -> {'COMPLETED' if d1 else 'PENDING'}\n"
        f"- Target 2 (CS Revision): {plan['target2']['text']} -> {'COMPLETED' if d2 else 'PENDING'}\n"
        f"- Target 3 (Deliverable): {plan['target3']['text']} -> {'COMPLETED' if d3 else 'PENDING'}\n"
        f"- Completed: {completed_count}/3 ({score}%)\n\n"
        "TASK:\n"
        "Deliver a concise, honest, motivational evening debrief in authentic British JARVIS tone.\n"
        "Acknowledge what was accomplished, state what carries over tomorrow, and end with a calm, resolute closing statement.\n"
        "Length: 3 to 4 short sentences maximum."
    )

    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3}
        )
        debrief_text = resp["message"]["content"].strip()
    except Exception:
        if score == 100:
            debrief_text = "All 3 tactical targets achieved today, sir. Execution was flawless. System efficiency is at peak."
        elif score >= 60:
            debrief_text = f"Two targets secured, with one carryover for tomorrow morning. Solid discipline maintained. Resting telemetry now."
        else:
            debrief_text = "Discipline fell short today, sir. Tomorrow presents an unblemished sheet. We initiate sprint protocol at 0600 hours."

    spoken_text = debrief_text.replace("\n", " ").strip()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE daily_battle_plans
        SET evening_debrief_text = ?, execution_score = ?
        WHERE plan_date = ?
    """, (debrief_text, score, today))
    conn.commit()
    conn.close()

    return {
        "score": score,
        "completed_count": completed_count,
        "written": debrief_text,
        "spoken": spoken_text,
    }
