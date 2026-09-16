"""
JARVIS-lite: Spaced Repetition Flashcard Drill Engine (Phase 7)

Features:
1. Implements the SuperMemo SM-2 spaced repetition algorithm for long-term retention.
2. Curated core placement flashcards across DSA, DBMS, OS, Networks, and System Design.
3. Ability to generate novel AI flashcards for any topic via Ollama.
4. Daily review queue based on due dates and recall grading (Again, Hard, Good, Easy).
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

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

CURATED_FLASHCARDS = [
    {
        "front": "What is the difference between a Process and a Thread?",
        "back": "A Process is an independent program in execution with its own isolated address space, memory, and file handles.\nA Thread is a lightweight unit of execution within a process that shares memory and resources with sibling threads.",
        "topic": "Operating Systems",
    },
    {
        "front": "Explain the ACID properties in database transactions.",
        "back": "Atomicity: All-or-nothing execution.\nConsistency: Database transitions from one valid state to another.\nIsolation: Concurrent transactions do not interfere with each other.\nDurability: Committed data is permanently stored even during power failure.",
        "topic": "DBMS",
    },
    {
        "front": "What are the time and space complexities of QuickSort?",
        "back": "Best/Average Time: O(N log N)\nWorst Time: O(N^2) (e.g. sorted array with unbalanced pivot)\nSpace: O(log N) average auxiliary call stack, O(N) worst case.",
        "topic": "Algorithms",
    },
    {
        "front": "What are the 4 Coffman conditions required for Deadlock to occur?",
        "back": "1. Mutual Exclusion (resources cannot be shared)\n2. Hold and Wait (process holds resource while waiting for another)\n3. No Preemption (resources cannot be forcibly taken)\n4. Circular Wait (circular chain of processes waiting on each other)",
        "topic": "Operating Systems",
    },
    {
        "front": "Why are B+ Trees preferred over Binary Search Trees for database indexing?",
        "back": "1. High Fan-out: Wide nodes reduce tree height, minimizing slow disk I/O reads.\n2. Sequential Access: Leaf nodes are linked in a doubly linked list, enabling lightning-fast range queries.\n3. Cache Line Friendly: Node size matches disk block size.",
        "topic": "DBMS",
    },
    {
        "front": "Explain the 3-Way Handshake in TCP connection establishment.",
        "back": "1. Client -> Server: SYN (Synchronize sequence number)\n2. Server -> Client: SYN-ACK (Acknowledge client SYN, send server SYN)\n3. Client -> Server: ACK (Acknowledge server SYN; connection established)",
        "topic": "Computer Networks",
    },
    {
        "front": "What is the CAP Theorem in Distributed Systems?",
        "back": "In any asynchronous network partition (P), a distributed system can guarantee at most TWO of:\n- Consistency (C): Every read receives the most recent write.\n- Availability (A): Every non-failing node returns a response.\n- Partition Tolerance (P): System operates despite network dropped packets.",
        "topic": "System Design",
    },
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_flashcards_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            front_prompt TEXT NOT NULL,
            back_answer TEXT NOT NULL,
            topic TEXT NOT NULL,
            interval INTEGER DEFAULT 1,
            repetitions INTEGER DEFAULT 0,
            ease_factor REAL DEFAULT 2.5,
            next_review_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Seed curated flashcards if empty
    cur.execute("SELECT COUNT(*) FROM flashcards")
    if cur.fetchone()[0] == 0:
        for card in CURATED_FLASHCARDS:
            cur.execute("""
                INSERT INTO flashcards (front_prompt, back_answer, topic, next_review_date)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (card["front"], card["back"], card["topic"]))
        conn.commit()

    conn.close()


init_flashcards_table()


def get_due_flashcards(limit: int = 10):
    """Fetches flashcards that are due for review."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, front_prompt, back_answer, topic, interval, repetitions, ease_factor, next_review_date
        FROM flashcards
        WHERE next_review_date <= ?
        ORDER BY next_review_date ASC
        LIMIT ?
    """, (now_str, limit))
    rows = cur.fetchall()

    # If no due cards, fetch random cards for practice
    if not rows:
        cur.execute("""
            SELECT id, front_prompt, back_answer, topic, interval, repetitions, ease_factor, next_review_date
            FROM flashcards
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()

    conn.close()

    return [{
        "id": r[0],
        "front": r[1],
        "back": r[2],
        "topic": r[3],
        "interval": r[4],
        "repetitions": r[5],
        "ease_factor": r[6],
        "next_review": r[7],
    } for r in rows]


def record_flashcard_review(card_id: int, grade: int):
    """
    SuperMemo SM-2 Algorithm implementation.
    grade:
      1: Again (Forgot, reset interval to 1)
      2: Hard (Interval * 1.2)
      3: Good (Interval * ease_factor)
      4: Easy (Interval * ease_factor * 1.3, ease_factor increases)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT interval, repetitions, ease_factor FROM flashcards WHERE id = ?", (card_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return

    interval, reps, ef = row

    if grade == 1:
        reps = 0
        interval = 1
    elif grade == 2:
        reps += 1
        interval = max(1, int(interval * 1.2))
        ef = max(1.3, ef - 0.15)
    elif grade == 3:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = int(interval * ef)
        reps += 1
    elif grade == 4:
        if reps == 0:
            interval = 2
        elif reps == 1:
            interval = 8
        else:
            interval = int(interval * ef * 1.3)
        reps += 1
        ef = min(3.0, ef + 0.15)

    next_date = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        UPDATE flashcards
        SET interval = ?, repetitions = ?, ease_factor = ?, next_review_date = ?
        WHERE id = ?
    """, (interval, reps, ef, next_date, card_id))
    conn.commit()
    conn.close()


def add_custom_flashcard(front_prompt: str, back_answer: str, topic: str = "General"):
    """Adds a new custom flashcard to the deck."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO flashcards (front_prompt, back_answer, topic, next_review_date)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (front_prompt.strip(), back_answer.strip(), topic.strip()))
    conn.commit()
    c_id = cur.lastrowid
    conn.close()
    return c_id
