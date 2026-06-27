import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3

DEFAULT_DB = "/Volumes/.timemachine/6943AA64-BA48-4F7D-B74D-AB16D4ECE81E/2026-06-18-231250.backup/2026-06-18-231250.backup/Data/Users/monicawiesener/Library/Messages/chat.db"

def search_messages(db_path, term):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    return cur.execute("""
        SELECT
          datetime(message.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS msg_date,
          COALESCE(handle.id, '') AS contact,
          CASE WHEN message.is_from_me=1 THEN 'Me' ELSE 'Them' END AS direction,
          COALESCE(message.text, '') AS text,
          message.ROWID
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.text LIKE ?
        ORDER BY message.date DESC
        LIMIT 500
    """, ("%" + term + "%",)).fetchall()

def get_context(db_path, rowid):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rowid = int(rowid)
    return cur.execute("""
        SELECT
          datetime(message.date/1000000000 + 978307200, 'unixepoch', 'localtime') AS msg_date,
          COALESCE(handle.id, '') AS contact,
          CASE WHEN message.is_from_me=1 THEN 'Me' ELSE 'Them' END AS direction,
          COALESCE(message.text, '') AS text,
          message.ROWID
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.ROWID BETWEEN ? AND ?
        ORDER BY message.ROWID
    """, (rowid-15, rowid+15)).fetchall()

def test_db():
    try:
        n = sqlite3.connect(db_var.get().strip()).execute("SELECT COUNT(*) FROM message").fetchone()[0]
        messagebox.showinfo("Database OK", "Opened chat.db successfully.\nMessages: " + format(n, ","))
    except Exception as e:
        messagebox.showerror("Database error", str(e))

def choose_db():
    p = filedialog.askopenfilename(title="Choose chat.db")
    if p:
        db_var.set(p)

def run_search(event=None):
    q = term_var.get().strip()
    tree.delete(*tree.get_children())
    context.delete("1.0", "end")
    if not q:
        return
    try:
        rows = search_messages(db_var.get().strip(), q)
        for d, c, direction, text, rowid in rows:
            msg = (text or "").replace("\n", " ")[:600]
            tree.insert("", "end", values=(d, c, direction, msg, rowid))
        status_var.set(str(len(rows)) + " result(s)")
    except Exception as e:
        messagebox.showerror("Search error", str(e))
        status_var.set("Error")

def show_context(event=None):
    sel = tree.selection()
    if not sel:
        return
    vals = tree.item(sel[0], "values")
    rowid = vals[4]
    context.delete("1.0", "end")
    try:
        for d, c, direction, text, rid in get_context(db_var.get().strip(), rowid):
            context.insert("end", f"{d} | {direction} | {c}\n{text}\n\n")
    except Exception as e:
        context.insert("end", str(e))

root = tk.Tk()
root.title("Messages Search v2")
root.geometry("1250x780")

db_var = tk.StringVar(value=DEFAULT_DB)
term_var = tk.StringVar()
status_var = tk.StringVar(value="Ready")

top = ttk.Frame(root, padding=10)
top.pack(fill="both", expand=True)

dbrow = ttk.Frame(top)
dbrow.pack(fill="x")
ttk.Label(dbrow, text="chat.db:").pack(side="left")
ttk.Entry(dbrow, textvariable=db_var).pack(side="left", fill="x", expand=True, padx=6)
ttk.Button(dbrow, text="Choose", command=choose_db).pack(side="left")
ttk.Button(dbrow, text="Test DB", command=test_db).pack(side="left", padx=4)

srow = ttk.Frame(top)
srow.pack(fill="x", pady=8)
ttk.Label(srow, text="Search:").pack(side="left")
entry = ttk.Entry(srow, textvariable=term_var, font=("Arial", 16))
entry.pack(side="left", fill="x", expand=True, padx=6)
entry.bind("<Return>", run_search)
ttk.Button(srow, text="Search", command=run_search).pack(side="left")

ttk.Label(top, textvariable=status_var).pack(anchor="w")

cols = ("date", "contact", "direction", "text", "rowid")
tree = ttk.Treeview(top, columns=cols, show="headings", height=18)
for col, title, w in [("date","Date",160),("contact","Contact",220),("direction","Dir",60),("text","Message",700),("rowid","RowID",70)]:
    tree.heading(col, text=title)
    tree.column(col, width=w)
tree.pack(fill="both", expand=True, pady=6)
tree.bind("<<TreeviewSelect>>", show_context)

context = tk.Text(top, height=13, wrap="word")
context.pack(fill="both", expand=False)

root.mainloop()
