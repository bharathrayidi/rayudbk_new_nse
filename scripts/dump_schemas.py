import os
import sqlite3

def dump_schemas():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(root, 'databases')
    scratch_dir = os.path.join(os.environ.get("APPDATA_DIR", root), "brain", "d3bc46ae-38ef-41ef-9222-30ecd324a32d", "scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    
    out_file = os.path.join(scratch_dir, 'schemas.txt')
    
    with open(out_file, 'w', encoding='utf-8') as f:
        for db_name in os.listdir(db_dir):
            if db_name.endswith('.db'):
                db_path = os.path.join(db_dir, db_name)
                f.write(f"=== {db_name} ===\n")
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    for t_name, sql in tables:
                        f.write(f"Table: {t_name}\n")
                        f.write(f"{sql}\n\n")
                    conn.close()
                except Exception as e:
                    f.write(f"Error: {e}\n\n")
    print(f"Schemas written to {out_file}")

if __name__ == "__main__":
    dump_schemas()
