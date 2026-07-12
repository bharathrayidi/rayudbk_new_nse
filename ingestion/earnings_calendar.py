"""
Earnings Calendar Downloader
----------------------------
Fetches upcoming earnings dates and EPS surprises.
"""

import sys
import os
from datetime import datetime
import pandas as pd

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import CORPORATE_DB
from ingestion.db_engine import save_to_db

def fetch_earnings_calendar():
    print("Fetching earnings calendar...")
    # Mock data
    return pd.DataFrame([
        {"Symbol": "RELIANCE", "EarningsDate": "2024-01-20", "EPSEstimate": 25.5, "EPSActual": 26.1, "SurprisePct": 2.35},
        {"Symbol": "TCS", "EarningsDate": "2024-01-15", "EPSEstimate": 30.0, "EPSActual": 29.5, "SurprisePct": -1.67}
    ])

def run():
    timestamp = datetime.now().isoformat()
    df = fetch_earnings_calendar()
    save_to_db(CORPORATE_DB, df, "earnings_calendar", timestamp, ["Symbol", "EarningsDate"])
    print("Earnings calendar sync completed.")

if __name__ == "__main__":
    run()
