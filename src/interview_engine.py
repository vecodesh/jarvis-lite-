"""
JARVIS-lite: AI Placement Mock Interviewer & Flashcard Drills (Phase 6)

Features:
1. Pulls technical topics from assistant.db or standard placement curricula.
2. Generates real-world technical and conceptual placement interview questions.
3. Evaluates spoken or typed candidate answers on a scale of 1-10.
4. Identifies candidate strengths, missed edge cases, and provides model answers.
5. Saves interview history into the database to track placement readiness over time.
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

DEFAULT_TOPICS = [
    "Data Structures (Arrays, Linked Lists, Trees, Graphs)",
    "Algorithms (Sorting, Binary Search, Dynamic Programming)",
    "DBMS (Indexing, Normalization, ACID Properties, SQL Joins)",
    "Operating Systems (Virtual Memory, Process Scheduling, Deadlocks)",
    "Computer Networks (TCP/UDP, DNS, HTTP/HTTPS, OSI Model)",
    "Object-Oriented Programming (Polymorphism, Inheritance, Solid Principles)",
    "System Design (Load Balancing, Caching, Sharding, CAP Theorem)",
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_interview_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mock_interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT,
            score INTEGER DEFAULT 0,
            feedback TEXT,
            model_answer TEXT,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_interview_table()


def get_available_topics():
    """Returns topics from the database combined with placement core domains."""
    topics = list(DEFAULT_TOPICS)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT topic_name FROM topics WHERE topic_name IS NOT NULL AND topic_name != ''")
        db_topics = [r[0] for r in cur.fetchall()]
        conn.close()
        for t in db_topics:
            if t not in topics:
                topics.insert(0, t)
    except Exception:
        pass
    return topics


QUESTION_PROMPT = """You are a senior tech lead at a premier tech firm (like Google, Amazon, Microsoft) conducting a technical placement interview.

TASK:
Generate ONE high-quality, practical technical interview question testing deep conceptual understanding of the given topic: {topic}.

RULES:
- Focus on practical trade-offs, internal mechanics, or realistic algorithmic challenges.
- Avoid trivia; ask how or why something works under the hood.
- Do NOT provide the answer. Return ONLY the interview question text.
- Tone: Professional, direct, and rigorous.
"""


def generate_interview_question(topic: str) -> str:
    """Generates an interview question for a specific topic."""
    prompt = QUESTION_PROMPT.format(topic=topic)
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.5}
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        return f"Explain the core mechanics and trade-offs of {topic}."


EVAL_PROMPT = """You are JARVIS, an elite AI technical interviewer evaluating a student's answer for a software engineering placement question.

TOPIC: {topic}
QUESTION: {question}
CANDIDATE ANSWER: {user_answer}

Evaluate the candidate's answer with extreme technical precision and fairness.
Return ONLY valid JSON matching this exact structure:
{{
  "score": <integer from 1 to 10>,
  "strengths": "<brief summary of what the candidate got right>",
  "missing_points": "<critical concepts, edge cases, or trade-offs the candidate missed>",
  "model_answer": "<concise, perfect 2-3 sentence answer suitable for an interview>"
}}

No markdown outside JSON. No extra commentary.
"""


def evaluate_interview_answer(topic: str, question: str, user_answer: str) -> dict:
    """Evaluates the candidate's response and returns score + feedback."""
    if not user_answer or len(user_answer.strip()) < 3:
        return {
            "score": 0,
            "strengths": "No answer provided.",
            "missing_points": "The question was not addressed.",
            "model_answer": "Provide a structured answer stating the core concept, mechanism, and trade-offs.",
        }

    prompt = EVAL_PROMPT.format(topic=topic, question=question, user_answer=user_answer)
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.2}
        )
        content = resp["message"]["content"]
        data = json.loads(content)
        # Ensure integer score
        data["score"] = int(data.get("score", 5))
        return data
    except Exception as e:
        return {
            "score": 5,
            "strengths": "Answer recorded.",
            "missing_points": f"AI evaluation notice: {e}",
            "model_answer": "Core mechanism, time complexity, and practical trade-offs.",
        }


def save_interview_result(topic: str, question: str, user_answer: str, eval_data: dict) -> int:
    """Saves interview question, answer, and evaluation to the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mock_interviews (topic, question, user_answer, score, feedback, model_answer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        topic,
        question,
        user_answer,
        eval_data.get("score", 0),
        json.dumps({
            "strengths": eval_data.get("strengths", ""),
            "missing_points": eval_data.get("missing_points", "")
        }),
        eval_data.get("model_answer", "")
    ))
    conn.commit()
    drill_id = cur.lastrowid
    conn.close()
    return drill_id


def get_interview_history(limit: int = 15):
    """Fetches recent mock interview drills."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, topic, question, user_answer, score, feedback, model_answer, created_date
        FROM mock_interviews
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def run_hands_free_interview_question(topic: str, on_status=None, on_question=None, on_eval=None) -> dict:
    """
    Executes a complete hands-free voice interview round:
    1. Generates technical question.
    2. Speaks question aloud using voice.speak.
    3. Plays chime and listens to microphone for spoken answer.
    4. Evaluates answer via local Ollama.
    5. Saves result in database.
    6. Speaks verdict and score aloud.
    """
    from voice import speak, listen_to_microphone, play_chime

    if on_status:
        on_status("Synthesizing technical question...")
    q = generate_interview_question(topic)

    if on_question:
        on_question(q)

    # Speak question aloud
    if on_status:
        on_status("JARVIS speaking question...")
    speak(q, async_mode=False)

    play_chime()

    # Listen to candidate's spoken response
    if on_status:
        on_status("🎤 Listening to your answer (speak clearly for up to 20s)...")

    user_ans, err = listen_to_microphone(timeout=10, phrase_time_limit=20)
    if not user_ans:
        user_ans = "No spoken answer detected."

    if on_status:
        on_status("Analyzing technical answer...")

    res = evaluate_interview_answer(topic, q, user_ans)
    save_interview_result(topic, q, user_ans, res)

    score = res.get("score", 5)

    if on_eval:
        on_eval(user_ans, res)

    speak(f"Score: {score} out of 10. {res.get('strengths', '')[:120]}", async_mode=True)
    return {
        "question": q,
        "answer": user_ans,
        "eval": res,
    }

