import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Sovereign Macro Engine", layout="wide")
st.title("Sovereign Macro Execution Engine")
st.caption("Execution > Prediction | Survival First[cite: 1]")

# --------------------------------------------------
# API CONFIG
# --------------------------------------------------
api_key = st.secrets.get("FRED_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Enter FRED API Key", type="password")

if not api_key:
    st.warning("Enter FRED API Key to run the sovereign monitoring engine.")
    st.stop()

start_date = "2015-01-01"
end_date = datetime.now().strftime("%Y-%m-%d")

# --------------------------------------------------
# SERIES MAP
# --------------------------------------------------
SERIES = {
    "DXY": "DTWEXAFEGS",
    "10Y": "DGS10",
    "FED": "WALCL",
    "RRP": "RRPONTSYD",
    "TGA": "WTREGEN",
    "CREDIT_SPREAD": "BAMLH0A0HYM2"
}

# --------------------------------------------------
# FETCH DATA
# --------------------------------------------------
@st.cache_data(ttl=86400)
def fetch(series):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if "observations" not in data:
            return pd.Series(dtype="float64")

        df = pd.DataFrame(data["observations"])
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        return df.dropna().set_index("date")["value"]
    except:
        return pd.Series(dtype="float64")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
dxy = fetch(SERIES["DXY"])
y10 = fetch(SERIES["10Y"])
fed = fetch(SERIES["FED"])
rrp = fetch(SERIES["RRP"])
tga = fetch(SERIES["TGA"])
credit_spread = fetch(SERIES["CREDIT_SPREAD"])

# --------------------------------------------------
# ALIGN & COMPUTE NET LIQUIDITY
# --------------------------------------------------
df_liq = pd.concat([fed, rrp, tga], axis=1)
df_liq.columns = ["fed", "rrp", "tga"]
df_liq = df_liq.ffill().dropna()

net_liquidity = df_liq["fed"] - (df_liq["rrp"] * 1000) - df_liq["tga"]

# Smoothed Liquidity Impulse
liq_impulse_raw = net_liquidity.pct_change(30)
liq_impulse = liq_impulse_raw.rolling(5).mean().dropna()
liq_trend = liq_impulse.iloc[-1] if not liq_impulse.empty else 0

# --------------------------------------------------
# CORE TREND SIGNALS
# --------------------------------------------------
yield_trend = y10.pct_change(60).iloc[-1] if not y10.empty else 0
dxy_trend = dxy.pct_change(30).iloc[-1] if not dxy.empty else 0

credit_trend = credit_spread.pct_change(30).rolling(3).mean().dropna()
credit_trend_val = credit_trend.iloc[-1] if not credit_trend.empty else 0

# Latest Absolute Values
latest_yield = y10.iloc[-1] if not y10.empty else 0
latest_dxy = dxy.iloc[-1] if not dxy.empty else 0
latest_credit = credit_spread.iloc[-1] if not credit_spread.empty else 0
latest_liquidity = net_liquidity.iloc[-1] if not net_liquidity.empty else 0

# --------------------------------------------------
# CREDIT STATE
# --------------------------------------------------
def credit_state(val):
    if val > 0.15:
        return "STRESS SPIKE"
    elif val > 0:
        return "WIDENING"
    else:
        return "STABLE"

credit_status = credit_state(credit_trend_val)

# --------------------------------------------------
# UNIFIED PLAYBOOK LIFE-CYCLE RESOLVER
# --------------------------------------------------
def resolve_macro_phase(liq, yld, dxy_t, credit_s):
    """
    Unifies raw trends directly into the 6 sequential phases 
    dictated by your sovereign playbook framework[cite: 1].
    """
    # CRISIS: Liquidity shrinking, dollar under stress, credit spiking violently
    if liq < 0 and dxy_t > 0 and credit_s == "STRESS SPIKE":
        return "CRISIS"
        
    # FRACTURE: Liquidity negative, system under pressure, credit starting to widen
    if liq < 0 and dxy_t > 0 and credit_s == "WIDENING":
        return "FRACTURE"
        
    # PIVOT: Liquidity begins structural turn higher while yields cool off
    if liq > 0 and yld < 0:
        return "PIVOT"
        
    # EXPANSION: Capital flowing smoothly into the system, credit markers quiet
    if liq > 0 and credit_s == "STABLE" and dxy_t <= 0:
        return "EXPANSION"
        
    # EUPHORIA: Overextended expansion, crowd-chasing environment
    if liq < 0 and yld < 0 and dxy_t < 0 and credit_s == "STABLE":
        return "EUPHORIA"
        
    # QT: Systematic central bank tightening (Default state when liquidity retreats safely)
    return "QT"

macro_phase = resolve_macro_phase(liq_trend, yield_trend, dxy_trend, credit_status)

# --------------------------------------------------
# ANTIFRAGILE DIRECTIVE ENGINE
# --------------------------------------------------
def derive_execution_protocol(phase, dxy_val):
    """
    Maps the detected macro phase to non-negotiable allocation directives[cite: 1].
    """
    if phase == "QT":
        return {
            "DCA_MODE": "STANDARD BASELOAD",
            "EM_LAYER": "ACTIVE" if dxy_val < 103 else "OFF (DXY Stress Triggered)[cite: 1]",
            "ACTION": "Accumulate strategic cash reserves[cite: 1]. Maintain fixed baseload deployments (BTC, Gold, Hard Assets, Monetary Royalties)[cite: 1]."
        }
    elif phase == "FRACTURE":
        return {
            "DCA_MODE": "DEFENSIVE PROTECTION",
            "EM_LAYER": "OFF (Systemic Liquidity Drain)[cite: 1]",
            "ACTION": "Do NOT buy early dips[cite: 1]. Focus heavily on capital preservation and parking strategic dry powder[cite: 1]."
        }
    elif phase == "CRISIS":
        return {
            "DCA_MODE": "MAXIMUM DEPLOYMENT PREP",
            "EM_LAYER": "OFF (Absolute Lock)",
            "ACTION": "Do nothing initially—let systemic panic run its full course[cite: 1]. Maximize cash reserves for ultimate deployment on capitulation[cite: 1]."
        }
    elif phase == "PIVOT":
        return {
            "DCA_MODE": "AGGRESSIVE CYCLE DEPLOY",
            "EM_LAYER": "REACTIVATING",
            "ACTION": "Liquidity has verified a turn[cite: 1]. Aggressively deploy your strategic cash weapon into Tier 1 pullbacks (ASML, TSM, Grid, and Utilities)[cite: 1]."
        }
    elif phase == "EXPANSION":
        return {
            "DCA_MODE": "STRATIFIED EXPANSION",
            "EM_LAYER": "ACTIVE",
            "ACTION": "Ride long-term compounding cycles[cite: 1]. Keep full target weights active across structural monopoly, tech, and commodity layers[cite: 1]."
        }
    elif phase == "EUPHORIA":
        return {
            "DCA_MODE": "HARVEST & REBUILD CASH",
            "EM_LAYER": "TRIMMING / REDUCING",
            "ACTION": "Crowds are chasing[cite: 1]. Trigger rule-based trims: 10-15% off at +50% gains, 20-30% off at +80% gains[cite: 1]. Route all profits to physical Gold & Strategic Cash[cite: 1]."
        }

exec_rules = derive_execution_protocol(macro_phase, latest_dxy)

# --------------------------------------------------
# SYSTEM VISUALS (DASHBOARD)
# --------------------------------------------------
def arrow(x):
    return "↑" if x > 0 else "↓" if x < 0 else "→"

def format_liquidity(x):
    if abs(x) >= 1e12:
        return f"{x/1e12:.2f}T"
    elif abs(x) >= 1e9:
        return f"{x/1e9:.0f}B"
    return f"{x/1e6:.0f}M"

st.subheader("Macro Chokepoints[cite: 1]")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Net Liquidity (Fed-RRP-TGA)",
          format_liquidity(latest_liquidity),
          f"{liq_trend*100:.2f}% {arrow(liq_trend)}")

c2.metric("10Y Treasury Yield",
          f"{latest_yield:.2f}%",
          f"{yield_trend*100:.2f}% {arrow(yield_trend)}")

c3.metric("US Dollar Index (DXY)",
          f"{latest_dxy:.2f}",
          f"{dxy_trend*100:.2f}% {arrow(dxy_trend)}")

c4.metric("High Yield Credit Spread",
          f"{latest_credit:.2f}%",
          f"{credit_trend_val*100:.2f}% {arrow(credit_trend_val)}")

st.markdown("---")

# --------------------------------------------------
# SYSTEM STATE INTERFACE
# --------------------------------------------------
st.subheader("Engine Diagnostics & Execution Directives")
c5, c6, c7 = st.columns(3)

with c5:
    st.metric("Identified Macro Phase", macro_phase)
with c6:
    st.metric("Credit Condition Matrix", credit_status)
with c7:
    st.metric("Global EM Safety Layer", "ACTIVE" if "OFF" not in exec_rules["EM_LAYER"] else "MUTED")

# Execution Command Center Display
st.info(f"### **Current DCA Mode:** {exec_rules['DCA_MODE']}")
st.warning(f"**Operational Instructions:** {exec_rules['ACTION']}")

# --------------------------------------------------
# STRUCTURAL HARD LAYER VERIFICATION REFERENCE
# --------------------------------------------------
with st.expander("View Structural Baseload Target Reference (Allocations.jpeg)[cite: 1]"):
    st.markdown("""
    ### **Permanent Structural Assets (Deploy Constantly regardless of Phase State)**
    *   **BTC Layer:** 25% Target $\rightarrow$ Route directly to Cold Wallet[cite: 1].
    *   **Gold Layer:** 10% Target $\rightarrow$ Direct physical accumulation[cite: 1].
    *   **INFRA Layer 1 (Hard Assets):** TPL, ADPORTS, ICTEY (Continuous Monthly Deployment. Never Pause)[cite: 1].
    *   **ENERGY Layer 1 (Monetary Royalties):** FNV, WPM (Continuous accumulation treated as Gold extension)[cite: 1].
    
    ### **Execution Guardrail Principle**
    > **Open system $\rightarrow$ Execute instructions $\rightarrow$ Close system. Do not override, do not second-guess, do not react emotionally[cite: 1].**
    """)
