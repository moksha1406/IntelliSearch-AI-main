"""
Local AI RAG Search
Split from original monolithic beta_new3.py
Behavior: IDENTICAL
"""

import os
import sys
import json
import argparse
from pathlib import Path

from app.core.device import log_device
from app.core.models import load_embeddings
from app.indexing.builder import build_index
from app.indexing.delta import DeltaIndexer
from app.chat.cli import chat
from app.chat.gui import launch_gui
from app.config import SUPPORTED_TEXT, SUPPORTED_IMG

# Start MENU
def run_menu(folder_arg: str):
    folder = Path(folder_arg).expanduser()
    if not folder.exists():
        print(f"❌ Folder does not exist: {folder}")
        sys.exit(1)

    name = folder.name
    embeddings = load_embeddings()

    print(f"\nRunning on folder: {folder}")
    print(f"Index name: '{name}'\n")

    print("Choose mode:")
    print("1. Index")
    print("2. Chat (CLI)")
    print("3. Watchdog")
    print("4. Chat (GUI)")
    print("q. Quit")

    choice = input("> ").strip().lower()

    if choice in {"q", "quit", "exit"}:
        print("->Exiting.")
        sys.exit(0)


    # 1. Full Index Build
    if choice == "1":
        print(f"-> Building index for '{name}' …")
        build_index(str(folder), name)
        sys.exit(0)


    # 2. CLI Chat
    elif choice == "2":
        db_dir = Path("vector_dbs") / f"{name}_bge_db"
        idx_json = Path("file_indexes", f"{name}.json")

        if not db_dir.exists() or not idx_json.exists():
            print("Index not found. Run Index mode first.")
            sys.exit(1)

        print("-> Starting CLI chat")
        chat(name, embeddings_obj=embeddings)
        sys.exit(0)

   
    # 3. Watchdog/Delta Sync
    elif choice == "3":
        db_dir = Path("vector_dbs") / f"{name}_bge_db"
        idx_json = Path("file_indexes", f"{name}.json")

        if not db_dir.exists() or not idx_json.exists():
            print("No index found. Run Index first.")
            sys.exit(1)

        rows = json.loads(idx_json.read_text())
        handler = DeltaIndexer(str(folder), name, embeddings, db_dir, rows)

        curr = {}
        for r, _, fns in os.walk(folder):
            for fn in fns:
                ext = Path(fn).suffix.lower().lstrip(".")
                if ext in SUPPORTED_TEXT or ext in SUPPORTED_IMG:
                    p = Path(r) / fn
                    try:
                        stat = p.stat()
                        curr[str(p)] = (stat.st_size, int(stat.st_mtime))
                    except Exception:
                        curr[str(p)] = (0, 0)

        idx_map = {
            r["path"]: (r.get("size", 0), r.get("mtime", 0))
            for r in rows
            if r.get("chunk_id", 0) == 0
        }

        to_add = set(curr) - set(idx_map)
        to_delete = set(idx_map) - set(curr)
        to_mod = {p for p in (set(curr) & set(idx_map)) if curr[p] != idx_map[p]}

        for p in sorted(to_delete):
            print(f"-> Removing {p}")
            handler._remove_path(Path(p))

        for p in sorted(to_mod):
            print(f"-> Re-indexing {p}")
            handler._remove_path(Path(p))
            handler._index_path(Path(p))

        for p in sorted(to_add):
            print(f"-> Adding {p}")
            handler._index_path(Path(p))

        print("✅ Delta sync complete.")
        sys.exit(0)

    
    # 4. GUI Chat (with auto-sync : Runs Watchdog to Check for Modified Files and Update Index)
    elif choice == "4":
        db_dir = Path("vector_dbs") / f"{name}_bge_db"
        idx_json = Path("file_indexes", f"{name}.json")

        if not db_dir.exists() or not idx_json.exists():
            print("Index not found.Run Index mode first.")
            sys.exit(1)

        print("Running watchdog sync before GUI launch...")

        rows = json.loads(idx_json.read_text())
        handler = DeltaIndexer(str(folder), name, embeddings, db_dir, rows)

        curr = {}
        for r, _, fns in os.walk(folder):
            for fn in fns:
                ext = Path(fn).suffix.lower().lstrip(".")
                if ext in SUPPORTED_TEXT or ext in SUPPORTED_IMG:
                    p = Path(r) / fn
                    try:
                        stat = p.stat()
                        curr[str(p)] = (stat.st_size, int(stat.st_mtime))
                    except Exception:
                        curr[str(p)] = (0, 0)

        idx_map = {
            r["path"]: (r.get("size", 0), r.get("mtime", 0))
            for r in rows
            if r.get("chunk_id", 0) == 0
        }

        to_add = set(curr) - set(idx_map)
        to_delete = set(idx_map) - set(curr)
        to_mod = {p for p in (set(curr) & set(idx_map)) if curr[p] != idx_map[p]}

        for p in sorted(to_delete):
            handler._remove_path(Path(p))
        for p in sorted(to_mod):
            handler._remove_path(Path(p))
            handler._index_path(Path(p))
        for p in sorted(to_add):
            handler._index_path(Path(p))

        print("-> Launching GUI")
        launch_gui(name)
        sys.exit(0)

    else:
        print("❌ Invalid choice.")
        sys.exit(1)



if __name__ == "__main__":
    log_device()

    parser = argparse.ArgumentParser(
        description="Local AI RAG Search (Index / Chat / Watchdog / GUI)"
    )
    parser.add_argument(
        "folder",
        help="Folder to operate on (index name derived from folder name)",
    )

    args = parser.parse_args()
    run_menu(args.folder)
