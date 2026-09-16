import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from remainder import show_reminders

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ollama


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "assistant.db"

MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """
You are JARVIS-lite, a local study and life assistant.

Your job is to extract structured information from what the user says.

Return ONLY valid JSON.
Do not use markdown.
Do not add explanations.

Use exactly this structure:

{
  "subjects": [],
  "topics": [],
  "tasks": []
}

Each subject must have:

{
  "name": "subject name"
}

Each topic must have:

{
  "name": "topic name",
  "status": "not_started | in_progress | done"
}

Each task must have:

{
  "name": "task name",
  "status": "pending | in_progress | done",
  "category": "life_admin | placement | academic"
}

IMPORTANT RULES:

1. Extract ALL relevant subjects, topics, and tasks mentioned by the user.

2. Do NOT invent information.

3. SUBJECT vs TOPIC:

A subject is a broad area of study.

Examples:
- Machine Learning
- Time Series Forecasting
- Natural Language Processing
- Database Management Systems

A topic is a specific concept, technique, or chapter within a subject.

Examples:
- Linear Regression
- Random Forest
- ARIMA
- Decomposition
- Autocorrelation
- ACF
- PACF

If the user says they are studying, learning, or have studied a specific concept, treat that concept as a TOPIC, not a subject.

For example:
"I am studying ARIMA today."

Return ARIMA as a topic with status "in_progress", not as a subject.

If the user mentions both a broad subject and a specific topic, extract both.

Example:
"I am studying Time Series Forecasting and learning ARIMA."

Return:
- Subject: Time Series Forecasting
- Topic: ARIMA, status in_progress

4. SUBJECT EXTRACTION CONSTRAINT (CRITICAL):
Only extract a subject when the user explicitly states they are studying, learning, or working through that subject as a field of knowledge (e.g., "I'm studying Time Series Forecasting").
A task description referencing a topic area or subject is NOT grounds for extracting a subject.
NEVER extract a subject when a topic or subject word merely appears inside a task name (e.g., "my time series assignment", "complete machine learning project"). In such task-only statements, return "subjects": [].

5. A task is an action the user needs to perform.

6. TASK NAME NORMALIZATION (CRITICAL):
Task names must be extracted as a short Title-Case noun phrase describing the deliverable or item itself (e.g., "Assignment", "Time Series Assignment", "Electricity Bill", "Resume").
The verb or action phrase used by the user ("complete", "finish", "need to", "still need to", "submit", "pay", etc.) MUST be stripped out entirely.
The verb should only ever determine the task status (pending, in_progress, done), and must NEVER appear inside the task name.

7. Determine topic status from the user's wording:
   - "I finished X" → done
   - "I completed X" → done
   - "I am studying X" → in_progress
   - "I am learning X" → in_progress
   - "I need to study X" → in_progress
   - "I haven't started X" → not_started

8. Determine task status:
   - "I need to do X" → pending
   - "I have to do X" → pending
   - "I should do X" → pending
   - "I am working on X" → in_progress
   - "I finished X" → done
   - "I completed X" → done

9. IMPORTANT:
   "I need to complete X" or "I still need to complete X" means the task is PENDING, not DONE. The task name is "X", not "Complete X".

10. Task category:
   - studying, assignments, exams, projects, coursework → academic
   - job applications, interviews, placements, resume → placement
   - personal errands, bills, appointments, shopping, etc. → life_admin

11. If there is no subject, topic, or task, return an empty array for that field.

12. If the user mentions several topics or tasks, include ALL of them.

EXAMPLES:

Example 1: Task with leading verbs (verb stripped out, Title-Case deliverable, negative subject example)
User:
"I need to complete my time series assignment."

Return:
{
  "subjects": [],
  "topics": [],
  "tasks": [
    {
      "name": "Time Series Assignment",
      "status": "pending",
      "category": "academic"
    }
  ]
}

Example 2: Re-mention of pending task (same normalized deliverable name, verb stripped)
User:
"I still need to complete my assignment."

Return:
{
  "subjects": [],
  "topics": [],
  "tasks": [
    {
      "name": "Assignment",
      "status": "pending",
      "category": "academic"
    }
  ]
}

Example 3: Completed task (verb determines status 'done', verb stripped from deliverable name, no subject)
User:
"I completed my assignment."

Return:
{
  "subjects": [],
  "topics": [],
  "tasks": [
    {
      "name": "Assignment",
      "status": "done",
      "category": "academic"
    }
  ]
}

Example 4: Life admin task with leading verb stripped
User:
"I have to pay the electricity bill."

Return:
{
  "subjects": [],
  "topics": [],
  "tasks": [
    {
      "name": "Electricity Bill",
      "status": "pending",
      "category": "life_admin"
    }
  ]
}

Example 5: Broad subject + topic + task combined
User:
"I'm studying time series forecasting. I finished decomposition, but I still need to study ARIMA and complete the assignment."

Return:
{
  "subjects": [
    {
      "name": "Time Series Forecasting"
    }
  ],
  "topics": [
    {
      "name": "Decomposition",
      "status": "done"
    },
    {
      "name": "ARIMA",
      "status": "in_progress"
    }
  ],
  "tasks": [
    {
      "name": "Assignment",
      "status": "pending",
      "category": "academic"
    }
  ]
}
"""


# --------------------------------------------------
# Database
# --------------------------------------------------

def get_connection():
    return sqlite3.connect(DB_PATH)


def insert_log(raw_text, parsed_summary):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO logs (raw_text, parsed_summary)
        VALUES (?, ?)
        """,
        (raw_text, parsed_summary)
    )

    connection.commit()
    connection.close()


def get_or_create_subject(subject_name):
    connection = get_connection()
    cursor = connection.cursor()

    # Check case-insensitively for an existing subject
    cursor.execute(
        "SELECT id FROM subjects WHERE LOWER(name) = Lower(?)",
        (subject_name.strip(),)
    )

    result = cursor.fetchone()

    if result:
        subject_id = result[0]
    else:
        cursor.execute(
            """
            INSERT INTO subjects (name)
            VALUES (?)
            """,
            (subject_name.strip(),)
        )

        subject_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return subject_id


def insert_topic(subject_id, topic_name, status):
    connection = get_connection()
    cursor = connection.cursor()

    # If status wasn't provided, default to in_progress
    if status not in ("not_started", "in_progress", "done"):
        status = "not_started"

    topic_name = topic_name.strip()

    # Check whether this topic already exists for this subject
    cursor.execute(
        """
        SELECT id
        FROM topics
        WHERE subject_id = ? AND LOWER(topic_name) = LOWER(?)
        """,
        (subject_id, topic_name)
    )

    result = cursor.fetchone()

    if result:
        cursor.execute(
            """
            UPDATE topics
            SET status = ?,
                last_touched_date = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, result[0])
        )
    else:
        cursor.execute(
            """
            INSERT INTO topics
                (subject_id, topic_name, status, last_touched_date)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (subject_id, topic_name, status)
        )

    connection.commit()
    connection.close()


def clean_task_name(task_name):
    """
    Python-side safety net: strips common leading verb phrases case-insensitively
    so normalization does not depend solely on LLM prompt compliance.
    """
    cleaned = task_name.strip()

    prefixes = [
        "still need to ",
        "need to ",
        "complete ",
        "finish ",
        "submit ",
        "pay ",
    ]

    changed = True
    while changed:
        changed = False
        lower = cleaned.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                changed = True
                break

    if not cleaned:
        return task_name.strip()

    if cleaned.islower():
        cleaned = cleaned.title()
    elif len(cleaned) > 0 and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned


def insert_task(task_name, status, category):
    connection = get_connection()
    cursor = connection.cursor()
    
    task_name = clean_task_name(task_name)

    if status not in ("pending", "in_progress", "done"):
        status = "pending"

    if category not in ("life_admin", "placement", "academic"):
        category = "academic"

    # Check whether this task already exists
    cursor.execute(
        """
        SELECT id
        FROM tasks
        WHERE LOWER(task_name) = LOWER(?)
        """,
        (task_name,)
    )
    result = cursor.fetchone()
    
    if result:
        # Task already exists → update it
        cursor.execute(
            """
            UPDATE tasks
            SET status = ?,
                category = ?
            WHERE id = ?
            """,
            (status, category, result[0])
        )
    else:
        # New task → create it
        cursor.execute(
            """
            INSERT INTO tasks
                (task_name, category, status)
            VALUES (?, ?, ?)
            """,
            (task_name, category, status)
        )
        
    connection.commit()
    connection.close()


# --------------------------------------------------
# AI
# --------------------------------------------------

def extract_information(user_text):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        format="json"
    )

    content = response["message"]["content"]

    return json.loads(content)


# --------------------------------------------------
# Main processing
# --------------------------------------------------

def process_input(user_text):
    print("\nThinking...")

    try:
        data = extract_information(user_text)

    except Exception as error:
        print(f"\nAI error: {error}")
        return

    print("\nExtracted:")
    print(json.dumps(data, indent=2))

    # --------------------------------------------------
    # Save original message FIRST
    # --------------------------------------------------

    parsed_summary = json.dumps(data)

    insert_log(user_text, parsed_summary)

    # --------------------------------------------------
    # Subjects
    # --------------------------------------------------

    subject_ids = {}

    for subject in data.get("subjects", []):
        subject_name = subject.get("name")

        if not subject_name:
            continue

        subject_id = get_or_create_subject(subject_name)
        subject_ids[subject_name] = subject_id

    # --------------------------------------------------
    # Topics
    # --------------------------------------------------

    for topic in data.get("topics", []):
        topic_name = topic.get("name")
        status = topic.get("status")

        if not topic_name:
            continue

        # If there is only one subject, associate the topic
        # with that subject.
        if len(subject_ids) == 1:
            subject_id = next(iter(subject_ids.values()))
            insert_topic(subject_id, topic_name, status)
        else:
            # No subject mentioned.
            # Try to find an existing topic with this name.
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT subject_id
                FROM topics
                WHERE LOWER(topic_name) = LOWER(?)
                LIMIT 1
                """,
                (topic_name.strip(),)
            )

            result = cursor.fetchone()
            connection.close()

            if result:
                subject_id = result[0]
                insert_topic(subject_id, topic_name, status)
            else:
                # No subject was given and topic is new: assign to a default subject
                subject_id = get_or_create_subject("General")
                insert_topic(subject_id, topic_name, status)

    # --------------------------------------------------
    # Tasks
    # --------------------------------------------------

    for task in data.get("tasks", []):
        task_name = task.get("name")
        status = task.get("status")
        category = task.get("category")

        if not task_name:
            continue

        task_name = clean_task_name(task_name)
        insert_task(task_name, status, category)

    print("\n✓ Remembered.")

# --------------------------------------------------
# Mrking Item as done
# --------------------------------------------------

def mark_item_as_done():
    connection = get_connection()
    cursor = connection.cursor()

    # Get unfinished topics
    cursor.execute("""
        SELECT
            topics.id,
            'topic' AS item_type,
            topics.topic_name,
            subjects.name
        FROM topics
        JOIN subjects
            ON topics.subject_id = subjects.id
        WHERE topics.status != 'done'
        ORDER BY topics.id
    """)

    topics = cursor.fetchall()

    # Get unfinished tasks
    cursor.execute("""
        SELECT
            id,
            'task' AS item_type,
            task_name,
            category
        FROM tasks
        WHERE status != 'done'
        ORDER BY id
    """)

    tasks = cursor.fetchall()

    connection.close()

    # Combine both lists
    items = topics + tasks

    if not items:
        print("\n✓ There are no unfinished items.")
        return

    print("\n===================================")
    print("       UNFINISHED ITEMS")
    print("===================================")

    for index, item in enumerate(items, start=1):
        item_id, item_type, item_name, extra_info = item

        if item_type == "topic":
            print(f"{index}. [Topic] {item_name} ({extra_info})")
        else:
            print(f"{index}. [Task] {item_name} ({extra_info})")

    print("\n0. Cancel")

    choice = input("\nChoose an item: ").strip()

    if choice == "0":
        print("\nCancelled.")
        return

    if not choice.isdigit():
        print("\nPlease enter a valid number.")
        return

    selected_index = int(choice)

    if selected_index < 1 or selected_index > len(items):
        print("\nInvalid item number.")
        return

    selected_item = items[selected_index - 1]

    item_id, item_type, item_name, extra_info = selected_item

    connection = get_connection()
    cursor = connection.cursor()

    if item_type == "topic":
        cursor.execute("""
            UPDATE topics
            SET status = 'done',
                last_touched_date = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (item_id,))
    else:
        cursor.execute("""
            UPDATE tasks
            SET status = 'done'
            WHERE id = ?
        """, (item_id,))

    connection.commit()
    connection.close()

    print(f"\n✓ Marked as done: {item_name}")

# --------------------------------------------------
# Interactive loop
# --------------------------------------------------

def main():
    print("===================================")
    print("       JARVIS-lite")
    print("===================================")
    print("Local AI Study/Life Assistant")

    while True:
        print("\n===================================")
        print("             MENU")
        print("===================================")
        print("1. Show stale items")
        print("2. Talk to assistant")
        print("3. Mark item as done")
        print("4. Exit")

        choice = input("\nChoose an option: ").strip()

        # ------------------------------------------
        # Option 1: Show stale items
        # ------------------------------------------

        if choice == "1":
            show_reminders()

        # ------------------------------------------
        # Option 2: Talk to assistant
        # ------------------------------------------

        elif choice == "2":
            print("\nTalk to JARVIS")
            print("Type 'back' to return to the menu.")

            while True:
                user_text = input("\nYou: ").strip()

                if user_text.lower() == "back":
                    break

                if not user_text:
                    continue

                process_input(user_text)

        # ------------------------------------------
        # Option 3: Mark item as done
        # ------------------------------------------

        elif choice == "3":
              mark_item_as_done()

        # ------------------------------------------
        # Option 4: Exit
        # ------------------------------------------

        elif choice == "4":
            print("\nGoodbye!")
            break

        # ------------------------------------------
        # Invalid option
        # ------------------------------------------

        else:
            print("\nPlease choose 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()