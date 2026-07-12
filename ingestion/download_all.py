import subprocess
import os
import sys
import sqlite3

# Ensure config is importable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import STOCK_DATA_DB
from ingestion.stock_downloader import get_stocks_list

def get_missing_stocks():
    """
    Connects to STOCK_DATA_DB, gets all table names, 
    and checks against the full listed stocks to find missing ones.
    """
    tables_set = set()
    try:
        if os.path.exists(STOCK_DATA_DB):
            conn = sqlite3.connect(STOCK_DATA_DB)
            cursor = conn.cursor()
            
            # Query to list all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables_set = set(row[0] for row in cursor.fetchall())
            
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Database error: {e}. Proceeding with clean run.")

    # Get all listed symbols
    all_symbols = get_stocks_list(nifty50_only=False)
    missing_stocks = []
    
    for symbol in all_symbols:
        table_name = f"hist_{symbol.replace('-', '_')}"
        if table_name not in tables_set:
            missing_stocks.append(symbol)
            
    return all_symbols, missing_stocks

# --- Main Script Execution ---

ingestion_dir = os.path.dirname(os.path.abspath(__file__))

print("============================================")
print(" Checking Existing Database Tables...")
print("============================================")

all_stocks, missing_stocks = get_missing_stocks()
existing_count = len(all_stocks) - len(missing_stocks)

print(f"Total listed stocks: {len(all_stocks)}")
print(f"Found {existing_count} stocks already present in the database.")
print(f"Missing stocks to download: {len(missing_stocks)}")

if len(missing_stocks) == 0:
    print("\nAll stocks are already downloaded!")
    sys.exit(0)

print("\n============================================")
print(" Downloading Remaining NSE Stocks Data")
print("============================================")

missing_symbols_str = ",".join(missing_stocks)

# Build your command dynamically
cmd = ["python", "stock_downloader.py", "--years", "1", "--workers", "10", "--symbols", missing_symbols_str]

if len(missing_symbols_str) > 8000:
    print("Warning: Symbol list is very long, splitting into batches.")
    # Batch processing
    batch_size = 500
    for i in range(0, len(missing_stocks), batch_size):
        batch = missing_stocks[i:i+batch_size]
        batch_str = ",".join(batch)
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} symbols)...")
        batch_cmd = ["python", "stock_downloader.py", "--years", "1", "--workers", "10", "--symbols", batch_str]
        subprocess.run(batch_cmd, cwd=ingestion_dir)
else:
    # Run the stock downloader
    subprocess.run(cmd, cwd=ingestion_dir)

print("\nFinished downloading the missing stocks!")
