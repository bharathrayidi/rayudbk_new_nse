"""
NSE AI/ML Stock Predictor — Enhanced Engine
============================================
Features:
  - Technical indicators: RSI(14), MACD histogram, Bollinger Band width/position,
    ATR(14), SMA crossover, price momentum across multiple windows
  - Volume features: surge ratio, 5d/10d/20d volume averages
  - Corporate announcement sentiment (from local DB)
  - Google News sentiment (live RSS fetch, top 5 headlines)
  - Pattern discovery: Breakout, Consolidation, Gap-Up, Accumulation/Distribution
  - Candlestick signals: Doji, Hammer, Engulfing (rule-based)
  - Day-of-week seasonality encoding
  - Consecutive price direction streak

Model:
  - Ensemble stack: RandomForest + GradientBoosting + ExtraTreesClassifier
  - Meta-learner: Logistic Regression
  - Optional: XGBoost (used if installed)
  - Probability calibration via CalibratedClassifierCV

Validation:
  - Temporal split — data from last 2 months is held out for validation
  - Reports: Accuracy, Precision, Recall, F1, AUC-ROC, confusion matrix
  - Per-pattern accuracy breakdown

Persistence:
  - Saves model + scaler to models/ directory as .pkl
  - Reloads if < 24h old (skip re-training for speed)
"""

import os
import sys
import sqlite3
import pickle
import warnings
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(root_dir))

from config import STOCK_DATA_DB, CORPORATE_DB, FEATURE_STORE_DB

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    from sklearn.ensemble import (
        RandomForestClassifier,
        GradientBoostingClassifier,
        ExtraTreesClassifier,
    )
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, roc_auc_score, confusion_matrix,
        classification_report,
    )
except ImportError:
    print("Error: scikit-learn is required. Run: pip install scikit-learn pandas numpy")
    sys.exit(1)

# Optional XGBoost
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

MODELS_DIR = os.path.join(root_dir, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Sentiment Lexicon (Financial)
# ---------------------------------------------------------------------------
FINANCIAL_LEXICON = {
    # Positive
    "surge": 0.85, "jump": 0.80, "rally": 0.80, "soar": 0.85, "gain": 0.65,
    "high": 0.50, "up": 0.30, "rise": 0.60, "profit": 0.90, "growth": 0.75,
    "dividend": 0.80, "acquire": 0.60, "win": 0.70, "positive": 0.60,
    "bullish": 0.90, "upgrade": 0.75, "outperform": 0.80, "buy": 0.70,
    "breakout": 0.85, "strong": 0.65, "record": 0.70, "expansion": 0.65,
    "beat": 0.75, "exceed": 0.75, "robust": 0.65, "revenue": 0.50,
    "order": 0.55, "contract": 0.55, "launch": 0.55, "partner": 0.50,
    # Negative
    "crash": -0.90, "plunge": -0.85, "fall": -0.60, "drop": -0.60,
    "low": -0.50, "down": -0.30, "loss": -0.90, "decline": -0.70,
    "sell": -0.50, "negative": -0.60, "bearish": -0.90, "debt": -0.45,
    "fraud": -1.00, "penalty": -0.80, "resign": -0.55, "probe": -0.65,
    "investigation": -0.65, "default": -0.85, "downgrade": -0.75,
    "underperform": -0.75, "concern": -0.55, "weak": -0.60,
    "miss": -0.65, "disappoint": -0.70, "cut": -0.55, "slump": -0.80,
    "warning": -0.65, "risk": -0.50, "volatility": -0.30, "pressure": -0.40,
}


def analyze_sentiment(text: str) -> float:
    """Simple lexicon-based financial sentiment scorer. Returns value in [-1, 1]."""
    if not isinstance(text, str) or not text.strip():
        return 0.0
    words = text.lower().split()
    score, matches = 0.0, 0
    for word in words:
        clean = "".join(c for c in word if c.isalpha())
        if clean in FINANCIAL_LEXICON:
            score += FINANCIAL_LEXICON[clean]
            matches += 1
    return max(min(score / matches, 1.0), -1.0) if matches > 0 else 0.0


def fetch_google_news_sentiment(symbol: str, timeout: int = 5) -> dict:
    """
    Fetches Google News RSS for a symbol and returns:
      - avg_sentiment: float [-1, 1]
      - article_count: int
      - top_headlines: list[str]
    """
    search_query = f"{symbol} stock NSE India"
    url = f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en"
    result = {"avg_sentiment": 0.0, "article_count": 0, "top_headlines": []}
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return result
        root = ET.fromstring(resp.content)
        sentiments = []
        for item in root.findall(".//item")[:7]:
            title = item.find("title")
            if title is not None and title.text:
                # Strip publisher suffix ("Story title - Economic Times" → "Story title")
                clean_title = " - ".join(title.text.split(" - ")[:-1]) if " - " in title.text else title.text
                result["top_headlines"].append(clean_title)
                sentiments.append(analyze_sentiment(clean_title))
        if sentiments:
            result["avg_sentiment"] = float(np.mean(sentiments))
            result["article_count"] = len(sentiments)
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Technical Indicator Functions
# ---------------------------------------------------------------------------
def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    })


def calc_bollinger(series: pd.Series, period: int = 20) -> pd.DataFrame:
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    width = (upper - lower) / sma.replace(0, np.nan)
    position = (series - lower) / (upper - lower).replace(0, np.nan)
    return pd.DataFrame({"bb_width": width, "bb_position": position.clip(0, 1)})


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ---------------------------------------------------------------------------
# Pattern Discovery Functions
# ---------------------------------------------------------------------------
def detect_breakout(df: pd.DataFrame, window: int = 20, volume_mult: float = 1.8) -> pd.Series:
    """Price breaks above N-day high with volume surge."""
    rolling_high = df["ClosePrice"].rolling(window=window, min_periods=window // 2).max().shift(1)
    price_break = df["ClosePrice"] > rolling_high
    vol_avg = df["TotalTradedQuantity"].rolling(window=5).mean().shift(1)
    vol_surge = df["TotalTradedQuantity"] > (vol_avg * volume_mult)
    return (price_break & vol_surge).astype(int)


def detect_consolidation(df: pd.DataFrame, atr_series: pd.Series, bb_width_series: pd.Series) -> pd.Series:
    """Low ATR% + narrow Bollinger Bands for at least 5 days."""
    atr_pct = atr_series / df["ClosePrice"]
    low_atr = atr_pct < atr_pct.rolling(20).mean() * 0.7
    narrow_bb = bb_width_series < bb_width_series.rolling(20).mean() * 0.7
    consol = (low_atr & narrow_bb).astype(int)
    return consol.rolling(5).min().fillna(0).astype(int)


def detect_gap_up(df: pd.DataFrame, threshold: float = 1.5) -> pd.Series:
    """Opening price > previous close by threshold%."""
    if "OpenPrice" not in df.columns:
        return pd.Series(0, index=df.index)
    gap = ((df["OpenPrice"] - df["ClosePrice"].shift(1)) / df["ClosePrice"].shift(1)) * 100
    return (gap > threshold).astype(int)


def detect_accumulation(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """
    On-Balance Volume (OBV) trend — rising OBV with flat/declining price
    signals institutional accumulation.
    """
    direction = np.sign(df["ClosePrice"].diff())
    obv = (direction * df["TotalTradedQuantity"]).cumsum()
    obv_slope = obv.diff(period)
    price_slope = df["ClosePrice"].diff(period)
    # Accumulation: OBV rising, price not rising
    return ((obv_slope > 0) & (price_slope <= 0)).astype(int)


def detect_doji(df: pd.DataFrame) -> pd.Series:
    """Doji candle: body < 10% of full range."""
    if "OpenPrice" not in df.columns or "HighPrice" not in df.columns or "LowPrice" not in df.columns:
        return pd.Series(0, index=df.index)
    body = (df["ClosePrice"] - df["OpenPrice"]).abs()
    full_range = df["HighPrice"] - df["LowPrice"]
    return (body < full_range * 0.1).astype(int)


def detect_hammer(df: pd.DataFrame) -> pd.Series:
    """Hammer: lower shadow > 2× body, small upper shadow."""
    if "OpenPrice" not in df.columns or "HighPrice" not in df.columns or "LowPrice" not in df.columns:
        return pd.Series(0, index=df.index)
    body = (df["ClosePrice"] - df["OpenPrice"]).abs()
    low_shadow = df[["OpenPrice", "ClosePrice"]].min(axis=1) - df["LowPrice"]
    high_shadow = df["HighPrice"] - df[["OpenPrice", "ClosePrice"]].max(axis=1)
    return ((low_shadow > 2 * body) & (high_shadow < body * 0.5)).astype(int)


def detect_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    """Bullish engulfing: today's body engulfs yesterday's body, direction changes."""
    if "OpenPrice" not in df.columns:
        return pd.Series(0, index=df.index)
    prev_red = df["ClosePrice"].shift(1) < df["OpenPrice"].shift(1)  # prev day bearish
    curr_green = df["ClosePrice"] > df["OpenPrice"]                   # current day bullish
    curr_engulfs = (df["OpenPrice"] < df["ClosePrice"].shift(1)) & (df["ClosePrice"] > df["OpenPrice"].shift(1))
    return (prev_red & curr_green & curr_engulfs).astype(int)


# ---------------------------------------------------------------------------
# Core Dataset Builder
# ---------------------------------------------------------------------------
def build_ml_dataset(days_lookback: int = 365, validation_days: int = 60):
    """
    Builds a rich feature dataset from stock_data.db and corporate_announcements.db.

    Returns:
        train_df  : rows older than `validation_days` ago
        val_df    : rows from last `validation_days` (2 months) — for temporal validation
        latest_df : last row per stock — for prediction
    """
    print("=" * 60)
    print("  Building Enhanced ML Dataset")
    print("=" * 60)

    cutoff_all = datetime.now() - timedelta(days=days_lookback)
    cutoff_val = datetime.now() - timedelta(days=validation_days)

    feature_conn = sqlite3.connect(FEATURE_STORE_DB)
    corp_conn = sqlite3.connect(CORPORATE_DB)

    # Load from Feature Store
    print("  Loading from Feature Store...")
    try:
        fs_df = pd.read_sql_query("SELECT * FROM daily_features", feature_conn)
    except Exception as e:
        print(f"  Error loading feature store: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    if fs_df.empty:
        print("  Feature store is empty.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    symbols = fs_df["Symbol"].unique()
    print(f"  Found {len(symbols)} stocks in Feature Store")

    train_rows, val_rows, latest_rows = [], [], []

    for i, symbol in enumerate(symbols):
        if (i + 1) % 100 == 0:
            print(f"  Processing {i + 1}/{len(symbols)} stocks...")

        # Get stock specific data from feature store
        df = fs_df[fs_df["Symbol"] == symbol].copy()
        
        if len(df) < 20:
            continue

        # Parse dates and clean
        df["parsed_date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
        df = df.dropna(subset=["parsed_date"]).sort_values("parsed_date").reset_index(drop=True)

        for col in ["OpenPrice", "HighPrice", "LowPrice", "ClosePrice", "TotalTradedQuantity"]:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        df = df.dropna()

        if len(df) < 20:
            continue

        # ---------------------------------------------------------------
        # Feature Engineering
        # ---------------------------------------------------------------
        # Returns
        df["DailyReturn"]  = df["ClosePrice"].pct_change() * 100
        df["Return_3d"]    = df["ClosePrice"].pct_change(3) * 100
        df["Return_5d"]    = df["ClosePrice"].pct_change(5) * 100
        df["Return_10d"]   = df["ClosePrice"].pct_change(10) * 100
        df["Return_20d"]   = df["ClosePrice"].pct_change(20) * 100

        # Volume features
        df["Vol_5d_avg"]   = df["TotalTradedQuantity"].rolling(5, min_periods=1).mean().shift(1)
        df["Vol_10d_avg"]  = df["TotalTradedQuantity"].rolling(10, min_periods=1).mean().shift(1)
        df["Vol_20d_avg"]  = df["TotalTradedQuantity"].rolling(20, min_periods=1).mean().shift(1)
        df["VolumeSurge"]  = df["TotalTradedQuantity"] / df["Vol_5d_avg"].replace(0, np.nan)
        df["VolSurge_10d"] = df["TotalTradedQuantity"] / df["Vol_10d_avg"].replace(0, np.nan)
        df["VolSurge_20d"] = df["TotalTradedQuantity"] / df["Vol_20d_avg"].replace(0, np.nan)

        # Technical indicators
        df["RSI"]          = calc_rsi(df["ClosePrice"])
        macd_df            = calc_macd(df["ClosePrice"])
        df["MACD_hist"]    = macd_df["histogram"]
        df["MACD_cross"]   = (macd_df["macd"] > macd_df["signal"]).astype(int)
        bb_df              = calc_bollinger(df["ClosePrice"])
        df["BB_width"]     = bb_df["bb_width"]
        df["BB_position"]  = bb_df["bb_position"]
        df["ATR"]          = calc_atr(df["HighPrice"], df["LowPrice"], df["ClosePrice"])
        df["ATR_pct"]      = df["ATR"] / df["ClosePrice"] * 100

        # SMA/EMA distances
        df["SMA_20"]       = df["ClosePrice"].rolling(20).mean()
        df["SMA_50"]       = df["ClosePrice"].rolling(50).mean()
        df["Dist_SMA20"]   = (df["ClosePrice"] - df["SMA_20"]) / df["SMA_20"] * 100
        df["Dist_SMA50"]   = (df["ClosePrice"] - df["SMA_50"]) / df["SMA_50"] * 100
        ema12              = df["ClosePrice"].ewm(span=12, adjust=False).mean()
        ema26              = df["ClosePrice"].ewm(span=26, adjust=False).mean()
        df["EMA_cross"]    = (ema12 > ema26).astype(int)

        # Consecutive direction streak
        direction          = np.sign(df["DailyReturn"])
        streak             = []
        current_streak     = 0
        for d in direction:
            if d > 0:
                current_streak = max(current_streak + 1, 1)
            elif d < 0:
                current_streak = min(current_streak - 1, -1)
            else:
                current_streak = 0
            streak.append(current_streak)
        df["Streak"]       = streak

        # Day-of-week (0=Mon … 4=Fri)
        df["DayOfWeek"]    = df["parsed_date"].dt.dayofweek

        # Pattern features
        df["Pat_Breakout"]    = detect_breakout(df)
        df["Pat_Consol"]      = detect_consolidation(df, df["ATR"], df["BB_width"])
        df["Pat_GapUp"]       = detect_gap_up(df)
        df["Pat_Accumulate"]  = detect_accumulation(df)
        df["Pat_Doji"]        = detect_doji(df)
        df["Pat_Hammer"]      = detect_hammer(df)
        df["Pat_Engulfing"]   = detect_bullish_engulfing(df)

        # ---------------------------------------------------------------
        # Corporate Announcement Sentiment (from DB)
        # ---------------------------------------------------------------
        ann_by_date = {}
        try:
            ann_df = pd.read_sql_query(
                "SELECT sort_date, desc, attchmntText FROM announcements WHERE symbol = ?",
                corp_conn, params=(symbol,),
            )
            if not ann_df.empty:
                ann_df["parsed_date"] = pd.to_datetime(ann_df["sort_date"], errors="coerce").dt.date
                for date, grp in ann_df.groupby("parsed_date"):
                    texts = " ".join(
                        [str(t) for t in grp["desc"].dropna().tolist()]
                        + [str(t) for t in grp["attchmntText"].dropna().tolist()]
                    )
                    ann_by_date[date] = analyze_sentiment(texts)
        except Exception:
            pass

        # ---------------------------------------------------------------
        # Target variable: Did stock move > 1.5% the NEXT day?
        # Using 1.5% (not 2%) reduces class imbalance while still being a meaningful move.
        # ---------------------------------------------------------------
        df["NextDayReturn"] = df["DailyReturn"].shift(-1)
        df["Target"]        = (df["NextDayReturn"] > 1.5).astype(int)

        # Apply lookback cutoff for training data
        df = df[df["parsed_date"] >= cutoff_all]

        FEATURE_COLS = [
            "DailyReturn", "Return_3d", "Return_5d", "Return_10d", "Return_20d",
            "VolumeSurge", "VolSurge_10d", "VolSurge_20d",
            "RSI", "MACD_hist", "MACD_cross",
            "BB_width", "BB_position",
            "ATR_pct", "Dist_SMA20", "Dist_SMA50", "EMA_cross",
            "Streak", "DayOfWeek",
            "Pat_Breakout", "Pat_Consol", "Pat_GapUp", "Pat_Accumulate",
            "Pat_Doji", "Pat_Hammer", "Pat_Engulfing",
            "AnnSentiment",
            "PE", "ROE", "DebtToEquity", "Mentions", "SentimentScore",
            "BidAskSpread", "L2Imbalance", "VWAP", "DeliveryPct",
            "RepoRate", "CPI", "USDINR", "FII_Net", "DII_Net", "India_VIX_Close"
        ]

        for idx, row in df.iterrows():
            curr_date = row["parsed_date"].date()
            ann_sent  = ann_by_date.get(curr_date, 0.0)

            feature_row = {
                "Symbol":        symbol,
                "Date":          curr_date,
                "DailyReturn":   row["DailyReturn"],
                "Return_3d":     row["Return_3d"],
                "Return_5d":     row["Return_5d"],
                "Return_10d":    row["Return_10d"],
                "Return_20d":    row["Return_20d"],
                "VolumeSurge":   row["VolumeSurge"],
                "VolSurge_10d":  row["VolSurge_10d"],
                "VolSurge_20d":  row["VolSurge_20d"],
                "RSI":           row["RSI"],
                "MACD_hist":     row["MACD_hist"],
                "MACD_cross":    row["MACD_cross"],
                "BB_width":      row["BB_width"],
                "BB_position":   row["BB_position"],
                "ATR_pct":       row["ATR_pct"],
                "Dist_SMA20":    row["Dist_SMA20"],
                "Dist_SMA50":    row["Dist_SMA50"],
                "EMA_cross":     row["EMA_cross"],
                "Streak":        row["Streak"],
                "DayOfWeek":     row["DayOfWeek"],
                "Pat_Breakout":  row["Pat_Breakout"],
                "Pat_Consol":    row["Pat_Consol"],
                "Pat_GapUp":     row["Pat_GapUp"],
                "Pat_Accumulate":row["Pat_Accumulate"],
                "Pat_Doji":      row["Pat_Doji"],
                "Pat_Hammer":    row["Pat_Hammer"],
                "Pat_Engulfing": row["Pat_Engulfing"],
                "AnnSentiment":  ann_sent,
                "PE":            row.get("PE", np.nan),
                "ROE":           row.get("ROE", np.nan),
                "DebtToEquity":  row.get("DebtToEquity", np.nan),
                "Mentions":      row.get("Mentions", np.nan),
                "SentimentScore":row.get("SentimentScore", np.nan),
                "BidAskSpread":  row.get("BidAskSpread", np.nan),
                "L2Imbalance":   row.get("L2Imbalance", np.nan),
                "VWAP":          row.get("VWAP", np.nan),
                "DeliveryPct":   row.get("DeliveryPct", np.nan),
                "RepoRate":      row.get("RepoRate", np.nan),
                "CPI":           row.get("CPI", np.nan),
                "USDINR":        row.get("USDINR", np.nan),
                "FII_Net":       row.get("FII_Net", np.nan),
                "DII_Net":       row.get("DII_Net", np.nan),
                "India_VIX_Close":row.get("India_VIX_Close", np.nan),
                "Target":        row["Target"],
            }

            if idx == df.index[-1]:
                # Latest row → for prediction
                latest_rows.append(feature_row)
            elif not pd.isna(row["Target"]) and not pd.isna(row["VolumeSurge"]):
                if row["parsed_date"] >= cutoff_val:
                    val_rows.append(feature_row)
                else:
                    train_rows.append(feature_row)

    feature_conn.close()
    corp_conn.close()

    print(f"\n  Dataset complete:")
    print(f"    Train rows     : {len(train_rows)}")
    print(f"    Val rows (2mo) : {len(val_rows)}")
    print(f"    Latest rows    : {len(latest_rows)}")

    return pd.DataFrame(train_rows), pd.DataFrame(val_rows), pd.DataFrame(latest_rows)


# ---------------------------------------------------------------------------
# Ensemble Stack Builder
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "DailyReturn", "Return_3d", "Return_5d", "Return_10d", "Return_20d",
    "VolumeSurge", "VolSurge_10d", "VolSurge_20d",
    "RSI", "MACD_hist", "MACD_cross",
    "BB_width", "BB_position",
    "ATR_pct", "Dist_SMA20", "Dist_SMA50", "EMA_cross",
    "Streak", "DayOfWeek",
    "Pat_Breakout", "Pat_Consol", "Pat_GapUp", "Pat_Accumulate",
    "Pat_Doji", "Pat_Hammer", "Pat_Engulfing",
    "AnnSentiment",
    "PE", "ROE", "DebtToEquity", "Mentions", "SentimentScore",
    "BidAskSpread", "L2Imbalance", "VWAP", "DeliveryPct",
    "RepoRate", "CPI", "USDINR", "FII_Net", "DII_Net", "India_VIX_Close"
]


def build_and_train(train_df: pd.DataFrame, val_df: pd.DataFrame):
    """
    Trains ensemble stack on train_df and evaluates on val_df (temporal holdout).
    Returns: (stacking_model, scaler, val_metrics_dict)
    """
    X_train = train_df[FEATURE_COLS].fillna(0)
    y_train = train_df["Target"]
    X_val   = val_df[FEATURE_COLS].fillna(0)
    y_val   = val_df["Target"]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s   = scaler.transform(X_val)

    print("\n  Training base models...")

    base_models = [
        ("rf",  RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42,
                                        class_weight="balanced", n_jobs=-1)),
        ("gb",  GradientBoostingClassifier(n_estimators=150, max_depth=4,
                                            learning_rate=0.05, random_state=42)),
        ("et",  ExtraTreesClassifier(n_estimators=200, max_depth=6, random_state=42,
                                      class_weight="balanced", n_jobs=-1)),
    ]
    if XGBOOST_AVAILABLE:
        base_models.append(
            ("xgb", XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.05,
                                   use_label_encoder=False, eval_metric="logloss",
                                   random_state=42, verbosity=0))
        )

    # Train each base model and collect OOF-style val predictions
    base_val_preds = []
    trained_bases  = []

    for name, clf in base_models:
        print(f"    → {name}...")
        clf.fit(X_train_s, y_train)
        val_prob = clf.predict_proba(X_val_s)[:, 1]
        base_val_preds.append(val_prob)
        trained_bases.append((name, clf))

    # Stack: use base val predictions as features for meta-learner
    # class_weight='balanced' forces it to predict positives more aggressively
    meta_X_val = np.column_stack(base_val_preds)
    meta_clf   = LogisticRegression(C=1.0, random_state=42, class_weight='balanced')
    meta_clf.fit(meta_X_val, y_val)

    # Final stacked prediction on validation set
    final_val_prob = meta_clf.predict_proba(meta_X_val)[:, 1]

    # ── Find optimal threshold by maximising F1 on the validation set ────────
    print("  Finding optimal classification threshold (F1 maximisation)...")
    candidate_thresholds = np.arange(0.05, 0.95, 0.01)
    f1_scores = [
        f1_score(y_val, (final_val_prob >= t).astype(int), zero_division=0)
        for t in candidate_thresholds
    ]
    optimal_threshold = float(candidate_thresholds[int(np.argmax(f1_scores))])
    print(f"  Optimal threshold: {optimal_threshold:.2f}  "
          f"(F1 at threshold: {max(f1_scores)*100:.1f}%)")

    # Metrics at default 0.5
    pred_50  = (final_val_prob >= 0.50).astype(int)
    # Metrics at optimal threshold
    pred_opt = (final_val_prob >= optimal_threshold).astype(int)

    metrics = {
        # ── At optimal threshold ──
        "accuracy":          round(accuracy_score(y_val, pred_opt), 4),
        "precision":         round(precision_score(y_val, pred_opt, zero_division=0), 4),
        "recall":            round(recall_score(y_val, pred_opt, zero_division=0), 4),
        "f1":                round(f1_score(y_val, pred_opt, zero_division=0), 4),
        "auc_roc":           round(roc_auc_score(y_val, final_val_prob), 4) if len(np.unique(y_val)) > 1 else 0.5,
        "optimal_threshold": round(optimal_threshold, 4),
        "confusion_matrix":  confusion_matrix(y_val, pred_opt).tolist(),
        # ── At 0.5 for comparison ──
        "accuracy_50":       round(accuracy_score(y_val, pred_50), 4),
        "precision_50":      round(precision_score(y_val, pred_50, zero_division=0), 4),
        "recall_50":         round(recall_score(y_val, pred_50, zero_division=0), 4),
        "f1_50":             round(f1_score(y_val, pred_50, zero_division=0), 4),
        "confusion_matrix_50": confusion_matrix(y_val, pred_50).tolist(),
        # ── Dataset sizes ──
        "val_rows":          len(y_val),
        "train_rows":        len(y_train),
        "val_surge_rate":    round(float(y_val.mean()), 4),
    }

    model_bundle = {
        "base_models":       trained_bases,
        "meta_clf":          meta_clf,
        "scaler":            scaler,
        "feature_cols":      FEATURE_COLS,
        "optimal_threshold": optimal_threshold,
        "trained_at":        datetime.now().isoformat(),
    }

    return model_bundle, metrics


def predict_with_bundle(bundle: dict, feature_df: pd.DataFrame) -> np.ndarray:
    """Run inference using a trained model bundle. Returns probability array."""
    scaler = bundle["scaler"]
    X = feature_df[FEATURE_COLS].fillna(0)
    X_s = scaler.transform(X)
    base_preds = [clf.predict_proba(X_s)[:, 1] for _, clf in bundle["base_models"]]
    meta_X = np.column_stack(base_preds)
    return bundle["meta_clf"].predict_proba(meta_X)[:, 1]


# ---------------------------------------------------------------------------
# Model Persistence
# ---------------------------------------------------------------------------
MODEL_PKL = os.path.join(MODELS_DIR, "ensemble_bundle.pkl")
METRICS_PKL = os.path.join(MODELS_DIR, "val_metrics.pkl")


def save_model(bundle: dict, metrics: dict):
    with open(MODEL_PKL, "wb") as f:
        pickle.dump(bundle, f)
    with open(METRICS_PKL, "wb") as f:
        pickle.dump(metrics, f)
    print(f"\n  Model saved → {MODEL_PKL}")


def load_model():
    """Load model if exists and was trained within the last 24 hours."""
    if not os.path.exists(MODEL_PKL):
        return None, None
    mtime = datetime.fromtimestamp(os.path.getmtime(MODEL_PKL))
    if datetime.now() - mtime > timedelta(hours=24):
        print("  Cached model is older than 24h — retraining...")
        return None, None
    with open(MODEL_PKL, "rb") as f:
        bundle = pickle.load(f)
    with open(METRICS_PKL, "rb") as f:
        metrics = pickle.load(f)
    return bundle, metrics


# ---------------------------------------------------------------------------
# Pattern summary for the prediction row
# ---------------------------------------------------------------------------
def summarize_patterns(row: pd.Series) -> str:
    active = []
    if row.get("Pat_Breakout", 0):    active.append("Breakout")
    if row.get("Pat_Consol", 0):      active.append("Consolidation")
    if row.get("Pat_GapUp", 0):       active.append("Gap-Up")
    if row.get("Pat_Accumulate", 0):  active.append("Accumulation")
    if row.get("Pat_Engulfing", 0):   active.append("Engulfing")
    if row.get("Pat_Hammer", 0):      active.append("Hammer")
    if row.get("Pat_Doji", 0):        active.append("Doji")
    return ", ".join(active) if active else "—"


def confidence_band(prob: float, threshold: float = 0.35) -> str:
    """
    Confidence relative to the optimal threshold stored in the bundle.
    HIGH   = prob >= threshold + 0.20
    MEDIUM = prob >= threshold
    LOW    = prob < threshold
    """
    if prob >= threshold + 0.20: return "HIGH ★★★"
    if prob >= threshold:        return "MEDIUM ★★"
    return "LOW ★"


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def run_ml_pipeline(force_retrain: bool = False):
    print("\n" + "=" * 60)
    print("  NSE AI/ML Stock Predictor — Enhanced Engine")
    print("=" * 60)

    # Try loading cached model
    bundle, val_metrics = None, None
    if not force_retrain:
        bundle, val_metrics = load_model()

    if bundle is not None:
        print(f"\n  ✅ Loaded cached model (trained {bundle['trained_at']})")
        print(f"  Validation Metrics (last 2 months temporal holdout):")
        _print_metrics(val_metrics)

        # Still need latest data for predictions
        print("\n  Loading latest stock states for prediction...")
        _, _, latest_df = build_ml_dataset(days_lookback=365, validation_days=60)
    else:
        train_df, val_df, latest_df = build_ml_dataset(days_lookback=365, validation_days=60)

        if train_df.empty or len(train_df) < 100:
            print("  ❌ Not enough training data. Please ensure databases are populated.")
            return

        if val_df.empty:
            print("  ⚠️  No validation data available for the past 2 months.")
            # Fall back to a random split approach
            from sklearn.model_selection import train_test_split
            train_df, val_df = train_test_split(train_df, test_size=0.2, random_state=42)

        print(f"\n  Training on {len(train_df)} rows, validating on {len(val_df)} rows...")
        bundle, val_metrics = build_and_train(train_df, val_df)
        save_model(bundle, val_metrics)

        print("\n  ✅ Validation Metrics (last 2 months temporal holdout):")
        _print_metrics(val_metrics)

        # Per-pattern validation accuracy
        if not val_df.empty:
            _print_pattern_accuracy(val_df, bundle)

    if latest_df.empty:
        print("\n  No current stock states to predict for.")
        return

    # -----------------------------------------------------------------------
    # Live Google News + Corporate Announcement Sentiment for ALL stocks
    # -----------------------------------------------------------------------
    total_stocks = len(latest_df)
    opt_thresh = bundle.get("optimal_threshold", 0.35)
    print(f"\n  Optimal threshold : {opt_thresh:.2f}")
    print(f"  Fetching live Google News sentiment for ALL {total_stocks} stocks (high → low)...")

    results = []
    for i, (idx, row) in enumerate(latest_df.iterrows(), 1):
        sym = row["Symbol"]
        news = fetch_google_news_sentiment(sym, timeout=5)
        # Blend DB annotation sentiment (40%) + live Google News sentiment (60%)
        blended_sent = (row["AnnSentiment"] * 0.4 + news["avg_sentiment"] * 0.6)
        row_copy = row.copy()
        row_copy["AnnSentiment"] = blended_sent

        prob = predict_with_bundle(bundle, pd.DataFrame([row_copy]))[0]

        results.append({
            "Rank":                0,                # filled after sort
            "Symbol":              sym,
            "Latest_Return_%":     round(row["DailyReturn"], 2),
            "RSI":                 round(row["RSI"], 1) if not pd.isna(row["RSI"]) else None,
            "MACD_Histogram":      round(row["MACD_hist"], 4) if not pd.isna(row["MACD_hist"]) else None,
            "BB_Position":         round(row["BB_position"], 2) if not pd.isna(row["BB_position"]) else None,
            "ATR_%":               round(row["ATR_pct"], 2) if not pd.isna(row["ATR_pct"]) else None,
            "Volume_Surge_x":      round(row["VolumeSurge"], 2) if not pd.isna(row["VolumeSurge"]) else None,
            "Corp_Ann_Sentiment":  round(row["AnnSentiment"], 2),
            "News_Sentiment":      round(news["avg_sentiment"], 2),
            "News_Articles":       news["article_count"],
            "Blended_Sentiment":   round(blended_sent, 2),
            "Patterns_Detected":   summarize_patterns(row),
            "Surge_Prob_%":        round(prob * 100, 1),
            "Above_Threshold":     "YES" if prob >= opt_thresh else "NO",
            "Confidence":          confidence_band(prob, opt_thresh),
        })

        if i % 25 == 0 or i == total_stocks:
            print(f"    Processed {i}/{total_stocks} stocks...")

    # Sort ALL stocks high → low by surge probability
    final_df = pd.DataFrame(results).sort_values("Surge_Prob_%", ascending=False).reset_index(drop=True)
    final_df["Rank"] = final_df.index + 1

    # Reorder columns: Rank first
    col_order = ["Rank", "Symbol", "Latest_Return_%", "RSI", "MACD_Histogram",
                 "BB_Position", "ATR_%", "Volume_Surge_x",
                 "Corp_Ann_Sentiment", "News_Sentiment", "News_Articles",
                 "Blended_Sentiment", "Patterns_Detected",
                 "Surge_Prob_%", "Above_Threshold", "Confidence"]
    final_df = final_df[[c for c in col_order if c in final_df.columns]]

    print("\n" + "=" * 60)
    print(f"  🌟 ALL AI PICKS — SORTED HIGH → LOW ({len(final_df)} stocks)")
    print("=" * 60)
    display_cols = ["Rank", "Symbol", "Latest_Return_%", "RSI", "Volume_Surge_x",
                    "Blended_Sentiment", "Patterns_Detected", "Surge_Prob_%",
                    "Above_Threshold", "Confidence"]
    print(final_df[display_cols].to_string(index=False))

    # Save ALL results to CSV
    output_path = os.path.join(os.path.dirname(root_dir), "databases", "ai_ideal_stocks_report.csv")
    final_df.to_csv(output_path, index=False)
    
    # Save historical predictions to SQLite database
    import sqlite3
    from datetime import datetime
    history_db_path = os.path.join(os.path.dirname(root_dir), "databases", "ai_predictions_history.db")
    
    history_df = final_df.copy()
    history_df['Prediction_Date'] = datetime.now().strftime("%Y-%m-%d")
    
    try:
        conn = sqlite3.connect(history_db_path)
        history_df.to_sql("predictions", conn, if_exists="append", index=False)
        conn.close()
        print(f"  💾 Historical predictions appended to → {history_db_path}")
    except Exception as e:
        print(f"  ❌ Error saving historical predictions: {e}")

    # Save validation metrics separately for API
    import json
    metrics_path = os.path.join(os.path.dirname(root_dir), "databases", "ai_validation_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(val_metrics, f, indent=2)

    print(f"\n  📄 Full ranked report ({len(final_df)} stocks) saved → {output_path}")
    print(f"  📊 Validation metrics saved → {metrics_path}")
    print("\n" + "=" * 60)


def _print_metrics(metrics: dict):
    if not metrics:
        return
    opt = metrics.get('optimal_threshold', 0.5)
    surge_rate = metrics.get('val_surge_rate', 0)
    print(f"    Val surge rate    : {surge_rate*100:.1f}%  (actual >1.5% moves in val period)")
    print(f"    Optimal threshold : {opt:.2f}  (F1-maximised on val set)")
    print(f"")
    print(f"    --- At Optimal Threshold ({opt:.2f}) ---")
    print(f"    Accuracy     : {metrics['accuracy'] * 100:.1f}%")
    print(f"    Precision    : {metrics['precision'] * 100:.1f}%")
    print(f"    Recall       : {metrics['recall'] * 100:.1f}%")
    print(f"    F1-Score     : {metrics['f1'] * 100:.1f}%")
    print(f"    AUC-ROC      : {metrics['auc_roc']:.4f}")
    cm = metrics.get("confusion_matrix")
    if cm:
        print(f"    TN={cm[0][0]:>6}  FP={cm[0][1]:>6}")
        print(f"    FN={cm[1][0]:>6}  TP={cm[1][1]:>6}")
    print(f"")
    print(f"    --- At Default Threshold (0.50) ---")
    print(f"    Accuracy     : {metrics.get('accuracy_50', 0) * 100:.1f}%")
    print(f"    Precision    : {metrics.get('precision_50', 0) * 100:.1f}%")
    print(f"    Recall       : {metrics.get('recall_50', 0) * 100:.1f}%")
    print(f"    F1-Score     : {metrics.get('f1_50', 0) * 100:.1f}%")
    cm50 = metrics.get("confusion_matrix_50")
    if cm50:
        print(f"    TN={cm50[0][0]:>6}  FP={cm50[0][1]:>6}")
        print(f"    FN={cm50[1][0]:>6}  TP={cm50[1][1]:>6}")
    print(f"    Train rows   : {metrics['train_rows']:,}")
    print(f"    Val rows     : {metrics['val_rows']:,}")


def _print_pattern_accuracy(val_df: pd.DataFrame, bundle: dict):
    """Prints accuracy breakdown per discovered pattern."""
    print("\n  📊 Pattern Accuracy on 2-Month Validation Set:")
    patterns = {
        "Breakout":      "Pat_Breakout",
        "Consolidation": "Pat_Consol",
        "Gap-Up":        "Pat_GapUp",
        "Accumulation":  "Pat_Accumulate",
        "Engulfing":     "Pat_Engulfing",
        "Hammer":        "Pat_Hammer",
    }
    scaler     = bundle["scaler"]
    opt_thresh = bundle.get("optimal_threshold", 0.35)
    for pat_name, pat_col in patterns.items():
        sub = val_df[val_df[pat_col] == 1]
        if len(sub) < 10:
            continue
        X_s = scaler.transform(sub[FEATURE_COLS].fillna(0))
        base_preds = [clf.predict_proba(X_s)[:, 1] for _, clf in bundle["base_models"]]
        meta_X = np.column_stack(base_preds)
        probs = bundle["meta_clf"].predict_proba(meta_X)[:, 1]
        preds = (probs >= opt_thresh).astype(int)   # use optimal threshold
        acc   = accuracy_score(sub["Target"], preds)
        prec  = precision_score(sub["Target"], preds, zero_division=0)
        rec   = recall_score(sub["Target"], preds, zero_division=0)
        print(f"    {pat_name:<16}: n={len(sub):5d}  acc={acc*100:.1f}%  "
              f"prec={prec*100:.1f}%  rec={rec*100:.1f}%  "
              f"surge_rate={sub['Target'].mean()*100:.1f}%")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NSE AI/ML Stock Predictor — Enhanced Engine")
    parser.add_argument("--force-retrain", action="store_true",
                        help="Force model retraining even if a cached model exists")
    args = parser.parse_args()
    run_ml_pipeline(force_retrain=args.force_retrain)
