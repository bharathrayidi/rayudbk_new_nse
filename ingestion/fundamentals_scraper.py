"""
Fundamentals Scraper (Screener.in mock)
---------------------------------------
Fetches basic fundamentals like PE, ROE, Debt ratio.
"""

import sys
import os
from datetime import datetime
import pandas as pd

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import FUNDAMENTALS_DB
from ingestion.db_engine import save_to_db

def fetch_fundamentals():
    print("Fetching fundamental data...")
    # Mock data
    return pd.DataFrame([
        {"Symbol": "RELIANCE", "PE": 28.5, "ROE": 9.2, "DebtToEquity": 0.35, "Date": datetime.now().strftime("%Y-%m-%d")},
        {"Symbol": "TCS", "PE": 32.1, "ROE": 43.5, "DebtToEquity": 0.05, "Date": datetime.now().strftime("%Y-%m-%d")}
    ])

def run():
    timestamp = datetime.now().isoformat()
    df = fetch_fundamentals()
    save_to_db(FUNDAMENTALS_DB, df, "fundamentals", timestamp, ["Symbol", "Date"])
    print("Fundamentals sync completed.")

if __name__ == "__main__":
    run()
