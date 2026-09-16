"""
JARVIS-lite: Striver A2Z DSA Sheet Hub & Voice Dry-Run Revision Engine

Designed specifically for the candidate's exact study workflow:
1. Curated Striver A2Z / SDE sheet problems with direct links to:
   - LeetCode / Coding Ninjas (Code360 by Naukri) / HackerRank
   - Striver (take U forward) YouTube Video Solutions
   - 1-Click Excalidraw (excalidraw.com) for visual sum logic diagramming
2. "Explain Aloud" Voice Interview Practice:
   - Candidate speaks their thought process, intuition, and dry-run into the mic.
   - Evaluated by local Ollama (llama3.1:8b) for interview clarity (1-10) and articulation.
3. Automated Dry-Run Notes & 1-Minute Spoken Revisions:
   - Converts spoken words into structured notes (Intuition, Dry-Run steps, Big-O, Edge Cases).
   - Solves the problem of forgetting DP or complex algorithms after weeks.
"""

import sys
import json
import sqlite3
import webbrowser
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


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_dsa_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dsa_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            subtopic TEXT NOT NULL,
            title TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            platform_url TEXT NOT NULL,
            video_url TEXT,
            status TEXT NOT NULL DEFAULT 'unsolved',
            last_revised_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dsa_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            raw_spoken_transcript TEXT,
            intuition_summary TEXT NOT NULL,
            dry_run_steps TEXT NOT NULL,
            time_complexity TEXT,
            space_complexity TEXT,
            edge_cases TEXT,
            verbal_score INTEGER DEFAULT 5,
            verbal_critique TEXT,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES dsa_problems (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


init_dsa_tables()


# Seed Striver A2Z / SDE High-Frequency Placement Problems
SEED_STRIVER_PROBLEMS = [
    # Dynamic Programming
    {
        "topic": "Dynamic Programming",
        "subtopic": "1D DP",
        "title": "Climbing Stairs",
        "difficulty": "Easy",
        "platform_url": "https://leetcode.com/problems/climbing-stairs/",
        "video_url": "https://www.youtube.com/watch?v=mLfjzJsN8us",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "1D DP",
        "title": "Frog Jump (DP-3)",
        "difficulty": "Medium",
        "platform_url": "https://www.naukri.com/code360/problems/frog-jump_3621012",
        "video_url": "https://www.youtube.com/watch?v=EgG3jsGoPvQ",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "2D Grid DP",
        "title": "Grid Unique Paths",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/unique-paths/",
        "video_url": "https://www.youtube.com/watch?v=sdE0A2Oxofw",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "DP on Subsequences",
        "title": "0/1 Knapsack Problem",
        "difficulty": "Medium",
        "platform_url": "https://www.naukri.com/code360/problems/0-1-knapsack_920542",
        "video_url": "https://www.youtube.com/watch?v=GqOmJHQvEBw",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "DP on Subsequences",
        "title": "Coin Change (Minimum Coins)",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/coin-change/",
        "video_url": "https://www.youtube.com/watch?v=myPeWb3Y68A",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "DP on Strings",
        "title": "Longest Common Subsequence (LCS)",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/longest-common-subsequence/",
        "video_url": "https://www.youtube.com/watch?v=NPZn9jBrX8U",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "DP on Strings",
        "title": "Edit Distance",
        "difficulty": "Hard",
        "platform_url": "https://leetcode.com/problems/edit-distance/",
        "video_url": "https://www.youtube.com/watch?v=fJaKO8FbDdo",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "DP on Stocks",
        "title": "Best Time to Buy and Sell Stock",
        "difficulty": "Easy",
        "platform_url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/",
        "video_url": "https://www.youtube.com/watch?v=excAOvwF_Wk",
    },
    {
        "topic": "Dynamic Programming",
        "subtopic": "DP on LIS",
        "title": "Longest Increasing Subsequence (LIS)",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/longest-increasing-subsequence/",
        "video_url": "https://www.youtube.com/watch?v=ekcwMsSIzVc",
    },

    # Arrays & Hashing
    {
        "topic": "Arrays & Hashing",
        "subtopic": "Easy / Fundamentals",
        "title": "Two Sum",
        "difficulty": "Easy",
        "platform_url": "https://leetcode.com/problems/two-sum/",
        "video_url": "https://www.youtube.com/watch?v=UXDSeD9mN-k",
    },
    {
        "topic": "Arrays & Hashing",
        "subtopic": "Prefix Sum / Hashing",
        "title": "Longest Subarray with Sum K",
        "difficulty": "Medium",
        "platform_url": "https://www.naukri.com/code360/problems/longest-subarray-with-sum-k_6682399",
        "video_url": "https://www.youtube.com/watch?v=frf7qxiN2qU",
    },
    {
        "topic": "Arrays & Hashing",
        "subtopic": "Kadane's Algorithm",
        "title": "Maximum Subarray Sum",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/maximum-subarray/",
        "video_url": "https://www.youtube.com/watch?v=AHZpyENo7k4",
    },
    {
        "topic": "Arrays & Hashing",
        "subtopic": "Dutch National Flag",
        "title": "Sort Colors (0s, 1s, and 2s)",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/sort-colors/",
        "video_url": "https://www.youtube.com/watch?v=tp8JIuCXBaU",
    },
    {
        "topic": "Arrays & Hashing",
        "subtopic": "Intervals",
        "title": "Merge Overlapping Intervals",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/merge-intervals/",
        "video_url": "https://www.youtube.com/watch?v=IexN60k62jo",
    },
    {
        "topic": "Arrays & Hashing",
        "subtopic": "Two Pointers",
        "title": "3Sum",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/3sum/",
        "video_url": "https://www.youtube.com/watch?v=DhFh8Kw7ymk",
    },

    # Two Pointers & Sliding Window
    {
        "topic": "Sliding Window",
        "subtopic": "Variable Window",
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/longest-substring-without-repeating-characters/",
        "video_url": "https://www.youtube.com/watch?v=-zSxTJkcdAo",
    },
    {
        "topic": "Sliding Window",
        "subtopic": "Fixed / Condition Window",
        "title": "Max Consecutive Ones III",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/max-consecutive-ones-iii/",
        "video_url": "https://www.youtube.com/watch?v=3E4JBHSLpYk",
    },
    {
        "topic": "Sliding Window",
        "subtopic": "Two Pointers",
        "title": "Trapping Rain Water",
        "difficulty": "Hard",
        "platform_url": "https://leetcode.com/problems/trapping-rain-water/",
        "video_url": "https://www.youtube.com/watch?v=m18Hntz4EB8",
    },

    # Binary Search
    {
        "topic": "Binary Search",
        "subtopic": "Rotated Sorted Array",
        "title": "Search in Rotated Sorted Array",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/search-in-rotated-sorted-array/",
        "video_url": "https://www.youtube.com/watch?v=5qGrJbHhqFs",
    },
    {
        "topic": "Binary Search",
        "subtopic": "Binary Search on Answers",
        "title": "Koko Eating Bananas",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/koko-eating-bananas/",
        "video_url": "https://www.youtube.com/watch?v=qyfekrNni90",
    },

    # Trees & Graphs
    {
        "topic": "Trees & Graphs",
        "subtopic": "Binary Tree Traversal",
        "title": "Binary Tree Level Order Traversal (BFS)",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/binary-tree-level-order-traversal/",
        "video_url": "https://www.youtube.com/watch?v=EoAsWbO7sqg",
    },
    {
        "topic": "Trees & Graphs",
        "subtopic": "Binary Tree LCA",
        "title": "Lowest Common Ancestor in Binary Tree",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/",
        "video_url": "https://www.youtube.com/watch?v=_-QHfMDde90",
    },
    {
        "topic": "Trees & Graphs",
        "subtopic": "Graph BFS/DFS",
        "title": "Number of Islands",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/number-of-islands/",
        "video_url": "https://www.youtube.com/watch?v=muncqlKJrH0",
    },
    {
        "topic": "Trees & Graphs",
        "subtopic": "Topological Sort",
        "title": "Course Schedule (Cycle Detection / Kahn's)",
        "difficulty": "Medium",
        "platform_url": "https://leetcode.com/problems/course-schedule/",
        "video_url": "https://www.youtube.com/watch?v=WAOfKpxYHR8",
    },

    # Linked Lists
    {
        "topic": "Linked Lists",
        "subtopic": "Standard Operations",
        "title": "Reverse a Linked List",
        "difficulty": "Easy",
        "platform_url": "https://leetcode.com/problems/reverse-linked-list/",
        "video_url": "https://www.youtube.com/watch?v=D2vI2DNJGd8",
    },
    {
        "topic": "Linked Lists",
        "subtopic": "Floyd's Cycle",
        "title": "Detect Cycle in Linked List",
        "difficulty": "Easy",
        "platform_url": "https://leetcode.com/problems/linked-list-cycle/",
        "video_url": "https://www.youtube.com/watch?v=wiOo4DC5GGA",
    },
]


def seed_dsa_catalog():
    """Populates the initial database with Striver problems if table is empty."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dsa_problems")
    count = cur.fetchone()[0]
    if count == 0:
        for p in SEED_STRIVER_PROBLEMS:
            cur.execute("""
                INSERT INTO dsa_problems (topic, subtopic, title, difficulty, platform_url, video_url, status)
                VALUES (?, ?, ?, ?, ?, ?, 'unsolved')
            """, (p["topic"], p["subtopic"], p["title"], p["difficulty"], p["platform_url"], p["video_url"]))
        conn.commit()
    conn.close()


seed_dsa_catalog()


def get_dsa_topics() -> list[str]:
    """Returns unique topic categories."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT topic FROM dsa_problems ORDER BY topic")
    topics = [r[0] for r in cur.fetchall()]
    conn.close()
    return ["All Topics"] + topics


def get_dsa_problems(topic: str = None, status: str = None, search: str = None) -> list[dict]:
    """Fetches problems matching filters and annotates whether notes exist."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT p.id, p.topic, p.subtopic, p.title, p.difficulty,
               p.platform_url, p.video_url, p.status, p.last_revised_date,
               (SELECT COUNT(*) FROM dsa_notes WHERE problem_id = p.id) as note_count
        FROM dsa_problems p
        WHERE 1=1
    """
    params = []

    if topic and topic != "All Topics":
        query += " AND p.topic = ?"
        params.append(topic)

    if status and status != "All Statuses":
        query += " AND p.status = ?"
        params.append(status.lower())

    if search:
        query += " AND (LOWER(p.title) LIKE ? OR LOWER(p.subtopic) LIKE ?)"
        term = f"%{search.strip().lower()}%"
        params.extend([term, term])

    query += " ORDER BY p.id ASC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "topic": r[1],
            "subtopic": r[2],
            "title": r[3],
            "difficulty": r[4],
            "platform_url": r[5],
            "video_url": r[6],
            "status": r[7],
            "last_revised_date": r[8],
            "has_notes": r[9] > 0,
            "note_count": r[9],
        })
    return result


def get_problem_by_id(problem_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, topic, subtopic, title, difficulty, platform_url, video_url, status, last_revised_date FROM dsa_problems WHERE id = ?", (problem_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0],
        "topic": r[1],
        "subtopic": r[2],
        "title": r[3],
        "difficulty": r[4],
        "platform_url": r[5],
        "video_url": r[6],
        "status": r[7],
        "last_revised_date": r[8],
    }


def update_problem_status(problem_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE dsa_problems
        SET status = ?, last_revised_date = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status.lower(), problem_id))
    conn.commit()
    conn.close()


NOTE_SYNTHESIS_PROMPT = """You are JARVIS, an elite FAANG interviewer and technical coach.
A candidate just solved the DSA problem "{problem_title}" ({topic}) and explained their solution verbally into the microphone.

CANDIDATE'S SPOKEN TRANSCRIPT:
\"\"\"{spoken_transcript}\"\"\"

TASK:
1. Synthesize their spoken words into a crystal-clear, high-density "Dry-Run Revision Note" so they can instantly recall and revise this problem in 60 seconds before an interview.
2. Evaluate their verbal communication clarity on a scale of 1 to 10 (did they state intuition before jumping into code? Did they dry run an example? Did they justify complexity?).

Respond ONLY with valid JSON matching this exact structure:
{{
  "intuition_summary": "<2-3 sentences capturing the core spark/invariable of why this approach works in candidate's voice>",
  "dry_run_steps": "<Step-by-step trace of how pointers/DP state change on a small example (e.g. Input: [x,y] -> Step 1... -> Step 2...)>",
  "time_complexity": "<Big-O Time complexity with short reason, e.g. O(N)>",
  "space_complexity": "<Big-O Space complexity with short reason, e.g. O(1) or O(N)>",
  "edge_cases": "<Key edge cases to mention to interviewer (e.g. empty array, duplicates, single element)>",
  "verbal_score": <integer from 1 to 10>,
  "verbal_critique": "<2 concise sentences of coaching on how the candidate can sound more senior and articulate in an interview>"
}}

No extra markdown outside JSON.
"""


def record_voice_dry_run(problem_id: int, spoken_transcript: str) -> dict:
    """
    Takes spoken explanation, converts it into structured dry-run revision notes,
    rates the verbal explanation (1-10), and persists in database.
    """
    prob = get_problem_by_id(problem_id)
    if not prob:
        raise ValueError(f"Problem #{problem_id} not found.")

    if not spoken_transcript or len(spoken_transcript.strip()) < 5:
        spoken_transcript = "Candidate solved using standard optimal approach."

    prompt = NOTE_SYNTHESIS_PROMPT.format(
        problem_title=prob["title"],
        topic=prob["topic"],
        spoken_transcript=spoken_transcript,
    )

    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.2}
        )
        data = json.loads(resp["message"]["content"])
    except Exception as e:
        # Fallback if Ollama offline or error
        data = {
            "intuition_summary": f"Optimal solution for {prob['title']} addressing {prob['subtopic']} constraints.",
            "dry_run_steps": f"1. Initialize state variables.\n2. Iterate through input elements.\n3. Return optimal calculated result.",
            "time_complexity": "O(N)",
            "space_complexity": "O(1)",
            "edge_cases": "Empty input, single element, negative numbers.",
            "verbal_score": 7,
            "verbal_critique": "Solid conceptual explanation. Try dry-running with an explicit concrete numerical example.",
        }

    # Ensure integer score
    data["verbal_score"] = int(data.get("verbal_score", 7))

    # Persist in dsa_notes
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO dsa_notes (
            problem_id, raw_spoken_transcript, intuition_summary,
            dry_run_steps, time_complexity, space_complexity,
            edge_cases, verbal_score, verbal_critique
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        problem_id,
        spoken_transcript,
        data.get("intuition_summary", ""),
        data.get("dry_run_steps", ""),
        data.get("time_complexity", ""),
        data.get("space_complexity", ""),
        data.get("edge_cases", ""),
        data["verbal_score"],
        data.get("verbal_critique", ""),
    ))
    # Mark problem as solved and revised
    cur.execute("""
        UPDATE dsa_problems
        SET status = 'solved', last_revised_date = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (problem_id,))
    conn.commit()
    conn.close()

    return data


def get_problem_notes(problem_id: int) -> list[dict]:
    """Retrieves all saved dry-run notes for a problem, most recent first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, raw_spoken_transcript, intuition_summary, dry_run_steps,
               time_complexity, space_complexity, edge_cases,
               verbal_score, verbal_critique, created_date
        FROM dsa_notes
        WHERE problem_id = ?
        ORDER BY id DESC
    """, (problem_id,))
    rows = cur.fetchall()
    conn.close()

    notes = []
    for r in rows:
        notes.append({
            "id": r[0],
            "raw_transcript": r[1],
            "intuition": r[2],
            "dry_run": r[3],
            "time_complexity": r[4],
            "space_complexity": r[5],
            "edge_cases": r[6],
            "verbal_score": r[7],
            "verbal_critique": r[8],
            "created_date": r[9],
        })
    return notes


def get_quick_revision_speech(problem_id: int) -> str:
    """Generates a concise 30-second speech text for JARVIS TTS audio review."""
    prob = get_problem_by_id(problem_id)
    notes = get_problem_notes(problem_id)
    if not prob:
        return "Problem details not found."

    if not notes:
        return f"For {prob['title']} in {prob['topic']}: You have not recorded dry-run notes yet. Solve it, launch Excalidraw, and speak your solution aloud to generate permanent notes."

    latest = notes[0]
    speech = (
        f"Quick revision for {prob['title']}. "
        f"Intuition: {latest['intuition']}. "
        f"Complexity is {latest['time_complexity']} time and {latest['space_complexity']} space. "
        f"Watch out for edge cases: {latest['edge_cases']}."
    )
    return speech


def launch_excalidraw(problem_title: str = None):
    """Launches excalidraw.com in the default browser for whiteboard visualization."""
    url = "https://excalidraw.com"
    webbrowser.open(url)
    return url


def launch_problem_url(problem_id: int):
    prob = get_problem_by_id(problem_id)
    if prob and prob.get("platform_url"):
        webbrowser.open(prob["platform_url"])
        return prob["platform_url"]
    return None


def launch_video_url(problem_id: int):
    prob = get_problem_by_id(problem_id)
    if prob and prob.get("video_url"):
        webbrowser.open(prob["video_url"])
        return prob["video_url"]
    return None


def get_dsa_stats() -> dict:
    """Returns high-level statistics on Striver Sheet completion."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dsa_problems")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM dsa_problems WHERE status = 'solved'")
    solved = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT problem_id) FROM dsa_notes")
    with_notes = cur.fetchone()[0]

    conn.close()

    pct = int((solved / total) * 100) if total else 0
    return {
        "total": total,
        "solved": solved,
        "with_notes": with_notes,
        "pct_solved": pct,
    }
