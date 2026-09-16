"""
JARVIS-lite: Advanced AI Resume Maker & JD Matcher (Phase 6)

Tony Stark-level AI Resume Studio:
1. Candidate Profile Management (Contact, Education, Experience, Projects).
2. Direct integration with assistant.db: automatically pulls verified 'done' topics into Technical Skills.
3. Google XYZ Formula Bullet Optimizer: Transforms basic project descriptions into high-impact ATS bullet points.
4. Job Description (JD) Matcher: Computes ATS match score, extracts missing skills, and one-click syncs gaps to study tracker.
5. Multi-format Exporter: Clean ATS Markdown & Executive HTML/PDF layout.
"""

import re
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


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_resume_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL DEFAULT 'Candidate Name',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            github TEXT DEFAULT '',
            linkedin TEXT DEFAULT '',
            portfolio TEXT DEFAULT '',
            education_json TEXT DEFAULT '[]',
            experience_json TEXT DEFAULT '[]',
            projects_json TEXT DEFAULT '[]',
            skills_json TEXT DEFAULT '[]',
            updated_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Seed initial default profile if empty
    cur.execute("SELECT COUNT(*) FROM resume_profiles")
    if cur.fetchone()[0] == 0:
        default_edu = json.dumps([{
            "degree": "B.Tech in Computer Science & Engineering",
            "institution": "University / College Name",
            "year": "2022 - 2026",
            "score": "CGPA: 8.8 / 10.0"
        }])
        default_exp = json.dumps([{
            "role": "Software Engineering Intern",
            "company": "Tech Innovations Inc.",
            "duration": "May 2025 - Aug 2025",
            "bullets": [
                "Engineered scalable REST APIs using Python & FastAPI, decreasing response latency by 32%.",
                "Implemented automated CI/CD deployment pipelines on GitHub Actions, reducing release cycles from 2 days to 30 minutes."
            ]
        }])
        default_proj = json.dumps([{
            "title": "JARVIS-lite Autonomous AI Desktop Companion",
            "tech": "Python, Ollama, SQLite, CustomTkinter, STT/TTS",
            "bullets": [
                "Architected an offline, privacy-first AI assistant processing natural language intent with zero external API latency.",
                "Built an automated placement pipeline tracker and real-time background scheduling daemon with desktop toast notifications."
            ]
        }])
        default_skills = json.dumps([
            "Python", "C++", "SQL", "FastAPI", "Data Structures & Algorithms",
            "Database Management Systems", "Operating Systems", "Git & Docker"
        ])
        cur.execute("""
            INSERT INTO resume_profiles (
                full_name, email, phone, github, linkedin, education_json, experience_json, projects_json, skills_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Alex Stark", "alex.stark@example.com", "+91 98765 43210",
            "github.com/alexstark", "linkedin.com/in/alexstark",
            default_edu, default_exp, default_proj, default_skills
        ))
        conn.commit()

    conn.close()


init_resume_tables()


def get_resume_profile():
    """Fetches the primary resume profile."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT full_name, email, phone, github, linkedin, portfolio,
               education_json, experience_json, projects_json, skills_json
        FROM resume_profiles ORDER BY id ASC LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if not row:
        return {}

    return {
        "full_name": row[0],
        "email": row[1],
        "phone": row[2],
        "github": row[3],
        "linkedin": row[4],
        "portfolio": row[5],
        "education": json.loads(row[6] or "[]"),
        "experience": json.loads(row[7] or "[]"),
        "projects": json.loads(row[8] or "[]"),
        "skills": json.loads(row[9] or "[]"),
    }


def save_resume_profile(data: dict):
    """Saves updated resume profile into the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE resume_profiles
        SET full_name = ?, email = ?, phone = ?, github = ?, linkedin = ?, portfolio = ?,
            education_json = ?, experience_json = ?, projects_json = ?, skills_json = ?,
            updated_date = CURRENT_TIMESTAMP
        WHERE id = 1
    """, (
        data.get("full_name", ""),
        data.get("email", ""),
        data.get("phone", ""),
        data.get("github", ""),
        data.get("linkedin", ""),
        data.get("portfolio", ""),
        json.dumps(data.get("education", [])),
        json.dumps(data.get("experience", [])),
        json.dumps(data.get("projects", [])),
        json.dumps(data.get("skills", [])),
    ))
    conn.commit()
    conn.close()


def add_resume_project(title: str, tech: str, bullets: list = None):
    """Appends a new engineering project to the candidate profile."""
    p = get_resume_profile()
    projs = p.get("projects", [])
    projs.append({
        "title": title.strip(),
        "tech": tech.strip(),
        "bullets": bullets or []
    })
    p["projects"] = projs
    save_resume_profile(p)


def delete_resume_project(index: int):
    """Deletes a project by its index."""
    p = get_resume_profile()
    projs = p.get("projects", [])
    if 0 <= index < len(projs):
        projs.pop(index)
        p["projects"] = projs
        save_resume_profile(p)


def append_bullet_to_project(project_index: int, bullet: str):
    """Appends a synthesized bullet point into a target project."""
    p = get_resume_profile()
    projs = p.get("projects", [])
    if 0 <= project_index < len(projs):
        projs[project_index].setdefault("bullets", []).append(bullet.strip())
        p["projects"] = projs
        save_resume_profile(p)


def add_resume_experience(role: str, company: str, duration: str, bullets: list = None):
    """Appends a new professional experience item to the candidate profile."""
    p = get_resume_profile()
    exps = p.get("experience", [])
    exps.append({
        "role": role.strip(),
        "company": company.strip(),
        "duration": duration.strip(),
        "bullets": bullets or []
    })
    p["experience"] = exps
    save_resume_profile(p)


def delete_resume_experience(index: int):
    """Deletes an experience entry by its index."""
    p = get_resume_profile()
    exps = p.get("experience", [])
    if 0 <= index < len(exps):
        exps.pop(index)
        p["experience"] = exps
        save_resume_profile(p)


def append_bullet_to_experience(exp_index: int, bullet: str):
    """Appends a synthesized bullet point into an experience item."""
    p = get_resume_profile()
    exps = p.get("experience", [])
    if 0 <= exp_index < len(exps):
        exps[exp_index].setdefault("bullets", []).append(bullet.strip())
        p["experience"] = exps
        save_resume_profile(p)


def get_project_summaries() -> list[dict]:
    """Returns a list of dicts with index and title for all projects in profile."""
    p = get_resume_profile()
    return [{"index": i, "title": proj.get("title", f"Project #{i+1}")} for i, proj in enumerate(p.get("projects", []))]



def sync_skills_from_database():
    """
    Pulls topics marked as 'done' from the topics table
    and merges them into the candidate's skills profile.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT topic_name FROM topics WHERE status = 'done'")
    done_topics = [r[0].strip() for r in cur.fetchall() if r[0] and r[0].strip()]
    conn.close()

    profile = get_resume_profile()
    existing_skills = profile.get("skills", [])
    added = []

    for t in done_topics:
        if t.lower() not in [s.lower() for s in existing_skills]:
            existing_skills.append(t)
            added.append(t)

    if added:
        profile["skills"] = existing_skills
        save_resume_profile(profile)

    return added, existing_skills


# --------------------------------------------------
# Google XYZ Formula AI Bullet Point Synthesizer
# --------------------------------------------------

XYZ_PROMPT = """You are JARVIS, an elite executive tech recruiter and resume optimizer.

TASK:
Rewrite the following raw project or experience description into 1 to 2 ultra-high-impact engineering bullet points.

Apply the Google XYZ Formula:
"Accomplished [X] as measured by [Y], by doing [Z]"

GUIDELINES:
- Start with a powerful action verb (e.g. Engineered, Architected, Optimized, Spearheaded, Reduced, Automated).
- Quantify impact with realistic metrics, latencies, percentages, or scale.
- Highlight modern tools, algorithms, or architecture.
- Keep bullets concise (18-28 words per bullet).
- Return ONLY the bullet points, each starting with "• ". Do not include explanations or markdown fences.

RAW INPUT:
{raw_input}
"""


def optimize_bullet_points(raw_input: str) -> list:
    """Takes user description and returns optimized Google XYZ bullet points."""
    if not raw_input.strip():
        return []

    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": XYZ_PROMPT.format(raw_input=raw_input)}],
            options={"temperature": 0.4}
        )
        content = resp["message"]["content"].strip()
        lines = [line.strip().lstrip("•-* ").strip() for line in content.split("\n") if line.strip()]
        return lines if lines else [raw_input.strip()]
    except Exception as e:
        return [f"{raw_input} (AI optimization note: {e})"]


# --------------------------------------------------
# Job Description (JD) Skill Matcher & Gap Analyzer
# --------------------------------------------------

JD_PROMPT = """You are JARVIS, an ATS screening engine and technical career advisor.

CANDIDATE SKILLS:
{skills_json}

CANDIDATE PROJECTS:
{projects_json}

TARGET JOB DESCRIPTION:
{job_description}

TASK:
Analyze the alignment between the candidate profile and the target job description.
Return ONLY a valid JSON object matching this exact schema:
{{
  "match_score": <integer from 0 to 100>,
  "matching_skills": ["skill1", "skill2", ...],
  "missing_skills": ["critical_skill1", "critical_skill2", ...],
  "recommendations": "<2-3 sentence strategic advice to tailor this resume for the role>"
}}

RULES:
- Evaluate technical hard skills (languages, frameworks, concepts, databases, cloud).
- Be realistic and rigorous with the match score.
- Output ONLY valid JSON.
"""


def analyze_job_description(jd_text: str) -> dict:
    """Matches resume profile against a target JD."""
    profile = get_resume_profile()
    skills_json = json.dumps(profile.get("skills", []))
    projects_json = json.dumps([p.get("title") + " " + p.get("tech", "") for p in profile.get("projects", [])])

    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": JD_PROMPT.format(
                    skills_json=skills_json,
                    projects_json=projects_json,
                    job_description=jd_text.strip()
                )
            }],
            format="json",
            options={"temperature": 0.2}
        )
        data = json.loads(resp["message"]["content"])
        data["match_score"] = max(0, min(100, int(data.get("match_score", 60))))
        return data
    except Exception as e:
        return {
            "match_score": 50,
            "matching_skills": ["Python", "SQL"],
            "missing_skills": ["See JD Details"],
            "recommendations": f"Analysis encountered error: {e}"
        }


def add_missing_skills_to_study(skills_list: list) -> int:
    """
    One-click sync: Automatically injects missing JD skills into
    assistant.db as pending topics under a 'Placement Preparation' subject.
    """
    from assistant import get_or_create_subject, insert_topic
    subject_id = get_or_create_subject("Placement Preparation")
    added_count = 0
    for skill in skills_list:
        clean = skill.strip()
        if clean:
            insert_topic(subject_id, clean, "not_started")
            added_count += 1
    return added_count


# --------------------------------------------------
# Exporters: Markdown & Executive HTML/PDF
# --------------------------------------------------

def export_resume_markdown() -> str:
    """Exports profile to clean ATS Markdown format."""
    p = get_resume_profile()
    md = []
    md.append(f"# {p.get('full_name', 'Candidate Name')}")
    contacts = [c for c in [p.get('email'), p.get('phone'), p.get('github'), p.get('linkedin')] if c]
    md.append(" | ".join(contacts))
    md.append("\n---\n")

    # Education
    if p.get("education"):
        md.append("## EDUCATION\n")
        for edu in p["education"]:
            md.append(f"**{edu.get('degree', '')}** — *{edu.get('institution', '')}*  ")
            md.append(f"{edu.get('year', '')} | {edu.get('score', '')}\n")

    # Skills
    if p.get("skills"):
        md.append("## TECHNICAL SKILLS\n")
        md.append(", ".join(p["skills"]) + "\n")

    # Experience
    if p.get("experience"):
        md.append("## EXPERIENCE\n")
        for exp in p["experience"]:
            md.append(f"**{exp.get('role', '')}** | *{exp.get('company', '')}* ({exp.get('duration', '')})")
            for b in exp.get("bullets", []):
                md.append(f"- {b}")
            md.append("")

    # Projects
    if p.get("projects"):
        md.append("## KEY PROJECTS\n")
        for proj in p["projects"]:
            md.append(f"**{proj.get('title', '')}** [{proj.get('tech', '')}]")
            for b in proj.get("bullets", []):
                md.append(f"- {b}")
            md.append("")

    return "\n".join(md)


def tailor_resume_for_application(company: str, role: str, notes: str = "") -> dict:
    """
    1-Click AI Tailoring: Customizes resume project and experience bullets
    specifically to emphasize competencies valued by the target company.
    """
    profile = get_resume_profile()
    prompt = f"""You are JARVIS, an elite executive resume consultant.

TARGET COMPANY: {company}
ROLE: {role}
JOB NOTES / CONTEXT: {notes or 'Software Engineering role focusing on backend, algorithms, and system design.'}

CANDIDATE PROJECTS:
{json.dumps(profile.get('projects', []))}

CANDIDATE EXPERIENCE:
{json.dumps(profile.get('experience', []))}

TASK:
Optimize the bullet points of the candidate's projects and experience to maximally resonate with {company}'s engineering culture and role requirements ({role}).
Keep facts truthful; highlight relevant tech, scalability, metrics, and architecture.
Return ONLY valid JSON matching this schema:
{{
  "projects": [
    {{"title": "...", "tech": "...", "bullets": ["...", "..."]}}
  ],
  "experience": [
    {{"role": "...", "company": "...", "duration": "...", "bullets": ["...", "..."]}}
  ]
}}
"""
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.3}
        )
        tailored_data = json.loads(resp["message"]["content"])
        tailored_profile = dict(profile)
        if "projects" in tailored_data and tailored_data["projects"]:
            tailored_profile["projects"] = tailored_data["projects"]
        if "experience" in tailored_data and tailored_data["experience"]:
            tailored_profile["experience"] = tailored_data["experience"]
        return tailored_profile
    except Exception as e:
        print(f"[Tailor Error] {e}")
        return profile


def export_resume_html(output_file: str = "resume.html", template: str = "stark", custom_profile: dict = None) -> str:
    """
    Exports profile to an executive, modern, printable HTML resume.
    Templates supported:
      - 'stark': Executive modern layout with cyan accents.
      - 'harvard': Traditional monochrome serif ATS standard.
      - 'modern': Contemporary clean tech layout.
    """
    p = custom_profile or get_resume_profile()
    out_path = BASE_DIR / output_file

    edu_html = "".join([f"""
        <div class="item">
            <div class="item-header">
                <span class="bold">{e.get('degree')}</span>
                <span class="muted">{e.get('year')}</span>
            </div>
            <div class="item-sub">
                <span>{e.get('institution')}</span>
                <span class="muted">{e.get('score')}</span>
            </div>
        </div>
    """ for e in p.get("education", [])])

    skills_html = f"<p class='skills-line'>{', '.join(p.get('skills', []))}</p>"

    exp_html = "".join([f"""
        <div class="item">
            <div class="item-header">
                <span class="bold">{e.get('role')}</span>
                <span class="muted">{e.get('duration')}</span>
            </div>
            <div class="item-sub bold text-accent">{e.get('company')}</div>
            <ul class="bullets">
                {''.join([f'<li>{b}</li>' for b in e.get('bullets', [])])}
            </ul>
        </div>
    """ for e in p.get("experience", [])])

    proj_html = "".join([f"""
        <div class="item">
            <div class="item-header">
                <span class="bold">{pr.get('title')}</span>
                <span class="muted tech-stack">{pr.get('tech')}</span>
            </div>
            <ul class="bullets">
                {''.join([f'<li>{b}</li>' for b in pr.get('bullets', [])])}
            </ul>
        </div>
    """ for pr in p.get("projects", [])])

    # Template Styles
    if template == "harvard":
        font_family = "Georgia, 'Times New Roman', serif"
        accent_color = "#000000"
        border_style = "1px solid #000000"
        header_align = "center"
        name_transform = "uppercase"
    elif template == "modern":
        font_family = "'Inter', system-ui, sans-serif"
        accent_color = "#0284c7"
        border_style = "2px solid #0284c7"
        header_align = "left"
        name_transform = "none"
    else:  # stark executive
        font_family = "'Segoe UI', -apple-system, Roboto, sans-serif"
        accent_color = "#0284c7"
        border_style = "2px solid #0284c7"
        header_align = "center"
        name_transform = "uppercase"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{p.get('full_name')} - Resume ({template.title()} Edition)</title>
<style>
    @page {{ size: A4; margin: 16mm; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: {font_family};
        color: #1e293b;
        background: #ffffff;
        line-height: 1.45;
        font-size: 10.5pt;
        padding: 24px;
        max-width: 850px;
        margin: 0 auto;
    }}
    .header {{ text-align: {header_align}; border-bottom: {border_style}; padding-bottom: 10px; margin-bottom: 14px; }}
    .name {{ font-size: 20pt; font-weight: 700; letter-spacing: -0.5px; color: #0f172a; text-transform: {name_transform}; }}
    .contacts {{ font-size: 9.5pt; color: #64748b; margin-top: 5px; }}
    .contacts a {{ color: {accent_color}; text-decoration: none; }}
    .section-title {{
        font-size: 11pt;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: {accent_color};
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 2px;
        margin-top: 14px;
        margin-bottom: 8px;
    }}
    .item {{ margin-bottom: 10px; }}
    .item-header {{ display: flex; justify-content: space-between; font-size: 10.5pt; }}
    .item-sub {{ display: flex; justify-content: space-between; font-size: 9.5pt; color: #475569; }}
    .bold {{ font-weight: 600; color: #0f172a; }}
    .muted {{ color: #64748b; }}
    .text-accent {{ color: {accent_color}; }}
    .tech-stack {{ font-style: italic; font-size: 9pt; }}
    .bullets {{ margin-left: 18px; margin-top: 4px; }}
    .bullets li {{ margin-bottom: 3px; font-size: 9.5pt; }}
    .skills-line {{ font-size: 9.5pt; line-height: 1.6; color: #334155; }}
    @media print {{
        body {{ padding: 0; max-width: 100%; }}
        .header {{ border-bottom: 2px solid #000; }}
        .section-title {{ color: #000; border-bottom: 1px solid #666; }}
    }}
</style>
</head>
<body>
    <div class="header">
        <h1 class="name">{p.get('full_name')}</h1>
        <div class="contacts">
            <span>{p.get('email')}</span> &bull;
            <span>{p.get('phone')}</span> &bull;
            <span>{p.get('github')}</span> &bull;
            <span>{p.get('linkedin')}</span>
        </div>
    </div>

    <div class="section-title">Technical Skills</div>
    {skills_html}

    <div class="section-title">Key Engineering Projects</div>
    {proj_html}

    <div class="section-title">Professional Experience</div>
    {exp_html}

    <div class="section-title">Education</div>
    {edu_html}
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_path)
