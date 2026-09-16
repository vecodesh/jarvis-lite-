"""
JARVIS-lite: Intelligent Intent Router & Voice Command Dispatcher

Dispatches user utterances to the appropriate cognitive or workstation subsystem:
1. NAVIGATE_APP: Voice-driven navigation switching tabs in real-time.
2. TRIGGER_ACTION: Voice-driven execution of Focus Timer, Battle Plan, Excalidraw, Cheat Sheet, Backup.
3. GENERAL_CHAT: Conversational inquiries, greetings, status check-ins ("hello", "what can we do now?").
4. SYSTEM_COMMAND: Workstation actions (Lock PC, take screenshot, open external links).
5. SET_REMINDER: Timed alarms and desktop notifications.
6. TECHNICAL_QA: Concept explanations & placement Q&A.
7. MORNING_BRIEFING: Daily status report & executive summary.
8. MOCK_INTERVIEW: Technical drills & interview grading.
9. LOG_PROGRESS: Task extraction and syllabus tracking (only when learning progress is stated).
"""

import re
import sys
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

INTENT_NAVIGATE = "NAVIGATE_APP"
INTENT_ACTION = "TRIGGER_ACTION"
INTENT_CHAT = "GENERAL_CHAT"
INTENT_SYSTEM = "SYSTEM_COMMAND"
INTENT_REMINDER = "SET_REMINDER"
INTENT_BRIEFING = "MORNING_BRIEFING"
INTENT_MOCK = "MOCK_INTERVIEW"
INTENT_QA = "TECHNICAL_QA"
INTENT_LOG = "LOG_PROGRESS"

SYSTEM_COMMANDS = (
    "open leetcode", "open github", "open linkedin",
    "lock pc", "lock workstation", "lock screen",
    "screenshot", "capture screen",
    "system status", "hardware status", "telemetry", "system load",
)

# App Navigation Mappings (Voice/Text Tab Switching)
NAV_KEYWORDS = {
    "🗺️ Striver Sheet": [
        "striver", "dsa sheet", "open striver", "striver sheet", "dsa problem",
        "go to striver", "show striver", "striver a2z", "open sheet"
    ],
    "💻 Coding Arena": [
        "coding arena", "open coding", "go to coding", "coding editor",
        "code runner", "open editor", "practice coding", "solve code"
    ],
    "🧮 Aptitude Arena": [
        "aptitude", "open aptitude", "aptitude arena", "speed drill",
        "mcq", "practice mcq", "quantitative", "core cs mcq", "oa drill"
    ],
    "🎯 Mock Interview": [
        "mock interview", "interview studio", "open mock", "interview practice",
        "hands free interview", "voice interview", "technical drill"
    ],
    "⚡ Flashcards": [
        "flashcard", "flashcards", "open flashcards", "spaced repetition",
        "review cards", "study cards", "card review"
    ],
    "📄 AI Resume": [
        "resume", "open resume", "resume builder", "ai resume", "edit resume",
        "my resume", "view resume", "tailor resume"
    ],
    "💼 Placements Kanban": [
        "kanban", "placements", "placement kanban", "open kanban", "pipeline",
        "job applications", "applied companies", "application tracker"
    ],
    "📚 Study Tracker": [
        "study tracker", "syllabus", "open study", "my subjects", "track study",
        "topics list", "subject tree"
    ],
    "⏰ Alarms": [
        "open alarms", "view alarms", "alarms tab", "reminders tab", "show alarms"
    ],
    "💬 Console": [
        "open console", "go to console", "home", "chat console", "main console"
    ],
}

# Action Triggers
ACTION_KEYWORDS = {
    "FOCUS_START": [
        "start focus", "focus timer", "start deep work", "deep work", "pomodoro",
        "start pomodoro", "begin focus", "focus session", "start sprint"
    ],
    "BATTLE_PLAN": [
        "battle plan", "open battle plan", "show battle plan", "today's plan",
        "todays plan", "my targets", "daily targets", "stark protocol"
    ],
    "EVENING_DEBRIEF": [
        "evening debrief", "run debrief", "debrief me", "end of day",
        "close out day", "daily debrief"
    ],
    "EXCALIDRAW": [
        "excalidraw", "open excalidraw", "whiteboard", "draw logic",
        "launch excalidraw", "open whiteboard"
    ],
    "CHEAT_SHEET": [
        "cheat sheet", "generate cheat sheet", "create cheat sheet",
        "company brief", "interview cheat sheet"
    ],
    "BACKUP": [
        "backup", "backup data", "save backup", "export database"
    ],
}

# Conversational Greetings & Inquiries
GREETINGS = (
    "hi", "hello", "hey", "hey jarvis", "hello jarvis", "hi jarvis",
    "good morning", "good evening", "good afternoon", "what's up", "sup", "yo"
)

INQUIRIES = (
    "what can we do", "what can you do", "what can i do", "what should i do",
    "what now", "what next", "what's next", "help", "guide me", "how to use",
    "who are you", "are you there", "how are you", "status"
)

QA_PREFIXES = (
    "what is", "what are", "what does",
    "explain", "how does", "how do", "how to",
    "difference between", "compare", "why is", "why do",
    "tell me about", "define", "describe",
    "what's the difference", "can you explain",
    "advantages of", "disadvantages of", "pros and cons",
    "time complexity of", "space complexity of",
)

BRIEFING_PHRASES = (
    "morning briefing", "daily briefing",
    "status report", "executive summary", "daily overview",
    "what's on my plate", "today's agenda",
)

REMINDER_PREFIXES = (
    "remind me", "set reminder", "set a reminder",
    "set alarm", "set an alarm", "alarm for",
)

STUDY_LOG_KEYWORDS = (
    "studied", "revised", "completed", "finished", "read",
    "covered", "solved", "done with", "add task", "new task",
    "i finished", "i revised", "i studied"
)


def get_navigation_target(text: str) -> str:
    """Finds which tab the user wants to navigate to, if any."""
    clean = text.strip().lower()
    for tab_name, triggers in NAV_KEYWORDS.items():
        if any(t in clean for t in triggers):
            return tab_name
    return None


def get_action_target(text: str) -> str:
    """Finds which action the user wants to trigger, if any."""
    clean = text.strip().lower()
    for action_name, triggers in ACTION_KEYWORDS.items():
        if any(t in clean for t in triggers):
            return action_name
    return None


def classify_intent(text: str) -> str:
    """
    Deterministically routes input to the correct subsystem.
    """
    clean = text.strip().lower()
    words = clean.split()

    # 0. Check System Workstation commands
    if any(cmd in clean for cmd in SYSTEM_COMMANDS):
        return INTENT_SYSTEM

    # 1. Check Voice App Navigation
    if get_navigation_target(text):
        # Exclude if it's an explicit action or reminder
        if not any(clean.startswith(p) for p in REMINDER_PREFIXES):
            return INTENT_NAVIGATE

    # 2. Check Action Triggers (Focus, Battle Plan, Excalidraw, Cheat Sheet)
    if get_action_target(text):
        return INTENT_ACTION

    # 3. Check Reminder intent
    if any(clean.startswith(p) for p in REMINDER_PREFIXES):
        return INTENT_REMINDER
    if re.search(r"\b(remind me|set (an? )?(alarm|reminder))\b", clean):
        return INTENT_REMINDER

    # 4. Check Briefing intent
    if any(phrase in clean for phrase in BRIEFING_PHRASES):
        return INTENT_BRIEFING

    # 5. Check Mock Interview intent
    if any(phrase in clean for phrase in ("mock interview", "quiz me", "interview me", "test me", "practice question")):
        return INTENT_MOCK

    # 6. Check Technical Q&A intent
    if any(clean.startswith(prefix) for prefix in QA_PREFIXES):
        return INTENT_QA
    if clean.endswith("?") and not any(k in clean for k in ["should i", "did i finish", "what did i", "what can we do", "what can you do"]):
        return INTENT_QA
    if re.search(r"\b(difference between|vs\.?|how does .* work|what is the time complexity)\b", clean):
        return INTENT_QA

    # 7. Check General Chat, Greetings & Inquiries
    if clean in GREETINGS or any(clean.startswith(g + " ") or clean.endswith(" " + g) for g in GREETINGS):
        return INTENT_CHAT
    if any(inq in clean for inq in INQUIRIES):
        return INTENT_CHAT

    # 8. Check explicit Study Progress / Task logging
    if any(k in clean for k in STUDY_LOG_KEYWORDS):
        return INTENT_LOG

    # 9. Default: Conversational Assistant Chat (NOT empty task logging!)
    return INTENT_CHAT
