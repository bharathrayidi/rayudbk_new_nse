import sqlite3
import pandas as pd
import threading

# Thread lock to serialize SQLite writes across concurrent threads
db_lock = threading.Lock()

def save_to_db(db_name: str, df: pd.DataFrame, table_name: str, timestamp: str, key_cols):
    """
    Saves a DataFrame into a SQLite database table.
    Only inserts rows whose data actually changed since the last saved
    snapshot for the same symbol/key to prevent data duplication.
    Safe for multi-threaded/concurrent usage.
    """
    if df is None or df.empty:
        print(f"[{table_name}] No data returned, skipping.")
        return

    if isinstance(key_cols, str):
        key_cols = [key_cols]

    df = df.copy()

    with db_lock:
        conn = sqlite3.connect(db_name, timeout=60)
        # Enable WAL mode for better concurrency performance
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            )
            table_exists = cursor.fetchone() is not None

            # First time seeing this table -> save everything as the baseline
            if not table_exists:
                df["fetchedAt"] = timestamp
                df.to_sql(table_name, conn, if_exists="append", index=False)
                print(f"[{table_name}] Baseline saved: {len(df)} rows.")
                return

            missing_keys = [k for k in key_cols if k not in df.columns]
            if missing_keys:
                df["fetchedAt"] = timestamp
                df.to_sql(table_name, conn, if_exists="append", index=False)
                print(f"[{table_name}] Key column(s) {missing_keys} not found, saved all {len(df)} rows as-is.")
                return

            existing_all = pd.read_sql(f"SELECT * FROM {table_name}", conn)

            if not existing_all.empty:
                last_per_key = (
                    existing_all.sort_values("fetchedAt")
                    .drop_duplicates(subset=key_cols, keep="last")
                )
            else:
                last_per_key = pd.DataFrame(columns=df.columns)

            compare_cols = [c for c in df.columns if c in last_per_key.columns and c != "fetchedAt"]

            if not last_per_key.empty and compare_cols:
                # Convert comparison columns to string type in copies to prevent merge type-mismatch errors
                df_temp = df.copy()
                last_per_key_temp = last_per_key.copy()
                for c in compare_cols:
                    df_temp[c] = df_temp[c].astype(str).str.strip()
                    last_per_key_temp[c] = last_per_key_temp[c].astype(str).str.strip()
                    
                merged = df_temp.merge(
                    last_per_key_temp[compare_cols], on=compare_cols, how="left", indicator=True
                )
                changed_or_new = df[merged["_merge"].values == "left_only"]
            else:
                changed_or_new = df

            if changed_or_new.empty:
                print(f"[{table_name}] No changes since last snapshot, nothing new saved.")
                return

            changed_or_new = changed_or_new.copy()
            changed_or_new["fetchedAt"] = timestamp
            changed_or_new.to_sql(table_name, conn, if_exists="append", index=False)
            print(f"[{table_name}] Saved {len(changed_or_new)} changed/new rows (out of {len(df)} fetched).")
        finally:
            conn.close()
