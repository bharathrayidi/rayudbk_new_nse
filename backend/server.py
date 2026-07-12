"""
NSE Dashboard FastAPI Backend Server
------------------------------------
Provides REST API endpoints for:
1. Fetching the list of all ingested stocks/indices.
2. Calculating historical metrics (LTP, Change %, 52-Week Range, Volume).
3. Retrieving daily historical prices for charting.
4. Retrieving corporate announcements.
5. Dynamically parsing live Google News RSS for any stock ticker.
6. Serving AI/ML predictions, validation metrics, and pattern discovery stats.
"""

import os
import sys
import json
import sqlite3
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import math
import threading
from datetime import datetime, timedelta
import subprocess
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    STOCK_DATA_DB,
    CORPORATE_DB,
    CAPITAL_MARKET_DB,
    FUNDAMENTALS_DB,
    SENTIMENT_DB,
    MICROSTRUCTURE_DB,
    BSE_DEALS_DB,
    MARKET_BREADTH_DB
)
from ingestion.stock_downloader import download_stock_history, download_announcements

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="NSE Market Data Dashboard API")

@app.middleware("http")
async def rewrite_api_path(request, call_next):
    path = request.scope.get("path", "")
    api_prefixes = ["/stocks", "/volume-gainers", "/most-active", "/stock/", "/ai-picks", "/ai-performance", "/market/", "/system/", "/debug/", "/screener", "/macro/"]
    if any(path.startswith(p) for p in api_prefixes):
        request.scope["path"] = "/api" + path
    return await call_next(request)

@app.get("/")
def root():
    return {"message": "NSE Dashboard backend is running. Open the frontend at http://localhost:5180"}

@app.get("/api")
def api_root():
    return {
        "message": "NSE Dashboard API is running",
        "endpoints": [
            "/api/stocks",
            "/api/volume-gainers",
            "/api/most-active",
            "/api/stock/{symbol}/metrics",
            "/api/stock/{symbol}/history",
            "/api/stock/{symbol}/announcements",
            "/api/stock/{symbol}/news",
            "/api/stock/{symbol}/deep-dive"
        ]
    }

# Add CORS Middleware to allow requests from React frontend (e.g. port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection(db_name: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

# Global lock to prevent race conditions when frontend makes concurrent API calls for the same missing stock
auto_fetch_lock = threading.Lock()

def ensure_stock_history(symbol: str, table_name: str):
    """Ensures stock history exists, fetching it concurrently-safely if missing."""
    with auto_fetch_lock:
        conn = get_db_connection(STOCK_DATA_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone() is not None
        conn.close()
        
        if not exists:
            print(f"[{symbol}] Data missing. Auto-fetching on demand...")
            to_dt = datetime.now()
            from_dt = to_dt - timedelta(days=360)
            download_stock_history(symbol, from_dt.strftime("%d-%m-%Y"), to_dt.strftime("%d-%m-%Y"), to_dt.strftime("%Y-%m-%d %H:%M:%S"))
            
            # Re-check database
            conn = get_db_connection(STOCK_DATA_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail=f"Stock history for symbol '{symbol}' could not be fetched.")
            conn.close()

def ensure_announcements(symbol: str):
    """Ensures announcements exist, fetching concurrently-safely if missing."""
    with auto_fetch_lock:
        conn = get_db_connection(CORPORATE_DB)
        try:
            df_check = pd.read_sql_query("SELECT 1 FROM announcements WHERE symbol = ? LIMIT 1", conn, params=(symbol,))
            missing = df_check.empty
        except Exception:
            missing = True
        conn.close()
        
        if missing:
            print(f"[{symbol}] Announcements missing. Auto-fetching on demand...")
            to_dt = datetime.now()
            from_dt = to_dt - timedelta(days=360)
            download_announcements(symbol, from_dt.strftime("%d-%m-%Y"), to_dt.strftime("%d-%m-%Y"), to_dt.strftime("%Y-%m-%d %H:%M:%S"))

@app.get("/api/stocks")
def get_stocks():
    """Returns a list of all stocks and indices that have historical tables in the database."""
    try:
        if not os.path.exists(STOCK_DATA_DB):
            return []
            
        conn = get_db_connection(STOCK_DATA_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'hist_%'")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()
        
        # Clean symbols (e.g., hist_SBIN -> SBIN, hist_NIFTY -> NIFTY)
        symbols = sorted([t.replace("hist_", "") for t in tables])
        return symbols
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/volume-gainers")
def get_volume_gainers():
    """Returns the list of volume gainers from capital_market.db."""
    try:
        if not os.path.exists(CAPITAL_MARKET_DB):
            return []
        conn = get_db_connection(CAPITAL_MARKET_DB)
        df = pd.read_sql_query("SELECT * FROM volume_gainers", conn)
        conn.close()
        df = df.replace({np.nan: None})
        df = df.drop_duplicates(subset=["symbol"])
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/api/most-active")
def get_most_active():
    """Returns the list of most active equities from capital_market.db."""
    try:
        if not os.path.exists(CAPITAL_MARKET_DB):
            return []
        conn = get_db_connection(CAPITAL_MARKET_DB)
        df = pd.read_sql_query("SELECT * FROM most_active_equities", conn)
        conn.close()
        df = df.replace({np.nan: None})
        df = df.drop_duplicates(subset=["symbol"])
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/api/stock/{symbol}/history")
def get_stock_history(symbol: str):
    """Retrieves chronological daily price history for charting."""
    table_name = f"hist_{symbol.replace('-', '_')}"
    try:
        os.makedirs(os.path.dirname(STOCK_DATA_DB), exist_ok=True)
            
        ensure_stock_history(symbol, table_name)
            
        conn = get_db_connection(STOCK_DATA_DB)
        df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY fetchedAt ASC", conn)
        conn.close()
        
        if df.empty:
            return []
            
        # Standardize column names from NSE format to frontend format
        rename_map = {
            "ClosePrice": "Close",
            "OpenPrice": "Open", 
            "HighPrice": "High",
            "LowPrice": "Low",
            "TotalTradedQuantity": "Volume"
        }
        df = df.rename(columns=rename_map)
        
        # Clean numeric columns (remove commas)
        for col in ["Close", "Open", "High", "Low", "Volume"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", "", regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
        # Clean date column and sort chronologically
        if "Date" in df.columns:
            df["parsed_date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
            df = df.dropna(subset=["parsed_date"]).sort_values("parsed_date")
            df["formatted_date"] = df["Date"].astype(str).str.strip()
            df = df.drop(columns=["parsed_date"])
            
        # Replace NaN with None for JSON compliance
        df = df.replace({np.nan: None})
            
        # Return records as list of dicts
        return df.to_dict(orient="records")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{symbol}/metrics")
def get_stock_metrics(symbol: str):
    """Calculates key performance metrics dynamically from historical price records."""
    table_name = f"hist_{symbol.replace('-', '_')}"
    try:
        os.makedirs(os.path.dirname(STOCK_DATA_DB), exist_ok=True)
            
        ensure_stock_history(symbol, table_name)
            
        # Load historical rows
        conn = get_db_connection(STOCK_DATA_DB)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for symbol '{symbol}'.")
            
        # Standardize column names from NSE format
        rename_map = {
            "ClosePrice": "Close",
            "OpenPrice": "Open", 
            "HighPrice": "High",
            "LowPrice": "Low",
            "TotalTradedQuantity": "Volume"
        }
        df = df.rename(columns=rename_map)
            
        # Clean numeric columns (remove commas)
        for col in ["Close", "Open", "High", "Low", "Volume"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", "", regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce")
                
        # Sort chronologically by date if possible
        # Check date parsing
        if "Date" in df.columns:
            df["parsed_date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
            df = df.dropna(subset=["parsed_date"]).sort_values("parsed_date")
            
        # Get latest metrics
        latest_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else latest_row
        
        def safe_float(val):
            try:
                f = float(val)
                return 0.0 if math.isnan(f) else f
            except:
                return 0.0
        
        ltp = safe_float(latest_row["Close"])
        prev_close = safe_float(prev_row["Close"])
        change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0.0
        
        # 52 Week High and Low (past 365 calendar days or all available data)
        fifty_two_week_high = safe_float(df["High"].max())
        fifty_two_week_low = safe_float(df["Low"].min())
        avg_price = safe_float(df["Close"].mean())
        volume = int(latest_row["Volume"]) if "Volume" in latest_row and not pd.isna(latest_row["Volume"]) else 0
        
        # Read AI Predictions if available
        surge_prob = None
        patterns_detected = None
        signal_strength = None
        
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(root_dir, "databases", "ai_ideal_stocks_report.csv")
        if os.path.exists(csv_path):
            try:
                ai_df = pd.read_csv(csv_path)
                ai_row = ai_df[ai_df["Symbol"] == symbol]
                if not ai_row.empty:
                    surge_prob = float(ai_row.iloc[0]["Surge_Prob_%"])
                    patterns_detected = str(ai_row.iloc[0].get("Patterns_Detected", ""))
                    signal_strength = str(ai_row.iloc[0].get("Signal_Strength", ""))
            except Exception:
                pass

        return {
            "symbol": symbol,
            "ltp": ltp,
            "changePercent": change_pct,
            "high_52week": fifty_two_week_high,
            "low_52week": fifty_two_week_low,
            "averagePrice": avg_price,
            "volume": volume,
            "lastUpdated": str(latest_row.get("fetchedAt", "")),
            "aiSurgeProb": surge_prob,
            "aiPatterns": patterns_detected,
            "aiSignalStrength": signal_strength
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{symbol}/announcements")
def get_stock_announcements(symbol: str):
    """Retrieves corporate announcements for a given symbol."""
    try:
        os.makedirs(os.path.dirname(CORPORATE_DB), exist_ok=True)
            
        ensure_announcements(symbol)
            
        conn = get_db_connection(CORPORATE_DB)
        df = pd.read_sql_query(
            "SELECT desc, attchmntText AS desc_details, attchmntFile AS attachment, sort_date, fetchedAt "
            "FROM announcements WHERE symbol = ? ORDER BY sort_date DESC",
            conn, params=(symbol,)
        )
        conn.close()
        
        # Replace NaN with None for JSON compliance
        df = df.replace({np.nan: None})
        
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{symbol}/news")
def get_stock_news(symbol: str):
    """Fetches and parses live Google News RSS articles for a given stock symbol in India."""
    # Search query combines the stock symbol + stock + India to ensure financial relevance
    search_query = f"{symbol} stock India"
    url = f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
            
        root = ET.fromstring(response.content)
        articles = []
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            source = item.find("source").text if item.find("source") is not None else "Google News"
            
            # Remove publisher suffix from title (e.g. "Tata Motors hits high - Economic Times" -> "Tata Motors hits high")
            if " - " in title:
                title_clean = " - ".join(title.split(" - ")[:-1])
            else:
                title_clean = title
                
            articles.append({
                "title": title_clean,
                "link": link,
                "pubDate": pub_date,
                "source": source
            })
            
        return articles[:12] # Limit to top 12 articles
    except Exception as e:
        # Silently fail and return empty list on parsing/network errors so dashboard doesn't crash
        print(f"Error fetching Google News for {symbol}: {e}")
        return []

@app.get("/api/ai-picks")
def get_ai_picks(force_retrain: bool = False):
    """
    Returns the latest ML predictions from the local CSV report.
    Pass ?force_retrain=true to trigger a fresh model retraining in the background.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(root_dir, "databases", "ai_ideal_stocks_report.csv")

    if force_retrain:
        import subprocess, sys
        script_path = os.path.join(root_dir, "ml", "ml_predictor.py")
        subprocess.Popen(
            [sys.executable, script_path, "--force-retrain"],
            cwd=root_dir,
        )
        return {"status": "retraining_started", "message": "Model retraining initiated in background. Refresh /api/ai-picks in a few minutes."}

    if not os.path.exists(csv_path):
        return []
    try:
        df = pd.read_csv(csv_path)
        df = df.replace({np.nan: None})
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error reading AI picks: {e}")
        return []


@app.get("/api/ai-picks/validate")
def get_ai_validation():
    """
    Returns the 2-month temporal validation metrics for the current trained model.
    Includes accuracy, precision, recall, F1, AUC-ROC, and confusion matrix.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    metrics_path = os.path.join(root_dir, "databases", "ai_validation_metrics.json")
    if not os.path.exists(metrics_path):
        return {"error": "No validation metrics found. Run ml_predictor.py first."}
    try:
        with open(metrics_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai-picks/patterns")
def get_ai_patterns():
    """
    Returns a summary of pattern statistics from the latest AI picks report.
    Shows how many stocks triggered each pattern and their average surge probability.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(root_dir, "databases", "ai_ideal_stocks_report.csv")
    if not os.path.exists(csv_path):
        return []
    try:
        df = pd.read_csv(csv_path)
        if "Patterns_Detected" not in df.columns:
            return []

        pattern_names = ["Breakout", "Consolidation", "Gap-Up", "Accumulation",
                         "Engulfing", "Hammer", "Doji"]
        results = []
        for pat in pattern_names:
            mask = df["Patterns_Detected"].fillna("").str.contains(pat, case=False)
            subset = df[mask]
            if len(subset) == 0:
                continue
            results.append({
                "pattern":             pat,
                "stock_count":         int(len(subset)),
                "avg_surge_prob_%":    round(subset["Surge_Prob_%"].mean(), 1) if "Surge_Prob_%" in subset.columns else None,
                "top_symbols":         subset.nlargest(3, "Surge_Prob_%")["Symbol"].tolist() if "Surge_Prob_%" in subset.columns else [],
            })
        return sorted(results, key=lambda x: x["avg_surge_prob_%"] or 0, reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{symbol}/deep-dive")
def get_stock_deep_dive(symbol: str):
    """
    Returns a unified object containing deep-dive alternative data for a stock
    including Fundamentals, Sentiment, Market Microstructure, and BSE Deals.
    """
    data = {
        "fundamentals": None,
        "sentiment": None,
        "microstructure": None,
        "deals": []
    }
    
    # 1. Fundamentals
    if os.path.exists(FUNDAMENTALS_DB):
        try:
            conn = get_db_connection(FUNDAMENTALS_DB)
            df = pd.read_sql_query("SELECT * FROM fundamentals WHERE Symbol = ?", conn, params=(symbol,))
            if not df.empty:
                data["fundamentals"] = df.iloc[0].to_dict()
            conn.close()
        except: pass
        
    # 2. Sentiment
    if os.path.exists(SENTIMENT_DB):
        try:
            conn = get_db_connection(SENTIMENT_DB)
            df = pd.read_sql_query("SELECT * FROM sentiment WHERE Symbol = ? ORDER BY Date DESC LIMIT 1", conn, params=(symbol,))
            if not df.empty:
                data["sentiment"] = df.iloc[0].to_dict()
            conn.close()
        except: pass
        
    # 3. Microstructure
    if os.path.exists(MICROSTRUCTURE_DB):
        try:
            conn = get_db_connection(MICROSTRUCTURE_DB)
            df = pd.read_sql_query("SELECT * FROM microstructure WHERE Symbol = ? ORDER BY Date DESC LIMIT 1", conn, params=(symbol,))
            if not df.empty:
                data["microstructure"] = df.iloc[0].to_dict()
            conn.close()
        except: pass
        
    # 4. BSE Deals
    if os.path.exists(BSE_DEALS_DB):
        try:
            conn = get_db_connection(BSE_DEALS_DB)
            # The BSE Deals schema might use 'Security Name' or 'Symbol'
            # We will use wildcards to find if the symbol is in the security name
            df = pd.read_sql_query("SELECT * FROM deals WHERE `Security Name` LIKE ? ORDER BY Date DESC LIMIT 5", conn, params=(f"%{symbol}%",))
            if not df.empty:
                data["deals"] = df.to_dict(orient="records")
            conn.close()
        except: pass

    # Replace NaNs for JSON compliance
    import math
    def clean_nan(obj):
        if isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_nan(i) for i in obj]
        elif isinstance(obj, float) and math.isnan(obj):
            return None
        return obj

    return clean_nan(data)

@app.get("/api/market/overview")
def get_market_overview():
    """
    Returns market health statistics (Advances, Declines, VIX).
    """
    data = {
        "advances": 0,
        "declines": 0,
        "vix": 0.0,
        "date": ""
    }
    if os.path.exists(MARKET_BREADTH_DB):
        try:
            conn = get_db_connection(MARKET_BREADTH_DB)
            df = pd.read_sql_query("SELECT * FROM market_breadth ORDER BY Date DESC LIMIT 1", conn)
            if not df.empty:
                data["advances"] = int(df.iloc[0].get("Advances", 0))
                data["declines"] = int(df.iloc[0].get("Declines", 0))
                data["vix"] = float(df.iloc[0].get("VIX", 0.0))
                data["date"] = str(df.iloc[0].get("Date", ""))
            conn.close()
        except Exception as e:
            print("Error reading market overview:", e)
    return data

@app.get("/api/ai-performance")
def get_ai_performance():
    """
    Returns historical AI predictions joined with their actual realized returns.
    """
    history_db_path = os.path.join(root_dir, "databases", "ai_predictions_history.db")
    if not os.path.exists(history_db_path):
        return []

    try:
        # Fetch predictions
        conn = get_db_connection(history_db_path)
        df_pred = pd.read_sql_query("SELECT Prediction_Date, Symbol, \"Surge_Prob_%\", Confidence FROM predictions ORDER BY Prediction_Date DESC, \"Surge_Prob_%\" DESC LIMIT 100", conn)
        conn.close()

        # Fetch current market performance (pChange)
        conn = get_db_connection(CAPITAL_MARKET_DB)
        df_market = pd.read_sql_query("SELECT symbol, pChange FROM equities", conn)
        conn.close()
        
        df_market = df_market.rename(columns={"symbol": "Symbol"})
        df_market["pChange"] = pd.to_numeric(df_market["pChange"], errors='coerce').fillna(0)
        
        # Merge to get Realized Return
        df_merged = pd.merge(df_pred, df_market, on="Symbol", how="left")
        df_merged["Realized_Return_%"] = df_merged["pChange"].round(2)
        
        # Format the response
        records = df_merged.to_dict("records")
        for r in records:
            # If the prediction was made today, you might consider it "pending", but showing current pChange is fine
            if pd.isna(r["Realized_Return_%"]):
                r["Realized_Return_%"] = None
        
        return clean_nan(records)
    except Exception as e:
        print(f"Error fetching AI performance: {e}")
        return []

@app.get("/api/system/log")
def get_system_log():
    db_path = os.path.join(root_dir, "databases", "ingestion_log.db")
    if not os.path.exists(db_path):
        return []
    try:
        conn = get_db_connection(db_path)
        df = pd.read_sql_query("SELECT * FROM sync_history ORDER BY last_updated_date DESC", conn)
        conn.close()
        return df.to_dict("records")
    except Exception as e:
        return {"error": str(e)}

pipeline_state = {
    "is_running": False,
    "last_started": None
}

def run_pipeline_bg():
    global pipeline_state
    try:
        script_path = os.path.join(root_dir, "scripts", "scheduler.py")
        pipeline_state["last_started"] = datetime.now().isoformat()
        subprocess.Popen(
            [sys.executable, script_path],
            cwd=root_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as e:
        print(f"Pipeline error: {e}")
        pipeline_state["is_running"] = False


@app.post("/api/system/run-pipeline")
def start_pipeline(background_tasks: BackgroundTasks):
    global pipeline_state
    if pipeline_state["is_running"]:
        return {"status": "Already running"}

    pipeline_state["is_running"] = True
    pipeline_state["last_started"] = datetime.now().isoformat()

    background_tasks.add_task(run_pipeline_bg)
    return {"status": "Started pipeline", "last_started": pipeline_state["last_started"]}

@app.get("/api/system/pipeline-status")
def get_pipeline_status():
    global pipeline_state
    return pipeline_state

@app.get("/api/debug/test_sync")
def test_sync():
    import sys
    ingestion_dir = os.path.join(root_dir, "ingestion")
    if ingestion_dir not in sys.path:
        sys.path.insert(0, ingestion_dir)
    try:
        import sync_log
        # Test marking
        sync_log.mark_updated_today("dummy_test_job")
        # Test checking
        updated = sync_log.is_updated_today("dummy_test_job")
        not_updated = sync_log.is_updated_today("fake_job")
        return {
            "dummy_test_job_is_updated": updated,
            "fake_job_is_updated": not_updated
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug/schemas")
def get_schemas():
    db_dir = os.path.join(root_dir, "databases")
    schemas = {}
    for db_name in os.listdir(db_dir):
        if db_name.endswith('.db'):
            try:
                conn = get_db_connection(os.path.join(db_dir, db_name))
                cursor = conn.cursor()
                cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                schemas[db_name] = {t[0]: t[1] for t in tables}
                conn.close()
            except:
                pass
    return schemas

@app.get("/api/debug/fiidii")
def debug_fiidii():
    db_path = os.path.join(root_dir, "databases", "institutional.db")
    try:
        conn = get_db_connection(db_path)
        df = pd.read_sql_query("SELECT * FROM fii_dii_flows", conn)
        conn.close()
        return df.to_dict("records")
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/macro/fii-dii")
def get_fii_dii():
    """
    Returns FII/DII activity data from institutional.db
    """
    db_path = os.path.join(root_dir, "databases", "institutional.db")
    if not os.path.exists(db_path):
        return []
    try:
        conn = get_db_connection(db_path)
        df = pd.read_sql_query(f"SELECT * FROM fii_dii_flows ORDER BY Date DESC LIMIT 60", conn)
        conn.close()
        
        # Make sure FII_Net and DII_Net columns exist
        if "netValue" in df.columns and "category" in df.columns:
            # The table has 'category' (FII/DII) and 'netValue'. We need to pivot it!
            # Let's pivot it so each row is a Date, with FII_Net and DII_Net
            df_pivot = df.pivot(index="date", columns="category", values="netValue").reset_index()
            df_pivot = df_pivot.rename(columns={"date": "Date", "FII": "FII_Net", "DII": "DII_Net"})
            
            # Fill NaN with 0
            df_pivot["FII_Net"] = df_pivot["FII_Net"].fillna(0)
            df_pivot["DII_Net"] = df_pivot["DII_Net"].fillna(0)
            return clean_nan(df_pivot.to_dict("records"))
        else:
            return clean_nan(df.to_dict("records"))
    except Exception as e:
        print(f"Error reading FII/DII: {e}")
        return []

@app.get("/api/screener")
def get_screener_data():
    """
    Returns a massive joined dataset of Equities + Fundamentals + Features + Sentiment
    """
    try:
        # 1. Equities
        conn_cap = get_db_connection(CAPITAL_MARKET_DB)
        df_eq = pd.read_sql_query("SELECT symbol, companyName, pChange, ltp, previousClose, volume FROM equities", conn_cap)
        conn_cap.close()
        df_eq = df_eq.rename(columns={"symbol": "Symbol"})
        
        # 2. Fundamentals
        fund_db = os.path.join(root_dir, "databases", "fundamentals.db")
        if os.path.exists(fund_db):
            conn_fund = get_db_connection(fund_db)
            cursor = conn_fund.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
            
            if len(tables) > 0:
                table_name = tables[0] # assuming first table is the main one, maybe 'fundamentals'
                df_fund = pd.read_sql_query(f"SELECT Symbol, PE_Ratio, PB_Ratio, ROE, Debt_to_Equity FROM {table_name}", conn_fund)
                df_eq = pd.merge(df_eq, df_fund, on="Symbol", how="left")
            conn_fund.close()
            
        # 3. Features (Technical Indicators)
        feat_db = os.path.join(root_dir, "databases", "feature_store.db")
        if os.path.exists(feat_db):
            conn_feat = get_db_connection(feat_db)
            df_feat = pd.read_sql_query("SELECT Symbol, RSI, MACD_Histogram, BB_Position, \"Volume_Surge_x\" FROM daily_features", conn_feat)
            df_eq = pd.merge(df_eq, df_feat, on="Symbol", how="left")
            conn_feat.close()
            
        # 4. Sentiment
        sent_db = os.path.join(root_dir, "databases", "sentiment.db")
        if os.path.exists(sent_db):
            conn_sent = get_db_connection(sent_db)
            cursor = conn_sent.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%sentiment%'")
            tables = [row[0] for row in cursor.fetchall()]
            if tables:
                df_sent = pd.read_sql_query(f"SELECT Symbol, News_Sentiment, Social_Sentiment FROM {tables[0]}", conn_sent)
                df_eq = pd.merge(df_eq, df_sent, on="Symbol", how="left")
            conn_sent.close()
            
        # Convert numerics
        for col in ["pChange", "ltp", "PE_Ratio", "ROE", "RSI"]:
            if col in df_eq.columns:
                df_eq[col] = pd.to_numeric(df_eq[col], errors='coerce')
                
        # Drop rows with no symbol
        df_eq = df_eq.dropna(subset=["Symbol"])
        
        return clean_nan(df_eq.to_dict("records"))
        
    except Exception as e:
        print(f"Error building screener data: {e}")
        return []

# --- STATIC FILES FOR REACT APP ---
# Serve React Frontend if it's built
dist_dir = os.path.join(root_dir, "frontend", "dist")

if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    def serve_react_app(catchall: str):
        # Catchall routes everything not in /api to the React index.html
        # to support React Router history API
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(dist_dir, catchall)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
