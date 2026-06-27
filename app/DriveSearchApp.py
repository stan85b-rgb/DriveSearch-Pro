import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, subprocess
from pathlib import Path

DB = Path.home() / "DriveSearch" / "drivesearch_v2.db"

def search_db(query):
    if not DB.exists():
        messagebox.showinfo("DriveSearch", f"Database not found:\n{DB}")
        return []
    con = sqlite3.connect(DB)
    cur = con.cursor()
    try:
        return cur.execute("""
            SELECT path, snippet(files_fts, 2, '[', ']', '...', 30)
            FROM files_fts
            WHERE files_fts MATCH ?
            LIMIT 200
        """, (query,)).fetchall()
    except Exception as e:
        messagebox.showerror("Search error", str(e))
        return []

def run_search(event=None):
    q = entry.get().strip()
    tree.delete(*tree.get_children())
    if not q:
        return
    for path, snippet in search_db(q):
        tree.insert("", "end", values=(path, snippet))

def open_selected(event=None):
    sel = tree.selection()
    if not sel:
        return
    path = tree.item(sel[0], "values")[0]
    subprocess.run(["open", path])

root = tk.Tk()
root.title("DriveSearch v2")
root.geometry("1200x700")

frm = ttk.Frame(root, padding=10)
frm.pack(fill="both", expand=True)

entry = ttk.Entry(frm, font=("Arial", 18))
entry.pack(fill="x", pady=(0, 10))
entry.bind("<Return>", run_search)

ttk.Button(frm, text="Search", command=run_search).pack(anchor="w", pady=(0, 10))

tree = ttk.Treeview(frm, columns=("path", "match"), show="headings")
tree.heading("path", text="Path")
tree.heading("match", text="Match")
tree.column("path", width=700)
tree.column("match", width=450)
tree.pack(fill="both", expand=True)
tree.bind("<Double-1>", open_selected)

root.mainloop()
