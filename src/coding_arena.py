"""
JARVIS-lite: Live DSA Coding Arena & Automated Code Reviewer (Phase 7)

Features:
1. Curated catalog & AI generation of high-frequency DSA placement problems.
2. Multi-language support (Python, C++, Java).
3. Automated AI Code Reviewer:
   - Evaluates Time and Space Complexity (Big-O).
   - Detects tricky edge-case bugs (null pointers, empty arrays, integer overflows, duplicates).
   - Suggests clean, production/interview-ready optimizations.
4. Stores coding drill history in SQLite.
"""

import sys
import json
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

CURATED_PROBLEMS = [
    {
        "title": "Two Sum",
        "topic": "Arrays & Hash Maps",
        "difficulty": "Easy",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
        "starter_python": "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Implement optimal O(N) hash map solution\n    seen = {}\n    for i, n in enumerate(nums):\n        diff = target - n\n        if diff in seen:\n            return [seen[diff], i]\n        seen[n] = i\n    return []\n",
        "starter_cpp": "#include <vector>\n#include <unordered_map>\n\nstd::vector<int> twoSum(std::vector<int>& nums, int target) {\n    // Implement optimal O(N) solution\n}\n",
        "test_python": 'print("Test 1:", twoSum([2, 7, 11, 15], 9))  # Expected: [0, 1]\nprint("Test 2:", twoSum([3, 2, 4], 6))        # Expected: [1, 2]\nprint("Test 3:", twoSum([3, 3], 6))           # Expected: [0, 1]',
    },
    {
        "title": "Valid Parentheses",
        "topic": "Stacks",
        "difficulty": "Easy",
        "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\nAn input string is valid if open brackets are closed by the same type of brackets in the correct order.",
        "starter_python": 'def isValid(s: str) -> bool:\n    stack = []\n    mapping = {")": "(", "}": "{", "]": "["}\n    for char in s:\n        if char in mapping:\n            top = stack.pop() if stack else "#"\n            if mapping[char] != top:\n                return False\n        else:\n            stack.append(char)\n    return not stack\n',
        "starter_cpp": "#include <string>\n#include <stack>\n\nbool isValid(std::string s) {\n    // Implement stack solution\n}\n",
        "test_python": 'print("Test 1 (\\\"()[]{}\\\"): ", isValid("()[]{}"))  # Expected: True\nprint("Test 2 (\\\"(]\\\"):     ", isValid("(]"))      # Expected: False\nprint("Test 3 (\\\"([)]\\\"):   ", isValid("([)]"))    # Expected: False',
    },
    {
        "title": "Longest Substring Without Repeating Characters",
        "topic": "Sliding Window",
        "difficulty": "Medium",
        "description": "Given a string s, find the length of the longest substring without duplicate characters.",
        "starter_python": "def lengthOfLongestSubstring(s: str) -> int:\n    char_set = set()\n    left = 0\n    res = 0\n    for right in range(len(s)):\n        while s[right] in char_set:\n            char_set.remove(s[left])\n            left += 1\n        char_set.add(s[right])\n        res = max(res, right - left + 1)\n    return res\n",
        "starter_cpp": "#include <string>\n#include <unordered_set>\n\nint lengthOfLongestSubstring(std::string s) {\n    // Implement sliding window\n}\n",
        "test_python": 'print("Test 1 (\\\"abcabcbb\\\"): ", lengthOfLongestSubstring("abcabcbb"))  # Expected: 3\nprint("Test 2 (\\\"bbbbb\\\"):    ", lengthOfLongestSubstring("bbbbb"))     # Expected: 1\nprint("Test 3 (\\\"pwwkew\\\"):   ", lengthOfLongestSubstring("pwwkew"))    # Expected: 3',
    },
    {
        "title": "Merge Intervals",
        "topic": "Arrays & Sorting",
        "difficulty": "Medium",
        "description": "Given an array of intervals where intervals[i] = [start_i, end_i], merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.",
        "starter_python": "def merge(intervals: list[list[int]]) -> list[list[int]]:\n    intervals.sort(key=lambda x: x[0])\n    merged = []\n    for interval in intervals:\n        if not merged or merged[-1][1] < interval[0]:\n            merged.append(interval)\n        else:\n            merged[-1][1] = max(merged[-1][1], interval[1])\n    return merged\n",
        "starter_cpp": "#include <vector>\n#include <algorithm>\n\nstd::vector<std::vector<int>> merge(std::vector<std::vector<int>>& intervals) {\n    // Implement interval merge\n}\n",
        "test_python": 'print("Test 1:", merge([[1,3],[2,6],[8,10],[15,18]]))  # Expected: [[1,6],[8,10],[15,18]]\nprint("Test 2:", merge([[1,4],[4,5]]))              # Expected: [[1,5]]',
    },
    {
        "title": "Course Schedule (Detect Cycle in DAG)",
        "topic": "Graphs & Topological Sort",
        "difficulty": "Medium",
        "description": "There are a total of numCourses courses you have to take, labeled from 0 to numCourses - 1. You are given an array prerequisites where prerequisites[i] = [a_i, b_i] indicates that you must take course b_i first if you want to take course a_i.\nReturn true if you can finish all courses, or false otherwise.",
        "starter_python": "def canFinish(numCourses: int, prerequisites: list[list[int]]) -> bool:\n    from collections import defaultdict, deque\n    adj = defaultdict(list)\n    in_degree = [0] * numCourses\n    for dest, src in prerequisites:\n        adj[src].append(dest)\n        in_degree[dest] += 1\n    queue = deque([i for i in range(numCourses) if in_degree[i] == 0])\n    visited = 0\n    while queue:\n        node = queue.popleft()\n        visited += 1\n        for neighbor in adj[node]:\n            in_degree[neighbor] -= 1\n            if in_degree[neighbor] == 0:\n                queue.append(neighbor)\n    return visited == numCourses\n",
        "starter_cpp": "#include <vector>\n#include <queue>\n\nbool canFinish(int numCourses, std::vector<std::vector<int>>& prerequisites) {\n    // Kahn's algorithm\n}\n",
        "test_python": 'print("Test 1 (2, [[1,0]]):       ", canFinish(2, [[1,0]]))        # Expected: True\nprint("Test 2 (2, [[1,0],[0,1]]): ", canFinish(2, [[1,0],[0,1]]))  # Expected: False',
    },
    {
        "title": "LRU Cache",
        "topic": "Design & Linked Lists",
        "difficulty": "Hard",
        "description": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache. Implement LRUCache with get(key) and put(key, value) in O(1) time complexity.",
        "starter_python": "from collections import OrderedDict\n\nclass LRUCache:\n    def __init__(self, capacity: int):\n        self.cap = capacity\n        self.cache = OrderedDict()\n\n    def get(self, key: int) -> int:\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n\n    def put(self, key: int, value: int) -> None:\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.cap:\n            self.cache.popitem(last=False)\n",
        "starter_cpp": "#include <unordered_map>\n#include <list>\n\nclass LRUCache {\npublic:\n    LRUCache(int capacity) {}\n    int get(int key) { return -1; }\n    void put(int key, int value) {}\n};\n",
        "test_python": 'c = LRUCache(2)\nc.put(1, 1)\nc.put(2, 2)\nprint("get(1):", c.get(1))  # Expected: 1\nc.put(3, 3)                  # Evicts key 2\nprint("get(2):", c.get(2))  # Expected: -1\nc.put(4, 4)                  # Evicts key 1\nprint("get(1):", c.get(1))  # Expected: -1\nprint("get(3):", c.get(3))  # Expected: 3\nprint("get(4):", c.get(4))  # Expected: 4',
    },
]


def run_python_code(user_code: str, test_harness: str = "") -> dict:
    """
    Safely executes user code and test harness in an isolated subprocess.
    Returns: { 'success': bool, 'output': str, 'error': str, 'runtime_ms': float }
    """
    import subprocess
    import time

    full_code = f"{user_code.strip()}\n\n# --- TEST HARNESS ---\n{test_harness.strip()}\n"

    start_t = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", full_code],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
        if proc.returncode == 0:
            return {
                "success": True,
                "output": proc.stdout.strip(),
                "error": "",
                "runtime_ms": elapsed_ms,
            }
        else:
            return {
                "success": False,
                "output": proc.stdout.strip(),
                "error": proc.stderr.strip(),
                "runtime_ms": elapsed_ms,
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution timed out (5.0s limit exceeded). Check for infinite loops or non-terminating recursion.",
            "runtime_ms": 5000.0,
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "runtime_ms": 0.0,
        }


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_coding_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coding_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_title TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'Python',
            user_code TEXT NOT NULL,
            verdict TEXT NOT NULL,
            time_complexity TEXT,
            space_complexity TEXT,
            review_notes TEXT,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_coding_table()


def get_curated_problems():
    """Returns the problem catalog."""
    return CURATED_PROBLEMS


def generate_custom_problem(topic: str, difficulty: str = "Medium") -> dict:
    """Generates a novel coding interview problem via Ollama."""
    prompt = (
        f"You are a principal engineer at Google designing a coding interview problem.\n\n"
        f"TOPIC: {topic}\nDIFFICULTY: {difficulty}\n\n"
        "Generate ONE clean, practical coding problem. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "title": "Problem Title",\n'
        f'  "difficulty": "{difficulty}",\n'
        f'  "topic": "{topic}",\n'
        '  "description": "Clear statement of the problem, input/output formats, and constraints.",\n'
        '  "starter_python": "def solution(...):\\n    pass",\n'
        '  "starter_cpp": "class Solution {\\npublic:\\n    void solve() {}\\n};",\n'
        '  "test_python": "print(\\"Test 1:\\", solution(...))\\nprint(\\"Test 2:\\", solution(...))"\n'
        "}\n"
    )
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.4}
        )
        return json.loads(resp["message"]["content"])
    except Exception:
        # Fallback to curated
        return CURATED_PROBLEMS[0]


REVIEW_PROMPT = """You are JARVIS, an elite algorithmic code reviewer and interviewer.

PROBLEM: {problem_title}
LANGUAGE: {language}
CANDIDATE CODE:
{user_code}

TASK:
Analyze the candidate's solution with extreme technical precision.
Return ONLY valid JSON with this exact structure:
{{
  "verdict": "Optimal | Suboptimal | Has Bugs | Incomplete",
  "time_complexity": "e.g. O(N) or O(N^2)",
  "space_complexity": "e.g. O(1) or O(N)",
  "bugs_and_edge_cases": ["bullet point 1", "bullet point 2"],
  "optimizations": ["key recommendation 1", "key recommendation 2"],
  "optimized_code": "# Clean, idiomatic, interview-grade code\\n..."
}}

RULES:
- Rigorously check edge cases: empty input, single element, negative numbers, overflow, duplicate keys.
- If solution is already optimal, state so in optimizations.
- Keep bullets concise and high-signal.
"""


def review_candidate_code(problem_title: str, user_code: str, language: str = "Python") -> dict:
    """Reviews code, evaluates Big-O, finds edge cases, and provides optimal code."""
    if not user_code or len(user_code.strip()) < 10:
        return {
            "verdict": "Incomplete",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "bugs_and_edge_cases": ["No substantive code submitted."],
            "optimizations": ["Write a complete implementation addressing the problem constraints."],
            "optimized_code": "# Awaiting implementation",
        }

    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": REVIEW_PROMPT.format(
                    problem_title=problem_title,
                    language=language,
                    user_code=user_code
                )
            }],
            format="json",
            options={"temperature": 0.2}
        )
        data = json.loads(resp["message"]["content"])

        # Save submission
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO coding_submissions
            (problem_title, language, user_code, verdict, time_complexity, space_complexity, review_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            problem_title,
            language,
            user_code,
            data.get("verdict", "Evaluated"),
            data.get("time_complexity", "O(N)"),
            data.get("space_complexity", "O(1)"),
            json.dumps({
                "bugs": data.get("bugs_and_edge_cases", []),
                "optimizations": data.get("optimizations", [])
            })
        ))
        conn.commit()
        conn.close()

        return data
    except Exception as e:
        return {
            "verdict": "Review Error",
            "time_complexity": "Unknown",
            "space_complexity": "Unknown",
            "bugs_and_edge_cases": [f"Review encountered an error: {e}"],
            "optimizations": ["Ensure Ollama is running and model is loaded."],
            "optimized_code": user_code,
        }
