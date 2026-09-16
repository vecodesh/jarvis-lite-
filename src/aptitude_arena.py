"""
JARVIS-lite: Campus Placement Aptitude & MCQ Drill Arena

Prepares engineering candidates for Round 1 Online Assessments (OA).
Covers:
1. Quantitative Aptitude (Time & Work, Speed & Distance, Probability, Combinatorics)
2. Logical Reasoning (Series, Syllogisms, Deduction)
3. Core Computer Science MCQs (OS Paging, DBMS Queries, Networks, C/C++ Pointers)

Features:
- Instant curated question bank for zero-latency drills.
- On-demand AI question generator via Ollama (llama3.1:8b).
- Performance tracking and accuracy analytics in assistant.db.
"""

import sys
import json
import random
import sqlite3
from pathlib import Path

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


def init_aptitude_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aptitude_drills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_idx INTEGER NOT NULL,
            user_selected_idx INTEGER,
            is_correct INTEGER NOT NULL DEFAULT 0,
            explanation TEXT,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_aptitude_table()

# Curated High-Frequency Placement OA Questions
CURATED_MCQS = [
    # Quantitative Aptitude
    {
        "category": "Quantitative Aptitude",
        "question": "A can complete a piece of work in 12 days and B in 16 days. If they work together for 4 days, what fraction of the work remains?",
        "options": ["7/12", "5/12", "1/3", "7/16"],
        "correct_idx": 1,
        "explanation": "Work done in 1 day = (1/12 + 1/16) = 7/48. In 4 days, work done = 4 * (7/48) = 7/12. Remaining work = 1 - 7/12 = 5/12."
    },
    {
        "category": "Quantitative Aptitude",
        "question": "Two trains running in opposite directions cross a man standing on the platform in 27 seconds and 17 seconds respectively and they cross each other in 23 seconds. The ratio of their speeds is:",
        "options": ["3:2", "1:3", "3:4", "2:1"],
        "correct_idx": 0,
        "explanation": "Let speeds be x and y. Distances = 27x and 17y. (27x + 17y) / (x + y) = 23 => 27x + 17y = 23x + 23y => 4x = 6y => x/y = 3/2."
    },
    {
        "category": "Quantitative Aptitude",
        "question": "In how many different ways can the letters of the word 'LEADING' be arranged in such a way that the vowels always come together?",
        "options": ["360", "480", "720", "5040"],
        "correct_idx": 2,
        "explanation": "Vowels are E, A, I (3 vowels). Treat (EAI) as 1 unit. Total units = L, D, N, G + (EAI) = 5 units. Arrangements = 5! * 3! = 120 * 6 = 720."
    },
    {
        "category": "Quantitative Aptitude",
        "question": "A bag contains 6 black and 8 white balls. One ball is drawn at random. What is the probability that the ball drawn is white?",
        "options": ["4/7", "3/7", "1/8", "3/4"],
        "correct_idx": 0,
        "explanation": "Total balls = 6 + 8 = 14. Probability of white = 8/14 = 4/7."
    },

    # Core CS: Operating Systems & Computer Networks
    {
        "category": "Operating Systems",
        "question": "Which of the following conditions is NOT required for a deadlock to occur in an operating system?",
        "options": ["Mutual Exclusion", "Hold and Wait", "Preemption", "Circular Wait"],
        "correct_idx": 2,
        "explanation": "The 4 Coffman conditions for deadlock are: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait. Preemption actually prevents deadlock!"
    },
    {
        "category": "Operating Systems",
        "question": "Belady's Anomaly states that:",
        "options": [
            "LRU page fault frequency increases with more frames",
            "FIFO page faults can increase even when page frames are increased",
            "Optimal page replacement requires future knowledge",
            "Thrashing occurs when CPU utilization reaches 100%"
        ],
        "correct_idx": 1,
        "explanation": "Belady's Anomaly is a counter-intuitive phenomenon where increasing the number of page frames results in an increase in the number of page faults for certain access patterns using FIFO."
    },
    {
        "category": "Computer Networks",
        "question": "What is the size of the TCP header with no optional fields?",
        "options": ["16 bytes", "20 bytes", "32 bytes", "64 bytes"],
        "correct_idx": 1,
        "explanation": "The standard minimum TCP header length is 20 bytes (5 32-bit words). It can extend up to 60 bytes with options."
    },
    {
        "category": "Computer Networks",
        "question": "Which protocol is responsible for mapping an IP address to a physical MAC address on a local area network?",
        "options": ["DHCP", "DNS", "ARP", "ICMP"],
        "correct_idx": 2,
        "explanation": "Address Resolution Protocol (ARP) translates an IPv4 address into the physical MAC hardware address."
    },

    # Core CS: DBMS & SQL
    {
        "category": "Database Management (DBMS)",
        "question": "Which normal form deals with eliminating Transitive Functional Dependencies (X -> Y and Y -> Z)?",
        "options": ["First Normal Form (1NF)", "Second Normal Form (2NF)", "Third Normal Form (3NF)", "Boyce-Codd Normal Form (BCNF)"],
        "correct_idx": 2,
        "explanation": "3NF removes transitive functional dependencies on the primary key. 2NF removes partial dependencies."
    },
    {
        "category": "Database Management (DBMS)",
        "question": "Why are B+ Trees predominantly preferred over standard Binary Search Trees or B-Trees for database disk indexes?",
        "options": [
            "All data pointers are stored in the leaf nodes, enabling high-fanout disk I/O and rapid range scans via leaf pointers",
            "B+ Trees consume less main memory than hash maps",
            "Binary search trees have lower worst-case Big-O time complexity",
            "B+ Trees do not require rebalancing operations"
        ],
        "correct_idx": 0,
        "explanation": "B+ Trees store key-only internal nodes (maximizing branching factor / fan-out per disk block) and link all leaf nodes in a doubly-linked list for lightning-fast sequential range scans."
    },

    # Core CS: Programming & Data Structures
    {
        "category": "Programming & DSA",
        "question": "What is the output of the C expression: sizeof('a') on a standard 32/64-bit C compiler?",
        "options": ["1", "4", "2", "Undefined"],
        "correct_idx": 1,
        "explanation": "In standard C, character constants like 'a' have type 'int', so sizeof('a') == sizeof(int) which is 4 bytes. (In C++, it evaluates to char which is 1 byte)."
    },
    {
        "category": "Programming & DSA",
        "question": "What is the worst-case time complexity of searching for an element in an AVL Tree with N elements?",
        "options": ["O(N)", "O(log N)", "O(N log N)", "O(1)"],
        "correct_idx": 1,
        "explanation": "Because an AVL tree is strictly balanced with height bounded by 1.44 * log2(N), its worst-case search complexity remains strictly O(log N)."
    },
]


def get_curated_quiz(category: str = "All", count: int = 5) -> list[dict]:
    """Retrieves randomized questions from the curated bank."""
    if category and category != "All":
        pool = [q for q in CURATED_MCQS if q["category"].lower() == category.lower()]
        if not pool:
            pool = CURATED_MCQS
    else:
        pool = CURATED_MCQS

    sample_size = min(count, len(pool))
    return random.sample(pool, sample_size)


def generate_ai_quiz(category: str = "Quantitative Aptitude", count: int = 3) -> list[dict]:
    """Generates novel placement OA MCQs using Ollama."""
    prompt = (
        f"You are an assessment architect designing campus placement Online Assessment (OA) MCQs.\n\n"
        f"CATEGORY: {category}\nCOUNT: {count}\n\n"
        "Generate realistic, rigorous placement MCQs. Return ONLY a valid JSON list matching this schema:\n"
        "[\n"
        "  {\n"
        f'    "category": "{category}",\n'
        '    "question": "Clear problem statement",\n'
        '    "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '    "correct_idx": 0,\n'
        '    "explanation": "Step by step mathematical or technical derivation."\n'
        "  }\n"
        "]\n"
    )
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.4}
        )
        data = json.loads(resp["message"]["content"])
        if isinstance(data, list) and len(data) > 0:
            return data
        elif isinstance(data, dict) and "questions" in data:
            return data["questions"]
        return get_curated_quiz(category, count)
    except Exception:
        return get_curated_quiz(category, count)


def record_drill_result(category: str, question: str, options: list, correct_idx: int, selected_idx: int, explanation: str) -> bool:
    """Logs the candidate's answer into the database."""
    is_corr = 1 if correct_idx == selected_idx else 0
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO aptitude_drills
        (category, question_text, options_json, correct_idx, user_selected_idx, is_correct, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (category, question, json.dumps(options), correct_idx, selected_idx, is_corr, explanation))
    conn.commit()
    conn.close()
    return bool(is_corr)


def get_aptitude_stats() -> dict:
    """Calculates overall drill accuracy and category performance."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(is_correct) FROM aptitude_drills")
    total, correct = cur.fetchone()
    total = total or 0
    correct = correct or 0
    accuracy = int((correct / total) * 100) if total else 0

    cur.execute("""
        SELECT category, COUNT(*), SUM(is_correct)
        FROM aptitude_drills
        GROUP BY category
    """)
    cat_breakdown = []
    for cat, c_tot, c_cor in cur.fetchall():
        c_tot = c_tot or 0
        c_cor = c_cor or 0
        c_acc = int((c_cor / c_tot) * 100) if c_tot else 0
        cat_breakdown.append({
            "category": cat,
            "total": c_tot,
            "correct": c_cor,
            "accuracy": c_acc,
        })

    conn.close()
    return {
        "total_attempted": total,
        "correct": correct,
        "overall_accuracy": accuracy,
        "categories": cat_breakdown,
    }
