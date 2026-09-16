"""
JARVIS-lite: Stark Focus / Deep Work Pomodoro Engine

Features:
1. Manages high-intensity 25-minute deep work sprints with 5-minute recharges.
2. Background countdown thread with thread-safe state inspection.
3. Audio completion signals (futuristic chimes) & native Windows toast alerts.
4. Automatically logs completed deep work sessions into assistant.db.
5. Calculates real daily focus hours logged today.
"""

import sys
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "assistant.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_focus_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            date_logged TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_focus_table()


def _play_focus_chime(mode="start"):
    """Plays subtle tone on sprint start/completion."""
    if not WINSOUND_AVAILABLE:
        return
    try:
        if mode == "start":
            winsound.Beep(587, 80)
            winsound.Beep(880, 140)
        elif mode == "complete":
            winsound.Beep(880, 100)
            winsound.Beep(1174, 120)
            winsound.Beep(1760, 200)
    except Exception:
        pass


class FocusTimerEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self.state = "idle"  # idle, running, paused, completed
        self.task_name = "Deep Work"
        self.duration_seconds = 25 * 60
        self.remaining_seconds = 25 * 60
        self.session_id = None
        self._stop_event = threading.Event()
        self._thread = None
        self._callbacks = []

    def register_callback(self, cb):
        """Registers callback(state, remaining_seconds, task_name) for UI updates."""
        self._callbacks.append(cb)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb(self.state, self.remaining_seconds, self.task_name)
            except Exception:
                pass

    def start_session(self, task_name: str = "Deep Work", duration_minutes: int = 25):
        """Initiates a new focus sprint."""
        with self._lock:
            if self.state == "running":
                return False

            self.task_name = task_name.strip() or "Deep Work"
            self.duration_seconds = duration_minutes * 60
            self.remaining_seconds = self.duration_seconds
            self.state = "running"
            self._stop_event.clear()

            # Record session in DB
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO focus_sessions (task_name, duration_minutes, completed)
                VALUES (?, ?, 0)
            """, (self.task_name, duration_minutes))
            conn.commit()
            self.session_id = cur.lastrowid
            conn.close()

            _play_focus_chime("start")

            self._thread = threading.Thread(target=self._countdown_loop, daemon=True)
            self._thread.start()
            self._notify()
            return True

    def pause_session(self):
        with self._lock:
            if self.state == "running":
                self.state = "paused"
                self._notify()

    def resume_session(self):
        with self._lock:
            if self.state == "paused":
                self.state = "running"
                self._notify()

    def stop_session(self):
        with self._lock:
            self._stop_event.set()
            self.state = "idle"
            self.remaining_seconds = self.duration_seconds
            self._notify()

    def _countdown_loop(self):
        while not self._stop_event.is_set() and self.remaining_seconds > 0:
            time.sleep(1)
            with self._lock:
                if self.state == "running":
                    self.remaining_seconds -= 1
                    self._notify()

        if self.remaining_seconds <= 0 and not self._stop_event.is_set():
            with self._lock:
                self.state = "completed"
                self._notify()

            self._on_sprint_finished()

    def _on_sprint_finished(self):
        _play_focus_chime("complete")

        # Mark completed in DB
        mins = int(self.duration_seconds / 60)
        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.session_id:
                cur.execute("UPDATE focus_sessions SET completed = 1 WHERE id = ?", (self.session_id,))
            # `logs` is the shared assistant event ledger.  The original
            # columns here belonged to an abandoned schema, so completed
            # sessions were silently lost by the broad exception handler.
            cur.execute("""
                INSERT INTO logs (raw_text, parsed_summary)
                VALUES (?, ?)
            """, (
                f"Completed {mins}-minute focus sprint: {self.task_name}",
                f'{{"event": "focus_completed", "duration_minutes": {mins}}}',
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        # Windows toast
        try:
            from reminder_service import send_windows_toast
            send_windows_toast("⚡ Sprint Completed!", f"Logged {mins}m of deep work on '{self.task_name}'. Take a 5m break.")
        except Exception:
            pass

    def get_status(self) -> dict:
        with self._lock:
            mins = self.remaining_seconds // 60
            secs = self.remaining_seconds % 60
            time_str = f"{mins:02d}:{secs:02d}"
            return {
                "state": self.state,
                "task_name": self.task_name,
                "remaining_seconds": self.remaining_seconds,
                "time_str": time_str,
                "progress": 1.0 - (self.remaining_seconds / max(1, self.duration_seconds)),
            }


_focus_singleton = FocusTimerEngine()


def get_focus_engine() -> FocusTimerEngine:
    return _focus_singleton


def get_today_focus_hours() -> float:
    """Calculates total completed focus hours today."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cur.execute("""
            SELECT SUM(duration_minutes) FROM focus_sessions
            WHERE completed = 1 AND date(date_logged) = date(?)
        """, (today,))
        total_mins = cur.fetchone()[0] or 0
        conn.close()
        return round(total_mins / 60.0, 1)
    except Exception:
        return 0.0
