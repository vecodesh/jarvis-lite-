"""
JARVIS-lite: Daily Morning Briefing & Placement Readiness Engine (Phase 6)

Provides:
1. Executive Morning Briefing: High-level overview of stale items, upcoming deadlines, and active alarms.
2. Placement Readiness Index (0-100%): Calculated from DSA, Core CS, and application pipeline health.
3. Daily Study Streak Tracker: Calculates continuous active study days from database logs.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "assistant.db"

from reminder_service import get_stale_topics, get_stale_tasks, get_active_reminders, days_old

try:
    from placements import get_placement_summary
except ImportError:
    get_placement_summary = lambda: {"total": 0, "active": 0, "by_stage": {}}


def get_connection():
    return sqlite3.connect(DB_PATH)


# --------------------------------------------------
# Study Streak Tracker
# --------------------------------------------------

def get_study_streak() -> int:
    """
    Calculates consecutive active days based on log and topic touch timestamps.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT substr(timestamp, 1, 10) FROM logs
            UNION
            SELECT DISTINCT substr(last_touched_date, 1, 10) FROM topics
            ORDER BY 1 DESC
        """)
        dates_raw = [r[0] for r in cur.fetchall() if r[0]]
        conn.close()

        if not dates_raw:
            return 1

        active_dates = set()
        for d in dates_raw:
            try:
                active_dates.add(datetime.strptime(d, "%Y-%m-%d").date())
            except Exception:
                pass

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # If neither today nor yesterday was active, streak is broken (0 or 1 if started today)
        if today not in active_dates and yesterday not in active_dates:
            return 0

        current = today if today in active_dates else yesterday
        streak = 0

        while current in active_dates:
            streak += 1
            current -= timedelta(days=1)

        return max(1, streak)
    except Exception:
        return 1


# --------------------------------------------------
# Placement Readiness Index
# --------------------------------------------------

def get_readiness_metrics() -> dict:
    """
    Calculates DSA, Core CS, and overall Placement Readiness percentages.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Topics overall
    cur.execute("SELECT status, LOWER(topic_name) FROM topics")
    all_topics = cur.fetchall()

    total_topics = len(all_topics)
    done_topics = sum(1 for s, _ in all_topics if s == "done")

    # DSA topics
    dsa_keywords = ["array", "tree", "graph", "dp", "dynamic programming", "sort", "search", "stack", "queue", "linked list", "recursion", "greedy"]
    dsa_all = [s for s, name in all_topics if any(k in name for k in dsa_keywords)]
    dsa_done = sum(1 for s in dsa_all if s == "done")
    dsa_score = int((dsa_done / len(dsa_all)) * 100) if dsa_all else 60

    # Core CS topics (DBMS, OS, CN, OOP)
    core_keywords = ["dbms", "sql", "index", "os", "operating system", "process", "thread", "memory", "tcp", "udp", "network", "oop", "class"]
    core_all = [s for s, name in all_topics if any(k in name for k in core_keywords)]
    core_done = sum(1 for s in core_all if s == "done")
    core_score = int((core_done / len(core_all)) * 100) if core_all else 55

    # Placements health
    summary = get_placement_summary()
    active_apps = summary.get("active", 0)
    app_score = min(100, active_apps * 15)  # E.g. 5+ active apps yields high application pipeline score

    # Overall weighted average
    overall_readiness = int((dsa_score * 0.45) + (core_score * 0.35) + (app_score * 0.20))
    overall_readiness = max(10, min(98, overall_readiness))

    conn.close()

    return {
        "overall": overall_readiness,
        "dsa": min(100, dsa_score),
        "core_cs": min(100, core_score),
        "active_applications": active_apps,
        "study_streak": get_study_streak(),
        "total_topics": total_topics,
        "done_topics": done_topics,
    }


# --------------------------------------------------
# Executive Morning Briefing
# --------------------------------------------------

def generate_morning_briefing() -> dict:
    """
    Generates a structured morning executive summary and spoken text.
    """
    metrics = get_readiness_metrics()
    stale_topics = get_stale_topics(days=3)
    stale_tasks = get_stale_tasks(days=3)
    active_reminders = get_active_reminders()
    placement_summary = get_placement_summary()

    hour = datetime.now().hour
    salutation = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")

    # Spoken summary for TTS
    spoken_parts = [f"{salutation}, sir. Standing by for today's briefing."]
    if active_reminders:
        spoken_parts.append(f"You have {len(active_reminders)} active alarm{'s' if len(active_reminders) > 1 else ''} scheduled.")
    if stale_topics:
        spoken_parts.append(f"{len(stale_topics)} study topic{'s' if len(stale_topics) > 1 else ''} require urgent review.")
    if stale_tasks:
        spoken_parts.append(f"{len(stale_tasks)} pending task{'s' if len(stale_tasks) > 1 else ''} on your board.")
    spoken_parts.append(f"Your placement readiness sits at {metrics['overall']}%, with an active streak of {metrics['study_streak']} days.")
    spoken_text = " ".join(spoken_parts)

    # Detailed written report
    lines = []
    lines.append(f"⚡ {salutation.upper()} — EXECUTIVE STATUS REPORT")
    lines.append("=" * 45)
    lines.append(f"🔥 Daily Study Streak: {metrics['study_streak']} Days Continuous")
    lines.append(f"🎯 Placement Readiness: {metrics['overall']}% (DSA: {metrics['dsa']}%, Core CS: {metrics['core_cs']}%)")
    lines.append(f"💼 Active Pipeline: {placement_summary.get('active', 0)} Applications In Progress")
    lines.append("")

    if active_reminders:
        lines.append("⏰ TODAY'S SCHEDULED REMINDERS:")
        for r_id, msg, r_time, _, _, _ in active_reminders[:5]:
            lines.append(f"  • [{r_time[11:16]}] {msg}")
        lines.append("")

    if stale_topics:
        lines.append("📚 URGENT REVISION REQUIRED (Stale 3+ Days):")
        for subj, topic, _, last_touched in stale_topics[:4]:
            lines.append(f"  • {topic} ({subj}) — untouched {days_old(last_touched)}d")
        lines.append("")

    if stale_tasks:
        lines.append("📋 PENDING TASKS:")
        for name, cat, _, created, _ in stale_tasks[:4]:
            lines.append(f"  • {name} [{cat}] — pending {days_old(created)}d")
        lines.append("")

    lines.append("System status nominal. What is our first objective?")

    return {
        "spoken": spoken_text,
        "written": "\n".join(lines),
        "metrics": metrics,
    }


if __name__ == "__main__":
    briefing = generate_morning_briefing()
    print(briefing["written"])
