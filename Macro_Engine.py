import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(page_title="Sovereign Macro Engine", layout="wide")

st.title("Sovereign Macro Execution Engine V3")
st.caption("Execution > Prediction | Survival First")

# ✅ Secure API key (Streamlit Cloud)
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except:
    st.error("Missing FRED_API_KEY in Streamlit secrets")
    st.stop()

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
# SAFE DATA FETCH
# --------------------------------------------------

@st.cache_data(ttl=86400)
def fetch_series(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": START_DATE,
        "observation_end": END_DATE
    }

    r = requests.get(url, params=params)

    try:
        data = r.json()
    except:
        st.error(f"Failed to parse API response for {series_id}")
        return None

    # ✅ CRITICAL DEFENSE
    if "observations" not in data:
        st.error(f"FRED API error ({series_id}): {data}")
        return None

    df = pd.DataFrame(data["observations"])

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])

    df = df.set_index("date")

    return df["value"].dropna()

# --------------------------------------------------
# SIGNALS
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
    return (dxy > 0) and (liq < 0) and (credit < 0) and (y > 0) and (vol > 1.5)

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
        val *= 0.9
        adjusted[k] = min(val, 0.35)
    return adjusted

def normalize(scores):
    total = sum(scores.values())
    if total == 0:
        return {k: 0 for k in scores}
    return {k: round(v / total * 100, 2) for k, v in scores.items()}

# --------------------------------------------------
# ENGINE
# --------------------------------------------------

def run_engine():

    # Fetch all data
    dxy = fetch_series(SERIES["DXY"])
    y = fetch_series(SERIES["YIELD"])
    fed = fetch_series(SERIES["FED"])
    rrp = fetch_series(SERIES["RRP"])
    tga = fetch_series(SERIES["TGA"])
    credit = fetch_series(SERIES["CREDIT"])
    vix = fetch_series(SERIES["VIX"])

    # ✅ FAIL-SAFE (critical)
    if any(x is None for x in [dxy, y, fed, rrp, tga, credit, vix]):
        st.error("Data fetch failed. Check API key or connection.")
        st.stop()

    # Liquidity
    net_liq = fed - rrp - tga

    # Trends
    liq_trend = compute_trend(net_liq)
    y_trend = compute_trend(y)
    dxy_trend = compute_trend(dxy)
    credit_trend = compute_trend(credit)

    # Volatility
    vol = z_score(vix)

    # Macro
    score = macro_score(liq_trend, y_trend, dxy_trend, credit_trend)
    regime = map_regime(score)

    # Risk kill
    if risk_kill(dxy_trend["short"], liq_trend["short"], credit_trend["short"], y_trend["short"], vol):
        return score, "CRISIS", {
            "BTC": 15,
            "Gold": 30,
            "Cash": 40,
            "Defensive": 15
        }

    # Z-score inputs
    liq_z = z_score(net_liq)
    y_z = z_score(y)
    dxy_z = z_score(dxy)
    credit_z = z_score(credit)

    # Allocation
    raw = asset_scores(liq_z, y_z, dxy_z, credit_z)
    conv = conviction(raw)
    allocation = normalize(conv)

    return score, regime, allocation

# --------------------------------------------------
# RUN + UI
# --------------------------------------------------

score, regime, allocation = run_engine()

col1, col2 = st.columns(2)

col1.metric("Macro Score", score)
col2.metric("Regime", regime)

st.subheader("Allocation (%)")

df = pd.DataFrame.from_dict(allocation, orient="index", columns=["Weight"])
st.dataframe(df)

st.bar_chart(df)
