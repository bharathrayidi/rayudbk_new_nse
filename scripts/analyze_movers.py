import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add current dir to path to import config
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import STOCK_DATA_DB, CORPORATE_DB

# Analysis Parameters
MOVE_THRESHOLD_PCT = 5.0
DAYS_LOOKBACK = 30
OUTPUT_CSV = os.path.join(root_dir, "high_movers_analysis.csv")

def get_db_connection(db_name: str) -> sqlite3.Connection:
    return sqlite3.connect(db_name)

def analyze_movers():
    print(f"==================================================")
    print(f" Stock Mover & News Correlation Analysis")
    print(f"==================================================")
    print(f"Threshold: > {MOVE_THRESHOLD_PCT}% move in a single day")
    print(f"Timeframe: Last {DAYS_LOOKBACK} days")
    print(f"==================================================\n")

    if not os.path.exists(STOCK_DATA_DB):
        print("Error: Stock database not found.")
        return

    # 1. Connect to both DBs
    stock_conn = get_db_connection(STOCK_DATA_DB)
    corp_conn = get_db_connection(CORPORATE_DB)

    # Calculate date limit
    cutoff_date = datetime.now() - timedelta(days=DAYS_LOOKBACK)

    cursor = stock_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'hist_%'")
    tables = [row[0] for row in cursor.fetchall()]

    results = []

    print(f"Analyzing {len(tables)} stock tables...")

    for table in tables:
        symbol = table.replace("hist_", "").replace("_", "-")
        
        # Load the last 30 days of price data for this symbol
        # We fetch extra days to compute the previous close properly
        try:
            df = pd.read_sql_query(f'SELECT Date, ClosePrice, OpenPrice, HighPrice, LowPrice, TotalTradedQuantity FROM "{table}"', stock_conn)
        except Exception:
            # Skip tables like NIFTY that do not have the expected column structure
            continue
            
        if df.empty or 'Date' not in df.columns or 'ClosePrice' not in df.columns:
            continue
            
        # Parse dates
        df['parsed_date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y', errors='coerce')
        df = df.dropna(subset=['parsed_date'])
        df = df.sort_values('parsed_date').reset_index(drop=True)
        
        if df.empty:
            continue

        # Clean ClosePrice (remove commas, cast to float)
        df['ClosePrice'] = df['ClosePrice'].astype(str).str.replace(',', '', regex=True)
        df['ClosePrice'] = pd.to_numeric(df['ClosePrice'], errors='coerce')
        df = df.dropna(subset=['ClosePrice'])
        
        # Calculate daily percentage change
        df['PrevClose'] = df['ClosePrice'].shift(1)
        df['PctChange'] = ((df['ClosePrice'] - df['PrevClose']) / df['PrevClose']) * 100
        
        # Filter for the last X days and threshold
        recent_df = df[df['parsed_date'] >= cutoff_date]
        surges = recent_df[recent_df['PctChange'].abs() >= MOVE_THRESHOLD_PCT]

        for _, row in surges.iterrows():
            surge_date = row['parsed_date']
            surge_date_str = surge_date.strftime('%Y-%m-%d')
            prev_date_str = (surge_date - timedelta(days=1)).strftime('%Y-%m-%d')
            pct_change = row['PctChange']
            
            # Check for announcements on T-1 or T-0
            # sort_date in db is usually YYYY-MM-DD HH:MM:SS
            ann_query = """
            SELECT sort_date, desc, attchmntText
            FROM announcements 
            WHERE symbol = ? 
            AND (DATE(sort_date) = ? OR DATE(sort_date) = ?)
            """
            
            ann_df = pd.DataFrame()
            try:
                ann_df = pd.read_sql_query(ann_query, corp_conn, params=(symbol, prev_date_str, surge_date_str))
            except Exception as e:
                # Table might not exist or be empty yet
                pass
            
            ann_count = len(ann_df)
            ann_titles = " | ".join(ann_df['desc'].dropna().tolist()) if ann_count > 0 else "None"
            
            results.append({
                "Symbol": symbol,
                "Date": surge_date_str,
                "Close": row['ClosePrice'],
                "% Move": round(pct_change, 2),
                "Announcements Count (T-0/T-1)": ann_count,
                "Announcement Headlines": ann_titles
            })

    stock_conn.close()
    corp_conn.close()

    if not results:
        print("No significant moves found in the timeframe.")
        return

    # Save to CSV and print summary
    results_df = pd.DataFrame(results)
    # Sort by absolute move descending
    results_df['AbsMove'] = results_df['% Move'].abs()
    results_df = results_df.sort_values(by=['AbsMove'], ascending=False).drop(columns=['AbsMove'])
    
    results_df.to_csv(OUTPUT_CSV, index=False)
    
    # Calculate Correlation metric
    total_surges = len(results_df)
    surges_with_news = len(results_df[results_df['Announcements Count (T-0/T-1)'] > 0])
    correlation_pct = (surges_with_news / total_surges) * 100 if total_surges > 0 else 0
    
    print(f"\n--- Analysis Complete ---")
    print(f"Found {total_surges} instances where a stock moved > {MOVE_THRESHOLD_PCT}%.")
    print(f"{surges_with_news} of these moves ({correlation_pct:.1f}%) were preceded by or occurred on the same day as a corporate announcement.")
    print(f"\nReport saved to: {OUTPUT_CSV}")
    print(f"\nTop 10 High Movers:\n")
    print(results_df.head(10).to_string(index=False))

if __name__ == "__main__":
    analyze_movers()
