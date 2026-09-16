"""
JARVIS-lite: Desktop GUI Dashboard (Phase 5 - Feature 3b)

Desktop GUI interface for JARVIS-lite built with Tkinter:
- Stale items dashboard (memory check)
- Hierarchical Subject -> Topic tree
- Interactive Task management list
- Natural language chat input for talking to JARVIS (multi-threaded)
- Syllabus file upload (PDF / TXT) integration
- Quick "Mark as Done" actions

All existing backend logic (assistant.py, remainder.py, database layer) is preserved untouched.
"""

import sys
import threading
import sqlite3
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from assistant import DB_PATH, get_connection, process_input
from remainder import get_stale_topics, get_stale_tasks, days_old
from syllabus_processor import process_syllabus
from placements import (
    add_application,
    update_application_stage,
    get_applications,
    delete_application,
    get_placement_summary,
    VALID_STAGES,
    VALID_RESULTS,
)

try:
    from personality import proactive_launch_greeting, get_confirmation_message
except ImportError:
    proactive_launch_greeting = lambda **k: "Good day. Ready to assist."
    get_confirmation_message = lambda d: "Updated your memory."

try:
    from voice import speak, listen_to_microphone, TTS_AVAILABLE, STT_AVAILABLE
except ImportError:
    TTS_AVAILABLE = False
    STT_AVAILABLE = False
    speak = lambda *args, **kwargs: None
    listen_to_microphone = lambda *args, **kwargs: (None, "Voice module not available")


class JarvisGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("JARVIS-lite — AI Study & Life Assistant")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.tts_enabled = tk.BooleanVar(value=True)

        # Proactive launch greeting (speaks if voice is available)
        self.proactive_greeting = proactive_launch_greeting(voice_enabled=True, print_output=False)

        # Style configuration
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._configure_styles()
        self._build_layout()
        self.refresh_all_data()

    def _configure_styles(self):
        self.configure(bg="#f4f6f9")
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), background="#1e293b", foreground="#ffffff")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 11, "bold"), foreground="#0f172a")
        self.style.configure("Card.TFrame", background="#ffffff", relief="flat")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", rowheight=24)

    def _build_layout(self):
        # 1. Top Navigation Bar
        top_bar = tk.Frame(self, bg="#1e293b", height=50)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(
            top_bar,
            text="⚡ JARVIS-lite Assistant",
            font=("Segoe UI", 14, "bold"),
            bg="#1e293b",
            fg="#f8fafc",
            padx=15,
            pady=10,
        )
        title_lbl.pack(side=tk.LEFT)

        btn_container = tk.Frame(top_bar, bg="#1e293b")
        btn_container.pack(side=tk.RIGHT, padx=15)

        upload_btn = tk.Button(
            btn_container,
            text="📄 Upload Syllabus (PDF/TXT)",
            command=self._on_upload_syllabus,
            bg="#2563eb",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        )
        upload_btn.pack(side=tk.LEFT, padx=5)

        placement_btn = tk.Button(
            btn_container,
            text="💼 Placements",
            command=self._on_open_placements,
            bg="#0f766e",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        )
        placement_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = tk.Button(
            btn_container,
            text="🔄 Refresh",
            command=self.refresh_all_data,
            bg="#334155",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # 2. Main Panes (Left: Stale Dashboard & Tasks; Right: Subject Tree & Chat)
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Column Frame
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # Right Column Frame
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # Build Left Components
        self._build_stale_dashboard(left_frame)
        self._build_task_panel(left_frame)

        # Build Right Components
        self._build_subject_tree(right_frame)
        self._build_chat_panel(right_frame)

    # --------------------------------------------------
    # Left Pane 1: Stale Items Dashboard
    # --------------------------------------------------
    def _build_stale_dashboard(self, parent):
        box = ttk.LabelFrame(parent, text=" 🔔 Memory Check (Stale > 3 Days) ", padding=8)
        box.pack(fill=tk.X, padx=5, pady=5)

        self.stale_text = tk.Text(box, height=5, font=("Segoe UI", 9), bg="#f8fafc", relief="flat", wrap="word")
        self.stale_text.pack(fill=tk.X, expand=True)
        self.stale_text.config(state=tk.DISABLED)

    # --------------------------------------------------
    # Left Pane 2: Task List
    # --------------------------------------------------
    def _build_task_panel(self, parent):
        box = ttk.LabelFrame(parent, text=" 📋 Tasks & Deliverables ", padding=8)
        box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Task Tree
        columns = ("id", "task", "category", "status", "created")
        self.task_tree = ttk.Treeview(box, columns=columns, show="headings", selectmode="browse", height=10)
        self.task_tree.heading("id", text="#")
        self.task_tree.heading("task", text="Task Name")
        self.task_tree.heading("category", text="Category")
        self.task_tree.heading("status", text="Status")
        self.task_tree.heading("created", text="Created")

        self.task_tree.column("id", width=30, anchor="center")
        self.task_tree.column("task", width=180, anchor="w")
        self.task_tree.column("category", width=90, anchor="center")
        self.task_tree.column("status", width=80, anchor="center")
        self.task_tree.column("created", width=110, anchor="center")

        task_scroll = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=task_scroll.set)

        self.task_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        task_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Action Buttons
        btn_bar = ttk.Frame(box)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))

        mark_task_btn = tk.Button(
            btn_bar,
            text="✓ Mark Task Done",
            command=self._on_mark_task_done,
            bg="#10b981",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        )
        mark_task_btn.pack(side=tk.LEFT)

    # --------------------------------------------------
    # Right Pane 1: Subject / Topic Tree
    # --------------------------------------------------
    def _build_subject_tree(self, parent):
        box = ttk.LabelFrame(parent, text=" 📚 Subjects & Topics Hierarchy ", padding=8)
        box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.subject_tree = ttk.Treeview(box, columns=("status", "last_touched"), selectmode="browse", height=9)
        self.subject_tree.heading("#0", text="Subject / Topic")
        self.subject_tree.heading("status", text="Status")
        self.subject_tree.heading("last_touched", text="Last Touched")

        self.subject_tree.column("#0", width=260, anchor="w")
        self.subject_tree.column("status", width=90, anchor="center")
        self.subject_tree.column("last_touched", width=130, anchor="center")

        tree_scroll = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.subject_tree.yview)
        self.subject_tree.configure(yscrollcommand=tree_scroll.set)

        self.subject_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_bar = ttk.Frame(box)
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))

        mark_topic_btn = tk.Button(
            btn_bar,
            text="✓ Mark Topic Done",
            command=self._on_mark_topic_done,
            bg="#10b981",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        )
        mark_topic_btn.pack(side=tk.LEFT)

    # --------------------------------------------------
    # Right Pane 2: Conversational Assistant Input
    # --------------------------------------------------
    def _build_chat_panel(self, parent):
        box = ttk.LabelFrame(parent, text=" 💬 Talk to JARVIS ", padding=8)
        box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_history = scrolledtext.ScrolledText(
            box, height=7, font=("Consolas", 9), bg="#1e293b", fg="#f8fafc", wrap="word", relief="flat"
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.chat_history.insert(tk.END, f"JARVIS: {self.proactive_greeting}\n\n")
        self.chat_history.config(state=tk.DISABLED)

        # Input Row
        input_row = ttk.Frame(box)
        input_row.pack(fill=tk.X)

        self.user_entry = ttk.Entry(input_row, font=("Segoe UI", 10))
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.user_entry.bind("<Return>", lambda e: self._on_send_chat())

        self.voice_btn = tk.Button(
            input_row,
            text="🎤 Mic",
            command=self._on_voice_input,
            bg="#0284c7",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.voice_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.send_btn = tk.Button(
            input_row,
            text="Send",
            command=self._on_send_chat,
            bg="#2563eb",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=15,
            pady=4,
            cursor="hand2",
        )
        self.send_btn.pack(side=tk.RIGHT)

        # Status and Voice Toggle Row
        status_row = ttk.Frame(box)
        status_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))

        self.status_lbl = ttk.Label(status_row, text="Ready", font=("Segoe UI", 8, "italic"))
        self.status_lbl.pack(side=tk.LEFT)

        self.tts_check = ttk.Checkbutton(status_row, text="🔊 Speak replies", variable=self.tts_enabled)
        self.tts_check.pack(side=tk.RIGHT)

    # --------------------------------------------------
    # Data Refresh & Rendering
    # --------------------------------------------------
    def refresh_all_data(self):
        self._load_stale_dashboard()
        self._load_tasks()
        self._load_subjects_and_topics()

    def _load_stale_dashboard(self):
        stale_topics = get_stale_topics(days=3)
        stale_tasks = get_stale_tasks(days=3)

        self.stale_text.config(state=tk.NORMAL)
        self.stale_text.delete("1.0", tk.END)

        if not stale_topics and not stale_tasks:
            self.stale_text.insert(tk.END, "✓ Everything is up to date! No stale items (3+ days old).\n")
        else:
            if stale_topics:
                self.stale_text.insert(tk.END, "📚 Untouched Topics:\n")
                for subject, topic, status, last_touched in stale_topics:
                    age = days_old(last_touched)
                    self.stale_text.insert(tk.END, f"  • {topic} ({subject}) — {age}d ago\n")
            if stale_tasks:
                self.stale_text.insert(tk.END, "\n📋 Overdue/Stale Tasks:\n")
                for task, category, status, created_date, due_date in stale_tasks:
                    age = days_old(created_date)
                    self.stale_text.insert(tk.END, f"  • {task} ({category}) — pending {age}d\n")

        self.stale_text.config(state=tk.DISABLED)

    def _load_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, task_name, category, status, created_date FROM tasks ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            task_id, name, cat, status, created = row
            status_display = "✓ Done" if status == "done" else ("⏳ " + status.title())
            self.task_tree.insert("", tk.END, values=(task_id, name, cat, status_display, created[:16]))

    def _load_subjects_and_topics(self):
        for item in self.subject_tree.get_children():
            self.subject_tree.delete(item)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM subjects ORDER BY id")
        subjects = cur.fetchall()

        for subj_id, subj_name in subjects:
            subj_node = self.subject_tree.insert("", tk.END, text=f"📁 {subj_name}", values=("", ""), open=True)

            cur.execute("""
                SELECT id, topic_name, status, last_touched_date
                FROM topics
                WHERE subject_id = ?
                ORDER BY id
            """, (subj_id,))
            topics = cur.fetchall()

            for t_id, t_name, status, last_touched in topics:
                status_icon = "✓ Done" if status == "done" else ("⏳ " + status)
                self.subject_tree.insert(
                    subj_node,
                    tk.END,
                    text=f"• {t_name}",
                    values=(status_icon, last_touched[:16]),
                    tags=(str(t_id),),
                )

        conn.close()

    # --------------------------------------------------
    # Actions & Async Handlers
    # --------------------------------------------------
    def _on_voice_input(self):
        if not STT_AVAILABLE:
            messagebox.showwarning("Voice Input", "SpeechRecognition is not available on this system.")
            return

        self.voice_btn.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.status_lbl.config(text="🎤 Listening... Speak into your microphone")

        threading.Thread(target=self._async_voice_input, daemon=True).start()

    def _async_voice_input(self):
        text, err = listen_to_microphone(timeout=5, phrase_time_limit=8)
        self.after(0, lambda: self._on_voice_input_completed(text, err))

    def _on_voice_input_completed(self, text, err):
        self.voice_btn.config(state=tk.NORMAL)
        self.send_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="Ready")

        if err:
            self._append_chat(f"System: Voice input error — {err}")
            return

        if text:
            self.user_entry.delete(0, tk.END)
            self.user_entry.insert(0, text)
            self._on_send_chat()

    def _on_send_chat(self):
        user_text = self.user_entry.get().strip()
        if not user_text:
            return

        self.user_entry.delete(0, tk.END)
        self._append_chat(f"You: {user_text}")

        # Execute extraction in a background thread so UI stays responsive
        self.send_btn.config(state=tk.DISABLED)
        self.voice_btn.config(state=tk.DISABLED)
        self.status_lbl.config(text="Ollama is thinking...")

        threading.Thread(target=self._async_process_input, args=(user_text,), daemon=True).start()

    def _async_process_input(self, user_text):
        try:
            process_input(user_text)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT parsed_summary FROM logs ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            conn.close()

            if row and row[0]:
                import json
                extracted = json.loads(row[0])
                msg_text = get_confirmation_message(extracted)
            else:
                msg_text = "Updated your memory."

            response_msg = f"JARVIS: {msg_text}"
        except Exception as e:
            response_msg = f"JARVIS: Error parsing request: {e}"

        self.after(0, lambda: self._on_chat_completed(response_msg))

    def _on_chat_completed(self, response_msg):
        self._append_chat(response_msg)
        self.send_btn.config(state=tk.NORMAL)
        self.voice_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="Ready")
        self.refresh_all_data()

        # Optional spoken voice feedback
        if self.tts_enabled.get() and TTS_AVAILABLE:
            speak("I updated your memory.", async_mode=True)

    def _append_chat(self, message):
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, message + "\n")
        self.chat_history.see(tk.END)
        self.chat_history.config(state=tk.DISABLED)

    def _on_mark_task_done(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showinfo("Select Task", "Please select a task from the list first.")
            return

        item = self.task_tree.item(selected[0])
        task_id = item["values"][0]
        task_name = item["values"][1]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        self._append_chat(f"System: Task '{task_name}' marked as done.")
        self.refresh_all_data()

    def _on_mark_topic_done(self):
        selected = self.subject_tree.selection()
        if not selected:
            messagebox.showinfo("Select Topic", "Please select a topic from the hierarchy tree first.")
            return

        item = self.subject_tree.item(selected[0])
        tags = item.get("tags", [])
        if not tags:
            messagebox.showinfo("Select Topic", "Please select a specific topic child node, not a subject header.")
            return

        topic_id = int(tags[0])
        topic_name = item["text"].lstrip("• ")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE topics SET status = 'done', last_touched_date = CURRENT_TIMESTAMP WHERE id = ?", (topic_id,))
        conn.commit()
        conn.close()

        self._append_chat(f"System: Topic '{topic_name}' marked as done.")
        self.refresh_all_data()

    def _on_upload_syllabus(self):
        file_path = filedialog.askopenfilename(
            title="Select Syllabus File",
            filetypes=[("Syllabus Files", "*.pdf *.txt *.md"), ("PDF Documents", "*.pdf"), ("Text Files", "*.txt *.md")],
        )
        if not file_path:
            return

        self.status_lbl.config(text="Processing syllabus file...")
        threading.Thread(target=self._async_upload_syllabus, args=(file_path,), daemon=True).start()

    def _async_upload_syllabus(self, file_path):
        try:
            result = process_syllabus(file_path)
            msg = f"JARVIS: Syllabus imported! Subject '{result['subject']}' with {result['total_topics']} topics."
        except Exception as e:
            msg = f"JARVIS: Failed to import syllabus: {e}"

        self.after(0, lambda: self._on_syllabus_completed(msg))

    def _on_syllabus_completed(self, msg):
        self._append_chat(msg)
        self.status_lbl.config(text="Ready")
        self.refresh_all_data()
        messagebox.showinfo("Syllabus Upload", msg)

    def _on_open_placements(self):
        PlacementWindow(self)


class PlacementWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("💼 Placement & Job Applications Tracker")
        self.geometry("980x560")
        self.minsize(800, 450)
        self.configure(bg="#f4f6f9")

        self._build_ui()
        self.refresh_applications()

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#0f766e", height=45)
        header.pack(fill=tk.X)

        lbl = tk.Label(
            header,
            text="💼 Job & Internship Application Pipeline",
            font=("Segoe UI", 13, "bold"),
            bg="#0f766e",
            fg="#ffffff",
            padx=15,
            pady=10,
        )
        lbl.pack(side=tk.LEFT)

        self.summary_lbl = tk.Label(
            header,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#0f766e",
            fg="#ccfbf1",
            padx=15,
        )
        self.summary_lbl.pack(side=tk.RIGHT)

        # Toolbar
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill=tk.X)

        add_btn = tk.Button(
            toolbar,
            text="➕ New Application",
            command=self._on_add,
            bg="#059669",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
        )
        add_btn.pack(side=tk.LEFT, padx=4)

        update_btn = tk.Button(
            toolbar,
            text="🔄 Update Stage",
            command=self._on_update_stage,
            bg="#0284c7",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
        )
        update_btn.pack(side=tk.LEFT, padx=4)

        del_btn = tk.Button(
            toolbar,
            text="🗑️ Delete",
            command=self._on_delete,
            bg="#dc2626",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
        )
        del_btn.pack(side=tk.LEFT, padx=4)

        refresh_btn = tk.Button(
            toolbar,
            text="🔄 Refresh",
            command=self.refresh_applications,
            bg="#475569",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
        )
        refresh_btn.pack(side=tk.RIGHT, padx=4)

        # Applications Table
        table_frame = ttk.Frame(self, padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "company", "role", "stage", "result", "applied_date", "notes")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="#")
        self.tree.heading("company", text="Company")
        self.tree.heading("role", text="Role")
        self.tree.heading("stage", text="Stage")
        self.tree.heading("result", text="Result")
        self.tree.heading("applied_date", text="Applied Date")
        self.tree.heading("notes", text="Notes")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("company", width=140, anchor="w")
        self.tree.column("role", width=150, anchor="w")
        self.tree.column("stage", width=150, anchor="center")
        self.tree.column("result", width=100, anchor="center")
        self.tree.column("applied_date", width=120, anchor="center")
        self.tree.column("notes", width=220, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_applications(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = get_applications()
        for r in rows:
            app_id, company, role, stage, applied_date, result, notes = r
            self.tree.insert("", tk.END, values=(app_id, company, role, stage, result, applied_date[:16], notes or ""))

        summary = get_placement_summary()
        self.summary_lbl.config(
            text=f"Total: {summary['total']} | Active: {summary['in_progress']} | Interviews: {summary['interviews']} | Offers: {summary['offers']}"
        )

    def _on_add(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Job Application")
        dialog.geometry("400x320")
        dialog.resizable(False, False)
        dialog.grab_set()

        ttk.Label(dialog, text="Company Name:").pack(anchor="w", padx=15, pady=(10, 2))
        comp_ent = ttk.Entry(dialog, width=40)
        comp_ent.pack(padx=15, fill=tk.X)
        comp_ent.focus_set()

        ttk.Label(dialog, text="Role / Title:").pack(anchor="w", padx=15, pady=(8, 2))
        role_ent = ttk.Entry(dialog, width=40)
        role_ent.pack(padx=15, fill=tk.X)

        ttk.Label(dialog, text="Current Stage:").pack(anchor="w", padx=15, pady=(8, 2))
        stage_cb = ttk.Combobox(dialog, values=VALID_STAGES, state="readonly")
        stage_cb.set(VALID_STAGES[0])
        stage_cb.pack(padx=15, fill=tk.X)

        ttk.Label(dialog, text="Notes:").pack(anchor="w", padx=15, pady=(8, 2))
        notes_ent = ttk.Entry(dialog, width=40)
        notes_ent.pack(padx=15, fill=tk.X)

        def _save():
            c = comp_ent.get().strip()
            r = role_ent.get().strip()
            if not c or not r:
                messagebox.showwarning("Validation", "Company and Role are required.", parent=dialog)
                return
            add_application(c, r, stage=stage_cb.get(), notes=notes_ent.get().strip())
            dialog.destroy()
            self.refresh_applications()

        tk.Button(
            dialog, text="Save Application", command=_save, bg="#059669", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", pady=5
        ).pack(fill=tk.X, padx=15, pady=15)

    def _on_update_stage(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Application", "Please select an application to update.", parent=self)
            return

        item = self.tree.item(selected[0])
        app_id = item["values"][0]
        company = item["values"][1]
        current_stage = item["values"][3]
        current_notes = item["values"][6]

        dialog = tk.Toplevel(self)
        dialog.title(f"Update Stage: {company}")
        dialog.geometry("380x250")
        dialog.resizable(False, False)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Update Stage for {company} (#{app_id}):", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

        ttk.Label(dialog, text="New Stage:").pack(anchor="w", padx=15, pady=(5, 2))
        stage_cb = ttk.Combobox(dialog, values=VALID_STAGES, state="readonly")
        stage_cb.set(current_stage if current_stage in VALID_STAGES else VALID_STAGES[0])
        stage_cb.pack(padx=15, fill=tk.X)

        ttk.Label(dialog, text="Updated Notes:").pack(anchor="w", padx=15, pady=(8, 2))
        notes_ent = ttk.Entry(dialog, width=40)
        notes_ent.insert(0, str(current_notes))
        notes_ent.pack(padx=15, fill=tk.X)

        def _save_update():
            update_application_stage(app_id, stage_cb.get(), notes=notes_ent.get().strip())
            dialog.destroy()
            self.refresh_applications()

        tk.Button(
            dialog, text="Save Update", command=_save_update, bg="#0284c7", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", pady=5
        ).pack(fill=tk.X, padx=15, pady=15)

    def _on_delete(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Application", "Please select an application to delete.", parent=self)
            return

        item = self.tree.item(selected[0])
        app_id = item["values"][0]
        company = item["values"][1]

        if messagebox.askyesno("Confirm Delete", f"Delete application for '{company}' (#{app_id})?", parent=self):
            delete_application(app_id)
            self.refresh_applications()


def launch_gui():
    app = JarvisGUI()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
