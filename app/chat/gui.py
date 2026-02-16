import os
import sys
import json
import subprocess
from pathlib import Path

from langchain_community.vectorstores import FAISS

from app.rag.llm import init_llm
from app.rag.answer import generate_answer_with_llm
from app.utils.misc import looks_like_gibberish
from app.core.models import load_embeddings

try:
    import tkinter as tk
    from tkinter import scrolledtext, filedialog
except Exception:
    tk = None


def _open_path_in_explorer(path: str):
    try:
        if sys.platform.startswith("win"):
            subprocess.call(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.call(["open", "-R", str(path)])
        else:
            subprocess.call(["xdg-open", str(Path(path).parent)])
    except Exception as e:
        print("⚠️ Could not reveal file:", e)


class SmartSearchUI:
    def __init__(self, root, vectordb, rows):
        self.root = root
        self.vectordb = vectordb
        self.rows = rows
        self.last_hits = []
        self.llm = None

        self.root.title("🧠 Smart File Search (GUI)")
        self.root.geometry("920x700")

        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=8, pady=(8, 0))

        tk.Button(
            top,
            text="Select file to open...",
            command=self.choose_and_open_file
        ).pack(side=tk.LEFT)

        # Chat box
        self.chat_box = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            state="disabled",
            font=("Helvetica", 11)
        )
        self.chat_box.pack(padx=10, pady=8, fill=tk.BOTH, expand=True)

        # Input
        bottom = tk.Frame(root)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.entry = tk.Entry(bottom, font=("Arial", 12))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda e: self.send_query())

        tk.Button(
            bottom,
            text="Send",
            width=12,
            command=self.send_query
        ).pack(side=tk.RIGHT)

        # Results
        self.results_frame = tk.LabelFrame(
            root,
            text="📂 Top results",
            font=("Arial", 11, "bold")
        )
        self.results_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

    def add_message(self, who, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert(tk.END, f"{who}: {text}\n\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.yview(tk.END)

    def clear_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()

    
    def choose_and_open_file(self):
        p = filedialog.askopenfilename()
        if not p:
            return
        self.open_file(p)

    def open_file(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as e:
            self.add_message("⚠️", f"Could not open file: {e}")

    def reveal_file(self, path):
        _open_path_in_explorer(path)


    def send_query(self):
        q = self.entry.get().strip()
        if not q:
            return

        self.entry.delete(0, tk.END)
        self.add_message("You", q)

        hits = self.vectordb.similarity_search_with_score(q, k=5)
        hits = [(d, s) for d, s in hits if s >= 0.3]

        if not hits:
            self.add_message("Bot", "No relevant files found.")
            self.clear_results()
            return

        self.last_hits = hits[:3]

        if self.llm is None:
            self.llm = init_llm()

        answer = None
        if self.llm:
            try:
                answer = generate_answer_with_llm(self.llm, q, self.last_hits)
                if looks_like_gibberish(answer):
                    answer = None
            except Exception:
                answer = None

        if answer:
            self.add_message("Bot", answer)
        else:
            self.add_message(
                "Bot",
                "Here are the most relevant files:"
            )

        
        self.clear_results()
        for d, s in self.last_hits:
            path = d.metadata.get("path")
            if not path:
                continue

            row = tk.Frame(self.results_frame)
            row.pack(fill=tk.X, padx=6, pady=2)

            tk.Label(
                row,
                text=f"{Path(path).name} (score {s:.2f})",
                anchor="w"
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Button(
                row,
                text="Open",
                width=8,
                command=lambda p=path: self.open_file(p)
            ).pack(side=tk.RIGHT, padx=(6, 0))

            tk.Button(
                row,
                text="Reveal",
                width=8,
                command=lambda p=path: self.reveal_file(p)
            ).pack(side=tk.RIGHT)


def launch_gui(name: str):
    if tk is None:
        print("tkinter not available.")
        return

    db_dir = Path("vector_dbs") / f"{name}_bge_db"
    idx_file = Path("file_indexes", f"{name}.json")

    embeddings = load_embeddings()
    vectordb = FAISS.load_local(
        str(db_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    rows = json.loads(idx_file.read_text())

    root = tk.Tk()
    SmartSearchUI(root, vectordb, rows)
    root.mainloop()
