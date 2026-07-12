import sqlite3
import os
import datetime

def get_db_path():
    # Assuming this script is inside ingestion/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "databases", "ingestion_log.db")

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            job_name TEXT PRIMARY KEY,
            last_updated_date TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def is_updated_today(job_name: str) -> bool:
    init_db()
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("SELECT last_updated_date, status FROM sync_history WHERE job_name = ?", (job_name,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        last_date, status = row
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if last_date == today and status == "SUCCESS":
            return True
    return False

def mark_updated_today(job_name: str, status: str = "SUCCESS"):
    init_db()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sync_history (job_name, last_updated_date, status)
        VALUES (?, ?, ?)
        ON CONFLICT(job_name) DO UPDATE SET 
            last_updated_date=excluded.last_updated_date,
            status=excluded.status
    """, (job_name, today, status))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Initialized Ingestion Log DB.")
