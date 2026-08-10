import sqlite3
import uuid
from pathlib import Path
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_videos INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            batch_id TEXT,
            filename TEXT,
            input_path TEXT,
            output_path TEXT,
            status TEXT DEFAULT 'queued',
            progress REAL DEFAULT 0.0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def create_batch(total_videos: int) -> str:
    batch_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute("INSERT INTO batches (batch_id, total_videos) VALUES (?, ?)", (batch_id, total_videos))
    conn.commit()
    conn.close()
    return batch_id

def create_task(batch_id: str, filename: str, input_path: str, output_path: str) -> str:
    task_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tasks (task_id, batch_id, filename, input_path, output_path, status, progress) VALUES (?, ?, ?, ?, ?, 'queued', 0.0)",
        (task_id, batch_id, filename, input_path, output_path)
    )
    conn.commit()
    conn.close()
    return task_id

def update_task_status(task_id: str, status: str, progress: float = None, error_message: str = None):
    conn = get_db_connection()
    if status == 'completed':
        conn.execute("UPDATE tasks SET status = ?, progress = 100.0 WHERE task_id = ?", (status, task_id))
    elif status == 'failed':
        conn.execute("UPDATE tasks SET status = ?, error_message = ? WHERE task_id = ?", (status, error_message, task_id))
    else:
        conn.execute("UPDATE tasks SET status = ?, progress = ? WHERE task_id = ?", (status, progress or 0.0, task_id))
    conn.commit()
    conn.close()

def get_next_queued_task():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_task(task_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_batch_tasks(batch_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE batch_id = ? ORDER BY created_at ASC", (batch_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_batches():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.batch_id, b.created_at, b.total_videos,
               COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_count
        FROM batches b
        LEFT JOIN tasks t ON b.batch_id = t.batch_id
        GROUP BY b.batch_id
        ORDER BY b.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]