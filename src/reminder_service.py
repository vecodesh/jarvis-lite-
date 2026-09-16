"""
JARVIS-lite: Real-Time Reminder & Scheduler Service (Phase 6 Upgrade)

Provides:
1. Persistent database storage for scheduled alarms and reminders.
2. Natural language time parsing (e.g. "in 10 minutes", "at 4:30 PM", "tomorrow at 10 AM").
3. Background daemon worker checking due alarms every 5 seconds.
4. Windows desktop toast notifications and Jarvis voice alerts.
5. Preserves complete backwards-compatibility with the original remainder.py.
"""

import sys
import os
import re
import time
import sqlite3
import threading
import subprocess
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

try:
    from voice import speak, TTS_AVAILABLE
except ImportError:
    TTS_AVAILABLE = False
    speak = lambda *args, **kwargs: None


def get_connection():
    return sqlite3.connect(DB_PATH)


# --------------------------------------------------
# Table Initialization
# --------------------------------------------------

def init_reminders_table():
    """Initializes reminders table and indexes."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            remind_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'scheduled'
                CHECK(status IN ('scheduled', 'triggered', 'dismissed')),
            category TEXT NOT NULL DEFAULT 'general',
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_remind_time
        ON reminders(remind_time, status)
    """)
    conn.commit()
    conn.close()


init_reminders_table()


# --------------------------------------------------
# Windows Toast Notification (Native PowerShell)
# --------------------------------------------------

def send_windows_toast(title, message):
    """Sends a native Windows desktop toast notification without extra pip dependencies."""
    try:
        # Sanitize single and double quotes for PowerShell
        clean_title = title.replace('"', '`"').replace("'", "''")
        clean_msg = message.replace('"', '`"').replace("'", "''")
        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{clean_title}</text>
            <text>{clean_msg}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default" />
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS-lite").Show($toast)
"""
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        print(f"[Toast Error] {e}")


# --------------------------------------------------
# Natural Language Time Parser
# --------------------------------------------------

def parse_natural_time(text):
    """
    Parses natural language phrases into a datetime object.
    Supports:
      - "in X minutes" / "in X mins" / "in X min"
      - "in X hours" / "in X hr"
      - "in X seconds" / "in X secs"
      - "at HH:MM" / "at HH:MM AM/PM"
      - "tomorrow at HH:MM AM/PM"
    Returns (datetime_obj, cleaned_message) or (None, None).
    """
    now = datetime.now()
    clean_text = text.strip()

    # 1. Relative: "in X minute(s)/hour(s)/second(s)"
    rel_match = re.search(
        r"(?:remind me\s+)?in\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\s*(?:to\s+|that\s+|about\s+)?(.*)",
        clean_text,
        re.IGNORECASE,
    )
    if rel_match:
        qty = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        msg = rel_match.group(3).strip() or "Reminder"

        if unit.startswith("s"):
            target_dt = now + timedelta(seconds=qty)
        elif unit.startswith("m"):
            target_dt = now + timedelta(minutes=qty)
        else:
            target_dt = now + timedelta(hours=qty)

        return target_dt, msg

    # 2. Tomorrow at HH:MM AM/PM
    tomorrow_match = re.search(
        r"(?:remind me\s+)?tomorrow(?:\s+at)?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to\s+|that\s+|about\s+)?(.*)",
        clean_text,
        re.IGNORECASE,
    )
    if tomorrow_match:
        hour = int(tomorrow_match.group(1))
        minute = int(tomorrow_match.group(2) or 0)
        meridiem = (tomorrow_match.group(3) or "").lower()
        msg = tomorrow_match.group(4).strip() or "Reminder"

        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        target_dt = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return target_dt, msg

    # 3. Absolute time: "at HH:MM AM/PM"
    abs_match = re.search(
        r"(?:remind me\s+)?at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to\s+|that\s+|about\s+)?(.*)",
        clean_text,
        re.IGNORECASE,
    )
    if abs_match:
        hour = int(abs_match.group(1))
        minute = int(abs_match.group(2) or 0)
        meridiem = (abs_match.group(3) or "").lower()
        msg = abs_match.group(4).strip() or "Reminder"

        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        elif not meridiem:
            # If no AM/PM, and hour has already passed today, assume PM or next day
            if hour < now.hour or (hour == now.hour and minute <= now.minute):
                if hour <= 12:
                    hour += 12  # e.g., "at 5" said at 2 PM -> 5 PM (17:00)

        target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_dt <= now:
            target_dt += timedelta(days=1)

        return target_dt, msg

    return None, None


# --------------------------------------------------
# CRUD Operations
# --------------------------------------------------

def add_reminder(message, remind_time, category="general"):
    """
    Schedules a new reminder.
    remind_time can be a datetime object or 'YYYY-MM-DD HH:MM:SS' string.
    """
    if isinstance(remind_time, datetime):
        time_str = remind_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(remind_time)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reminders (message, remind_time, status, category)
        VALUES (?, ?, 'scheduled', ?)
    """, (message.strip(), time_str, category))
    conn.commit()
    rem_id = cur.lastrowid
    conn.close()
    return rem_id


def get_active_reminders():
    """Returns all currently scheduled upcoming reminders."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, message, remind_time, status, category, created_date
        FROM reminders
        WHERE status = 'scheduled'
        ORDER BY remind_time ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def dismiss_reminder(reminder_id):
    """Marks a reminder as dismissed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET status = 'dismissed' WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def get_due_reminders():
    """Fetches reminders that are scheduled and due for firing."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, message, remind_time, category
        FROM reminders
        WHERE status = 'scheduled' AND remind_time <= ?
    """, (now_str,))
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_reminder_triggered(reminder_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET status = 'triggered' WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


# --------------------------------------------------
# Background Daemon Worker
# --------------------------------------------------

_daemon_started = False
_daemon_lock = threading.Lock()
_trigger_callbacks = []


def register_reminder_callback(fn):
    """Allows GUI or other modules to register a callback when a reminder fires."""
    if fn not in _trigger_callbacks:
        _trigger_callbacks.append(fn)


def _reminder_daemon_loop():
    while True:
        try:
            due = get_due_reminders()
            for rem_id, message, remind_time, category in due:
                mark_reminder_triggered(rem_id)
                # Toast notification
                send_windows_toast("JARVIS Reminder", message)
                # Spoken audio alert
                if TTS_AVAILABLE:
                    speak(f"Sir, reminder: {message}", async_mode=True)
                # Execute registered UI callbacks
                for cb in _trigger_callbacks:
                    try:
                        cb(rem_id, message, remind_time)
                    except Exception as e:
                        print(f"[Callback Error] {e}")
        except Exception as err:
            print(f"[Reminder Daemon Error] {err}")
        time.sleep(5)


def start_reminder_daemon():
    """Starts the background worker thread if not already running."""
    global _daemon_started
    with _daemon_lock:
        if not _daemon_started:
            t = threading.Thread(target=_reminder_daemon_loop, daemon=True, name="JarvisReminderDaemon")
            t.start()
            _daemon_started = True


# Auto-start daemon upon module import
start_reminder_daemon()


# --------------------------------------------------
# Backwards Compatibility with remainder.py
# --------------------------------------------------

def get_stale_topics(days=3):
    """Finds topics not touched in `days` days."""
    conn = get_connection()
    cur = conn.cursor()
    cutoff_date = datetime.now() - timedelta(days=days)
    cur.execute("""
        SELECT subjects.name, topics.topic_name, topics.status, topics.last_touched_date
        FROM topics
        JOIN subjects ON topics.subject_id = subjects.id
        WHERE topics.status != 'done' AND topics.last_touched_date < ?
        ORDER BY topics.last_touched_date ASC
    """, (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),))
    results = cur.fetchall()
    conn.close()
    return results


def get_stale_tasks(days=3):
    """Finds tasks created > `days` ago that are still pending."""
    conn = get_connection()
    cur = conn.cursor()
    cutoff_date = datetime.now() - timedelta(days=days)
    cur.execute("""
        SELECT task_name, category, status, created_date, due_date
        FROM tasks
        WHERE status != 'done' AND created_date < ?
        ORDER BY created_date ASC
    """, (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),))
    results = cur.fetchall()
    conn.close()
    return results


def days_old(date_string):
    try:
        date = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - date).days
    except Exception:
        return 0


def show_reminders():
    """CLI printer for stale topics and tasks."""
    stale_topics = get_stale_topics()
    stale_tasks = get_stale_tasks()
    active_reminders = get_active_reminders()

    print("\n===================================")
    print("       ACTIVE REMINDERS & ALARMS")
    print("===================================")
    if not active_reminders:
        print("No active alarms scheduled.")
    else:
        for r_id, msg, r_time, _, _, _ in active_reminders:
            print(f"[{r_time}] #{r_id}: {msg}")

    print("\n===================================")
    print("       STALE TOPICS & TASKS")
    print("===================================")
    if not stale_topics and not stale_tasks:
        print("Everything is up to date!")
        return

    if stale_topics:
        print("\nUntouched Topics:")
        for subj, topic, _, last_touched in stale_topics:
            print(f" - {topic} ({subj}) [untouched {days_old(last_touched)} days]")

    if stale_tasks:
        print("\nPending Tasks:")
        for name, cat, _, created, _ in stale_tasks:
            print(f" - {name} [{cat}] [pending {days_old(created)} days]")
