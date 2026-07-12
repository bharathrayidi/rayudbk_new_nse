"""
BSE Bulk/Block Deals Downloader
-------------------------------
Fetches daily bulk and block deals from BSE API.
"""

import sys
import os
from datetime import datetime
import pandas as pd
import requests

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import BSE_DEALS_DB
from ingestion.db_engine import save_to_db

def fetch_bse_deals(deal_type="bulk"):
    """
    Mock/Stub for fetching BSE deals from bseindia.com API.
    In a real implementation, this would hit the bseindia.com AJAX endpoints.
    """
    # NOTE: BSE India's actual API requires specific headers and session cookies.
    # We are generating a dummy dataframe for the architecture scaffolding.
    print(f"Fetching {deal_type} deals from BSE...")
    
    # Mock data
    data = [
        {"Symbol": "RELIANCE", "ClientName": "MOCK FUND A", "DealType": "BUY", "Quantity": 1500000, "Price": 2500.5},
        {"Symbol": "TCS", "ClientName": "MOCK FUND B", "DealType": "SELL", "Quantity": 800000, "Price": 3400.0},
    ]
    df = pd.DataFrame(data)
    df["Date"] = datetime.now().strftime("%Y-%m-%d")
    df["Type"] = deal_type
    return df

def run():
    timestamp = datetime.now().isoformat()
    bulk_df = fetch_bse_deals("bulk")
    block_df = fetch_bse_deals("block")
    
    deals_df = pd.concat([bulk_df, block_df], ignore_index=True)
    
    save_to_db(
        BSE_DEALS_DB,
        deals_df,
        "bse_deals",
        timestamp,
        ["Symbol", "ClientName", "Date", "DealType", "Type"]
    )
    print("BSE Deals sync completed.")

if __name__ == "__main__":
    run()
