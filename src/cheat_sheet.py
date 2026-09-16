"""
JARVIS-lite: 1-Click "Interview Day" Company Cheat-Sheet Generator

Generates a 1-page high-density, printable Stark Executive HTML cheat-sheet
designed for rapid review right before technical rounds.

Includes:
1. Target Company Header & Role Overview.
2. Past Interview Questions logged for that firm in assistant.db.
3. Top 6 Algorithmic Patterns & Big-O Quick Reference.
4. Core CS Rapid-Fire Reminders (OS, DBMS, Networks, Concurrency).
5. Candidate's Customized Project Elevator Pitch & Metrics.
"""

import sys
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

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "assistant.db"
OUTPUT_DIR = BASE_DIR / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    return sqlite3.connect(DB_PATH)


CHEAT_SHEET_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Interview Brief // {company_name}</title>
<style>
  @page {{ size: A4; margin: 10mm; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Consolas", monospace;
    background: #080c14;
    color: #e2e8f0;
    margin: 0;
    padding: 24px;
    font-size: 12px;
    line-height: 1.45;
  }}
  @media print {{
    body {{ background: #ffffff; color: #0f172a; padding: 0; font-size: 11px; }}
    .card {{ border-color: #cbd5e1 !important; background: #f8fafc !important; color: #0f172a !important; }}
    .badge {{ background: #e2e8f0 !important; color: #0f172a !important; }}
    h1, h2, h3, .accent {{ color: #0369a1 !important; }}
  }}
  .hdr {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #00d2ff;
    padding-bottom: 10px;
    margin-bottom: 16px;
  }}
  h1 {{ margin: 0; font-size: 20px; letter-spacing: 1px; color: #ffffff; }}
  h2 {{ margin: 0 0 6px 0; font-size: 13px; color: #00d2ff; text-transform: uppercase; letter-spacing: 0.5px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .card {{
    background: #0e1422;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 12px;
  }}
  .full-width {{ grid-column: span 2; }}
  ul {{ margin: 4px 0 0 0; padding-left: 18px; }}
  li {{ margin-bottom: 4px; }}
  .badge {{
    background: #1e293b;
    color: #38bdf8;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    display: inline-block;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 11px; }}
  th, td {{ text-align: left; padding: 4px 6px; border-bottom: 1px solid #1e293b; }}
  th {{ color: #94a3b8; font-weight: 600; }}
  .accent {{ color: #00d2ff; font-weight: bold; }}
  .gold {{ color: #f59e0b; }}
</style>
</head>
<body>

<div class="hdr">
  <div>
    <h1>⚡ TONY STARK INTERVIEW BRIEF: <span class="accent">{company_name_upper}</span></h1>
    <span style="color: #64748b; font-size: 10px;">Target Candidate: {candidate_name} | Generated: {current_date}</span>
  </div>
  <div style="text-align: right;">
    <span class="badge" style="background: #0f766e; color: #ffffff;">READINESS CONFIRMED</span>
  </div>
</div>

<div class="grid">

  <!-- Column 1: Company Past Questions -->
  <div class="card">
    <h2>🎯 Past Questions Asked by {company_name}</h2>
    {company_questions_html}
  </div>

  <!-- Column 2: Candidate Project Elevator Pitch -->
  <div class="card">
    <h2>💼 Your Project Elevator Pitch</h2>
    <p style="margin: 0 0 6px 0; font-size: 11px; color: #94a3b8;">When asked: <em>"Walk me through your most impactful project"</em></p>
    {candidate_project_html}
  </div>

  <!-- Column 3: High-Frequency Algorithmic Patterns -->
  <div class="card">
    <h2>⚡ Top Algorithmic Patterns & Complexities</h2>
    <table>
      <tr><th>Pattern</th><th>Data Structure</th><th>Time</th><th>Space</th></tr>
      <tr><td>Two Pointers / Hash</td><td>Dict / Array</td><td>O(N)</td><td>O(1) / O(N)</td></tr>
      <tr><td>Sliding Window</td><td>Set / Deque</td><td>O(N)</td><td>O(K)</td></tr>
      <tr><td>Monotonic Stack</td><td>Stack (LIFO)</td><td>O(N)</td><td>O(N)</td></tr>
      <tr><td>Topological Sort</td><td>Adjacency List + Queue</td><td>O(V+E)</td><td>O(V)</td></tr>
      <tr><td>Interval Merge</td><td>Sorted Array</td><td>O(N log N)</td><td>O(1)</td></tr>
      <tr><td>LRU Cache</td><td>Doubly Linked + Hash</td><td>O(1)</td><td>O(Capacity)</td></tr>
    </table>
  </div>

  <!-- Column 4: Core CS Rapid-Fire Cheatsheet -->
  <div class="card">
    <h2>🧠 Core CS Rapid-Fire Reminders</h2>
    <ul>
      <li><strong>Process vs Thread:</strong> Process has separate virtual address space; threads share heap/code and have private stack.</li>
      <li><strong>Deadlock 4 Conditions:</strong> Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait.</li>
      <li><strong>DBMS B+ Tree:</strong> Data pointers stored only in linked leaves, allowing high fan-out & sequential range queries.</li>
      <li><strong>TCP 3-Way Handshake:</strong> SYN (Seq X) ➔ SYN-ACK (Seq Y, Ack X+1) ➔ ACK (Seq X+1, Ack Y+1).</li>
      <li><strong>ACID Guarantees:</strong> Atomicity (all or none), Consistency (valid state), Isolation (MVCC/locking), Durability (WAL log).</li>
    </ul>
  </div>

</div>

<div style="margin-top: 14px; text-align: center; color: #475569; font-size: 10px;">
  JARVIS-lite // Neural Engineering & Career Console // Walk in calm, articulate your trade-offs, and secure the offer.
</div>

</body>
</html>
"""


def generate_company_cheat_sheet(company_name: str, output_filename: str = None) -> str:
    """
    Assembles company questions and candidate data into an executive printable HTML cheat-sheet.
    """
    c_name = company_name.strip() or "Tech Enterprise"

    # Fetch past company questions
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT round_type, question_text, difficulty
        FROM company_questions
        WHERE LOWER(company) LIKE ?
        ORDER BY id DESC LIMIT 5
    """, (f"%{c_name.lower()}%",))
    rows = cur.fetchall()

    if rows:
        q_items = []
        for r_type, q_txt, diff in rows:
            q_items.append(f"<li><span class='badge'>{r_type}</span> <span class='gold'>[{diff}]</span> {q_txt}</li>")
        company_questions_html = f"<ul>{''.join(q_items)}</ul>"
    else:
        company_questions_html = f"""
        <p style="color: #94a3b8; margin: 0 0 6px 0;">No past rounds specifically logged for {c_name}. Universal high-frequency round questions:</p>
        <ul>
          <li><span class='badge'>Tech Round 1</span> Reverse Linked List in K-Groups & detect cycle.</li>
          <li><span class='badge'>Tech Round 2</span> Design a rate-limiter using Token Bucket or Leaky Bucket.</li>
          <li><span class='badge'>Core CS</span> Explain indexing tradeoffs: B+ Tree vs Hash Index in MySQL/PostgreSQL.</li>
        </ul>
        """

    # Fetch candidate profile & project
    cur.execute("""
        SELECT full_name, projects_json FROM resume_profiles
        ORDER BY id ASC LIMIT 1
    """)
    prof_row = cur.fetchone()
    conn.close()

    candidate_name = prof_row[0] if prof_row and prof_row[0] else "Candidate"
    projects = []
    if prof_row and prof_row[1]:
        try:
            import json
            projects = json.loads(prof_row[1])
        except Exception:
            pass

    if projects:
        top_p = projects[0]
        p_title = top_p.get("title", "Engineering Project")
        p_tech = top_p.get("tech", "")
        p_bullets = top_p.get("bullets", [])
        b_html = "".join([f"<li>{b}</li>" for b in p_bullets[:2]])
        candidate_project_html = f"""
        <div>
          <span class='accent'>{p_title}</span> <span class='badge'>{p_tech}</span>
          <ul>{b_html}</ul>
        </div>
        """
    else:
        candidate_project_html = """
        <div>
          <span class='accent'>JARVIS-lite Autonomous AI Desktop Companion</span>
          <span class='badge'>Python, Ollama, SQLite, Subprocess Sandboxing</span>
          <ul>
            <li>Architected an offline, local neural assistant eliminating cloud API subscription fees with zero-latency response.</li>
            <li>Engineered sandboxed subprocess code runner with 5-second timeout protections and SM-2 spaced repetition memory retention.</li>
          </ul>
        </div>
        """

    safe_name = "".join(c for c in c_name.lower() if c.isalnum() or c == "_")
    out_file = OUTPUT_DIR / (output_filename or f"cheatsheet_{safe_name}.html")

    html_content = CHEAT_SHEET_HTML_TEMPLATE.format(
        company_name=c_name,
        company_name_upper=c_name.upper(),
        candidate_name=candidate_name,
        current_date=datetime.now().strftime("%d %B %Y"),
        company_questions_html=company_questions_html,
        candidate_project_html=candidate_project_html,
    )

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_file)
