"""
Market Breadth & India VIX Downloader
-------------------------------------
Fetches advances/declines, Put-Call ratio, and India VIX index data.
"""

import sys
import os
from datetime import datetime
import pandas as pd
import requests

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import MARKET_BREADTH_DB, OPTION_CHAIN_DB
from ingestion.db_engine import save_to_db

def fetch_india_vix():
    """
    Mock fetch for India VIX. Real implementation could use nsepython or NSE API.
    """
    print("Fetching India VIX...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    return pd.DataFrame([
        {"Date": date_str, "Index": "INDIA VIX", "Close": 14.5, "PreviousClose": 14.2, "Change": 0.3}
    ])

def fetch_market_breadth():
    """
    Mock fetch for Market Breadth (Advances/Declines).
    """
    print("Fetching Market Breadth...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    return pd.DataFrame([
        {"Date": date_str, "Advances": 1200, "Declines": 800, "Unchanged": 50, "Total": 2050}
    ])

def run():
    timestamp = datetime.now().isoformat()
    
    vix_df = fetch_india_vix()
    breadth_df = fetch_market_breadth()
    
    save_to_db(
        MARKET_BREADTH_DB,
        vix_df,
        "india_vix",
        timestamp,
        ["Date", "Index"]
    )
    
    save_to_db(
        MARKET_BREADTH_DB,
        breadth_df,
        "market_breadth",
        timestamp,
        ["Date"]
    )
    
    print("Market Breadth & VIX sync completed.")

if __name__ == "__main__":
    run()
