"""
JARVIS-lite: Personality & Conversational Response Module (Phase 5 Extension)

Handles:
1. Proactive launch greeting based on stale topics and tasks.
2. Distinct SECOND system prompt establishing a calm, direct, dry-humored personality.
3. Crisp, single-line confirmation messages following user interactions.

Keeps the extraction prompt in assistant.py completely isolated and untouched.
"""

import sys
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from remainder import get_stale_topics, get_stale_tasks, days_old

try:
    from voice import speak, TTS_AVAILABLE
except ImportError:
    TTS_AVAILABLE = False
    speak = lambda *args, **kwargs: None


# --------------------------------------------------
# Distinct Second System Prompt: Personality Layer
# --------------------------------------------------

PERSONALITY_SYSTEM_PROMPT = """You are JARVIS-lite, a calm, direct, and slightly dry-humored personal study and life assistant.

Your role here is to generate brief spoken and printed replies back to the user.

TONE & BEHAVIOR:
- Calm, competent, and understated.
- Direct and low on fluff.
- Dry-humored when appropriate, never corny or sarcastic.
- No excessive enthusiasm (never say "Awesome!", "Great job!", "Hooray!", "I would be happy to help!").
- No emojis.
- Short sentences. Get straight to the point.
- Keep post-action confirmation messages to a single crisp line.

FEW-SHOT EXAMPLES:

Example 1:
User Event: User just logged "I finished ARIMA."
Reply: Marked ARIMA done. What's next?

Example 2:
User Event: User just logged "I'm studying ARIMA."
Reply: Noted ARIMA in progress. Don't let it sit untouched too long.

Example 3:
User Event: User just logged "I need to complete my assignment."
Reply: Added Assignment to pending academic tasks.

Example 4:
User Event: User just logged "I still need to complete my assignment."
Reply: Assignment is already tracked as pending. Still needs doing.

Example 5:
User Event: User just logged "I completed my assignment."
Reply: Marked Assignment done. One less thing on your plate.

Example 6:
User Event: Morning startup greeting. Stale items: ARIMA untouched for 5 days, Assignment pending for 5 days.
Reply: Good morning. It's been 5 days since you touched ARIMA, and your assignment is still pending.

Example 7:
User Event: Startup greeting. Stale items: none.
Reply: Good morning. Nothing urgent — you're on top of things.
"""


# --------------------------------------------------
# Proactive Greeting Builder (Task 1)
# --------------------------------------------------

def get_salutation():
    """Returns time-of-day salutation."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning."
    elif hour < 17:
        return "Good afternoon."
    else:
        return "Good evening."


def build_stale_greeting(stale_topics=None, stale_tasks=None):
    """
    Builds a natural language greeting summarizing stale items.
    Fast, deterministic, and reliable without requiring an LLM inference delay on launch.
    """
    if stale_topics is None:
        stale_topics = get_stale_topics(days=3)
    if stale_tasks is None:
        stale_tasks = get_stale_tasks(days=3)

    salutation = get_salutation()

    if not stale_topics and not stale_tasks:
        return f"{salutation} Nothing urgent — you're on top of things."

    topic_part = None
    if stale_topics:
        if len(stale_topics) == 1:
            subj, topic, status, last_touched = stale_topics[0]
            age = days_old(last_touched)
            topic_part = f"it's been {age} days since you touched {topic}"
        else:
            subj, top_topic, status, last_touched = stale_topics[0]
            age = days_old(last_touched)
            topic_part = f"you have {len(stale_topics)} untouched topics, including {top_topic} ({age} days ago)"

    task_part = None
    if stale_tasks:
        if len(stale_tasks) == 1:
            task_name, cat, status, created, due = stale_tasks[0]
            task_part = f"your {task_name.lower() if not task_name.isupper() else task_name} is still pending"
        else:
            task_part = f"{len(stale_tasks)} tasks are still pending"

    def _cap_first(s):
        return s[0].upper() + s[1:] if s else s

    if topic_part and task_part:
        return f"{salutation} {_cap_first(topic_part)}, and {task_part}."
    elif topic_part:
        return f"{salutation} {_cap_first(topic_part)}."
    elif task_part:
        return f"{salutation} {_cap_first(task_part)}."

    return f"{salutation} Nothing urgent — you're on top of things."


def proactive_launch_greeting(voice_enabled=True, print_output=True):
    """
    Runs the proactive memory check on startup and speaks/prints the greeting.
    """
    greeting = build_stale_greeting()

    if print_output:
        print("\n" + "=" * 50)
        print(f"JARVIS: {greeting}")
        print("=" * 50)

    if voice_enabled and TTS_AVAILABLE:
        speak(greeting, async_mode=True)

    return greeting


# --------------------------------------------------
# Personality Confirmation Messages (Task 2)
# --------------------------------------------------

def get_confirmation_message(extracted_data):
    """
    Generates a calm, direct, one-line confirmation message in the new personality tone.
    """
    topics = extracted_data.get("topics", [])
    tasks = extracted_data.get("tasks", [])

    # Topic responses
    for t in topics:
        name = t.get("name", "topic")
        status = t.get("status", "")
        if status == "done":
            return f"Marked {name} done. What's next?"
        elif status == "in_progress":
            return f"Noted {name} in progress. Don't let it sit untouched too long."
        elif status == "not_started":
            return f"Logged {name}. It's on your list."

    # Task responses
    for tk in tasks:
        name = tk.get("name", "task")
        status = tk.get("status", "")
        category = tk.get("category", "task")
        if status == "done":
            return f"Marked {name} done. One less thing on your plate."
        elif status == "pending":
            return f"Added {name} to pending {category} tasks."
        elif status == "in_progress":
            return f"Noted {name} in progress."

    return "I'm right here with you, sir. Systems are nominal. We can review your Battle Plan, jump into the Striver Sheet, or launch a deep work sprint."


if __name__ == "__main__":
    proactive_launch_greeting()
