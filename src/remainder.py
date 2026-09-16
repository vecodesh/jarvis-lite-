"""
JARVIS-lite: Remainder (Legacy Compatibility Wrapper)

Re-exports all stale-checking, timer, and scheduling functions from
reminder_service.py to maintain 100% backwards compatibility while
providing active real-time scheduling.
"""

from reminder_service import (
    DB_PATH,
    get_connection,
    get_stale_topics,
    get_stale_tasks,
    days_old,
    show_reminders,
    add_reminder,
    get_active_reminders,
    dismiss_reminder,
    parse_natural_time,
    send_windows_toast,
    start_reminder_daemon,
)

if __name__ == "__main__":
    show_reminders()