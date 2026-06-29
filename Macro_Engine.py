import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

FRED_API_KEY = "YOUR_API_KEY"
START_DATE = "2015-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")

SERIES = {
    "DXY": "DTWEXAFE",
    "YIELD": "DGS10",
    "FED": "WALCL",
    "RRP": "RRPONTSYD",
    "TGA": "WTREGEN",
    "CREDIT": "TOTLL",
    "VIX": "VIXCLS"
}

# --------------------------------------------------
# DATA FETCH
# --------------------------------------------------

def fetch_series(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": START_DATE,
        "observation_end": END_DATE
    }

    r = requests.get(url, params=params).json()
    df = pd.DataFrame(r["observations"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    return df["value"].dropna()

# --------------------------------------------------
# SIGNAL PROCESSING
# --------------------------------------------------

def compute_trend(series):
    return {
        "short": series.pct_change(30).iloc[-1],
        "long": series.pct_change(90).iloc[-1]
    }

def z_score(series):
    mean = series.rolling(90).mean()
    std = series.rolling(90).std()
    return ((series - mean) / std).iloc[-1]

# --------------------------------------------------
# MACRO ENGINE
# --------------------------------------------------

def macro_score(liq, y, dxy, credit):

    score = 0

    # Liquidity weighted stronger
    score += 2 if liq["short"] > 0 else -2
    score += 1 if liq["long"] > 0 else -1

    score += 1 if y["short"] < 0 else -1
    score += 1 if dxy["short"] < 0 else -1
    score += 1 if credit["short"] > 0 else -1

    return score

def map_regime(score):
    if score >= 4:
        return "EXPANSION"
    elif score >= 2:
        return "EARLY_RISK_ON"
    elif score >= -1:
        return "TRANSITION"
    elif score >= -4:
        return "TIGHTENING"
    else:
        return "CRISIS"

# --------------------------------------------------
# RISK ENGINE
# --------------------------------------------------

def risk_kill(dxy, liq, credit, y, vol):
    if (dxy > 0) and (liq < 0) and (credit < 0) and (y > 0) and (vol > 1.5):
        return True
    return False

# --------------------------------------------------
# ASSET MODEL
# --------------------------------------------------

def asset_scores(liq, y, dxy, credit):

    return {
        "BTC": (liq * 2) - dxy,
        "Gold": (-y) + (-credit),
        "Energy": liq - y,
        "Materials": liq,
        "Infra": 0.5 + liq,
        "AI": (liq * 2) - credit,
        "EM": liq - dxy,
        "Cash": (-liq) + dxy
    }

def conviction(scores):

    adjusted = {}
    for k, v in scores.items():
        val = max(v, 0) ** 2
        val *= 0.9  # decay
        adjusted[k] = min(val, 0.35)

    return adjusted

def normalize(scores):
    total = sum(scores.values())
    return {k: round(v / total * 100, 2) for k, v in scores.items()}

# --------------------------------------------------
# ENGINE EXECUTION
# --------------------------------------------------

def run_engine():

    # Fetch data
    dxy = fetch_series(SERIES["DXY"])
    y = fetch_series(SERIES["YIELD"])
    fed = fetch_series(SERIES["FED"])
    rrp = fetch_series(SERIES["RRP"])
    tga = fetch_series(SERIES["TGA"])
    credit = fetch_series(SERIES["CREDIT"])
    vix = fetch_series(SERIES["VIX"])

    # Liquidity
    net_liq = fed - rrp - tga

    # Trends
    liq_trend = compute_trend(net_liq)
    y_trend = compute_trend(y)
    dxy_trend = compute_trend(dxy)
    credit_trend = compute_trend(credit)

    # Volatility
    vol = z_score(vix)

    # Macro score
    score = macro_score(liq_trend, y_trend, dxy_trend, credit_trend)
    regime = map_regime(score)

    # Risk kill
    if risk_kill(dxy_trend["short"], liq_trend["short"], credit_trend["short"], y_trend["short"], vol):
        allocation = {
            "BTC": 15,
            "Gold": 30,
            "Cash": 40,
            "Defensive": 15
        }

        return {
            "macro_score": score,
            "regime": "CRISIS",
            "allocation": allocation
        }

    # Z-scored inputs
    liq_z = z_score(net_liq)
    y_z = z_score(y)
    dxy_z = z_score(dxy)
    credit_z = z_score(credit)

    # Factor scores
    raw = asset_scores(liq_z, y_z, dxy_z, credit_z)

    # Conviction
    conv = conviction(raw)

    # Normalize
    allocation = normalize(conv)

    return {
        "macro_score": score,
        "regime": regime,
        "allocation": allocation
    }

# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":
    result = run_engine()

    print("\n--- SOVEREIGN ENGINE OUTPUT ---")
    print("Macro Score:", result["macro_score"])
    print("Regime:", result["regime"])
    print("Allocation:")
    for k, v in result["allocation"].items():
        print(f"{k}: {v}%")
