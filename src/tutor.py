"""
JARVIS-lite: Placement Technical Tutor & Concept Explainer (Phase 6)

Provides concise, high-impact explanations for technical placement topics:
- Data Structures & Algorithms (DSA)
- Database Management Systems (DBMS)
- Operating Systems (OS)
- Computer Networks (CN)
- System Design & Software Engineering

Maintains Tony Stark's calm, authoritative, and direct persona.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ollama

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL = "llama3.1:8b"

TUTOR_SYSTEM_PROMPT = """You are JARVIS, an elite AI technical mentor helping a student ace top-tier software engineering and campus placement interviews.

PERSONA & TONE:
- Calm, authoritative, razor-sharp, and direct.
- Low on fluff, zero conversational filler (no "Sure, I'd love to help!", no "Great question!").
- Speak with the precision of Tony Stark's AI: clear, structured, and technically impeccable.
- Format responses cleanly for readability in an IDE console.

ANSWER STRUCTURE:
1. CORE INTUITION: A crisp 1-2 sentence definition that interviewers love.
2. KEY MECHANICS / TRADE-OFFS: 2-3 bullet points breaking down how it works or comparing trade-offs.
3. COMPLEXITY / GOTCHAS: State Time/Space complexity or key edge cases if applicable.
4. CODE SNIPPET (if relevant): A brief, elegant Python or pseudo-code snippet.

Keep total length focused and punchy (around 100-180 words). Get straight to the essence.
"""


def answer_placement_question(question: str) -> str:
    """
    Answers a technical placement or conceptual question using Ollama.
    """
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": TUTOR_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": question.strip(),
                }
            ],
            options={
                "temperature": 0.3,  # Deterministic, precise technical answers
            }
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return f"Unable to retrieve technical explanation from Ollama: {e}"


if __name__ == "__main__":
    sample = "What is the difference between TCP and UDP?"
    print(f"Q: {sample}\n")
    print(answer_placement_question(sample))
