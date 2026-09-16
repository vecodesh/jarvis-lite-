"""
JARVIS-lite: Desktop GUI Dashboard (Phase 7 Refined - Complete Engineering Console)

Refined features:
1. Live Python Code Execution ("▶️ Run Code") + AI Big-O & Bug Reviewer in Coding Arena.
2. Visual Project & Experience Manager + Google XYZ Bullet Injector in AI Resume Studio.
3. Real-Time Company Search & Filter in Placements Kanban + Offer Received celebration.
4. Spaced Repetition Flashcard Progress Tracker + Custom Card Creator.
5. Subject Mastery Completion % Badges ([X/Y Done — Z%]) + Direct Topic Creator in Study Tracker.
6. Windows SAPI5 Voice Selector (British Hazel / US Zira), Chat Clear, and Log Exporter in Console.
7. Real-Time Hardware Telemetry (CPU %, RAM %, Battery) in top HUD bar.
"""

import sys
import math
import json
import time
import threading
import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import customtkinter as ctk

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from assistant import DB_PATH, get_connection, process_input, get_or_create_subject, insert_topic
from reminder_service import (
    get_stale_topics,
    get_stale_tasks,
    days_old,
    add_reminder,
    get_active_reminders,
    dismiss_reminder,
    parse_natural_time,
    register_reminder_callback,
    send_windows_toast,
)
from syllabus_processor import process_syllabus
from placements import (
    add_application,
    update_application_stage,
    get_applications,
    delete_application,
    get_placement_summary,
    get_kanban_data,
    promote_application,
    demote_application,
    add_company_question,
    get_company_questions,
    delete_company_question,
    VALID_STAGES,
    VALID_RESULTS,
)
from interview_engine import (
    get_available_topics,
    generate_interview_question,
    evaluate_interview_answer,
    save_interview_result,
    get_interview_history,
    run_hands_free_interview_question,
)
from resume_builder import (
    get_resume_profile,
    save_resume_profile,
    sync_skills_from_database,
    optimize_bullet_points,
    analyze_job_description,
    add_missing_skills_to_study,
    export_resume_html,
    tailor_resume_for_application,
    add_resume_project,
    delete_resume_project,
    append_bullet_to_project,
    add_resume_experience,
    delete_resume_experience,
    append_bullet_to_experience,
    get_project_summaries,
)
from briefing import generate_morning_briefing, get_readiness_metrics, get_study_streak
from system_control import get_system_telemetry, execute_system_command
from coding_arena import get_curated_problems, generate_custom_problem, review_candidate_code, run_python_code
from spaced_repetition import get_due_flashcards, record_flashcard_review, add_custom_flashcard
from data_backup import export_database_to_json, export_applications_to_csv, export_study_topics_to_csv
from battle_plan import generate_daily_battle_plan, toggle_target_done, generate_evening_debrief
from aptitude_arena import get_curated_quiz, generate_ai_quiz, record_drill_result, get_aptitude_stats
from focus_timer import get_focus_engine, get_today_focus_hours
from cheat_sheet import generate_company_cheat_sheet
from dsa_sheet import (
    get_dsa_topics,
    get_dsa_problems,
    get_problem_by_id,
    update_problem_status,
    record_voice_dry_run,
    get_problem_notes,
    get_quick_revision_speech,
    launch_excalidraw,
    launch_problem_url,
    launch_video_url,
    get_dsa_stats,
)


try:
    from personality import proactive_launch_greeting, get_confirmation_message
except ImportError:
    proactive_launch_greeting = lambda **k: "Good day. Ready to assist."
    get_confirmation_message = lambda d: "Updated your memory."

try:
    from voice import (
        speak,
        listen_to_microphone,
        play_chime,
        listen_for_wake_word,
        get_available_voices,
        set_voice_preference,
        TTS_AVAILABLE,
        STT_AVAILABLE,
    )
except ImportError:
    TTS_AVAILABLE = False
    STT_AVAILABLE = False
    speak = lambda *args, **kwargs: None
    listen_to_microphone = lambda *args, **kwargs: (None, "Voice module not available")
    play_chime = lambda: None
    listen_for_wake_word = lambda *args, **kwargs: None
    get_available_voices = lambda: []
    set_voice_preference = lambda v: None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class JarvisGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("JARVIS-lite // Neural Engineering & Career Console")
        self.geometry("1260x800")
        self.minsize(1040, 700)
        self.configure(fg_color="#080c14")

        self.tts_enabled = tk.BooleanVar(value=True)
        self.wake_enabled = tk.BooleanVar(value=False)
        self.wake_stop_event = None

        # Waveform animation state
        self._anim_angle = 0
        self._anim_mode = "idle"

        # Flashcards state
        self.flashcards = []
        self.current_flashcard_idx = 0
        self.flashcard_revealed = False

        # Aptitude drill state
        self.current_aptitude_quiz = []
        self.current_quiz_idx = 0
        self.current_quiz_score = 0
        self.quiz_timer_seconds = 60
        self.quiz_timer_running = False

        # Striver Sheet state
        self.selected_dsa_problem_id = None

        # Register reminder background callback for live HUD alert
        register_reminder_callback(self._on_reminder_fired_event)

        # Register Focus Engine callback
        self.focus_engine = get_focus_engine()
        self.focus_engine.register_callback(self._on_focus_timer_tick)

        # Global hotkey
        self.bind("<Control-space>", lambda e: self._on_voice_input())

        self._configure_styles()
        self._build_top_hud()
        self._build_tabview()
        self.refresh_all_data()

        # Start HUD Arc Reactor animation & hardware telemetry loop
        self._start_hud_animation()
        self._start_telemetry_loop()

        # Proactive initial greeting
        self.after(600, self._initial_greeting)

    def _configure_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(
            "Treeview",
            background="#0e1422",
            foreground="#e2e8f0",
            fieldbackground="#0e1422",
            rowheight=26,
            font=("Segoe UI", 9),
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#1e293b",
            foreground="#38bdf8",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        self.style.map("Treeview", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

    # --------------------------------------------------
    # Top HUD Bar with Live CPU/RAM & Career Telemetry
    # --------------------------------------------------
    def _build_top_hud(self):
        top_bar = ctk.CTkFrame(self, height=52, fg_color="#0a0e17", corner_radius=0, border_width=1, border_color="#1e293b")
        top_bar.pack(side=tk.TOP, fill=tk.X)

        brand_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        brand_frame.pack(side=tk.LEFT, padx=14, pady=6)

        ctk.CTkLabel(brand_frame, text="⚡", font=("Segoe UI", 16, "bold"), text_color="#00d2ff").pack(side=tk.LEFT, padx=(0, 6))
        ctk.CTkLabel(brand_frame, text="JARVIS-LITE", font=("Consolas", 14, "bold"), text_color="#ffffff").pack(side=tk.LEFT)
        ctk.CTkLabel(brand_frame, text=" // HUD", font=("Consolas", 10), text_color="#00d2ff").pack(side=tk.LEFT, padx=(4, 0))

        # Center: Telemetry Badges
        telemetry_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        telemetry_frame.pack(side=tk.LEFT, expand=True, padx=10)

        # Hardware CPU & RAM
        self.cpu_badge = ctk.CTkLabel(
            telemetry_frame,
            text="CPU: --%",
            font=("Consolas", 9, "bold"),
            fg_color="#1e293b",
            text_color="#38bdf8",
            corner_radius=6,
            padx=8,
            pady=3,
        )
        self.cpu_badge.pack(side=tk.LEFT, padx=4)

        self.ram_badge = ctk.CTkLabel(
            telemetry_frame,
            text="RAM: --%",
            font=("Consolas", 9, "bold"),
            fg_color="#1e293b",
            text_color="#00d2ff",
            corner_radius=6,
            padx=8,
            pady=3,
        )
        self.ram_badge.pack(side=tk.LEFT, padx=4)

        # Career Metrics
        self.streak_badge = ctk.CTkLabel(
            telemetry_frame,
            text="🔥 --d",
            font=("Segoe UI", 10, "bold"),
            fg_color="#1e293b",
            text_color="#f59e0b",
            corner_radius=6,
            padx=8,
            pady=3,
        )
        self.streak_badge.pack(side=tk.LEFT, padx=4)

        self.readiness_badge = ctk.CTkLabel(
            telemetry_frame,
            text="🎯 --%",
            font=("Segoe UI", 10, "bold"),
            fg_color="#1e293b",
            text_color="#10b981",
            corner_radius=6,
            padx=8,
            pady=3,
        )
        self.readiness_badge.pack(side=tk.LEFT, padx=4)

        self.alarm_badge = ctk.CTkLabel(
            telemetry_frame,
            text="⏰ --",
            font=("Segoe UI", 10, "bold"),
            fg_color="#1e293b",
            text_color="#a855f7",
            corner_radius=6,
            padx=8,
            pady=3,
        )
        self.alarm_badge.pack(side=tk.LEFT, padx=4)

        self.focus_btn = ctk.CTkButton(
            telemetry_frame,
            text="⏱️ 25:00 [Focus]",
            command=self._on_toggle_focus_timer,
            font=("Consolas", 9, "bold"),
            fg_color="#1e293b",
            hover_color="#0284c7",
            text_color="#f59e0b",
            corner_radius=6,
            height=26,
            width=120,
            cursor="hand2",
        )
        self.focus_btn.pack(side=tk.LEFT, padx=4)

        # Right Actions
        btn_container = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_container.pack(side=tk.RIGHT, padx=14, pady=6)

        self.battle_btn = ctk.CTkButton(
            btn_container,
            text="⚔️ Battle Plan",
            command=self._on_open_battle_plan_modal,
            fg_color="#7c2d12",
            hover_color="#9a3412",
            text_color="#ffffff",
            font=("Segoe UI", 10, "bold"),
            corner_radius=6,
            height=30,
            cursor="hand2",
        )
        self.battle_btn.pack(side=tk.LEFT, padx=3)

        backup_btn = ctk.CTkButton(
            btn_container,
            text="💾 Backup",
            command=self._on_backup_data,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=("Segoe UI", 9),
            corner_radius=6,
            height=30,
            width=65,
            cursor="hand2",
        )
        backup_btn.pack(side=tk.LEFT, padx=3)

        self.briefing_btn = ctk.CTkButton(
            btn_container,
            text="⚡ Briefing",
            command=self._on_trigger_briefing,
            fg_color="#0f766e",
            hover_color="#115e59",
            text_color="#ffffff",
            font=("Segoe UI", 10, "bold"),
            corner_radius=6,
            height=30,
            cursor="hand2",
        )
        self.briefing_btn.pack(side=tk.LEFT, padx=3)

        refresh_btn = ctk.CTkButton(
            btn_container,
            text="🔄",
            command=self.refresh_all_data,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            font=("Segoe UI", 10),
            corner_radius=6,
            height=30,
            width=40,
            cursor="hand2",
        )
        refresh_btn.pack(side=tk.LEFT, padx=3)

    # --------------------------------------------------
    # Master Tabview
    # --------------------------------------------------
    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#0b0f19",
            segmented_button_fg_color="#0e1422",
            segmented_button_selected_color="#0284c7",
            segmented_button_selected_hover_color="#0369a1",
            segmented_button_unselected_hover_color="#1e293b",
            text_color="#cbd5e1",
            corner_radius=8,
        )
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 8))

        self.tab_console = self.tabview.add("💬 Console")
        self.tab_coding = self.tabview.add("💻 Coding Arena")
        self.tab_dsa = self.tabview.add("🗺️ Striver Sheet")
        self.tab_aptitude = self.tabview.add("🧮 Aptitude Arena")
        self.tab_mock = self.tabview.add("🎯 Mock Interview")
        self.tab_flashcards = self.tabview.add("⚡ Flashcards")
        self.tab_resume = self.tabview.add("📄 AI Resume")
        self.tab_kanban = self.tabview.add("💼 Placements Kanban")
        self.tab_study = self.tabview.add("📚 Study Tracker")
        self.tab_reminders = self.tabview.add("⏰ Alarms")

        self._build_tab_console()
        self._build_tab_coding()
        self._build_tab_dsa()
        self._build_tab_aptitude()
        self._build_tab_mock()
        self._build_tab_flashcards()
        self._build_tab_resume()
        self._build_tab_kanban()
        self._build_tab_study()
        self._build_tab_reminders()

    # --------------------------------------------------
    # TAB 1: Neural Console & Voice HUD
    # --------------------------------------------------
    def _build_tab_console(self):
        parent = self.tab_console

        hud_canvas_frame = ctk.CTkFrame(parent, fg_color="#080c14", height=82, corner_radius=6, border_width=1, border_color="#1e293b")
        hud_canvas_frame.pack(fill=tk.X, padx=6, pady=(2, 4))
        hud_canvas_frame.pack_propagate(False)

        self.hud_canvas = tk.Canvas(hud_canvas_frame, bg="#080c14", highlightthickness=0, height=78)
        self.hud_canvas.pack(fill=tk.BOTH, expand=True)

        chips_frame = ctk.CTkFrame(parent, fg_color="transparent")
        chips_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        quick_prompts = [
            ("Open LeetCode", "open leetcode"),
            ("Hardware Status", "system status"),
            ("TCP vs UDP", "What is the difference between TCP and UDP?"),
            ("Explain Indexing", "Explain how indexing works in DBMS and its trade-offs"),
            ("Today's Briefing", "Good morning JARVIS"),
            ("Take Screenshot", "take screenshot"),
        ]
        for label, full_text in quick_prompts:
            btn = ctk.CTkButton(
                chips_frame,
                text=label,
                command=lambda t=full_text: self._send_quick_prompt(t),
                fg_color="#1e293b",
                hover_color="#0284c7",
                text_color="#94a3b8",
                font=("Segoe UI", 9),
                corner_radius=12,
                height=22,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Voice Selector & Chat Controls
        ctrl_strip = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl_strip.pack(fill=tk.X, padx=6, pady=(0, 2))

        ctk.CTkLabel(ctrl_strip, text="TTS Voice:", font=("Segoe UI", 8), text_color="#64748b").pack(side=tk.LEFT, padx=(4, 2))

        voices = get_available_voices()
        voice_names = [v["name"] for v in voices] if voices else ["Default System Voice"]
        self.voice_picker = ctk.CTkOptionMenu(
            ctrl_strip,
            values=voice_names,
            command=self._on_change_tts_voice,
            fg_color="#0e1422",
            button_color="#1e293b",
            font=("Segoe UI", 8),
            width=190,
            height=20,
        )
        self.voice_picker.pack(side=tk.LEFT, padx=2)
        if voices:
            # Prefer British Hazel if available
            for idx, v in enumerate(voices):
                if "hazel" in v["name"].lower() or "great britain" in v["name"].lower():
                    self.voice_picker.set(v["name"])
                    set_voice_preference(v["id"])
                    break

        clear_chat_btn = ctk.CTkButton(
            ctrl_strip,
            text="🗑️ Clear",
            command=self._on_clear_chat,
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#64748b",
            font=("Segoe UI", 8),
            height=20,
            width=50,
        )
        clear_chat_btn.pack(side=tk.RIGHT, padx=2)

        save_log_btn = ctk.CTkButton(
            ctrl_strip,
            text="💾 Save Log",
            command=self._on_save_chat_log,
            fg_color="transparent",
            hover_color="#1e293b",
            text_color="#64748b",
            font=("Segoe UI", 8),
            height=20,
            width=65,
        )
        save_log_btn.pack(side=tk.RIGHT, padx=2)

        self.chat_history = scrolledtext.ScrolledText(
            parent,
            height=13,
            font=("Consolas", 9),
            bg="#080c14",
            fg="#cbd5e1",
            insertbackground="#00d2ff",
            wrap="word",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        self.chat_history.tag_configure("jarvis", foreground="#00d2ff", font=("Consolas", 9, "bold"))
        self.chat_history.tag_configure("user", foreground="#ffffff", font=("Consolas", 9, "bold"))
        self.chat_history.tag_configure("system", foreground="#fbbf24", font=("Consolas", 9, "italic"))
        self.chat_history.tag_configure("body", foreground="#cbd5e1", font=("Consolas", 9))

        input_row = ctk.CTkFrame(parent, fg_color="transparent")
        input_row.pack(fill=tk.X, padx=6, pady=(0, 4))

        self.user_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Ask technical questions, give voice commands, schedule reminders, or log progress...",
            font=("Segoe UI", 10),
            fg_color="#0e1422",
            border_color="#1e293b",
            text_color="#f8fafc",
            corner_radius=6,
            height=32,
        )
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.user_entry.bind("<Return>", lambda e: self._on_send_chat())

        self.voice_btn = ctk.CTkButton(
            input_row,
            text="🎤 Mic (Ctrl+Space)",
            command=self._on_voice_input,
            fg_color="#0891b2",
            hover_color="#0e7490",
            text_color="#ffffff",
            font=("Segoe UI", 10, "bold"),
            corner_radius=6,
            width=135,
            height=32,
            cursor="hand2",
        )
        self.voice_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self.send_btn = ctk.CTkButton(
            input_row,
            text="Send",
            command=self._on_send_chat,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            font=("Segoe UI", 10, "bold"),
            corner_radius=6,
            width=65,
            height=32,
            cursor="hand2",
        )
        self.send_btn.pack(side=tk.RIGHT)

        status_row = ctk.CTkFrame(parent, fg_color="transparent")
        status_row.pack(fill=tk.X, padx=6, pady=(2, 4))

        self.status_lbl = ctk.CTkLabel(status_row, text="● Systems Nominal", font=("Consolas", 9), text_color="#38bdf8")
        self.status_lbl.pack(side=tk.LEFT)

        self.wake_switch = ctk.CTkSwitch(
            status_row,
            text="Wake Word ('Hey Jarvis')",
            variable=self.wake_enabled,
            command=self._on_toggle_wake_word,
            font=("Segoe UI", 9),
            progress_color="#00d2ff",
        )
        self.wake_switch.pack(side=tk.RIGHT, padx=(10, 0))

        self.tts_switch = ctk.CTkSwitch(
            status_row,
            text="Voice replies",
            variable=self.tts_enabled,
            font=("Segoe UI", 9),
            progress_color="#00d2ff",
        )
        self.tts_switch.pack(side=tk.RIGHT)

    def _on_change_tts_voice(self, choice_name):
        voices = get_available_voices()
        for v in voices:
            if v["name"] == choice_name:
                set_voice_preference(v["id"])
                break

    def _on_clear_chat(self):
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.delete("1.0", tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _on_save_chat_log(self):
        content = self.chat_history.get("1.0", tk.END).strip()
        if not content:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = BASE_DIR / f"chat_log_{timestamp}.txt"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Log Saved", f"Conversation exported to:\n{log_file.name}")

    # --------------------------------------------------
    # TAB 2: Live DSA Coding Arena & Reviewer
    # --------------------------------------------------
    def _build_tab_coding(self):
        parent = self.tab_coding

        top_ctrl = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        top_ctrl.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(top_ctrl, text="Problem:", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT, padx=8, pady=6)

        self.curated_problems = get_curated_problems()
        prob_titles = [p["title"] for p in self.curated_problems]
        self.prob_selector = ctk.CTkOptionMenu(
            top_ctrl,
            values=prob_titles,
            command=self._on_select_problem,
            fg_color="#1e293b",
            button_color="#0284c7",
            width=200,
            height=28,
        )
        self.prob_selector.pack(side=tk.LEFT, padx=4)

        self.lang_selector = ctk.CTkOptionMenu(
            top_ctrl,
            values=["Python", "C++"],
            command=self._on_change_coding_lang,
            fg_color="#1e293b",
            button_color="#0f766e",
            width=90,
            height=28,
        )
        self.lang_selector.pack(side=tk.LEFT, padx=4)

        gen_prob_btn = ctk.CTkButton(
            top_ctrl,
            text="🎲 AI Problem",
            command=self._on_ai_gen_problem,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=("Segoe UI", 9),
            height=28,
            width=90,
            cursor="hand2",
        )
        gen_prob_btn.pack(side=tk.LEFT, padx=4)

        self.run_code_btn = ctk.CTkButton(
            top_ctrl,
            text="▶️ Run Code",
            command=self._on_run_python_code,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#022c22",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=100,
            cursor="hand2",
        )
        self.run_code_btn.pack(side=tk.RIGHT, padx=6)

        reset_btn = ctk.CTkButton(
            top_ctrl,
            text="↺ Reset",
            command=self._on_reset_problem_code,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=("Segoe UI", 9),
            height=28,
            width=70,
            cursor="hand2",
        )
        reset_btn.pack(side=tk.RIGHT, padx=4)

        self.review_btn = ctk.CTkButton(
            top_ctrl,
            text="⚡ AI Review",
            command=self._on_run_code_review,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=100,
            cursor="hand2",
        )
        self.review_btn.pack(side=tk.RIGHT, padx=4)

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left: Problem Description & Test Harness
        left_box = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(left_box, weight=1)

        self.prob_title_lbl = ctk.CTkLabel(left_box, text="Two Sum (Easy)", font=("Consolas", 11, "bold"), text_color="#00d2ff")
        self.prob_title_lbl.pack(anchor="w", padx=10, pady=(8, 2))

        self.prob_desc_text = scrolledtext.ScrolledText(
            left_box,
            height=5,
            font=("Segoe UI", 9),
            bg="#080c14",
            fg="#e2e8f0",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
        )
        self.prob_desc_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # Right: Candidate Code Editor
        right_box = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(right_box, weight=1)

        ctk.CTkLabel(right_box, text="CODE EDITOR (Python / C++):", font=("Consolas", 10, "bold"), text_color="#38bdf8").pack(anchor="w", padx=10, pady=(8, 2))

        self.code_editor = scrolledtext.ScrolledText(
            right_box,
            height=10,
            font=("Consolas", 10),
            bg="#080c14",
            fg="#e2e8f0",
            insertbackground="#00d2ff",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
        )
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.code_editor.bind("<Tab>", self._on_editor_tab)

        # Bottom: Execution Output Terminal & AI Review
        rev_box = ctk.CTkFrame(parent, fg_color="#0e1422", height=130, corner_radius=6, border_width=1, border_color="#1e293b")
        rev_box.pack(fill=tk.X, padx=6, pady=(0, 4))
        rev_box.pack_propagate(False)

        rev_hdr = ctk.CTkFrame(rev_box, fg_color="transparent")
        rev_hdr.pack(fill=tk.X, padx=10, pady=4)

        ctk.CTkLabel(rev_hdr, text="EXECUTION OUTPUT & AI REVIEW:", font=("Consolas", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)

        self.complexity_badge = ctk.CTkLabel(rev_hdr, text="Runtime: -- | Verdict: --", font=("Consolas", 9, "bold"), fg_color="#1e293b", text_color="#10b981", corner_radius=4, padx=8, pady=2)
        self.complexity_badge.pack(side=tk.RIGHT)

        self.code_review_text = scrolledtext.ScrolledText(
            rev_box,
            height=4,
            font=("Segoe UI", 9),
            bg="#080c14",
            fg="#e2e8f0",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
        )
        self.code_review_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        self.code_review_text.insert(tk.END, "Click '▶️ Run Code' to execute against test cases, or '⚡ AI Review' for Big-O and edge-case analysis.")
        self.code_review_text.configure(state=tk.DISABLED)

        self._on_select_problem(prob_titles[0])

    def _on_select_problem(self, title):
        for p in self.curated_problems:
            if p["title"] == title:
                self.prob_title_lbl.configure(text=f"{p['title']} ({p.get('difficulty', 'Medium')})")
                self.prob_desc_text.configure(state=tk.NORMAL)
                self.prob_desc_text.delete("1.0", tk.END)
                self.prob_desc_text.insert(tk.END, p["description"])
                self.prob_desc_text.configure(state=tk.DISABLED)

                lang = self.lang_selector.get()
                starter = p.get("starter_python") if lang == "Python" else p.get("starter_cpp", "")
                self.code_editor.delete("1.0", tk.END)
                self.code_editor.insert(tk.END, starter)
                break

    def _on_change_coding_lang(self, lang):
        curr_title = self.prob_selector.get()
        self._on_select_problem(curr_title)

    def _on_editor_tab(self, event):
        self.code_editor.insert(tk.INSERT, "    ")
        return "break"

    def _on_reset_problem_code(self):
        curr_title = self.prob_selector.get()
        self._on_select_problem(curr_title)


    def _on_ai_gen_problem(self):
        self.status_lbl.configure(text="Generating novel coding problem via Ollama...")
        self._anim_mode = "thinking"

        def _run():
            p = generate_custom_problem("Data Structures & Algorithms", "Medium")
            self.after(0, lambda: self._on_problem_generated(p))

        threading.Thread(target=_run, daemon=True).start()

    def _on_problem_generated(self, p):
        self._anim_mode = "idle"
        self.status_lbl.configure(text="● Systems Nominal")
        self.curated_problems.insert(0, p)
        prob_titles = [prob["title"] for prob in self.curated_problems]
        self.prob_selector.configure(values=prob_titles)
        self.prob_selector.set(p["title"])
        self._on_select_problem(p["title"])

    def _on_run_python_code(self):
        title = self.prob_selector.get()
        code = self.code_editor.get("1.0", tk.END).strip()
        prob = next((p for p in self.curated_problems if p["title"] == title), {})
        harness = prob.get("test_python", "")

        self.run_code_btn.configure(state=tk.DISABLED)
        self.code_review_text.configure(state=tk.NORMAL)
        self.code_review_text.delete("1.0", tk.END)
        self.code_review_text.insert(tk.END, "Executing code in local sandbox...\n")

        def _exec():
            res = run_python_code(code, harness)
            self.after(0, lambda: self._on_code_executed(res))

        threading.Thread(target=_exec, daemon=True).start()

    def _on_code_executed(self, res):
        self.run_code_btn.configure(state=tk.NORMAL)
        status_str = "Passed" if res["success"] else "Failed"
        color = "#10b981" if res["success"] else "#dc2626"
        self.complexity_badge.configure(text=f"Runtime: {res['runtime_ms']}ms | Execution: {status_str}", text_color=color)

        self.code_review_text.delete("1.0", tk.END)
        if res["success"]:
            self.code_review_text.insert(tk.END, f"✓ TEST HARNESS OUTPUT ({res['runtime_ms']} ms):\n")
            self.code_review_text.insert(tk.END, res["output"] + "\n\nAll test statements completed successfully.")
        else:
            self.code_review_text.insert(tk.END, f"❌ EXECUTION ERROR ({res['runtime_ms']} ms):\n")
            self.code_review_text.insert(tk.END, res["error"] or res["output"])

        self.code_review_text.configure(state=tk.DISABLED)

    def _on_run_code_review(self):
        title = self.prob_selector.get()
        code = self.code_editor.get("1.0", tk.END).strip()
        lang = self.lang_selector.get()

        self.review_btn.configure(state=tk.DISABLED)
        self.code_review_text.configure(state=tk.NORMAL)
        self.code_review_text.delete("1.0", tk.END)
        self.code_review_text.insert(tk.END, "Analyzing Big-O complexity and scanning for edge-case bugs...")
        self.code_review_text.configure(state=tk.DISABLED)
        self._anim_mode = "thinking"

        def _run():
            res = review_candidate_code(title, code, lang)
            self.after(0, lambda: self._on_review_completed(res))

        threading.Thread(target=_run, daemon=True).start()

    def _on_review_completed(self, res):
        self.review_btn.configure(state=tk.NORMAL)
        self._anim_mode = "idle"
        t_comp = res.get("time_complexity", "Unknown")
        s_comp = res.get("space_complexity", "Unknown")
        verdict = res.get("verdict", "Evaluated")

        self.complexity_badge.configure(text=f"Time: {t_comp} | Space: {s_comp} | {verdict}", text_color="#10b981")

        self.code_review_text.configure(state=tk.NORMAL)
        self.code_review_text.delete("1.0", tk.END)
        self.code_review_text.insert(tk.END, f"★ VERDICT: {verdict}\n")
        self.code_review_text.insert(tk.END, f"• Time: {t_comp} | Space: {s_comp}\n\n")

        bugs = res.get("bugs_and_edge_cases", [])
        if bugs:
            self.code_review_text.insert(tk.END, "⚠️ BUGS & EDGE CASES:\n")
            for b in bugs:
                self.code_review_text.insert(tk.END, f"  - {b}\n")
            self.code_review_text.insert(tk.END, "\n")

        opts = res.get("optimizations", [])
        if opts:
            self.code_review_text.insert(tk.END, "💡 OPTIMIZATIONS:\n")
            for o in opts:
                self.code_review_text.insert(tk.END, f"  - {o}\n")

        self.code_review_text.configure(state=tk.DISABLED)

    # --------------------------------------------------
    # TAB: Striver A2Z DSA Sheet & Voice Dry-Run Journal
    # --------------------------------------------------
    def _build_tab_dsa(self):
        parent = self.tab_dsa

        # Top Control Bar
        top_ctrl = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        top_ctrl.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(top_ctrl, text="Topic:", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT, padx=(10, 4), pady=6)

        dsa_topics = get_dsa_topics()
        self.dsa_topic_menu = ctk.CTkOptionMenu(
            top_ctrl,
            values=dsa_topics,
            command=lambda v: self._load_dsa_problems(),
            fg_color="#1e293b",
            button_color="#0284c7",
            font=("Segoe UI", 9),
            width=165,
            height=28,
        )
        self.dsa_topic_menu.pack(side=tk.LEFT, padx=4)

        ctk.CTkLabel(top_ctrl, text="Status:", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT, padx=(8, 4))

        self.dsa_status_menu = ctk.CTkOptionMenu(
            top_ctrl,
            values=["All Statuses", "Unsolved", "Solved", "Stuck"],
            command=lambda v: self._load_dsa_problems(),
            fg_color="#1e293b",
            button_color="#0f766e",
            font=("Segoe UI", 9),
            width=110,
            height=28,
        )
        self.dsa_status_menu.pack(side=tk.LEFT, padx=4)

        self.dsa_search_entry = ctk.CTkEntry(
            top_ctrl,
            placeholder_text="🔍 Filter problem or subtopic...",
            width=200,
            height=28,
        )
        self.dsa_search_entry.pack(side=tk.LEFT, padx=6)
        self.dsa_search_entry.bind("<KeyRelease>", lambda e: self._load_dsa_problems())

        excal_btn = ctk.CTkButton(
            top_ctrl,
            text="🎨 Excalidraw",
            command=launch_excalidraw,
            fg_color="#b45309",
            hover_color="#92400e",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=110,
            cursor="hand2",
        )
        excal_btn.pack(side=tk.LEFT, padx=4)

        self.dsa_stats_badge = ctk.CTkLabel(
            top_ctrl,
            text="Solved: -- / -- (0%)",
            font=("Consolas", 9, "bold"),
            fg_color="#1e293b",
            text_color="#10b981",
            corner_radius=4,
            padx=8,
            pady=3,
        )
        self.dsa_stats_badge.pack(side=tk.RIGHT, padx=10)

        # Paned Window (Left: Table, Right: Dry-Run Hub)
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left Column: Problem Catalog
        l_col = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(l_col, weight=5)

        l_hdr = ctk.CTkFrame(l_col, fg_color="transparent")
        l_hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
        ctk.CTkLabel(l_hdr, text="STRIVER A2Z PROBLEM SHEET", font=("Consolas", 10, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)

        # Treeview
        tree_frame = ctk.CTkFrame(l_col, fg_color="transparent")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        self.dsa_tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Title", "Subtopic", "Diff", "Status", "Notes"),
            show="headings",
            selectmode="browse",
            height=16,
        )
        self.dsa_tree.heading("ID", text="#")
        self.dsa_tree.heading("Title", text="Problem Title")
        self.dsa_tree.heading("Subtopic", text="Subtopic / Pattern")
        self.dsa_tree.heading("Diff", text="Difficulty")
        self.dsa_tree.heading("Status", text="Status")
        self.dsa_tree.heading("Notes", text="Notes?")

        self.dsa_tree.column("ID", width=28, anchor="center")
        self.dsa_tree.column("Title", width=170, anchor="w")
        self.dsa_tree.column("Subtopic", width=130, anchor="w")
        self.dsa_tree.column("Diff", width=65, anchor="center")
        self.dsa_tree.column("Status", width=75, anchor="center")
        self.dsa_tree.column("Notes", width=55, anchor="center")

        dsa_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.dsa_tree.yview)
        self.dsa_tree.configure(yscrollcommand=dsa_scroll.set)
        self.dsa_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsa_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.dsa_tree.bind("<<TreeviewSelect>>", self._on_select_dsa_problem)
        self.dsa_tree.bind("<Double-1>", lambda e: self._on_dsa_open_problem())

        # Left Action Bar
        l_act = ctk.CTkFrame(l_col, fg_color="transparent")
        l_act.pack(fill=tk.X, padx=6, pady=6)

        ctk.CTkButton(
            l_act,
            text="🌐 Open Problem",
            command=self._on_dsa_open_problem,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=110,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)

        ctk.CTkButton(
            l_act,
            text="▶️ Striver Video",
            command=self._on_dsa_watch_video,
            fg_color="#b91c1c",
            hover_color="#991b1b",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=110,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)

        ctk.CTkButton(
            l_act,
            text="✓ Solved",
            command=lambda: self._on_dsa_mark_status("solved"),
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=75,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)

        ctk.CTkButton(
            l_act,
            text="⚠️ Stuck",
            command=lambda: self._on_dsa_mark_status("stuck"),
            fg_color="#7c2d12",
            hover_color="#9a3412",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=70,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)

        # Right Column: Voice Dry-Run & Revision Notes Hub
        r_col = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(r_col, weight=6)

        # Selected Problem Header
        r_hdr = ctk.CTkFrame(r_col, fg_color="transparent")
        r_hdr.pack(fill=tk.X, padx=10, pady=(8, 2))

        self.dsa_detail_title = ctk.CTkLabel(
            r_hdr,
            text="Select a Problem from the Sheet",
            font=("Consolas", 12, "bold"),
            text_color="#00d2ff",
            anchor="w",
        )
        self.dsa_detail_title.pack(side=tk.LEFT)

        self.dsa_verbal_badge = ctk.CTkLabel(
            r_hdr,
            text="VERBAL CLARITY: --/10",
            font=("Consolas", 9, "bold"),
            fg_color="#1e293b",
            text_color="#38bdf8",
            corner_radius=4,
            padx=8,
            pady=2,
        )
        self.dsa_verbal_badge.pack(side=tk.RIGHT)

        self.dsa_detail_meta = ctk.CTkLabel(
            r_col,
            text="Topic: -- // Subtopic: -- // Difficulty: --",
            font=("Segoe UI", 9),
            text_color="#64748b",
            anchor="w",
        )
        self.dsa_detail_meta.pack(fill=tk.X, padx=10, pady=(0, 6))

        # Action Buttons Row (Voice Dry Run Practice)
        v_row = ctk.CTkFrame(r_col, fg_color="transparent")
        v_row.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.dsa_voice_btn = ctk.CTkButton(
            v_row,
            text="🎙️ Explain Aloud (Voice Practice)",
            command=self._on_dsa_voice_dry_run,
            fg_color="#10b981",
            hover_color="#059669",
            font=("Segoe UI", 9, "bold"),
            height=30,
            cursor="hand2",
        )
        self.dsa_voice_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.dsa_type_btn = ctk.CTkButton(
            v_row,
            text="⌨️ Type Notes",
            command=self._on_dsa_type_dry_run_modal,
            fg_color="#1e293b",
            hover_color="#334155",
            font=("Segoe UI", 9),
            height=30,
            width=90,
            cursor="hand2",
        )
        self.dsa_type_btn.pack(side=tk.LEFT, padx=4)

        self.dsa_audio_rev_btn = ctk.CTkButton(
            v_row,
            text="🔊 1-Min Audio Revision",
            command=self._on_dsa_read_aloud_notes,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 9, "bold"),
            height=30,
            cursor="hand2",
        )
        self.dsa_audio_rev_btn.pack(side=tk.LEFT, padx=4)

        # Notes Display Tabs or Panes
        notes_box = ctk.CTkFrame(r_col, fg_color="#080c14", corner_radius=6, border_width=1, border_color="#1e293b")
        notes_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 8))

        ctk.CTkLabel(notes_box, text="💡 INTUITION & CORE INVARIANT:", font=("Consolas", 9, "bold"), text_color="#f59e0b").pack(anchor="w", padx=8, pady=(6, 2))
        self.dsa_intuition_text = scrolledtext.ScrolledText(
            notes_box,
            height=3,
            font=("Segoe UI", 9),
            bg="#0e1422",
            fg="#e2e8f0",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
        )
        self.dsa_intuition_text.pack(fill=tk.X, padx=8, pady=(0, 4))

        ctk.CTkLabel(notes_box, text="🔍 STEP-BY-STEP DRY-RUN TRACE:", font=("Consolas", 9, "bold"), text_color="#00d2ff").pack(anchor="w", padx=8, pady=(2, 2))
        self.dsa_dryrun_text = scrolledtext.ScrolledText(
            notes_box,
            height=4,
            font=("Consolas", 9),
            bg="#0e1422",
            fg="#e2e8f0",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
        )
        self.dsa_dryrun_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        # Bottom split: Complexity & Critique
        bot_split = ctk.CTkFrame(notes_box, fg_color="transparent")
        bot_split.pack(fill=tk.X, padx=8, pady=(2, 6))

        c_left = ctk.CTkFrame(bot_split, fg_color="#0e1422", corner_radius=4, border_width=1, border_color="#1e293b")
        c_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        ctk.CTkLabel(c_left, text="COMPLEXITY & EDGE CASES", font=("Consolas", 9, "bold"), text_color="#a855f7").pack(anchor="w", padx=6, pady=2)
        self.dsa_complexity_text = ctk.CTkLabel(c_left, text="Time: -- | Space: --\nEdge cases: None logged", font=("Segoe UI", 8), text_color="#94a3b8", justify="left")
        self.dsa_complexity_text.pack(anchor="w", padx=6, pady=(0, 4))

        c_right = ctk.CTkFrame(bot_split, fg_color="#0e1422", corner_radius=4, border_width=1, border_color="#1e293b")
        c_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        ctk.CTkLabel(c_right, text="INTERVIEW VERBAL COACHING", font=("Consolas", 9, "bold"), text_color="#10b981").pack(anchor="w", padx=6, pady=2)
        self.dsa_critique_text = ctk.CTkLabel(c_right, text="Practice explaining your thought process clearly.", font=("Segoe UI", 8), text_color="#94a3b8", justify="left", wraplength=280)
        self.dsa_critique_text.pack(anchor="w", padx=6, pady=(0, 4))

    def _load_dsa_problems(self):
        if not hasattr(self, "dsa_tree"):
            return
        topic = getattr(self, "dsa_topic_menu", None)
        t_val = topic.get() if topic else "All Topics"

        status = getattr(self, "dsa_status_menu", None)
        s_val = status.get() if status else "All Statuses"

        search = getattr(self, "dsa_search_entry", None)
        q_val = search.get().strip() if search else None

        probs = get_dsa_problems(topic=t_val, status=s_val, search=q_val)

        for item in self.dsa_tree.get_children():
            self.dsa_tree.delete(item)

        for p in probs:
            status_disp = "✓ Solved" if p["status"] == "solved" else ("⚠️ Stuck" if p["status"] == "stuck" else "○ Pending")
            notes_disp = "★ Yes" if p["has_notes"] else "--"
            self.dsa_tree.insert(
                "",
                tk.END,
                values=(p["id"], p["title"], p["subtopic"], p["difficulty"], status_disp, notes_disp),
                tags=(p["difficulty"].lower(), p["status"]),
            )

        # Update stats
        stats = get_dsa_stats()
        self.dsa_stats_badge.configure(
            text=f"Solved: {stats['solved']}/{stats['total']} ({stats['pct_solved']}%) | Notes: {stats['with_notes']}"
        )

        # Style tags
        self.dsa_tree.tag_configure("easy", foreground="#10b981")
        self.dsa_tree.tag_configure("medium", foreground="#f59e0b")
        self.dsa_tree.tag_configure("hard", foreground="#ef4444")

    def _on_select_dsa_problem(self, event=None):
        sel = self.dsa_tree.selection()
        if not sel:
            return
        prob_id = int(self.dsa_tree.item(sel[0])["values"][0])
        self.selected_dsa_problem_id = prob_id
        self._refresh_dsa_detail_view(prob_id)

    def _refresh_dsa_detail_view(self, prob_id):
        prob = get_problem_by_id(prob_id)
        if not prob:
            return

        self.dsa_detail_title.configure(text=f"#{prob['id']}. {prob['title']}")
        self.dsa_detail_meta.configure(text=f"Topic: {prob['topic']} // Subtopic: {prob['subtopic']} // Difficulty: {prob['difficulty']} // Status: {prob['status'].upper()}")

        notes = get_problem_notes(prob_id)
        self.dsa_intuition_text.delete("1.0", tk.END)
        self.dsa_dryrun_text.delete("1.0", tk.END)

        if notes:
            latest = notes[0]
            self.dsa_verbal_badge.configure(
                text=f"VERBAL CLARITY: {latest['verbal_score']}/10",
                text_color="#10b981" if latest["verbal_score"] >= 8 else "#f59e0b"
            )
            self.dsa_intuition_text.insert(tk.END, latest["intuition"])
            self.dsa_dryrun_text.insert(tk.END, latest["dry_run"])
            self.dsa_complexity_text.configure(
                text=f"Time: {latest['time_complexity']} | Space: {latest['space_complexity']}\nEdge Cases: {latest['edge_cases'][:65]}"
            )
            self.dsa_critique_text.configure(
                text=latest.get("verbal_critique", "Clear explanation delivered.")
            )
        else:
            self.dsa_verbal_badge.configure(text="VERBAL CLARITY: --/10", text_color="#38bdf8")
            self.dsa_intuition_text.insert(tk.END, "No dry-run notes recorded yet.\nClick '🎙️ Explain Aloud (Voice Practice)' to speak your solution and have JARVIS generate structured revision notes.")
            self.dsa_dryrun_text.insert(tk.END, "// Dry-run trace will be generated from your spoken voice explanation.")
            self.dsa_complexity_text.configure(text="Time: -- | Space: --\nEdge cases: None logged")
            self.dsa_critique_text.configure(text="Solve on LeetCode/Code360, sketch on Excalidraw, then speak your solution aloud.")

    def _on_dsa_open_problem(self):
        if not self.selected_dsa_problem_id:
            messagebox.showinfo("Select Problem", "Please select a problem from the table first.")
            return
        launch_problem_url(self.selected_dsa_problem_id)

    def _on_dsa_watch_video(self):
        if not self.selected_dsa_problem_id:
            messagebox.showinfo("Select Problem", "Please select a problem from the table first.")
            return
        launch_video_url(self.selected_dsa_problem_id)

    def _on_dsa_mark_status(self, status):
        if not self.selected_dsa_problem_id:
            return
        update_problem_status(self.selected_dsa_problem_id, status)
        self._load_dsa_problems()
        self._refresh_dsa_detail_view(self.selected_dsa_problem_id)

    def _on_dsa_voice_dry_run(self):
        if not self.selected_dsa_problem_id:
            messagebox.showinfo("Select Problem", "Please select a problem first.")
            return

        prob = get_problem_by_id(self.selected_dsa_problem_id)
        if not STT_AVAILABLE:
            messagebox.showwarning("Voice Unavailable", "Speech recognition is not available. Please use '⌨️ Type Notes'.")
            return

        play_chime()
        self.dsa_voice_btn.configure(state=tk.DISABLED)
        self.status_lbl.configure(text=f"🎤 Listening to your dry-run explanation for {prob['title']}...")
        self._anim_mode = "listening"

        def _record():
            transcript, err = listen_to_microphone(timeout=10, phrase_time_limit=35)
            if not transcript:
                transcript = "Candidate solved the problem optimally with standard dry run."

            self.after(0, lambda: self.status_lbl.configure(text="Synthesizing dry-run notes & evaluating interview delivery..."))
            self.after(0, lambda: setattr(self, "_anim_mode", "thinking"))

            try:
                res = record_voice_dry_run(self.selected_dsa_problem_id, transcript)
                self.after(0, lambda: self._on_dsa_voice_dry_run_done(self.selected_dsa_problem_id, res))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Note Synthesis Error", str(e)))
            finally:
                def _reset():
                    self.dsa_voice_btn.configure(state=tk.NORMAL)
                    self._anim_mode = "idle"
                    self.status_lbl.configure(text="● Systems Nominal")
                self.after(0, _reset)

        threading.Thread(target=_record, daemon=True).start()

    def _on_dsa_voice_dry_run_done(self, prob_id, res):
        self._load_dsa_problems()
        self._refresh_dsa_detail_view(prob_id)
        score = res.get("verbal_score", 7)
        if self.tts_enabled.get() and TTS_AVAILABLE:
            speak(f"Dry-run notes generated for problem. Verbal clarity score: {score} out of 10.", async_mode=True)
        messagebox.showinfo("Dry-Run Notes Generated", f"Notes successfully created and saved!\nVerbal Score: {score}/10\n{res.get('verbal_critique', '')}")

    def _on_dsa_type_dry_run_modal(self):
        if not self.selected_dsa_problem_id:
            messagebox.showinfo("Select Problem", "Please select a problem first.")
            return

        prob = get_problem_by_id(self.selected_dsa_problem_id)
        modal = ctk.CTkToplevel(self)
        modal.title(f"Type Explanation: {prob['title']}")
        modal.geometry("520x420")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text=f"EXPLAIN SOLUTION // {prob['title'].upper()}", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)
        ctk.CTkLabel(modal, text="Type your intuition, walkthrough, or code logic below. JARVIS will synthesize\npermanent dry-run revision notes for you:", font=("Segoe UI", 9), text_color="#94a3b8", justify="center").pack(pady=(0, 8))

        t_entry = scrolledtext.ScrolledText(modal, height=10, font=("Consolas", 9), bg="#0e1422", fg="#e2e8f0", wrap="word", relief="flat", bd=0, padx=8, pady=6)
        t_entry.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)
        t_entry.insert(tk.END, "To solve this problem, we can use ...\n1. State: dp[i] represents ...\n2. Transition: ...\n3. Base case: ...\nTime complexity is O(...) and space is O(...).")

        def _save():
            text = t_entry.get("1.0", tk.END).strip()
            if not text:
                return
            modal.destroy()
            self.status_lbl.configure(text=f"Synthesizing dry-run notes for {prob['title']}...")
            self._anim_mode = "thinking"

            def _thread():
                try:
                    res = record_voice_dry_run(self.selected_dsa_problem_id, text)
                    self.after(0, lambda: self._on_dsa_voice_dry_run_done(self.selected_dsa_problem_id, res))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Note Synthesis Error", str(e)))
                finally:
                    self.after(0, lambda: setattr(self, "_anim_mode", "idle"))
                    self.after(0, lambda: self.status_lbl.configure(text="● Systems Nominal"))

            threading.Thread(target=_thread, daemon=True).start()

        ctk.CTkButton(modal, text="⚡ Synthesize Structured Revision Notes", command=_save, fg_color="#0f766e", hover_color="#115e59", width=480, height=34, font=("Segoe UI", 9, "bold")).pack(pady=12)

    def _on_dsa_read_aloud_notes(self):
        if not self.selected_dsa_problem_id:
            messagebox.showinfo("Select Problem", "Please select a problem first.")
            return

        speech = get_quick_revision_speech(self.selected_dsa_problem_id)
        if self.tts_enabled.get() and TTS_AVAILABLE:
            self.status_lbl.configure(text="JARVIS reading 1-minute revision note...")
            speak(speech, async_mode=True)
        else:
            messagebox.showinfo("1-Minute Revision", speech)

    # --------------------------------------------------
    # TAB: Campus Placement Aptitude & MCQ Arena
    # --------------------------------------------------
    def _build_tab_aptitude(self):
        parent = self.tab_aptitude

        top_ctrl = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        top_ctrl.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(top_ctrl, text="Domain:", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT, padx=10, pady=6)

        self.apt_category_menu = ctk.CTkOptionMenu(
            top_ctrl,
            values=["All", "Quantitative Aptitude", "Operating Systems", "Database Management (DBMS)", "Computer Networks", "Programming & DSA"],
            fg_color="#1e293b",
            button_color="#0284c7",
            font=("Segoe UI", 9),
            width=210,
            height=28,
        )
        self.apt_category_menu.pack(side=tk.LEFT, padx=4)

        start_drill_btn = ctk.CTkButton(
            top_ctrl,
            text="⚡ Start 5-Q Speed Drill",
            command=self._on_start_aptitude_drill,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 9, "bold"),
            height=28,
            cursor="hand2",
        )
        start_drill_btn.pack(side=tk.LEFT, padx=6)

        gen_ai_quiz_btn = ctk.CTkButton(
            top_ctrl,
            text="🤖 Generate AI Quiz",
            command=self._on_generate_ai_quiz,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=("Segoe UI", 9),
            height=28,
            cursor="hand2",
        )
        gen_ai_quiz_btn.pack(side=tk.LEFT, padx=4)

        self.apt_accuracy_lbl = ctk.CTkLabel(
            top_ctrl,
            text="Accuracy: --%",
            font=("Consolas", 9, "bold"),
            fg_color="#1e293b",
            text_color="#10b981",
            corner_radius=4,
            padx=8,
            pady=3,
        )
        self.apt_accuracy_lbl.pack(side=tk.RIGHT, padx=10)

        # Center Quiz Card
        self.quiz_card = ctk.CTkFrame(parent, fg_color="#080c14", corner_radius=8, border_width=1, border_color="#00d2ff")
        self.quiz_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        quiz_hdr = ctk.CTkFrame(self.quiz_card, fg_color="transparent")
        quiz_hdr.pack(fill=tk.X, padx=14, pady=(10, 4))

        self.quiz_progress_lbl = ctk.CTkLabel(
            quiz_hdr,
            text="QUESTION 1 OF 5 // QUANTITATIVE APTITUDE",
            font=("Consolas", 10, "bold"),
            text_color="#00d2ff",
        )
        self.quiz_progress_lbl.pack(side=tk.LEFT)

        self.quiz_timer_badge = ctk.CTkLabel(
            quiz_hdr,
            text="⏱️ 60s",
            font=("Consolas", 11, "bold"),
            fg_color="#1e293b",
            text_color="#f59e0b",
            corner_radius=4,
            padx=8,
            pady=2,
        )
        self.quiz_timer_badge.pack(side=tk.RIGHT)

        self.quiz_q_text = ctk.CTkLabel(
            self.quiz_card,
            text="Click '⚡ Start 5-Q Speed Drill' above to launch Round 1 OA placement simulation.",
            font=("Segoe UI", 11, "bold"),
            text_color="#ffffff",
            wraplength=900,
            justify="left",
        )
        self.quiz_q_text.pack(anchor="w", padx=14, pady=10)

        # 4 Options Radio Group
        self.quiz_option_var = tk.IntVar(value=-1)
        self.quiz_option_radios = []
        opts_frame = ctk.CTkFrame(self.quiz_card, fg_color="transparent")
        opts_frame.pack(fill=tk.X, padx=14, pady=4)

        for i in range(4):
            r = ctk.CTkRadioButton(
                opts_frame,
                text=f"Option {chr(65+i)}",
                variable=self.quiz_option_var,
                value=i,
                font=("Segoe UI", 10),
                text_color="#cbd5e1",
            )
            r.pack(anchor="w", pady=4)
            self.quiz_option_radios.append(r)

        # Action Buttons
        act_row = ctk.CTkFrame(self.quiz_card, fg_color="transparent")
        act_row.pack(fill=tk.X, padx=14, pady=(6, 8))

        self.submit_quiz_btn = ctk.CTkButton(
            act_row,
            text="✓ Submit Answer",
            command=self._on_submit_quiz_answer,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 9, "bold"),
            height=30,
            width=130,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.submit_quiz_btn.pack(side=tk.LEFT)

        self.next_quiz_btn = ctk.CTkButton(
            act_row,
            text="Next Question ➔",
            command=self._on_next_quiz_question,
            fg_color="#1e293b",
            hover_color="#334155",
            font=("Segoe UI", 9),
            height=30,
            width=130,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.next_quiz_btn.pack(side=tk.LEFT, padx=6)

        # Derivation & Explanation Area
        self.quiz_feedback_text = scrolledtext.ScrolledText(
            self.quiz_card,
            height=5,
            font=("Segoe UI", 9),
            bg="#0e1422",
            fg="#e2e8f0",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
        )
        self.quiz_feedback_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))
        self.quiz_feedback_text.insert(tk.END, "Explanations, mathematical steps, and derivations will appear here upon submission.")
        self.quiz_feedback_text.configure(state=tk.DISABLED)

    def _on_start_aptitude_drill(self):
        cat = self.apt_category_menu.get()
        self.current_aptitude_quiz = get_curated_quiz(category=cat, count=5)
        self.current_quiz_idx = 0
        self.current_quiz_score = 0
        self._display_current_quiz_question()

    def _on_generate_ai_quiz(self):
        cat = self.apt_category_menu.get()
        self.status_lbl.configure(text=f"Generating novel {cat} questions via Ollama...")
        self._anim_mode = "thinking"

        def _run():
            q_list = generate_ai_quiz(category=cat if cat != "All" else "Quantitative Aptitude", count=5)
            self.after(0, lambda: self._on_ai_quiz_ready(q_list))

        threading.Thread(target=_run, daemon=True).start()

    def _on_ai_quiz_ready(self, q_list):
        self._anim_mode = "idle"
        self.status_lbl.configure(text="● Systems Nominal")
        self.current_aptitude_quiz = q_list
        self.current_quiz_idx = 0
        self.current_quiz_score = 0
        self._display_current_quiz_question()

    def _display_current_quiz_question(self):
        if not self.current_aptitude_quiz or self.current_quiz_idx >= len(self.current_aptitude_quiz):
            return

        q = self.current_aptitude_quiz[self.current_quiz_idx]
        total = len(self.current_aptitude_quiz)
        curr = self.current_quiz_idx + 1

        self.quiz_progress_lbl.configure(text=f"QUESTION {curr} OF {total} // {q.get('category', 'GENERAL').upper()}")
        self.quiz_q_text.configure(text=q["question"])

        options = q.get("options", [])
        self.quiz_option_var.set(-1)
        for i, opt in enumerate(options[:4]):
            prefix = chr(65 + i)
            self.quiz_option_radios[i].configure(text=f"{prefix}) {opt}", state=tk.NORMAL)

        self.submit_quiz_btn.configure(state=tk.NORMAL)
        self.next_quiz_btn.configure(state=tk.DISABLED)

        self.quiz_feedback_text.configure(state=tk.NORMAL)
        self.quiz_feedback_text.delete("1.0", tk.END)
        self.quiz_feedback_text.insert(tk.END, "Select an option above and click '✓ Submit Answer'.")
        self.quiz_feedback_text.configure(state=tk.DISABLED)

        # Reset 60s timer
        self.quiz_timer_seconds = 60
        self.quiz_timer_running = True
        self._tick_quiz_timer()

    def _tick_quiz_timer(self):
        if not self.quiz_timer_running:
            return
        self.quiz_timer_badge.configure(
            text=f"⏱️ {self.quiz_timer_seconds}s",
            text_color="#ef4444" if self.quiz_timer_seconds <= 10 else "#f59e0b"
        )
        if self.quiz_timer_seconds > 0:
            self.quiz_timer_seconds -= 1
            self.after(1000, self._tick_quiz_timer)
        else:
            self._on_submit_quiz_answer()

    def _on_submit_quiz_answer(self):
        if not self.quiz_timer_running:
            return
        self.quiz_timer_running = False

        sel_idx = self.quiz_option_var.get()
        q = self.current_aptitude_quiz[self.current_quiz_idx]
        corr_idx = int(q.get("correct_idx", 0))
        opts = q.get("options", [])
        expl = q.get("explanation", "Derivation complete.")

        is_correct = (sel_idx == corr_idx)
        if is_correct:
            self.current_quiz_score += 1

        record_drill_result(q.get("category", "General"), q["question"], opts, corr_idx, sel_idx, expl)

        self.submit_quiz_btn.configure(state=tk.DISABLED)
        self.next_quiz_btn.configure(state=tk.NORMAL)

        corr_letter = chr(65 + corr_idx) if 0 <= corr_idx < 4 else "N/A"
        self.quiz_feedback_text.configure(state=tk.NORMAL)
        self.quiz_feedback_text.delete("1.0", tk.END)
        if is_correct:
            self.quiz_feedback_text.insert(tk.END, f"✓ CORRECT! Option {corr_letter} is accurate.\n\n")
        else:
            sel_str = chr(65 + sel_idx) if 0 <= sel_idx < 4 else "Timed Out"
            self.quiz_feedback_text.insert(tk.END, f"❌ INCORRECT (You selected: {sel_str}). Correct Answer: Option {corr_letter}\n\n")

        self.quiz_feedback_text.insert(tk.END, f"💡 STEP-BY-STEP DERIVATION / MECHANICS:\n{expl}")
        self.quiz_feedback_text.configure(state=tk.DISABLED)
        self._refresh_aptitude_stats_display()

    def _on_next_quiz_question(self):
        self.current_quiz_idx += 1
        if self.current_quiz_idx < len(self.current_aptitude_quiz):
            self._display_current_quiz_question()
        else:
            total = len(self.current_aptitude_quiz)
            pct = int((self.current_quiz_score / total) * 100) if total else 0
            messagebox.showinfo("Drill Completed", f"Speed drill finished!\nScore: {self.current_quiz_score} / {total} ({pct}% accuracy)")
            self.quiz_progress_lbl.configure(text=f"DRILL COMPLETED // SCORE: {self.current_quiz_score} / {total} ({pct}%)")

    def _refresh_aptitude_stats_display(self):
        try:
            stats = get_aptitude_stats()
            self.apt_accuracy_lbl.configure(text=f"Accuracy: {stats['overall_accuracy']}% ({stats['correct']}/{stats['total_attempted']})")
        except Exception:
            pass

    # --------------------------------------------------
    # TAB 3: Mock Interview Studio
    # --------------------------------------------------
    def _build_tab_mock(self):
        parent = self.tab_mock

        ctrl_frame = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        ctrl_frame.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(ctrl_frame, text="Placement Domain:", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT, padx=10, pady=6)

        self.mock_topics = get_available_topics()
        self.mock_topic_menu = ctk.CTkOptionMenu(
            ctrl_frame,
            values=self.mock_topics[:15],
            font=("Segoe UI", 9),
            fg_color="#1e293b",
            button_color="#0284c7",
            width=230,
            height=28,
        )
        self.mock_topic_menu.pack(side=tk.LEFT, padx=4)

        self.gen_q_btn = ctk.CTkButton(
            ctrl_frame,
            text="🎲 Question",
            command=self._on_generate_interview_q,
            fg_color="#0f766e",
            hover_color="#115e59",
            text_color="#ffffff",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=95,
            cursor="hand2",
        )
        self.gen_q_btn.pack(side=tk.LEFT, padx=4)

        self.hands_free_btn = ctk.CTkButton(
            ctrl_frame,
            text="🎙️ Hands-Free Drill",
            command=self._on_hands_free_voice_drill,
            fg_color="#7c2d12",
            hover_color="#9a3412",
            text_color="#ffffff",
            font=("Segoe UI", 9, "bold"),
            height=28,
            cursor="hand2",
        )
        self.hands_free_btn.pack(side=tk.LEFT, padx=4)

        q_frame = ctk.CTkFrame(parent, fg_color="#080c14", corner_radius=6, border_width=1, border_color="#00d2ff")
        q_frame.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(q_frame, text="INTERVIEW QUESTION:", font=("Consolas", 9, "bold"), text_color="#00d2ff").pack(anchor="w", padx=10, pady=(6, 2))

        self.mock_q_text = ctk.CTkLabel(
            q_frame,
            text="Click 'Generate Question' to begin your placement interview drill.",
            font=("Segoe UI", 10),
            text_color="#f8fafc",
            wraplength=920,
            justify="left",
        )
        self.mock_q_text.pack(anchor="w", padx=10, pady=(2, 8))

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        ans_box = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(ans_box, weight=1)

        ctk.CTkLabel(ans_box, text="Your Answer (Spoken or Typed):", font=("Segoe UI", 9, "bold"), text_color="#94a3b8").pack(anchor="w", padx=10, pady=(6, 2))

        self.mock_ans_entry = scrolledtext.ScrolledText(
            ans_box,
            height=8,
            font=("Consolas", 9),
            bg="#080c14",
            fg="#e2e8f0",
            insertbackground="#00d2ff",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
        )
        self.mock_ans_entry.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        ans_btn_row = ctk.CTkFrame(ans_box, fg_color="transparent")
        ans_btn_row.pack(fill=tk.X, padx=10, pady=(2, 6))

        self.mock_voice_btn = ctk.CTkButton(
            ans_btn_row,
            text="🎤 Speak Answer",
            command=self._on_mock_voice_answer,
            fg_color="#0891b2",
            hover_color="#0e7490",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=110,
            cursor="hand2",
        )
        self.mock_voice_btn.pack(side=tk.LEFT)

        self.hands_free_btn = ctk.CTkButton(
            ans_btn_row,
            text="🎙️ Hands-Free Drill",
            command=self._on_hands_free_voice_drill,
            fg_color="#10b981",
            hover_color="#059669",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=135,
            cursor="hand2",
        )
        self.hands_free_btn.pack(side=tk.LEFT, padx=6)

        self.grade_btn = ctk.CTkButton(
            ans_btn_row,
            text="⚡ Grade & Evaluate",
            command=self._on_evaluate_mock_answer,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 9, "bold"),
            height=28,
            cursor="hand2",
        )
        self.grade_btn.pack(side=tk.RIGHT)

        eval_box = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(eval_box, weight=1)

        eval_hdr = ctk.CTkFrame(eval_box, fg_color="transparent")
        eval_hdr.pack(fill=tk.X, padx=10, pady=(6, 2))

        ctk.CTkLabel(eval_hdr, text="AI Evaluator Feedback:", font=("Segoe UI", 9, "bold"), text_color="#94a3b8").pack(side=tk.LEFT)

        self.mock_score_badge = ctk.CTkLabel(eval_hdr, text="SCORE: -- / 10", font=("Consolas", 10, "bold"), fg_color="#1e293b", text_color="#38bdf8", corner_radius=4, padx=6, pady=2)
        self.mock_score_badge.pack(side=tk.RIGHT)

        self.mock_eval_text = scrolledtext.ScrolledText(
            eval_box,
            height=8,
            font=("Segoe UI", 9),
            bg="#080c14",
            fg="#e2e8f0",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
        )
        self.mock_eval_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 6))
        self.mock_eval_text.insert(tk.END, "Awaiting candidate answer...")
        self.mock_eval_text.configure(state=tk.DISABLED)

    def _on_generate_interview_q(self):
        topic = self.mock_topic_menu.get()
        self.gen_q_btn.configure(state=tk.DISABLED)
        self.mock_q_text.configure(text=f"Generating FAANG placement question for {topic}...")
        self._anim_mode = "thinking"

        def _run():
            q = generate_interview_question(topic)
            self.after(0, lambda: self._on_q_generated(q))

        threading.Thread(target=_run, daemon=True).start()

    def _on_q_generated(self, q):
        self.gen_q_btn.configure(state=tk.NORMAL)
        self._anim_mode = "idle"
        self.mock_q_text.configure(text=q)
        self.mock_ans_entry.delete("1.0", tk.END)
        self.mock_score_badge.configure(text="SCORE: -- / 10")
        if self.tts_enabled.get() and TTS_AVAILABLE:
            speak(q, async_mode=True)

    def _on_mock_voice_answer(self):
        if not STT_AVAILABLE:
            messagebox.showwarning("Voice Input", "Speech recognition unavailable.")
            return
        play_chime()
        self.mock_voice_btn.configure(state=tk.DISABLED)
        self._anim_mode = "listening"

        def _listen():
            text, err = listen_to_microphone(timeout=10, phrase_time_limit=30)
            self.after(0, lambda: self._on_mock_voice_done(text, err))

        threading.Thread(target=_listen, daemon=True).start()

    def _on_mock_voice_done(self, text, err):
        self.mock_voice_btn.configure(state=tk.NORMAL)
        self._anim_mode = "idle"
        if text:
            self.mock_ans_entry.delete("1.0", tk.END)
            self.mock_ans_entry.insert(tk.END, text)

    def _on_evaluate_mock_answer(self):
        topic = self.mock_topic_menu.get()
        question = self.mock_q_text.cget("text")
        user_ans = self.mock_ans_entry.get("1.0", tk.END).strip()
        if not user_ans or len(user_ans) < 5:
            messagebox.showwarning("Evaluation", "Please type or speak an answer first.")
            return

        self.grade_btn.configure(state=tk.DISABLED)
        self._anim_mode = "thinking"

        def _run():
            res = evaluate_interview_answer(topic, question, user_ans)
            save_interview_result(topic, question, user_ans, res)
            self.after(0, lambda: self._on_mock_eval_done(res))

        threading.Thread(target=_run, daemon=True).start()

    def _on_mock_eval_done(self, res):
        self.grade_btn.configure(state=tk.NORMAL)
        self._anim_mode = "idle"
        score = res.get("score", 5)
        self.mock_score_badge.configure(text=f"SCORE: {score} / 10")

        self.mock_eval_text.configure(state=tk.NORMAL)
        self.mock_eval_text.delete("1.0", tk.END)
        self.mock_eval_text.insert(tk.END, f"★ STRENGTHS:\n{res.get('strengths', '')}\n\n")
        self.mock_eval_text.insert(tk.END, f"⚠️ MISSED POINTS:\n{res.get('missing_points', '')}\n\n")
        self.mock_eval_text.insert(tk.END, f"💡 MODEL ANSWER:\n{res.get('model_answer', '')}\n")
        self.mock_eval_text.configure(state=tk.DISABLED)

    def _on_hands_free_voice_drill(self):
        topic = self.mock_topic_menu.get()
        self.hands_free_btn.configure(state=tk.DISABLED)
        self.mock_voice_btn.configure(state=tk.DISABLED)
        self.gen_q_btn.configure(state=tk.DISABLED)
        self.grade_btn.configure(state=tk.DISABLED)
        self._anim_mode = "thinking"
        self.mock_q_text.configure(text=f"Hands-Free Drill: Synthesizing placement question on {topic}...")

        def on_status(msg):
            self.after(0, lambda: self.status_lbl.configure(text=f"● {msg}"))

        def on_question(q):
            self.after(0, lambda: self.mock_q_text.configure(text=q))
            self.after(0, lambda: setattr(self, "_anim_mode", "speaking"))

        def on_eval(ans, res):
            self.after(0, lambda: self._on_hands_free_eval_done(ans, res))

        def _run():
            try:
                run_hands_free_interview_question(
                    topic,
                    on_status=on_status,
                    on_question=on_question,
                    on_eval=on_eval,
                )
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Hands-Free Drill Error", str(e)))
            finally:
                def _reset():
                    self.hands_free_btn.configure(state=tk.NORMAL)
                    self.mock_voice_btn.configure(state=tk.NORMAL)
                    self.gen_q_btn.configure(state=tk.NORMAL)
                    self.grade_btn.configure(state=tk.NORMAL)
                    self._anim_mode = "idle"
                    self.status_lbl.configure(text="● Systems Nominal")
                self.after(0, _reset)

        threading.Thread(target=_run, daemon=True).start()

    def _on_hands_free_eval_done(self, user_ans, res):
        self.mock_ans_entry.delete("1.0", tk.END)
        self.mock_ans_entry.insert(tk.END, user_ans)
        score = res.get("score", 5)
        self.mock_score_badge.configure(text=f"SCORE: {score} / 10")
        self.mock_eval_text.configure(state=tk.NORMAL)
        self.mock_eval_text.delete("1.0", tk.END)
        self.mock_eval_text.insert(tk.END, f"★ STRENGTHS:\n{res.get('strengths', '')}\n\n")
        self.mock_eval_text.insert(tk.END, f"⚠️ MISSED POINTS:\n{res.get('missing_points', '')}\n\n")
        self.mock_eval_text.insert(tk.END, f"💡 MODEL ANSWER:\n{res.get('model_answer', '')}\n")
        self.mock_eval_text.configure(state=tk.DISABLED)

    # --------------------------------------------------
    # TAB 4: Spaced Repetition Flashcards
    # --------------------------------------------------
    def _build_tab_flashcards(self):
        parent = self.tab_flashcards

        f_ctrl = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        f_ctrl.pack(fill=tk.X, padx=6, pady=4)

        self.fc_count_lbl = ctk.CTkLabel(f_ctrl, text="Card Queue: -- / --", font=("Segoe UI", 9, "bold"), text_color="#38bdf8")
        self.fc_count_lbl.pack(side=tk.LEFT, padx=12, pady=6)

        self.fc_progress_bar = ctk.CTkProgressBar(f_ctrl, width=220, height=10, progress_color="#00d2ff", fg_color="#1e293b")
        self.fc_progress_bar.pack(side=tk.LEFT, padx=8)
        self.fc_progress_bar.set(0.0)

        add_fc_btn = ctk.CTkButton(
            f_ctrl,
            text="➕ New Flashcard",
            command=self._on_add_flashcard_modal,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 9, "bold"),
            height=28,
            width=110,
        )
        add_fc_btn.pack(side=tk.RIGHT, padx=4)

        reload_fc_btn = ctk.CTkButton(
            f_ctrl,
            text="🔄 Refresh",
            command=self._load_flashcard_queue,
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            width=70,
        )
        reload_fc_btn.pack(side=tk.RIGHT, padx=4)

        # Flashcard Flip Card
        self.fc_card = ctk.CTkFrame(parent, fg_color="#080c14", corner_radius=8, border_width=1, border_color="#00d2ff")
        self.fc_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.fc_topic_badge = ctk.CTkLabel(self.fc_card, text="TOPIC: GENERAL", font=("Consolas", 9, "bold"), text_color="#00d2ff")
        self.fc_topic_badge.pack(anchor="w", padx=14, pady=(12, 4))

        self.fc_question_text = ctk.CTkLabel(
            self.fc_card,
            text="Awaiting flashcard load...",
            font=("Segoe UI", 12, "bold"),
            text_color="#ffffff",
            wraplength=900,
            justify="left",
        )
        self.fc_question_text.pack(anchor="w", padx=14, pady=8)

        # Answer Section
        self.fc_answer_frame = ctk.CTkFrame(self.fc_card, fg_color="#0e1422", corner_radius=6)
        self.fc_answer_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        self.fc_answer_text = ctk.CTkLabel(
            self.fc_answer_frame,
            text="[Click 'Show Answer' below to flip card]",
            font=("Segoe UI", 10),
            text_color="#94a3b8",
            wraplength=880,
            justify="left",
        )
        self.fc_answer_text.pack(anchor="w", padx=12, pady=12)

        # Action Buttons Row
        self.fc_action_row = ctk.CTkFrame(self.fc_card, fg_color="transparent")
        self.fc_action_row.pack(fill=tk.X, padx=14, pady=(6, 14))

        self.flip_btn = ctk.CTkButton(
            self.fc_action_row,
            text="👁️ Show Answer",
            command=self._on_flip_flashcard,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 10, "bold"),
            height=32,
            width=140,
            cursor="hand2",
        )
        self.flip_btn.pack(side=tk.LEFT)

        # Grade Buttons (1: Again, 2: Hard, 3: Good, 4: Easy)
        self.grade_btn_frame = ctk.CTkFrame(self.fc_action_row, fg_color="transparent")
        self.grade_btn_frame.pack(side=tk.RIGHT)

        grades = [
            ("1. Again", "#dc2626", "#b91c1c", 1),
            ("2. Hard", "#d97706", "#b45309", 2),
            ("3. Good", "#0284c7", "#0369a1", 3),
            ("4. Easy", "#10b981", "#059669", 4),
        ]
        for lbl, col, hov, g_val in grades:
            btn = ctk.CTkButton(
                self.grade_btn_frame,
                text=lbl,
                command=lambda v=g_val: self._on_grade_flashcard(v),
                fg_color=col,
                hover_color=hov,
                font=("Segoe UI", 9, "bold"),
                height=32,
                width=85,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=3)

        self._load_flashcard_queue()

    def _load_flashcard_queue(self):
        self.flashcards = get_due_flashcards(limit=15)
        self.current_flashcard_idx = 0
        total = len(self.flashcards)
        self.fc_count_lbl.configure(text=f"Queue: 1 of {total} (Due today)")
        if hasattr(self, "fc_progress_bar"):
            self.fc_progress_bar.set(1.0 / total if total else 0.0)
        self._display_current_flashcard()

    def _display_current_flashcard(self):
        if not self.flashcards:
            self.fc_question_text.configure(text="All flashcard drills complete for today! Exceptional retention.")
            self.fc_answer_text.configure(text="")
            self.flip_btn.configure(state=tk.DISABLED)
            if hasattr(self, "fc_progress_bar"):
                self.fc_progress_bar.set(1.0)
            return

        total = len(self.flashcards)
        curr = self.current_flashcard_idx + 1
        pct = int((curr / total) * 100) if total else 0
        self.fc_count_lbl.configure(text=f"Queue: {curr} of {total} ({pct}% complete)")
        if hasattr(self, "fc_progress_bar"):
            self.fc_progress_bar.set(curr / total if total else 0.0)

        card = self.flashcards[self.current_flashcard_idx]
        self.fc_topic_badge.configure(text=f"TOPIC: {card['topic'].upper()}")
        self.fc_question_text.configure(text=card["front"])
        self.fc_answer_text.configure(text="[Click 'Show Answer' below to flip card]")
        self.flashcard_revealed = False
        self.flip_btn.configure(state=tk.NORMAL)

    def _on_flip_flashcard(self):
        if not self.flashcards:
            return
        card = self.flashcards[self.current_flashcard_idx]
        self.fc_answer_text.configure(text=card["back"])
        self.flashcard_revealed = True

    def _on_grade_flashcard(self, grade):
        if not self.flashcards:
            return
        card = self.flashcards[self.current_flashcard_idx]
        record_flashcard_review(card["id"], grade)
        self.current_flashcard_idx = (self.current_flashcard_idx + 1) % len(self.flashcards)
        self._display_current_flashcard()

    def _on_add_flashcard_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Add Placement Flashcard")
        modal.geometry("440x370")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="CREATE PLACEMENT FLASHCARD", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

        top_presets = ["Operating Systems", "DBMS", "Computer Networks", "Data Structures & Algorithms", "System Design", "Placement General"]
        t_menu = ctk.CTkOptionMenu(modal, values=top_presets, width=370, height=30, fg_color="#1e293b", button_color="#0284c7")
        t_menu.pack(pady=4)

        f_ent = ctk.CTkEntry(modal, placeholder_text="Front Question (e.g. What is Mutex vs Semaphore?)", width=370, height=30)
        f_ent.pack(pady=4)

        b_ent = ctk.CTkEntry(modal, placeholder_text="Back Answer (Concise explanation)...", width=370, height=50)
        b_ent.pack(pady=4)

        def _save():
            top = t_menu.get().strip() or "General"
            fr = f_ent.get().strip()
            bk = b_ent.get().strip()
            if not fr or not bk:
                return
            add_custom_flashcard(fr, bk, top)
            modal.destroy()
            self._load_flashcard_queue()

        ctk.CTkButton(modal, text="Save Card to Queue", command=_save, fg_color="#0284c7", width=360, height=32).pack(pady=16)

    # --------------------------------------------------
    # TAB 5: AI Resume Studio & Project Manager
    # --------------------------------------------------
    def _build_tab_resume(self):
        parent = self.tab_resume

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left Column: Profile & Project Manager
        l_box = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(l_box, weight=1)

        ctk.CTkLabel(l_box, text="RESUME PROFILE & PROJECT STUDIO", font=("Consolas", 10, "bold"), text_color="#38bdf8").pack(anchor="w", padx=10, pady=(8, 4))

        info_r = ctk.CTkFrame(l_box, fg_color="transparent")
        info_r.pack(fill=tk.X, padx=10, pady=2)

        self.res_name = ctk.CTkEntry(info_r, placeholder_text="Full Name", height=28)
        self.res_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.res_email = ctk.CTkEntry(info_r, placeholder_text="Email", height=28)
        self.res_email.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        skills_r = ctk.CTkFrame(l_box, fg_color="transparent")
        skills_r.pack(fill=tk.X, padx=10, pady=(6, 2))

        ctk.CTkLabel(skills_r, text="Skills:", font=("Segoe UI", 9, "bold"), text_color="#94a3b8").pack(side=tk.LEFT)

        sync_btn = ctk.CTkButton(
            skills_r,
            text="🔄 Sync Mastered Skills",
            command=self._on_sync_resume_skills,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 8, "bold"),
            height=22,
            cursor="hand2",
        )
        sync_btn.pack(side=tk.RIGHT)

        self.res_skills = ctk.CTkEntry(l_box, placeholder_text="Skills (comma-separated)...", height=28)
        self.res_skills.pack(fill=tk.X, padx=10, pady=2)

        # Projects & Experience Manager Bar
        proj_hdr_r = ctk.CTkFrame(l_box, fg_color="transparent")
        proj_hdr_r.pack(fill=tk.X, padx=10, pady=(6, 2))

        ctk.CTkLabel(proj_hdr_r, text="Target Proj:", font=("Segoe UI", 9, "bold"), text_color="#94a3b8").pack(side=tk.LEFT)

        self.target_project_menu = ctk.CTkOptionMenu(
            proj_hdr_r,
            values=["[No Projects]"],
            fg_color="#1e293b",
            button_color="#0284c7",
            font=("Segoe UI", 8),
            width=160,
            height=22,
        )
        self.target_project_menu.pack(side=tk.LEFT, padx=3)

        add_proj_btn = ctk.CTkButton(
            proj_hdr_r,
            text="➕ Proj",
            command=self._on_add_project_modal,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 8, "bold"),
            height=22,
            width=50,
        )
        add_proj_btn.pack(side=tk.LEFT, padx=2)

        add_exp_btn = ctk.CTkButton(
            proj_hdr_r,
            text="➕ Exp",
            command=self._on_add_experience_modal,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 8, "bold"),
            height=22,
            width=50,
        )
        add_exp_btn.pack(side=tk.LEFT, padx=2)

        del_proj_btn = ctk.CTkButton(
            proj_hdr_r,
            text="🗑️",
            command=self._on_delete_selected_project,
            fg_color="#1e293b",
            hover_color="#dc2626",
            text_color="#ef4444",
            font=("Segoe UI", 8),
            height=22,
            width=26,
        )
        del_proj_btn.pack(side=tk.LEFT, padx=2)

        # Google XYZ Card
        xyz_card = ctk.CTkFrame(l_box, fg_color="#080c14", corner_radius=6, border_width=1, border_color="#1e293b")
        xyz_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 4))

        ctk.CTkLabel(xyz_card, text="⚡ Google XYZ Bullet Synthesizer", font=("Segoe UI", 9, "bold"), text_color="#00d2ff").pack(anchor="w", padx=8, pady=(4, 2))

        self.xyz_input = ctk.CTkEntry(xyz_card, placeholder_text="Describe raw project accomplishment...", height=28)
        self.xyz_input.pack(fill=tk.X, padx=8, pady=2)

        xyz_btn_r = ctk.CTkFrame(xyz_card, fg_color="transparent")
        xyz_btn_r.pack(fill=tk.X, padx=8, pady=4)

        xyz_btn = ctk.CTkButton(
            xyz_btn_r,
            text="✨ Synthesize Bullets",
            command=self._on_optimize_bullets,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 8, "bold"),
            height=24,
            cursor="hand2",
        )
        xyz_btn.pack(side=tk.LEFT)

        inject_btn = ctk.CTkButton(
            xyz_btn_r,
            text="📥 Inject Bullet to Project",
            command=self._on_inject_xyz_bullet,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 8, "bold"),
            height=24,
            cursor="hand2",
        )
        inject_btn.pack(side=tk.RIGHT)

        self.xyz_output = scrolledtext.ScrolledText(xyz_card, height=4, font=("Segoe UI", 9), bg="#0e1422", fg="#e2e8f0", relief="flat", bd=0, padx=6, pady=4)
        self.xyz_output.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 4))

        # Multi-template exporter row
        exp_row = ctk.CTkFrame(l_box, fg_color="transparent")
        exp_row.pack(fill=tk.X, padx=10, pady=(4, 8))

        ctk.CTkLabel(exp_row, text="Template:", font=("Segoe UI", 9), text_color="#94a3b8").pack(side=tk.LEFT, padx=(0, 4))

        self.template_menu = ctk.CTkOptionMenu(
            exp_row,
            values=["stark", "harvard", "modern"],
            fg_color="#1e293b",
            button_color="#0284c7",
            width=85,
            height=26,
        )
        self.template_menu.pack(side=tk.LEFT, padx=4)

        html_btn = ctk.CTkButton(
            exp_row,
            text="📄 Export HTML/PDF",
            command=self._on_export_resume_html,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 9, "bold"),
            height=26,
            cursor="hand2",
        )
        html_btn.pack(side=tk.RIGHT)

        preview_btn = ctk.CTkButton(
            exp_row,
            text="👁️ View Profile",
            command=self._on_view_full_resume_modal,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#38bdf8",
            font=("Segoe UI", 8),
            height=26,
            cursor="hand2",
        )
        preview_btn.pack(side=tk.RIGHT, padx=4)

        # Right Column: JD Matcher
        r_box = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(r_box, weight=1)

        r_hdr = ctk.CTkFrame(r_box, fg_color="transparent")
        r_hdr.pack(fill=tk.X, padx=10, pady=(8, 4))

        ctk.CTkLabel(r_hdr, text="JOB DESCRIPTION (JD) ATS MATCHER", font=("Consolas", 10, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)

        self.jd_score_lbl = ctk.CTkLabel(r_hdr, text="ATS MATCH: --%", font=("Consolas", 9, "bold"), fg_color="#1e293b", text_color="#10b981", corner_radius=4, padx=6, pady=2)
        self.jd_score_lbl.pack(side=tk.RIGHT)

        self.jd_text = scrolledtext.ScrolledText(r_box, height=6, font=("Segoe UI", 9), bg="#080c14", fg="#e2e8f0", insertbackground="#00d2ff", relief="flat", bd=0, padx=8, pady=4)
        self.jd_text.pack(fill=tk.X, padx=10, pady=2)

        jd_btn_r = ctk.CTkFrame(r_box, fg_color="transparent")
        jd_btn_r.pack(fill=tk.X, padx=10, pady=4)

        self.sync_gaps_btn = ctk.CTkButton(
            jd_btn_r,
            text="📥 Sync Gaps to Study Queue",
            command=self._on_sync_jd_gaps_to_study,
            fg_color="#1e293b",
            hover_color="#334155",
            font=("Segoe UI", 9),
            height=26,
            state=tk.DISABLED,
        )
        self.sync_gaps_btn.pack(side=tk.LEFT)

        analyze_jd_btn = ctk.CTkButton(
            jd_btn_r,
            text="🎯 Match Against JD",
            command=self._on_analyze_jd,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 9, "bold"),
            height=26,
            cursor="hand2",
        )
        analyze_jd_btn.pack(side=tk.RIGHT)

        self.jd_results_text = scrolledtext.ScrolledText(r_box, height=7, font=("Segoe UI", 9), bg="#080c14", fg="#e2e8f0", relief="flat", bd=0, padx=8, pady=4)
        self.jd_results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 8))
        self.jd_results_text.insert(tk.END, "Paste Job Description above to calculate ATS score and reveal missing competencies.")
        self.jd_results_text.configure(state=tk.DISABLED)

    def _on_add_project_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Add Engineering Project")
        modal.geometry("420x320")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="ADD ENGINEERING PROJECT", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

        t_ent = ctk.CTkEntry(modal, placeholder_text="Project Title (e.g. Distributed Cache)", width=360, height=30)
        t_ent.pack(pady=4)

        tc_ent = ctk.CTkEntry(modal, placeholder_text="Tech Stack (e.g. Python, Redis, Docker)", width=360, height=30)
        tc_ent.pack(pady=4)

        b_ent = ctk.CTkEntry(modal, placeholder_text="Initial Accomplishment Bullet...", width=360, height=45)
        b_ent.pack(pady=4)

        def _save():
            t = t_ent.get().strip()
            tc = tc_ent.get().strip()
            b = b_ent.get().strip()
            if not t:
                return
            add_resume_project(t, tc, [b] if b else [])
            modal.destroy()
            self._refresh_project_dropdown()
            messagebox.showinfo("Project Added", f"Added project '{t}' to resume profile.")

        ctk.CTkButton(modal, text="Save Project", command=_save, fg_color="#0284c7", width=360, height=32).pack(pady=14)

    def _refresh_project_dropdown(self):
        try:
            projs = get_project_summaries()
            if projs:
                vals = [f"[{p['index']}] {p['title'][:24]}" for p in projs]
                self.target_project_menu.configure(values=vals)
                self.target_project_menu.set(vals[0])
            else:
                self.target_project_menu.configure(values=["[No Projects]"])
                self.target_project_menu.set("[No Projects]")
        except Exception:
            pass

    def _on_inject_xyz_bullet(self):
        sel_proj = self.target_project_menu.get()
        if not sel_proj or "[" not in sel_proj or "]" not in sel_proj:
            messagebox.showwarning("Inject Bullet", "No valid project selected. Add or select a project first.")
            return
        try:
            idx = int(sel_proj.split("[")[1].split("]")[0])
        except Exception:
            messagebox.showwarning("Inject Bullet", "Could not determine project index.")
            return

        raw_bullets = self.xyz_output.get("1.0", tk.END).strip()
        if not raw_bullets or "Synthesizing" in raw_bullets:
            messagebox.showwarning("Inject Bullet", "No synthesized bullets available. Click '✨ Synthesize Bullets' first.")
            return

        # Extract first bullet
        lines = [line.strip().lstrip("•").strip() for line in raw_bullets.split("\n") if line.strip() and not line.startswith("//")]
        if not lines:
            messagebox.showwarning("Inject Bullet", "No bullet points found in output.")
            return

        chosen_bullet = lines[0]
        append_bullet_to_project(idx, chosen_bullet)
        messagebox.showinfo("Bullet Injected", f"Successfully injected bullet into project #{idx}:\n\n\"{chosen_bullet}\"")
        self.refresh_all_data()

    def _on_add_experience_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Add Professional Experience")
        modal.geometry("420x360")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="ADD WORK EXPERIENCE", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

        r_ent = ctk.CTkEntry(modal, placeholder_text="Role (e.g. Software Engineering Intern)", width=360, height=30)
        r_ent.pack(pady=4)

        c_ent = ctk.CTkEntry(modal, placeholder_text="Company (e.g. Google, Amazon, Startup)", width=360, height=30)
        c_ent.pack(pady=4)

        d_ent = ctk.CTkEntry(modal, placeholder_text="Duration (e.g. May 2025 - Aug 2025)", width=360, height=30)
        d_ent.pack(pady=4)

        b_ent = ctk.CTkEntry(modal, placeholder_text="Accomplishment Bullet...", width=360, height=45)
        b_ent.pack(pady=4)

        def _save():
            r = r_ent.get().strip()
            c = c_ent.get().strip()
            d = d_ent.get().strip()
            b = b_ent.get().strip()
            if not r or not c:
                return
            add_resume_experience(r, c, d, [b] if b else [])
            modal.destroy()
            messagebox.showinfo("Experience Added", f"Added experience at '{c}' to resume profile.")
            self.refresh_all_data()

        ctk.CTkButton(modal, text="Save Experience", command=_save, fg_color="#0f766e", width=360, height=32).pack(pady=14)

    def _on_delete_selected_project(self):
        sel_proj = self.target_project_menu.get()
        if not sel_proj or "[" not in sel_proj or "]" not in sel_proj:
            return
        try:
            idx = int(sel_proj.split("[")[1].split("]")[0])
            if messagebox.askyesno("Delete Project", f"Delete project #{idx} from your profile?"):
                delete_resume_project(idx)
                self._refresh_project_dropdown()
                self.refresh_all_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def _on_view_full_resume_modal(self):
        p = get_resume_profile()
        modal = ctk.CTkToplevel(self)
        modal.title(f"Resume Profile: {p.get('full_name', 'Candidate')}")
        modal.geometry("560x520")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text=f"PROFILE SUMMARY // {p.get('full_name', 'CANDIDATE').upper()}", font=("Consolas", 11, "bold"), text_color="#00d2ff").pack(pady=10)

        t_view = scrolledtext.ScrolledText(modal, font=("Segoe UI", 9), bg="#0e1422", fg="#e2e8f0", relief="flat", bd=0, padx=12, pady=10)
        t_view.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        t_view.insert(tk.END, f"NAME: {p.get('full_name', '')}\n")
        t_view.insert(tk.END, f"EMAIL: {p.get('email', '')} | PHONE: {p.get('phone', '')}\n")
        t_view.insert(tk.END, f"GITHUB: {p.get('github', '')} | LINKEDIN: {p.get('linkedin', '')}\n\n")

        t_view.insert(tk.END, "=== TECHNICAL SKILLS ===\n")
        t_view.insert(tk.END, ", ".join(p.get("skills", [])) + "\n\n")

        t_view.insert(tk.END, "=== EXPERIENCE ===\n")
        for exp in p.get("experience", []):
            t_view.insert(tk.END, f"• {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('duration', '')})\n")
            for b in exp.get("bullets", []):
                t_view.insert(tk.END, f"   - {b}\n")
        t_view.insert(tk.END, "\n")

        t_view.insert(tk.END, "=== PROJECTS ===\n")
        for proj in p.get("projects", []):
            t_view.insert(tk.END, f"• {proj.get('title', '')} | Tech: {proj.get('tech', '')}\n")
            for b in proj.get("bullets", []):
                t_view.insert(tk.END, f"   - {b}\n")
        t_view.insert(tk.END, "\n")

        t_view.insert(tk.END, "=== EDUCATION ===\n")
        for edu in p.get("education", []):
            t_view.insert(tk.END, f"• {edu.get('degree', '')} - {edu.get('institution', '')} ({edu.get('year', '')}) [{edu.get('score', '')}]\n")

        t_view.configure(state=tk.DISABLED)


    def _on_sync_resume_skills(self):
        added, all_skills = sync_skills_from_database()
        self.res_skills.delete(0, tk.END)
        self.res_skills.insert(0, ", ".join(all_skills))
        messagebox.showinfo("Skills Synced", f"Synchronized {len(added)} completed topics into your resume profile.")

    def _on_optimize_bullets(self):
        raw = self.xyz_input.get().strip()
        if not raw:
            return
        self.xyz_output.delete("1.0", tk.END)
        self.xyz_output.insert(tk.END, "Synthesizing XYZ impact bullet points...")
        self._anim_mode = "thinking"

        def _run():
            bullets = optimize_bullet_points(raw)
            self.after(0, lambda: self._on_bullets_done(bullets))

        threading.Thread(target=_run, daemon=True).start()

    def _on_bullets_done(self, bullets):
        self._anim_mode = "idle"
        self.xyz_output.delete("1.0", tk.END)
        for b in bullets:
            self.xyz_output.insert(tk.END, f"• {b}\n\n")

    def _on_export_resume_html(self):
        tmpl = self.template_menu.get()
        p = get_resume_profile()
        p["full_name"] = self.res_name.get().strip()
        p["email"] = self.res_email.get().strip()
        p["skills"] = [s.strip() for s in self.res_skills.get().split(",") if s.strip()]
        save_resume_profile(p)
        out_file = export_resume_html(f"resume_{tmpl}.html", template=tmpl, custom_profile=p)
        messagebox.showinfo("Resume Exported", f"Exported {tmpl.title()} resume to:\n{out_file}\nOpening in browser...")
        webbrowser.open(f"file:///{out_file}")

    def _on_analyze_jd(self):
        jd = self.jd_text.get("1.0", tk.END).strip()
        if not jd or len(jd) < 20:
            return
        self.jd_results_text.configure(state=tk.NORMAL)
        self.jd_results_text.delete("1.0", tk.END)
        self.jd_results_text.insert(tk.END, "Matching resume against JD requirements...")
        self.jd_results_text.configure(state=tk.DISABLED)
        self._anim_mode = "thinking"

        def _run():
            res = analyze_job_description(jd)
            self.after(0, lambda: self._on_jd_done(res))

        threading.Thread(target=_run, daemon=True).start()

    def _on_jd_done(self, res):
        self._anim_mode = "idle"
        score = res.get("match_score", 65)
        self.jd_score_lbl.configure(text=f"ATS MATCH: {score}%")
        self.current_jd_missing = res.get("missing_skills", [])
        if self.current_jd_missing:
            self.sync_gaps_btn.configure(state=tk.NORMAL)

        self.jd_results_text.configure(state=tk.NORMAL)
        self.jd_results_text.delete("1.0", tk.END)
        self.jd_results_text.insert(tk.END, f"🎯 ATS SCORE: {score}%\n\n")
        self.jd_results_text.insert(tk.END, f"✓ MATCHING SKILLS:\n{', '.join(res.get('matching_skills', []))}\n\n")
        self.jd_results_text.insert(tk.END, f"⚠️ MISSING CRITICAL SKILLS:\n{', '.join(self.current_jd_missing)}\n\n")
        self.jd_results_text.insert(tk.END, f"💡 STRATEGIC ADVICE:\n{res.get('recommendations', '')}\n")
        self.jd_results_text.configure(state=tk.DISABLED)

    def _on_sync_jd_gaps_to_study(self):
        if hasattr(self, "current_jd_missing") and self.current_jd_missing:
            added = add_missing_skills_to_study(self.current_jd_missing)
            messagebox.showinfo("Synced", f"Added {added} missing topics to study tracker under 'Placement Preparation'.")
            self.refresh_all_data()

    # --------------------------------------------------
    # TAB 6: Placements Kanban Board & Question Vault
    # --------------------------------------------------
    def _build_tab_kanban(self):
        parent = self.tab_kanban

        top_r = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        top_r.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(top_r, text="PLACEMENT PIPELINE KANBAN", font=("Consolas", 10, "bold"), text_color="#38bdf8").pack(side=tk.LEFT, padx=10, pady=6)

        self.kanban_search_entry = ctk.CTkEntry(top_r, placeholder_text="🔍 Filter by company...", height=28, width=170)
        self.kanban_search_entry.pack(side=tk.LEFT, padx=6)
        self.kanban_search_entry.bind("<KeyRelease>", lambda e: self._load_kanban_board())

        self.offer_badge = ctk.CTkLabel(top_r, text="", font=("Segoe UI", 9, "bold"), fg_color="#064e3b", text_color="#34d399", corner_radius=6, padx=8, pady=2)


        add_app_btn = ctk.CTkButton(
            top_r,
            text="➕ Add Application",
            command=self._on_open_add_application_modal,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 9, "bold"),
            height=28,
            cursor="hand2",
        )
        add_app_btn.pack(side=tk.RIGHT, padx=6)

        tailor_btn = ctk.CTkButton(
            top_r,
            text="🎯 Tailor Resume",
            command=self._on_tailor_resume_modal,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 9, "bold"),
            height=28,
            cursor="hand2",
        )
        tailor_btn.pack(side=tk.RIGHT, padx=4)

        cheat_btn = ctk.CTkButton(
            top_r,
            text="📑 Cheat Sheet",
            command=self._on_generate_cheat_sheet,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 9, "bold"),
            height=28,
            cursor="hand2",
        )
        cheat_btn.pack(side=tk.RIGHT, padx=4)

        # Kanban Board Frame (4 Active Columns)
        self.kanban_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.kanban_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.kanban_cols = ["Applied", "OA (Online Assessment)", "Technical Interview", "Offer Received"]
        self.kanban_trees = {}

        for col_name in self.kanban_cols:
            col_color = "#10b981" if col_name == "Offer Received" else "#00d2ff"
            col_frame = ctk.CTkFrame(self.kanban_container, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
            col_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)

            col_title = ctk.CTkLabel(col_frame, text=col_name.upper(), font=("Consolas", 9, "bold"), text_color=col_color)
            col_title.pack(anchor="w", padx=8, pady=(6, 2))

            tree = ttk.Treeview(col_frame, columns=("ID", "Company", "Role"), show="headings", height=8)
            tree.heading("ID", text="#")
            tree.heading("Company", text="Company")
            tree.heading("Role", text="Role")
            tree.column("ID", width=30, anchor="center")
            tree.column("Company", width=100, anchor="w")
            tree.column("Role", width=95, anchor="w")
            tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
            self.kanban_trees[col_name] = tree

            # Promotion Buttons
            b_frame = ctk.CTkFrame(col_frame, fg_color="transparent")
            b_frame.pack(fill=tk.X, padx=4, pady=4)

            dem_btn = ctk.CTkButton(
                b_frame,
                text="⬅",
                command=lambda t=tree: self._on_demote_card(t),
                fg_color="#1e293b",
                hover_color="#334155",
                font=("Segoe UI", 9, "bold"),
                width=35,
                height=22,
            )
            dem_btn.pack(side=tk.LEFT)

            prom_btn = ctk.CTkButton(
                b_frame,
                text="➔ Promote",
                command=lambda t=tree: self._on_promote_card(t),
                fg_color="#0284c7",
                hover_color="#0369a1",
                font=("Segoe UI", 8, "bold"),
                height=22,
            )
            prom_btn.pack(side=tk.RIGHT)

        # Bottom: Company Question Vault
        v_box = ctk.CTkFrame(parent, fg_color="#0e1422", height=130, corner_radius=6, border_width=1, border_color="#1e293b")
        v_box.pack(fill=tk.X, padx=6, pady=(2, 4))
        v_box.pack_propagate(False)

        v_hdr = ctk.CTkFrame(v_box, fg_color="transparent")
        v_hdr.pack(fill=tk.X, padx=8, pady=4)

        ctk.CTkLabel(v_hdr, text="COMPANY QUESTION VAULT (Past Round Archive):", font=("Consolas", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)

        add_q_btn = ctk.CTkButton(
            v_hdr,
            text="➕ Log Question",
            command=self._on_add_company_question_modal,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 8, "bold"),
            height=22,
        )
        add_q_btn.pack(side=tk.RIGHT)

        self.vault_tree = ttk.Treeview(v_box, columns=("ID", "Company", "Round", "Question", "Difficulty"), show="headings", height=3)
        self.vault_tree.heading("ID", text="#")
        self.vault_tree.heading("Company", text="Company")
        self.vault_tree.heading("Round", text="Round")
        self.vault_tree.heading("Question", text="Question / Challenge Asked")
        self.vault_tree.heading("Difficulty", text="Level")
        self.vault_tree.column("ID", width=30, anchor="center")
        self.vault_tree.column("Company", width=120, anchor="w")
        self.vault_tree.column("Round", width=100, anchor="center")
        self.vault_tree.column("Question", width=550, anchor="w")
        self.vault_tree.column("Difficulty", width=80, anchor="center")
        self.vault_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

    def _load_kanban_board(self):
        flt = getattr(self, "kanban_search_entry", None)
        query = flt.get().strip() if flt else None
        kdata = get_kanban_data(company_filter=query)

        offers = kdata.get("Offer Received", [])
        if offers and hasattr(self, "offer_badge"):
            self.offer_badge.configure(text=f"🎉 {len(offers)} OFFER{'S' if len(offers) > 1 else ''} ACTIVE!")
            self.offer_badge.pack(side=tk.LEFT, padx=8)
        elif hasattr(self, "offer_badge"):
            self.offer_badge.pack_forget()

        for col_name, tree in self.kanban_trees.items():
            for item in tree.get_children():
                tree.delete(item)
            apps = kdata.get(col_name, [])
            for a in apps:
                comp_display = f"⭐ {a['company']}" if col_name == "Offer Received" else a["company"]
                tree.insert("", tk.END, values=(a["id"], comp_display, a["role"]))


        # Load question vault
        for item in self.vault_tree.get_children():
            self.vault_tree.delete(item)
        for q in get_company_questions(company=query):
            self.vault_tree.insert("", tk.END, values=(q["id"], q["company"], q["round_type"], q["question_text"], q["difficulty"]))

    def _on_promote_card(self, tree):
        sel = tree.selection()
        if not sel:
            return
        app_id = tree.item(sel[0])["values"][0]
        nxt = promote_application(app_id)
        if nxt == "Offer Received":
            messagebox.showinfo("🎉 CONGRATULATIONS!", f"Application #{app_id} advanced to OFFER RECEIVED! Exceptional achievement.")
        self.refresh_all_data()

    def _on_demote_card(self, tree):
        sel = tree.selection()
        if not sel:
            return
        app_id = tree.item(sel[0])["values"][0]
        demote_application(app_id)
        self.refresh_all_data()

    def _on_add_company_question_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Log Company Interview Question")
        modal.geometry("420x360")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="LOG COMPANY INTERVIEW QUESTION", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

        c_ent = ctk.CTkEntry(modal, placeholder_text="Company Name (e.g. Amazon, Google)", width=360, height=30)
        c_ent.pack(pady=4)

        r_ent = ctk.CTkEntry(modal, placeholder_text="Round (e.g. OA, Tech Round 1, System Design)", width=360, height=30)
        r_ent.pack(pady=4)

        q_ent = ctk.CTkEntry(modal, placeholder_text="Question or Problem statement...", width=360, height=30)
        q_ent.pack(pady=4)

        def _save():
            c = c_ent.get().strip()
            r = r_ent.get().strip()
            q = q_ent.get().strip()
            if not c or not q:
                return
            add_company_question(c, "SDE", r or "Technical", q)
            modal.destroy()
            self.refresh_all_data()

        ctk.CTkButton(modal, text="Save to Vault", command=_save, fg_color="#0284c7", width=360, height=32).pack(pady=16)

    def _on_tailor_resume_modal(self):
        apps = get_applications()
        if not apps:
            messagebox.showinfo("Tailor Resume", "No placement applications found to tailor for.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title("1-Click AI Resume Tailoring")
        modal.geometry("420x280")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="1-CLICK AI RESUME TAILORING", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=12)

        options = [f"#{a['id']}: {a['company']} ({a['role']})" for a in apps]
        menu = ctk.CTkOptionMenu(modal, values=options, width=360, height=32, fg_color="#1e293b", button_color="#0284c7")
        menu.pack(pady=8)

        def _tailor():
            sel_text = menu.get()
            app_id = int(sel_text.split(":")[0].replace("#", "").strip())
            app = next(a for a in apps if a["id"] == app_id)
            modal.destroy()
            self.status_lbl.configure(text=f"Tailoring resume for {app['company']}...")
            self._anim_mode = "thinking"

            def _run():
                t_prof = tailor_resume_for_application(app["company"], app["role"], app["notes"])
                out_file = export_resume_html(f"resume_{app['company'].lower()}.html", template="stark", custom_profile=t_prof)
                self.after(0, lambda: self._on_tailor_done(app["company"], out_file))

            threading.Thread(target=_run, daemon=True).start()

        ctk.CTkButton(modal, text="⚡ Tailor & Export HTML Resume", command=_tailor, fg_color="#0f766e", width=360, height=34, font=("Segoe UI", 9, "bold")).pack(pady=16)

    def _on_tailor_done(self, company, out_file):
        self._anim_mode = "idle"
        self.status_lbl.configure(text="● Systems Nominal")
        messagebox.showinfo("Resume Tailored", f"Tailored resume for {company} generated successfully:\n{out_file}\nOpening in browser...")
        webbrowser.open(f"file:///{out_file}")

    def _on_generate_cheat_sheet(self):
        apps = get_applications()
        comp_set = set(a["company"] for a in apps if a.get("company"))
        vault_qs = get_company_questions()
        for q in vault_qs:
            if q.get("company"):
                comp_set.add(q["company"])

        if not comp_set:
            comp_set = {"Amazon", "Google", "Microsoft", "TCS", "Infosys"}

        modal = ctk.CTkToplevel(self)
        modal.title("Generate 1-Click Company Cheat Sheet")
        modal.geometry("440x260")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="COMPANY INTERVIEW CHEAT SHEET", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=12)
        ctk.CTkLabel(modal, text="Generates a high-density, printable Stark Executive brief\nwith past questions, core CS essentials, Big-O tables, & pitch.", font=("Segoe UI", 9), text_color="#94a3b8", justify="center").pack(pady=(0, 10))

        comp_list = sorted(list(comp_set))
        comp_menu = ctk.CTkOptionMenu(modal, values=comp_list, width=320, height=32, fg_color="#1e293b", button_color="#0f766e")
        comp_menu.pack(pady=6)

        def _generate():
            target_company = comp_menu.get().strip()
            modal.destroy()
            self.status_lbl.configure(text=f"Generating Cheat Sheet for {target_company}...")
            self._anim_mode = "thinking"

            def _run():
                try:
                    out_path = generate_company_cheat_sheet(target_company)
                    self.after(0, lambda: self._on_cheat_sheet_done(target_company, out_path))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Cheat Sheet Error", str(e)))
                    self.after(0, lambda: setattr(self, "_anim_mode", "idle"))

            threading.Thread(target=_run, daemon=True).start()

        ctk.CTkButton(modal, text="⚡ Generate Executive HTML Brief", command=_generate, fg_color="#0f766e", hover_color="#115e59", width=320, height=34, font=("Segoe UI", 9, "bold")).pack(pady=14)

    def _on_cheat_sheet_done(self, company, out_path):
        self._anim_mode = "idle"
        self.status_lbl.configure(text="● Systems Nominal")
        messagebox.showinfo("Cheat Sheet Ready", f"Interview Day Cheat-Sheet for {company} created successfully:\n{out_path}\nOpening in your browser...")
        webbrowser.open(f"file:///{out_path}")

    # --------------------------------------------------
    # TAB 7: Study Tracker & Syllabus
    # --------------------------------------------------
    def _build_tab_study(self):
        parent = self.tab_study

        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        l_col = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(l_col, weight=1)

        t_hdr = ctk.CTkFrame(l_col, fg_color="transparent")
        t_hdr.pack(fill=tk.X, padx=8, pady=(6, 2))

        ctk.CTkLabel(t_hdr, text="📁 SUBJECTS & TOPICS", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)

        add_top_btn = ctk.CTkButton(
            t_hdr,
            text="➕ Add Topic",
            command=self._on_add_topic_modal,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 8, "bold"),
            height=22,
            width=70,
        )
        add_top_btn.pack(side=tk.RIGHT, padx=2)

        upload_btn = ctk.CTkButton(
            t_hdr,
            text="📄 Upload",
            command=self._on_upload_syllabus,
            fg_color="#0f766e",
            hover_color="#115e59",
            font=("Segoe UI", 8, "bold"),
            height=22,
            width=65,
            cursor="hand2",
        )
        upload_btn.pack(side=tk.RIGHT, padx=2)

        self.topic_filter_entry = ctk.CTkEntry(l_col, placeholder_text="🔍 Filter topics...", height=24)
        self.topic_filter_entry.pack(fill=tk.X, padx=8, pady=2)
        self.topic_filter_entry.bind("<KeyRelease>", lambda e: self._load_subjects_and_topics())

        tree_s = ttk.Scrollbar(l_col)
        tree_s.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)

        self.subject_tree = ttk.Treeview(l_col, columns=("Status", "LastTouched"), yscrollcommand=tree_s.set)
        tree_s.config(command=self.subject_tree.yview)

        self.subject_tree.heading("#0", text="Topic Name", anchor="w")
        self.subject_tree.heading("Status", text="Status", anchor="center")
        self.subject_tree.heading("LastTouched", text="Last Touched", anchor="w")
        self.subject_tree.column("#0", width=200, anchor="w")
        self.subject_tree.column("Status", width=85, anchor="center")
        self.subject_tree.column("LastTouched", width=110, anchor="w")

        self.subject_tree.tag_configure("done", foreground="#10b981")
        self.subject_tree.tag_configure("in_progress", foreground="#38bdf8")
        self.subject_tree.tag_configure("not_started", foreground="#94a3b8")
        self.subject_tree.tag_configure("subject_head", font=("Segoe UI", 9, "bold"), foreground="#00d2ff")

        self.subject_tree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 4))
        self.subject_tree.bind("<Double-1>", self._on_topic_tree_double_click)

        act_r = ctk.CTkFrame(l_col, fg_color="transparent")
        act_r.pack(fill=tk.X, padx=8, pady=(0, 6))

        ctk.CTkButton(act_r, text="Mark Done", command=lambda: self._set_selected_topic_status("done"), fg_color="#10b981", text_color="#022c22", font=("Segoe UI", 8, "bold"), height=22).pack(side=tk.LEFT, padx=(0, 4))
        ctk.CTkButton(act_r, text="Mark Active", command=lambda: self._set_selected_topic_status("in_progress"), fg_color="#0284c7", font=("Segoe UI", 8), height=22).pack(side=tk.LEFT)

        r_col = ctk.CTkFrame(paned, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        paned.add(r_col, weight=1)

        task_hdr = ctk.CTkFrame(r_col, fg_color="transparent")
        task_hdr.pack(fill=tk.X, padx=8, pady=(6, 2))

        ctk.CTkLabel(task_hdr, text="📋 ACTION ITEMS & DELIVERABLES", font=("Segoe UI", 9, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)

        add_task_btn = ctk.CTkButton(
            task_hdr,
            text="➕ Add Task",
            command=self._on_add_task_modal,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=("Segoe UI", 8, "bold"),
            height=22,
            width=70,
            cursor="hand2",
        )
        add_task_btn.pack(side=tk.RIGHT)

        t_scroll = ttk.Scrollbar(r_col)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)

        self.task_tree = ttk.Treeview(r_col, columns=("ID", "TaskName", "Category", "Status"), yscrollcommand=t_scroll.set, show="headings", height=7)
        t_scroll.config(command=self.task_tree.yview)

        self.task_tree.heading("ID", text="#")
        self.task_tree.heading("TaskName", text="Task Deliverable")
        self.task_tree.heading("Category", text="Category")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.column("ID", width=30, anchor="center")
        self.task_tree.column("TaskName", width=190, anchor="w")
        self.task_tree.column("Category", width=80, anchor="center")
        self.task_tree.column("Status", width=80, anchor="center")
        self.task_tree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 4))
        self.task_tree.bind("<Double-1>", self._on_task_tree_double_click)

        ctk.CTkLabel(r_col, text="⚠️ STALE ITEMS (Untouched 3+ Days):", font=("Segoe UI", 8, "bold"), text_color="#f59e0b").pack(anchor="w", padx=8, pady=(2, 0))

        self.stale_text = scrolledtext.ScrolledText(r_col, height=4, font=("Consolas", 8), bg="#080c14", fg="#cbd5e1", relief="flat", bd=0, padx=6, pady=2)
        self.stale_text.pack(fill=tk.X, padx=8, pady=(2, 6))

    def _on_add_topic_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Add Study Topic")
        modal.geometry("380x260")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="ADD STUDY TOPIC", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

        s_ent = ctk.CTkEntry(modal, placeholder_text="Subject (e.g. Operating Systems, DSA)", width=320, height=30)
        s_ent.pack(pady=4)

        t_ent = ctk.CTkEntry(modal, placeholder_text="Topic Name (e.g. Semaphore vs Mutex)", width=320, height=30)
        t_ent.pack(pady=4)

        def _save():
            s = s_ent.get().strip() or "General"
            t = t_ent.get().strip()
            if not t:
                return
            subj_id = get_or_create_subject(s)
            insert_topic(subj_id, t, "not_started")
            modal.destroy()
            self.refresh_all_data()

        ctk.CTkButton(modal, text="Save Topic", command=_save, fg_color="#0284c7", width=320, height=32).pack(pady=14)

    def _on_add_task_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Add Action Item / Task")
        modal.geometry("380x290")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="ADD ACTION ITEM", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

        n_ent = ctk.CTkEntry(modal, placeholder_text="Task deliverable (e.g. Complete Dynamic Programming module)", width=320, height=30)
        n_ent.pack(pady=4)

        cat_menu = ctk.CTkOptionMenu(modal, values=["DSA", "Placement", "Core CS", "System Design", "Projects", "General"], width=320, height=30, fg_color="#1e293b", button_color="#0284c7")
        cat_menu.pack(pady=4)

        def _save():
            name = n_ent.get().strip()
            cat = cat_menu.get().strip()
            if not name:
                return
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO tasks (task_name, category, status) VALUES (?, ?, 'pending')", (name, cat))
            conn.commit()
            conn.close()
            modal.destroy()
            self.refresh_all_data()

        ctk.CTkButton(modal, text="Save Task", command=_save, fg_color="#0284c7", width=320, height=32).pack(pady=14)

    def _on_topic_tree_double_click(self, event):
        item_id = self.subject_tree.focus()
        if not item_id:
            return
        tags = self.subject_tree.item(item_id, "tags")
        if not tags or tags[0] == "subject_head":
            return
        try:
            t_id = int(tags[0])
            curr_status = tags[1] if len(tags) > 1 else "not_started"
            # Cycle: not_started -> in_progress -> done -> not_started
            next_status = "in_progress" if curr_status == "not_started" else ("done" if curr_status == "in_progress" else "not_started")
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE topics SET status = ?, last_touched_date = CURRENT_TIMESTAMP WHERE id = ?", (next_status, t_id))
            conn.commit()
            conn.close()
            self.refresh_all_data()
        except Exception:
            pass

    def _on_task_tree_double_click(self, event):
        item_id = self.task_tree.focus()
        if not item_id:
            return
        vals = self.task_tree.item(item_id, "values")
        if not vals:
            return
        try:
            t_id = vals[0]
            curr_status_disp = str(vals[3])
            next_status = "in_progress" if "Pending" in curr_status_disp else ("done" if "Active" in curr_status_disp else "pending")
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE tasks SET status = ? WHERE id = ?", (next_status, t_id))
            conn.commit()
            conn.close()
            self.refresh_all_data()
        except Exception:
            pass

    # --------------------------------------------------
    # TAB 8: Alarms & Reminders
    # --------------------------------------------------
    def _build_tab_reminders(self):
        parent = self.tab_reminders

        add_box = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        add_box.pack(fill=tk.X, padx=6, pady=4)

        ctk.CTkLabel(add_box, text="SCHEDULE NEW ALARM / REMINDER:", font=("Consolas", 9, "bold"), text_color="#38bdf8").pack(anchor="w", padx=10, pady=(6, 2))

        in_r = ctk.CTkFrame(add_box, fg_color="transparent")
        in_r.pack(fill=tk.X, padx=10, pady=(2, 6))

        self.alarm_input = ctk.CTkEntry(in_r, placeholder_text="e.g. in 45 minutes to submit resume, or tomorrow at 10 AM for Google OA...", height=30)
        self.alarm_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.alarm_input.bind("<Return>", lambda e: self._on_schedule_alarm())

        ctk.CTkButton(in_r, text="⏰ Schedule", command=self._on_schedule_alarm, fg_color="#0284c7", width=80, height=30).pack(side=tk.RIGHT)
        ctk.CTkButton(in_r, text="🔔 Test Toast", command=lambda: send_windows_toast("JARVIS Alert", "Test notification confirmed."), fg_color="#1e293b", width=75, height=30).pack(side=tk.RIGHT, padx=4)

        t_box = ctk.CTkFrame(parent, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        t_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        t_hdr = ctk.CTkFrame(t_box, fg_color="transparent")
        t_hdr.pack(fill=tk.X, padx=10, pady=(6, 2))

        ctk.CTkLabel(t_hdr, text="ACTIVE SCHEDULED ALARMS:", font=("Segoe UI", 9, "bold"), text_color="#94a3b8").pack(side=tk.LEFT)
        ctk.CTkButton(t_hdr, text="Dismiss Selected", command=self._on_dismiss_alarm, fg_color="#334155", height=22).pack(side=tk.RIGHT)

        self.rem_tree = ttk.Treeview(t_box, columns=("ID", "Time", "Message", "Status"), show="headings")
        self.rem_tree.heading("ID", text="#")
        self.rem_tree.heading("Time", text="Scheduled Time")
        self.rem_tree.heading("Message", text="Reminder Alert")
        self.rem_tree.heading("Status", text="Status")
        self.rem_tree.column("ID", width=35, anchor="center")
        self.rem_tree.column("Time", width=140, anchor="w")
        self.rem_tree.column("Message", width=450, anchor="w")
        self.rem_tree.column("Status", width=90, anchor="center")
        self.rem_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

    # --------------------------------------------------
    # Data Refresh & Telemetry Loop
    # --------------------------------------------------
    def _start_telemetry_loop(self):
        def _update():
            t = get_system_telemetry()
            self.cpu_badge.configure(text=f"CPU: {t['cpu_percent']}%")
            self.ram_badge.configure(text=f"RAM: {t['ram_percent']}%")
            self.after(3000, _update)
        self.after(2000, _update)

    def refresh_all_data(self):
        metrics = get_readiness_metrics()
        active_alarms = get_active_reminders()

        self.streak_badge.configure(text=f"🔥 {metrics['study_streak']}d")
        self.readiness_badge.configure(text=f"🎯 {metrics['overall']}%")
        self.alarm_badge.configure(text=f"⏰ {len(active_alarms)}")

        self._load_subjects_and_topics()
        self._load_tasks()
        self._load_stale_dashboard()
        self._load_kanban_board()
        self._load_reminders_table()
        self._load_resume_profile_into_ui()
        self._load_dsa_problems()

    def _load_subjects_and_topics(self):
        for item in self.subject_tree.get_children():
            self.subject_tree.delete(item)

        filter_q = getattr(self, "topic_filter_entry", None)
        query = filter_q.get().strip().lower() if filter_q else ""

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM subjects ORDER BY id")
        subjects = cur.fetchall()

        for subj_id, subj_name in subjects:
            cur.execute("SELECT id, topic_name, status, last_touched_date FROM topics WHERE subject_id = ? ORDER BY id", (subj_id,))
            topics = cur.fetchall()
            if not topics:
                continue

            done_count = sum(1 for _, _, st, _ in topics if st == "done")
            total_count = len(topics)
            pct = int((done_count / total_count) * 100) if total_count else 0
            header_text = f"📁 {subj_name}  [{done_count}/{total_count} Done — {pct}%]"

            filtered_topics = [t for t in topics if not query or query in t[1].lower() or query in subj_name.lower()]
            if query and not filtered_topics:
                continue

            subj_node = self.subject_tree.insert("", tk.END, text=header_text, open=True, tags=("subject_head",))
            for t_id, t_name, status, last_touched in filtered_topics:
                status_icon = "● Done" if status == "done" else ("◐ Active" if status == "in_progress" else "○ Pending")
                self.subject_tree.insert(subj_node, tk.END, text=f"  • {t_name}", values=(status_icon, last_touched[:16]), tags=(str(t_id), status))

        conn.close()

    def _load_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, task_name, category, status FROM tasks ORDER BY id DESC")
        for row in cur.fetchall():
            t_id, name, cat, status = row
            status_disp = "● Done" if status == "done" else ("◐ Active" if status == "in_progress" else "○ Pending")
            self.task_tree.insert("", tk.END, values=(t_id, name, cat, status_disp), tags=(status,))
        conn.close()

    def _load_stale_dashboard(self):
        stale_topics = get_stale_topics(days=3)
        stale_tasks = get_stale_tasks(days=3)
        self.stale_text.configure(state=tk.NORMAL)
        self.stale_text.delete("1.0", tk.END)
        if not stale_topics and not stale_tasks:
            self.stale_text.insert(tk.END, "✓ All topics and tasks are fresh.\n")
        else:
            if stale_topics:
                for subj, topic, _, last_touched in stale_topics[:4]:
                    self.stale_text.insert(tk.END, f"• {topic} ({subj}) — {days_old(last_touched)}d stale\n")
            if stale_tasks:
                for name, cat, _, created, _ in stale_tasks[:3]:
                    self.stale_text.insert(tk.END, f"• {name} [{cat}] — {days_old(created)}d pending\n")
        self.stale_text.configure(state=tk.DISABLED)

    def _load_reminders_table(self):
        for item in self.rem_tree.get_children():
            self.rem_tree.delete(item)
        for r in get_active_reminders():
            r_id, msg, r_time, status, _, _ = r
            self.rem_tree.insert("", tk.END, values=(r_id, r_time, msg, status))

    def _load_resume_profile_into_ui(self):
        try:
            p = get_resume_profile()
            self.res_name.delete(0, tk.END)
            self.res_name.insert(0, p.get("full_name", ""))
            self.res_email.delete(0, tk.END)
            self.res_email.insert(0, p.get("email", ""))
            self.res_skills.delete(0, tk.END)
            self.res_skills.insert(0, ", ".join(p.get("skills", [])))
            self._refresh_project_dropdown()
        except Exception:
            pass

    # --------------------------------------------------
    # Arc Reactor & Waveform Animation
    # --------------------------------------------------
    def _start_hud_animation(self):
        def _tick():
            self._draw_hud_waveform()
            self.after(50, _tick)
        self.after(100, _tick)

    def _draw_hud_waveform(self):
        canvas = self.hud_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50 or h < 30:
            return

        canvas.delete("all")
        self._anim_angle = (self._anim_angle + 6) % 360
        cx = 50
        cy = h // 2

        r = 20
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#164e63", width=2)
        core_color = "#00d2ff" if self._anim_mode != "listening" else "#f59e0b"
        pulse_r = 10 + math.sin(math.radians(self._anim_angle * 2)) * 3
        canvas.create_oval(cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r, fill=core_color, outline="#ffffff", width=1)

        start_x = 95
        end_x = w - 20
        wave_w = max(40, end_x - start_x)
        num_bars = 42
        step = wave_w / num_bars
        amp = 2.4 if self._anim_mode == "listening" else (2.0 if self._anim_mode in ("speaking", "thinking") else 1.0)

        for i in range(num_bars):
            bx = start_x + (i * step)
            phase = math.sin(math.radians(self._anim_angle * 3 + (i * 12)))
            bar_h = (abs(phase) * 14 * amp) + 3
            color = "#f59e0b" if self._anim_mode == "listening" else ("#00d2ff" if i % 2 == 0 else "#38bdf8")
            canvas.create_line(bx, cy - bar_h / 2, bx, cy + bar_h / 2, fill=color, width=2)

        canvas.create_text(w - 20, cy, text=f"// {self._anim_mode.upper()}", font=("Consolas", 8, "bold"), fill="#64748b", anchor="e")

    # --------------------------------------------------
    # Chat & Voice Handlers
    # --------------------------------------------------
    def _initial_greeting(self):
        g = proactive_launch_greeting(voice_enabled=False, print_output=False)
        self._append_chat(f"JARVIS: {g}")

    def _send_quick_prompt(self, text):
        self.user_entry.delete(0, tk.END)
        self.user_entry.insert(0, text)
        self._on_send_chat()

    def _on_send_chat(self):
        text = self.user_entry.get().strip()
        if not text:
            return
        self.user_entry.delete(0, tk.END)
        self._append_chat(f"You: {text}")

        self.send_btn.configure(state=tk.DISABLED)
        self.voice_btn.configure(state=tk.DISABLED)
        self._anim_mode = "thinking"

        threading.Thread(target=self._async_chat, args=(text,), daemon=True).start()

    def _async_chat(self, text):
        try:
            res = process_input(text)
            if isinstance(res, dict):
                reply = res.get("reply", "Done.")
                spoken = res.get("spoken", reply[:140])
                intent = res.get("intent", "LOG_PROGRESS")
                tab = res.get("tab")
                action = res.get("action")
            else:
                reply = str(res)
                spoken = reply[:140]
                intent = "LOG_PROGRESS"
                tab = None
                action = None
        except Exception as e:
            reply = f"Error: {e}"
            spoken = "Error encountered."
            intent = "ERROR"
            tab = None
            action = None

        self.after(0, lambda: self._on_chat_done(reply, spoken, intent, tab, action))

    def _on_chat_done(self, reply, spoken, intent, tab=None, action=None):
        self._append_chat(f"JARVIS: {reply}")
        self.send_btn.configure(state=tk.NORMAL)
        self.voice_btn.configure(state=tk.NORMAL)
        self._anim_mode = "idle"
        self.refresh_all_data()

        # Handle Tab Navigation via Voice / Chat
        if tab:
            try:
                self.tabview.set(tab)
            except Exception:
                pass
        elif intent == "MOCK_INTERVIEW":
            self.tabview.set("🎯 Mock Interview")

        # Handle Action Triggers via Voice / Chat
        if action == "FOCUS_START":
            self._on_toggle_focus_timer()
        elif action == "BATTLE_PLAN":
            self._on_open_battle_plan_modal()
        elif action == "EVENING_DEBRIEF":
            self._on_open_battle_plan_modal()
        elif action == "EXCALIDRAW":
            launch_excalidraw()
        elif action == "CHEAT_SHEET":
            self._on_generate_cheat_sheet()
        elif action == "BACKUP":
            self._on_backup_data()

        if self.tts_enabled.get() and TTS_AVAILABLE and spoken:
            self._anim_mode = "speaking"
            speak(spoken, async_mode=True)
            self.after(3500, lambda: setattr(self, "_anim_mode", "idle"))

    def _append_chat(self, msg):
        self.chat_history.configure(state=tk.NORMAL)
        if msg.startswith("JARVIS:"):
            self.chat_history.insert(tk.END, "JARVIS: ", "jarvis")
            self.chat_history.insert(tk.END, msg[7:].lstrip() + "\n\n", "body")
        elif msg.startswith("You:"):
            self.chat_history.insert(tk.END, "You: ", "user")
            self.chat_history.insert(tk.END, msg[4:].lstrip() + "\n", "body")
        else:
            self.chat_history.insert(tk.END, f"{msg}\n", "system")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _on_voice_input(self):
        if not STT_AVAILABLE:
            messagebox.showwarning("Voice", "Microphone recognition is not installed.")
            return
        play_chime()
        self.voice_btn.configure(state=tk.DISABLED)
        self._anim_mode = "listening"

        def _run():
            text, err = listen_to_microphone(timeout=8, phrase_time_limit=14)
            self.after(0, lambda: self._on_voice_done(text, err))

        threading.Thread(target=_run, daemon=True).start()

    def _on_voice_done(self, text, err):
        self.voice_btn.configure(state=tk.NORMAL)
        self._anim_mode = "idle"
        if text:
            self.user_entry.delete(0, tk.END)
            self.user_entry.insert(0, text)
            self._on_send_chat()

    def _on_toggle_wake_word(self):
        if self.wake_enabled.get():
            self.wake_stop_event = threading.Event()
            threading.Thread(target=lambda: listen_for_wake_word(stop_event=self.wake_stop_event, on_wake=lambda p: self.after(0, self._on_voice_input)), daemon=True).start()
        else:
            if self.wake_stop_event:
                self.wake_stop_event.set()

    def _on_trigger_briefing(self):
        self._anim_mode = "thinking"

        def _run():
            b = generate_morning_briefing()
            self.after(0, lambda: self._on_briefing_done(b))

        threading.Thread(target=_run, daemon=True).start()

    def _on_briefing_done(self, b):
        self._anim_mode = "idle"
        self._append_chat(f"JARVIS: {b['written']}")
        if self.tts_enabled.get() and TTS_AVAILABLE:
            speak(b["spoken"], async_mode=True)

    # --------------------------------------------------
    # Backup & Reminders & Syllabus Handlers
    # --------------------------------------------------
    def _on_backup_data(self):
        j = export_database_to_json()
        c = export_applications_to_csv()
        export_study_topics_to_csv()
        messagebox.showinfo("Backup Successful", f"Full database snapshot exported to:\n{j}\n\nApplications CSV saved to:\n{c}")

    def _on_schedule_alarm(self):
        text = self.alarm_input.get().strip()
        if not text:
            return
        dt, msg = parse_natural_time(text)
        if not dt:
            messagebox.showwarning("Alarm", "Could not parse time. Try: 'in 30 mins to study' or 'at 5 PM'")
            return
        rem_id = add_reminder(msg, dt)
        self.alarm_input.delete(0, tk.END)
        self.refresh_all_data()
        messagebox.showinfo("Alarm Scheduled", f"Reminder #{rem_id} scheduled for {dt.strftime('%I:%M %p')}: {msg}")

    def _on_dismiss_alarm(self):
        sel = self.rem_tree.selection()
        if not sel:
            return
        r_id = self.rem_tree.item(sel[0])["values"][0]
        dismiss_reminder(r_id)
        self.refresh_all_data()

    def _on_reminder_fired_event(self, rem_id, message, remind_time):
        self.after(0, lambda: self._append_chat(f"JARVIS [ALARM]: {message}"))
        self.after(0, self.refresh_all_data)

    def _set_selected_topic_status(self, status):
        sel = self.subject_tree.selection()
        if not sel:
            return
        tags = self.subject_tree.item(sel[0], "tags")
        if not tags or tags[0] == "subject_head":
            return
        t_id = int(tags[0])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE topics SET status = ?, last_touched_date = CURRENT_TIMESTAMP WHERE id = ?", (status, t_id))
        conn.commit()
        conn.close()
        self.refresh_all_data()

    def _on_upload_syllabus(self):
        fp = filedialog.askopenfilename(title="Select Syllabus", filetypes=[("Docs", "*.pdf;*.txt;*.md")])
        if not fp:
            return
        self._anim_mode = "thinking"

        def _run():
            try:
                res = process_syllabus(fp)
                self.after(0, lambda: self._on_syllabus_done(res))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to ingest: {e}"))
                self.after(0, lambda: setattr(self, "_anim_mode", "idle"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_syllabus_done(self, res):
        self._anim_mode = "idle"
        messagebox.showinfo("Syllabus Ingested", f"Added {len(res.get('topics', []))} topics for {res.get('subject')}")
        self.refresh_all_data()

    def _on_open_add_application_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Add Placement Application")
        modal.geometry("420x420")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        ctk.CTkLabel(modal, text="NEW APPLICATION", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=12)

        c_ent = ctk.CTkEntry(modal, placeholder_text="Company Name (e.g. Google, Amazon)", width=350, height=32)
        c_ent.pack(pady=4)

        r_ent = ctk.CTkEntry(modal, placeholder_text="Role (e.g. SDE-1, Software Engineer)", width=350, height=32)
        r_ent.pack(pady=4)

        stg_menu = ctk.CTkOptionMenu(modal, values=VALID_STAGES, width=350, height=32, fg_color="#1e293b", button_color="#0284c7")
        stg_menu.pack(pady=4)

        notes_ent = ctk.CTkEntry(modal, placeholder_text="Notes / OA test link / deadline...", width=350, height=32)
        notes_ent.pack(pady=4)

        def _save():
            c = c_ent.get().strip()
            r = r_ent.get().strip()
            if not c or not r:
                return
            add_application(c, r, stage=stg_menu.get(), notes=notes_ent.get().strip())
            modal.destroy()
            self.refresh_all_data()

        ctk.CTkButton(modal, text="Save Application", command=_save, fg_color="#0284c7", width=350, height=34).pack(pady=16)

    # --------------------------------------------------
    # Stark Deep Work Focus Engine
    # --------------------------------------------------
    def _on_focus_timer_tick(self, state, remaining_seconds, task_name):
        def _update():
            mins = remaining_seconds // 60
            secs = remaining_seconds % 60
            time_str = f"{mins:02d}:{secs:02d}"
            if state == "running":
                self.focus_btn.configure(
                    text=f"⏱️ {time_str} [Active]",
                    text_color="#10b981",
                    fg_color="#064e3b"
                )
            elif state == "paused":
                self.focus_btn.configure(
                    text=f"⏸️ {time_str} [Paused]",
                    text_color="#f59e0b",
                    fg_color="#78350f"
                )
            elif state == "completed":
                self.focus_btn.configure(
                    text="🎉 Complete!",
                    text_color="#38bdf8",
                    fg_color="#1e293b"
                )
            else:  # idle
                today_hrs = get_today_focus_hours()
                self.focus_btn.configure(
                    text=f"⏱️ 25:00 [{today_hrs}h]",
                    text_color="#f59e0b",
                    fg_color="#1e293b"
                )
        self.after(0, _update)

    def _on_toggle_focus_timer(self):
        engine = self.focus_engine
        if engine.state == "running":
            modal = ctk.CTkToplevel(self)
            modal.title("Focus Sprint Active")
            modal.geometry("360x220")
            modal.configure(fg_color="#080c14")
            modal.grab_set()

            ctk.CTkLabel(modal, text="SPRINT IN PROGRESS", font=("Consolas", 11, "bold"), text_color="#10b981").pack(pady=12)
            mins = engine.remaining_seconds // 60
            secs = engine.remaining_seconds % 60
            ctk.CTkLabel(modal, text=f"Target: {engine.task_name}\nTime Remaining: {mins:02d}:{secs:02d}", font=("Segoe UI", 10), text_color="#cbd5e1").pack(pady=4)

            btn_f = ctk.CTkFrame(modal, fg_color="transparent")
            btn_f.pack(pady=14)

            def _pause():
                engine.pause_session()
                modal.destroy()

            def _stop():
                engine.stop_session()
                modal.destroy()

            ctk.CTkButton(btn_f, text="⏸️ Pause", command=_pause, fg_color="#d97706", width=110, height=32, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6)
            ctk.CTkButton(btn_f, text="⏹️ Stop", command=_stop, fg_color="#ef4444", width=110, height=32, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6)

        elif engine.state == "paused":
            modal = ctk.CTkToplevel(self)
            modal.title("Focus Sprint Paused")
            modal.geometry("360x200")
            modal.configure(fg_color="#080c14")
            modal.grab_set()

            ctk.CTkLabel(modal, text="SPRINT PAUSED", font=("Consolas", 11, "bold"), text_color="#f59e0b").pack(pady=12)
            ctk.CTkLabel(modal, text=f"Target: {engine.task_name}", font=("Segoe UI", 10), text_color="#cbd5e1").pack(pady=4)

            btn_f = ctk.CTkFrame(modal, fg_color="transparent")
            btn_f.pack(pady=14)

            def _resume():
                engine.resume_session()
                modal.destroy()

            def _stop():
                engine.stop_session()
                modal.destroy()

            ctk.CTkButton(btn_f, text="▶️ Resume", command=_resume, fg_color="#10b981", width=110, height=32, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6)
            ctk.CTkButton(btn_f, text="⏹️ Stop", command=_stop, fg_color="#ef4444", width=110, height=32, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6)

        else:
            # Idle / Completed: Start new sprint
            modal = ctk.CTkToplevel(self)
            modal.title("Initiate Stark Focus Sprint")
            modal.geometry("420x300")
            modal.configure(fg_color="#080c14")
            modal.grab_set()

            ctk.CTkLabel(modal, text="INITIATE DEEP WORK SPRINT", font=("Consolas", 11, "bold"), text_color="#38bdf8").pack(pady=10)

            ctk.CTkLabel(modal, text="Sprint Focus Target:", font=("Segoe UI", 9), text_color="#94a3b8").pack(anchor="w", padx=24, pady=(4, 2))
            task_entry = ctk.CTkEntry(modal, placeholder_text="e.g. Solve Binary Search / Revise OS Paging", width=370, height=30)
            task_entry.insert(0, "DSA Coding Sprint")
            task_entry.pack(pady=4)

            # Quick presets
            preset_f = ctk.CTkFrame(modal, fg_color="transparent")
            preset_f.pack(fill=tk.X, padx=24, pady=4)
            for p in ["DSA Problem", "CS Revision", "Resume Tuning"]:
                ctk.CTkButton(
                    preset_f,
                    text=p,
                    command=lambda t=p: (task_entry.delete(0, tk.END), task_entry.insert(0, t)),
                    fg_color="#1e293b",
                    hover_color="#334155",
                    text_color="#94a3b8",
                    font=("Segoe UI", 8),
                    height=22,
                ).pack(side=tk.LEFT, padx=2)

            ctk.CTkLabel(modal, text="Duration:", font=("Segoe UI", 9), text_color="#94a3b8").pack(anchor="w", padx=24, pady=(6, 2))
            dur_menu = ctk.CTkOptionMenu(modal, values=["15 minutes", "25 minutes (Pomodoro)", "45 minutes", "60 minutes"], width=370, height=30, fg_color="#1e293b", button_color="#0284c7")
            dur_menu.set("25 minutes (Pomodoro)")
            dur_menu.pack(pady=4)

            def _start():
                task = task_entry.get().strip() or "Deep Work"
                sel_dur = dur_menu.get()
                mins = 25
                if "15" in sel_dur:
                    mins = 15
                elif "45" in sel_dur:
                    mins = 45
                elif "60" in sel_dur:
                    mins = 60
                modal.destroy()
                engine.start_session(task_name=task, duration_minutes=mins)

            ctk.CTkButton(modal, text="⚡ Start Sprint Protocol", command=_start, fg_color="#0f766e", hover_color="#115e59", width=370, height=34, font=("Segoe UI", 9, "bold")).pack(pady=12)

    # --------------------------------------------------
    # 6:00 AM Stark Battle Plan & Evening Debrief Modal
    # --------------------------------------------------
    def _on_open_battle_plan_modal(self):
        plan = generate_daily_battle_plan()
        modal = ctk.CTkToplevel(self)
        modal.title("Stark Protocol // Daily Battle Plan")
        modal.geometry("560x580")
        modal.configure(fg_color="#080c14")
        modal.grab_set()

        hdr = ctk.CTkFrame(modal, fg_color="transparent")
        hdr.pack(fill=tk.X, padx=16, pady=(12, 6))

        ctk.CTkLabel(hdr, text="⚔️ STARK PROTOCOL: BATTLE PLAN", font=("Consolas", 12, "bold"), text_color="#38bdf8").pack(side=tk.LEFT)
        score_badge = ctk.CTkLabel(
            hdr,
            text=f"EXECUTION: {plan['execution_score']}%",
            font=("Consolas", 10, "bold"),
            fg_color="#1e293b",
            text_color="#10b981" if plan["execution_score"] == 100 else "#f59e0b",
            corner_radius=4,
            padx=8,
            pady=3,
        )
        score_badge.pack(side=tk.RIGHT)

        ctk.CTkLabel(modal, text=f"Date: {plan['plan_date']} // Strict 3-Target Protocol to eliminate task paralysis.", font=("Segoe UI", 9), text_color="#64748b").pack(anchor="w", padx=16, pady=(0, 8))

        # Target 1
        t1_box = ctk.CTkFrame(modal, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        t1_box.pack(fill=tk.X, padx=16, pady=4)
        ctk.CTkLabel(t1_box, text="TARGET 1 // DSA & ALGORITHM CODING", font=("Consolas", 9, "bold"), text_color="#00d2ff").pack(anchor="w", padx=10, pady=(6, 2))

        t1_var = tk.BooleanVar(value=plan["target1"]["done"])
        def _toggle_t1():
            updated = toggle_target_done(1)
            score_badge.configure(
                text=f"EXECUTION: {updated['execution_score']}%",
                text_color="#10b981" if updated["execution_score"] == 100 else "#f59e0b",
            )
        ctk.CTkCheckBox(t1_box, text=plan["target1"]["text"], variable=t1_var, command=_toggle_t1, font=("Segoe UI", 9), fg_color="#0284c7", hover_color="#0369a1").pack(anchor="w", padx=10, pady=(2, 8))

        # Target 2
        t2_box = ctk.CTkFrame(modal, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        t2_box.pack(fill=tk.X, padx=16, pady=4)
        ctk.CTkLabel(t2_box, text="TARGET 2 // CORE CS REVISION (STALE RECOVERY)", font=("Consolas", 9, "bold"), text_color="#a855f7").pack(anchor="w", padx=10, pady=(6, 2))

        t2_var = tk.BooleanVar(value=plan["target2"]["done"])
        def _toggle_t2():
            updated = toggle_target_done(2)
            score_badge.configure(
                text=f"EXECUTION: {updated['execution_score']}%",
                text_color="#10b981" if updated["execution_score"] == 100 else "#f59e0b",
            )
        ctk.CTkCheckBox(t2_box, text=plan["target2"]["text"], variable=t2_var, command=_toggle_t2, font=("Segoe UI", 9), fg_color="#0284c7", hover_color="#0369a1").pack(anchor="w", padx=10, pady=(2, 8))

        # Target 3
        t3_box = ctk.CTkFrame(modal, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        t3_box.pack(fill=tk.X, padx=16, pady=4)
        ctk.CTkLabel(t3_box, text="TARGET 3 // LIFE / PLACEMENT DELIVERABLE", font=("Consolas", 9, "bold"), text_color="#10b981").pack(anchor="w", padx=10, pady=(6, 2))

        t3_var = tk.BooleanVar(value=plan["target3"]["done"])
        def _toggle_t3():
            updated = toggle_target_done(3)
            score_badge.configure(
                text=f"EXECUTION: {updated['execution_score']}%",
                text_color="#10b981" if updated["execution_score"] == 100 else "#f59e0b",
            )
        ctk.CTkCheckBox(t3_box, text=plan["target3"]["text"], variable=t3_var, command=_toggle_t3, font=("Segoe UI", 9), fg_color="#0284c7", hover_color="#0369a1").pack(anchor="w", padx=10, pady=(2, 8))

        # Debrief Section
        debrief_box = ctk.CTkFrame(modal, fg_color="#0e1422", corner_radius=6, border_width=1, border_color="#1e293b")
        debrief_box.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        ctk.CTkLabel(debrief_box, text="EVENING DEBRIEF & ACCOUNTABILITY:", font=("Consolas", 9, "bold"), text_color="#94a3b8").pack(anchor="w", padx=10, pady=(6, 2))

        debrief_display = scrolledtext.ScrolledText(
            debrief_box,
            height=5,
            font=("Segoe UI", 9),
            bg="#080c14",
            fg="#e2e8f0",
            wrap="word",
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
        )
        debrief_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 6))

        if plan.get("evening_debrief"):
            debrief_display.insert(tk.END, plan["evening_debrief"])
        else:
            debrief_display.insert(tk.END, "No evening debrief run yet today. Click '🌙 Run Evening Debrief' below to evaluate your execution score.")
        debrief_display.configure(state=tk.DISABLED)

        # Action Buttons
        act_f = ctk.CTkFrame(modal, fg_color="transparent")
        act_f.pack(fill=tk.X, padx=16, pady=(4, 12))

        def _run_debrief():
            debrief_btn.configure(state=tk.DISABLED)
            debrief_display.configure(state=tk.NORMAL)
            debrief_display.delete("1.0", tk.END)
            debrief_display.insert(tk.END, "JARVIS compiling daily execution telemetry and generating spoken debrief...")
            debrief_display.configure(state=tk.DISABLED)

            def _thread():
                try:
                    res = generate_evening_debrief()
                    self.after(0, lambda: self._on_battle_debrief_done(res, debrief_display, debrief_btn, score_badge))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Debrief Error", str(e)))
                    self.after(0, lambda: debrief_btn.configure(state=tk.NORMAL))

            threading.Thread(target=_thread, daemon=True).start()

        debrief_btn = ctk.CTkButton(
            act_f,
            text="🌙 Run Evening Debrief",
            command=_run_debrief,
            fg_color="#7c2d12",
            hover_color="#9a3412",
            font=("Segoe UI", 9, "bold"),
            height=30,
            cursor="hand2",
        )
        debrief_btn.pack(side=tk.LEFT, padx=4)

        close_btn = ctk.CTkButton(
            act_f,
            text="Close",
            command=modal.destroy,
            fg_color="#1e293b",
            hover_color="#334155",
            font=("Segoe UI", 9),
            height=30,
            width=80,
            cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT, padx=4)

    def _on_battle_debrief_done(self, res, display_widget, debrief_btn, score_badge):
        debrief_btn.configure(state=tk.NORMAL)
        score_badge.configure(
            text=f"EXECUTION: {res['score']}%",
            text_color="#10b981" if res["score"] == 100 else "#f59e0b",
        )
        display_widget.configure(state=tk.NORMAL)
        display_widget.delete("1.0", tk.END)
        display_widget.insert(tk.END, f"★ EXECUTION SCORE: {res['score']}%\n\n{res['written']}")
        display_widget.configure(state=tk.DISABLED)

        if self.tts_enabled.get() and TTS_AVAILABLE:
            speak(res.get("spoken", res["written"]), async_mode=True)


def main():
    app = JarvisGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
