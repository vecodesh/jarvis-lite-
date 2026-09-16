"""
JARVIS-lite: Syllabus Processor (Phase 5 - Feature 3a)

Extracts course subjects and hierarchical Unit -> Topic structures from
syllabus documents (PDF or plain text / markdown) and inserts them into
the database using existing get_or_create logic without modifying the schema.

Isolated from the frozen V1 core.
"""

import sys
import json
import sqlite3
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ollama
from pypdf import PdfReader

# Reuse database access and deterministic helpers from frozen assistant core
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from assistant import (
    MODEL,
    DB_PATH,
    get_connection,
    get_or_create_subject,
    insert_topic,
    insert_log,
)

SYLLABUS_SYSTEM_PROMPT = """You are JARVIS-lite Syllabus Parser.
Your job is to parse a university course syllabus document and extract its structured hierarchy:
Subject -> Units -> Topics.

Return ONLY valid JSON.
Do not use markdown blocks or explanations.

Use exactly this JSON structure:
{
  "subject": "Course or Subject Name",
  "units": [
    {
      "unit": "Unit 1: Unit Title or Number",
      "topics": [
        "Topic 1 Name",
        "Topic 2 Name"
      ]
    }
  ]
}

RULES:
1. Identify the overarching course/subject name (e.g. "Operating Systems", "Computer Networks", "Database Management Systems").
2. Group all specific sub-concepts under their respective Unit, Module, or Chapter headings.
3. Keep topic names concise, informative, and title-cased.
4. If the syllabus does not explicitly label units, use "Unit 1: Core Topics" or logical groupings.
5. Do NOT invent concepts that are not present in the input text.
"""


def extract_text_from_file(file_path):
    """
    Extracts raw text from a PDF or plain text/markdown file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".pdf":
        reader = PdfReader(str(path))
        extracted_pages = []
        for index, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text.strip())
        full_text = "\n\n".join(extracted_pages)
        if not full_text.strip():
            raise ValueError(f"Could not extract any readable text from PDF: {file_path}")
        return full_text

    elif extension in (".txt", ".md", ".text", ".rst"):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    else:
        # Attempt plain text read as fallback
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Unsupported file format '{extension}'. Expected PDF (.pdf) or text (.txt, .md): {e}")


def parse_syllabus_with_llm(syllabus_text):
    """
    Sends syllabus text to Ollama to extract structured JSON {subject, units}.
    """
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYLLABUS_SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this syllabus into structured JSON:\n\n{syllabus_text}"},
        ],
        format="json",
    )

    content = response["message"]["content"]
    return json.loads(content)


def process_syllabus(file_path_or_text, is_raw_text=False):
    """
    Main processing entry point:
    1. Extracts text from file (or uses raw text).
    2. Uses Ollama to extract subject and Unit -> Topic hierarchy.
    3. Deterministically inserts/updates subjects and topics using existing logic.
    4. Logs the interaction in the logs table.

    Returns a summary dictionary: {subject, total_units, total_topics, topics_list}.
    """
    if is_raw_text:
        raw_text = file_path_or_text
        source_label = "Raw Text Input"
    else:
        raw_text = extract_text_from_file(file_path_or_text)
        source_label = str(file_path_or_text)

    print(f"\nProcessing syllabus from: {source_label}")
    print("Extracting course structure via Ollama...")

    structured_data = parse_syllabus_with_llm(raw_text)

    subject_name = structured_data.get("subject", "").strip()
    if not subject_name:
        subject_name = "General Syllabus"

    units = structured_data.get("units", [])
    if not units:
        print("Warning: No structured units found in LLM extraction.")

    # 1. Deterministically get or create subject (reusing assistant.get_or_create_subject)
    subject_id = get_or_create_subject(subject_name)

    # 2. Insert topics under Unit -> Topic naming convention
    inserted_topics = []
    for unit_block in units:
        unit_label = unit_block.get("unit", "").strip()
        topics = unit_block.get("topics", [])

        for topic in topics:
            topic_str = str(topic).strip()
            if not topic_str:
                continue

            # Preserve Unit -> Topic hierarchy inside topic_name
            if unit_label and not topic_str.lower().startswith(unit_label.lower()):
                formatted_topic_name = f"{unit_label} - {topic_str}"
            else:
                formatted_topic_name = topic_str

            # Reuses assistant.insert_topic (default status: 'not_started')
            insert_topic(subject_id, formatted_topic_name, status="not_started")
            inserted_topics.append(formatted_topic_name)

    # 3. Log interaction to logs table
    summary_for_log = json.dumps({
        "source": source_label,
        "subject": subject_name,
        "topics_count": len(inserted_topics),
        "data": structured_data,
    })
    insert_log(f"[Syllabus Upload] {source_label}", summary_for_log)

    print(f"\n✓ Successfully imported syllabus for: '{subject_name}'")
    print(f"  • Subject ID: {subject_id}")
    print(f"  • Units parsed: {len(units)}")
    print(f"  • Topics registered: {len(inserted_topics)}")

    return {
        "subject": subject_name,
        "subject_id": subject_id,
        "total_units": len(units),
        "total_topics": len(inserted_topics),
        "topics": inserted_topics,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/syllabus_processor.py <path_to_syllabus_file.pdf|.txt>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        result = process_syllabus(file_path)
        print("\nRegistered Topics:")
        for t in result["topics"]:
            print(f"  - {t}")
    except Exception as e:
        print(f"\nError processing syllabus: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
