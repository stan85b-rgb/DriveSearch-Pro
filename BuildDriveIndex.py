import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

OUT_DB = Path.home() / "DriveSearch" / "drivesearch_v2.db"
APPLE_EPOCH = 978307200

def apple_time(ns):
    if not ns:
        return ""
    try:
        return datetime.fromtimestamp(ns / 1_000_000_000 + APPLE_EPOCH).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""

def init_db():
    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS files;
    DROP TABLE IF EXISTS messages;
    DROP TABLE IF EXISTS files_fts;

    CREATE TABLE files(
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE,
        name TEXT,
        extension TEXT,
        size INTEGER,
        modified TEXT,
        kind TEXT
    );

    CREATE TABLE messages(
        id INTEGER PRIMARY KEY,
        source_db TEXT,
        rowid_message INTEGER,
        msg_date TEXT,
        contact TEXT,
        direction TEXT,
        text TEXT
    );

    CREATE VIRTUAL TABLE files_fts USING fts5(
        path,
        name,
        content
    );
    """)
    con.commit()
    return con

def is_chat_db(path):
    if path.name != "chat.db":
        return False
    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        return {"message", "handle"}.issubset(tables)
    except Exception:
        return False

def index_file(con, path, root):
    try:
        st = path.stat()
        name = path.name
        ext = path.suffix.lower()
        modified = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        kind = "chat.db" if is_chat_db(path) else "file"

        con.execute("""
            INSERT OR IGNORE INTO files(path,name,extension,size,modified,kind)
            VALUES(?,?,?,?,?,?)
        """, (str(path), name, ext, st.st_size, modified, kind))

        content = f"{name} {ext} {kind} {str(path)}"
        con.execute("""
            INSERT INTO files_fts(path,name,content)
            VALUES(?,?,?)
        """, (str(path), name, content))

        if kind == "chat.db":
            index_messages(con, path)

    except Exception as e:
        print(f"SKIP {path}: {e}")

def index_messages(con, db_path):
    print(f"\nFound Messages DB: {db_path}")
    src = sqlite3.connect(db_path)
    cur = src.cursor()

    rows = cur.execute("""
        SELECT
          message.ROWID,
          message.date,
          COALESCE(handle.id, '') AS contact,
          CASE WHEN message.is_from_me=1 THEN 'Me' ELSE 'Them' END AS direction,
          COALESCE(message.text, '') AS text
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.text IS NOT NULL
          AND TRIM(message.text) != ''
        ORDER BY message.date
    """)

    count = 0
    for rowid, raw_date, contact, direction, text in rows:
        msg_date = apple_time(raw_date)
        con.execute("""
            INSERT INTO messages(source_db,rowid_message,msg_date,contact,direction,text)
            VALUES(?,?,?,?,?,?)
        """, (str(db_path), rowid, msg_date, contact, direction, text))

        searchable = f"Message {msg_date} {contact} {direction} {text}"
        con.execute("""
            INSERT INTO files_fts(path,name,content)
            VALUES(?,?,?)
        """, (f"{db_path}#message-{rowid}", f"Message {rowid}", searchable))

        count += 1
        if count % 5000 == 0:
            print(f"  indexed {count:,} messages...")

    src.close()
    print(f"  indexed {count:,} messages")

def scan(root):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Folder not found: {root}")

    con = init_db()
    total = 0

    print(f"Indexing: {root}")
    print(f"Output DB: {OUT_DB}")

    for dirpath, dirnames, filenames in os.walk(root):
        # avoid obvious noisy/system folders when possible
        dirnames[:] = [d for d in dirnames if d not in {".Spotlight-V100", ".fseventsd", ".Trashes"}]

        for filename in filenames:
            path = Path(dirpath) / filename
            index_file(con, path, root)
            total += 1

            if total % 1000 == 0:
                con.commit()
                print(f"Indexed {total:,} files...")

    con.commit()
    con.close()
    print(f"\nDone. Indexed {total:,} files.")
    print(f"Search DB created at: {OUT_DB}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 BuildDriveIndex.py /path/to/folder")
        sys.exit(1)

    scan(sys.argv[1])

