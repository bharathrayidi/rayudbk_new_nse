"""
Social Sentiment Downloader
---------------------------
Fetches mention velocity from Reddit/StockTwits.
"""

import sys
import os
from datetime import datetime
import pandas as pd

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import SENTIMENT_DB
from ingestion.db_engine import save_to_db

def fetch_social_sentiment():
    print("Fetching social sentiment data...")
    # Mock data
    return pd.DataFrame([
        {"Symbol": "RELIANCE", "Platform": "Reddit", "Mentions": 150, "SentimentScore": 0.65, "Date": datetime.now().strftime("%Y-%m-%d")},
        {"Symbol": "TCS", "Platform": "StockTwits", "Mentions": 85, "SentimentScore": 0.45, "Date": datetime.now().strftime("%Y-%m-%d")}
    ])

def run():
    timestamp = datetime.now().isoformat()
    df = fetch_social_sentiment()
    save_to_db(SENTIMENT_DB, df, "social_sentiment", timestamp, ["Symbol", "Platform", "Date"])
    print("Social sentiment sync completed.")

if __name__ == "__main__":
    run()
