"""
Feature Store Engine
--------------------
Merges data from all SQLite databases into a unified daily snapshot per symbol.
Outputs to feature_store.db (or parquet) for ML predictor.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import (
    STOCK_DATA_DB, CAPITAL_MARKET_DB, DERIVATIVES_MARKET_DB,
    CORPORATE_DB, BSE_DEALS_DB, MACRO_DATA_DB, SENTIMENT_DB,
    FUNDAMENTALS_DB, INSTITUTIONAL_DB, MARKET_BREADTH_DB,
    MICROSTRUCTURE_DB, FEATURE_STORE_DB
)

def load_table(db_path, query):
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error loading from {db_path}: {e}")
        return pd.DataFrame()

def build_feature_store():
    print("Building Feature Store...")
    
    # 1. Base Stock Data (Price history)
    # stock_data.db has tables like hist_RELIANCE
    df_stock = pd.DataFrame()
    if os.path.exists(STOCK_DATA_DB):
        try:
            with sqlite3.connect(STOCK_DATA_DB) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'hist_%'")
                tables = [row[0] for row in cursor.fetchall()]
                
                dfs = []
                for tbl in tables:
                    symbol = tbl.replace("hist_", "").replace("_", "-")
                    df_sym = pd.read_sql(f"SELECT * FROM {tbl}", conn)
                    df_sym["Symbol"] = symbol
                    dfs.append(df_sym)
                
                if dfs:
                    df_stock = pd.concat(dfs, ignore_index=True)
        except Exception as e:
            print(f"Error loading from stock_data.db: {e}")

    if df_stock.empty:
        print("No stock history found. Feature store build aborted.")
        return
    
    if "Date" not in df_stock.columns and "TIMESTAMP" in df_stock.columns:
        df_stock["Date"] = pd.to_datetime(df_stock["TIMESTAMP"]).dt.strftime('%Y-%m-%d')
    elif "Date" in df_stock.columns:
        df_stock["Date"] = pd.to_datetime(df_stock["Date"]).dt.strftime('%Y-%m-%d')
    else:
        print("Date column missing in stock history. Ensure proper formatting.")
        return

    # Ensure Symbol is clean
    if "SYMBOL" in df_stock.columns and "Symbol" not in df_stock.columns:
        df_stock.rename(columns={"SYMBOL": "Symbol"}, inplace=True)
    
    df_stock["Symbol"] = df_stock["Symbol"].astype(str).str.strip()
    
    # Sort for rolling merges
    df_stock = df_stock.sort_values(["Symbol", "Date"])
    
    merged_df = df_stock.copy()

    # Helper function to merge Symbol-Date tables
    def merge_symbol_date(base_df, db_path, table_name, df_cols=None):
        if not os.path.exists(db_path):
            return base_df
        try:
            with sqlite3.connect(db_path) as conn:
                # check if table exists
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    return base_df
                
                query = f"SELECT * FROM {table_name}"
                df = pd.read_sql(query, conn)
                
                if "Date" not in df.columns or "Symbol" not in df.columns:
                    # If columns are named differently, try to adapt or skip
                    return base_df
                
                df["Date"] = pd.to_datetime(df["Date"]).dt.strftime('%Y-%m-%d')
                df["Symbol"] = df["Symbol"].astype(str).str.strip()
                
                if df_cols:
                    df = df[["Symbol", "Date"] + df_cols]
                    
                return pd.merge(base_df, df, on=["Symbol", "Date"], how="left")
        except Exception as e:
            print(f"Error merging {table_name}: {e}")
            return base_df

    # Merge Fundamentals
    merged_df = merge_symbol_date(merged_df, FUNDAMENTALS_DB, "fundamentals", ["PE", "ROE", "DebtToEquity"])
    
    # Merge Social Sentiment
    merged_df = merge_symbol_date(merged_df, SENTIMENT_DB, "social_sentiment", ["Mentions", "SentimentScore"])
    
    # Merge Microstructure
    merged_df = merge_symbol_date(merged_df, MICROSTRUCTURE_DB, "microstructure_daily", ["BidAskSpread", "L2Imbalance", "VWAP", "DeliveryPct"])
    
    # Global/Market Features (Merge by Date only)
    def merge_date_only(base_df, db_path, table_name, prefix=""):
        if not os.path.exists(db_path):
            return base_df
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    return base_df
                
                df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                if "Date" not in df.columns and "date" in df.columns:
                    df.rename(columns={"date": "Date"}, inplace=True)
                if "Date" not in df.columns:
                    return base_df
                
                df["Date"] = pd.to_datetime(df["Date"]).dt.strftime('%Y-%m-%d')
                
                # For indicator tables, we might need pivot
                if "Indicator" in df.columns and "Value" in df.columns:
                    df = df.pivot_table(index="Date", columns="Indicator", values="Value").reset_index()
                elif "category" in df.columns and "netValue" in df.columns:
                    df = df.pivot_table(index="Date", columns="category", values="netValue").reset_index()
                    df.rename(columns={"FII": "FII_Net", "DII": "DII_Net"}, inplace=True)
                elif "Index" in df.columns and "Close" in df.columns:
                    df = df.pivot_table(index="Date", columns="Index", values="Close").reset_index()
                    df.rename(columns={"INDIA VIX": "India_VIX_Close"}, inplace=True)
                
                if prefix:
                    df.columns = [f"{prefix}_{c}" if c != "Date" else c for c in df.columns]
                
                return pd.merge(base_df, df, on="Date", how="left")
        except Exception as e:
            print(f"Error merging {table_name} by date: {e}")
            return base_df
            
    # Merge Macro
    merged_df = merge_date_only(merged_df, MACRO_DATA_DB, "macro_indicators")
    # Merge Institutional
    merged_df = merge_date_only(merged_df, INSTITUTIONAL_DB, "fii_dii_flows")
    # Merge VIX
    merged_df = merge_date_only(merged_df, MARKET_BREADTH_DB, "india_vix")
    
    # Fill forwards for daily macro/global data that might not be available on weekends but stock traded? 
    # Usually stock data is only on trading days. We fill forward just in case.
    merged_df.fillna(method='ffill', inplace=True)
    
    # Save to Feature Store DB
    with sqlite3.connect(FEATURE_STORE_DB) as conn:
        merged_df.to_sql("daily_features", conn, if_exists="replace", index=False)
        
    print(f"Feature store built successfully! Rows: {len(merged_df)}, Columns: {len(merged_df.columns)}")
    print(f"Saved to {FEATURE_STORE_DB}")

if __name__ == "__main__":
    build_feature_store()
