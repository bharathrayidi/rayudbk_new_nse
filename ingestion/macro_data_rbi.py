"""
Macro Data Downloader (RBI)
---------------------------
Fetches RBI macro data like Rates, CPI, FX.
"""

import sys
import os
from datetime import datetime
import pandas as pd

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import MACRO_DATA_DB
from ingestion.db_engine import save_to_db

def fetch_macro_data():
    print("Fetching RBI macro data...")
    # Mock data
    return pd.DataFrame([
        {"Date": datetime.now().strftime("%Y-%m-%d"), "Indicator": "RepoRate", "Value": 6.5},
        {"Date": datetime.now().strftime("%Y-%m-%d"), "Indicator": "CPI", "Value": 5.1},
        {"Date": datetime.now().strftime("%Y-%m-%d"), "Indicator": "USDINR", "Value": 83.2}
    ])

def run():
    timestamp = datetime.now().isoformat()
    df = fetch_macro_data()
    save_to_db(MACRO_DATA_DB, df, "macro_indicators", timestamp, ["Date", "Indicator"])
    print("Macro data sync completed.")

if __name__ == "__main__":
    run()
