import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from config import DATA_DIR

DB = DATA_DIR / 'inspections.sqlite3'

def connect():
    c = sqlite3.connect(DB, timeout=15)
    c.execute('CREATE TABLE IF NOT EXISTS inspections (id TEXT PRIMARY KEY, created_at TEXT, status TEXT, summary TEXT, elapsed REAL, defects TEXT, alignment TEXT, reference_file TEXT, result_file TEXT)')
    c.commit()
    return c

def save_inspection(status, summary, elapsed, defects, alignment, reference_jpg, result_jpg):
    uid = uuid.uuid4().hex
    folder = DATA_DIR / 'images'
    folder.mkdir(exist_ok=True)
    (folder / f'{uid}_ref.jpg').write_bytes(reference_jpg)
    (folder / f'{uid}_result.jpg').write_bytes(result_jpg)
    with connect() as c:
        c.execute('INSERT INTO inspections VALUES (?,?,?,?,?,?,?,?,?)', (uid,datetime.now(timezone.utc).isoformat(),status,summary,elapsed,json.dumps(defects),alignment,str(folder / f'{uid}_ref.jpg'),str(folder / f'{uid}_result.jpg')))
    return uid

def recent(limit=30):
    with connect() as c:
        c.row_factory = sqlite3.Row
        return [dict(x) for x in c.execute('SELECT id,created_at,status,summary,elapsed,defects,alignment FROM inspections ORDER BY created_at DESC LIMIT ?', (limit,))]

def get_inspection(uid):
    with connect() as c:
        c.row_factory = sqlite3.Row
        row = c.execute('SELECT * FROM inspections WHERE id=?', (uid,)).fetchone()
        return dict(row) if row else None
