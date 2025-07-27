import requests
import streamlit as st
import pandas as pd
import datetime
import numpy as np
import uuid
import json

# -----------------------
# Session State Init
# -----------------------
if "positions" not in st.session_state:
    st.session_state.positions = []
if "last_added_coin" not in st.session_state:
    st.session_state.last_added_coin = None
if "scenario_moves" not in st.session_state:
    st.session_state.scenario_moves = {}
if "positions_uploaded" not in st.session_state:
    st.session_state.positions_uploaded = False
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# -----------------------
# API Functions
# -----------------------

def get_prices():
    """Fetch latest prices. Primary: CoinPaprika, Fallback: CoinGecko"""
    try:
        url = "https://api.coinpaprika.com/v1/tickers"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        prices = {c["id"]: {"usd": c["quotes"]["USD"]["price"]} for c in data}
        return prices, "CoinPaprika"
    except Exception:
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin,ethereum,solana,cardano,sui,chainlink,pepe,aave,ondo-finance,paal-ai",
                "vs_currencies": "usd"
            }
            r = requests.get(url, params=params, timeout=5)
            r.raise_for_status()
            return r.json(), "CoinGecko"
        except Exception as e:
            st.error(f"Price fetch failed: {e}")
            return {}, "None"

def get_top_coins(limit=50):
    """Fetch top coins with symbol, id and price from CoinPaprika"""
    try:
        r = requests.get("https://api.coinpaprika.com/v1/tickers", timeout=5)
        r.raise_for_status()
        data = r.json()
        top = sorted(data, key=lambda x: x.get("rank", 9999))[:limit]
        return {c["symbol"].upper(): (c["id"], c["quotes"]["USD"]["price"]) for c in top}
    except Exception as e:
        st.error(f"Failed to fetch top coins: {e}")
        return {}

def get_history(coin_id, days=7):
    """Fetch historical price for the past N days from CoinPaprika"""
    try:
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)
        r = requests.get(
            f"https://api.coinpaprika.com/v1/tickers/{coin_id}/historical",
            params={
                "start": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "interval": "24h"
            },
            timeout=5
        )
        r.raise_for_status()
        prices = r.json()
        df = pd.DataFrame(prices)
        df["time"] = pd.to_datetime(df["timestamp"])
        return df[["time", "price"]].sort_values("time"), True
    except Exception:
        now = datetime.datetime.utcnow()
        sample = [{"timestamp": (now - datetime.timedelta(days=i)).isoformat()+"Z",
                   "price": 1 + 0.05*np.sin(i)} for i in range(days)]
        df = pd.DataFrame(sample)
        df["time"] = pd.to_datetime(df["timestamp"])
        return df[["time", "price"]].sort_values("time"), False

# -----------------------
# Utility
# -----------------------
def funding_fee(total_exposure, rate=0.0002):
    return total_exposure * rate

def remove_position(idx):
    if "positions" in st.session_state and idx < len(st.session_state.positions):
        st.session_state.positions.pop(idx)

# -----------------------
# Layout & CSS
# -----------------------
st.subheader("Crypto Plays Leverage Trade Calculator")

st.markdown("""
<style>
.instructions-box {
    padding: 20px 15px;
    border: 1px solid #444;
    border-radius: 6px;
    font-size: 0.95rem;
    line-height: 1.4;
    margin-bottom: 20px;
    background-color: #1e1e1e;
    color: #ffffff;
}
.instructions-box strong { color: #4CAF50; }

/* Container max width */
.block-container {
    max-width: 980px;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Trash button (id starts with 'remove_') */
div[data-testid="stButton"][id*="remove_"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 38px !important;
    height: 38px !important;
    font-size: 18px !important;
    padding: 0 !important;
}
div[data-testid="stButton"][id*="remove_"] button p {
    margin: 0 !important;
    line-height: 1 !important;
}

/* Primary button style */
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: transparent !important;
    border-color: rgb(0, 255, 9) !important;
    color: white !important;
    margin-top: 20px;
    font-weight: 600 !important;
    border-radius: 6px !important;
    height: 40px !important;
    font-size: 14px !important;
    border-width: 1px;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: rgb(0, 255, 9) !important;
}

/* All secondary buttons = text-only */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: none;
    border: 1px solid darkred !important;
    margin-top: 20px;
    padding: 4px 12px !important;
    color: white !important;
    font-size: 16px !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: darkred !important;
    color: white !important;
}

/* Download button */
div[data-testid="stDownloadButton"] button {
    background-color: transparent !important;
    border-color: rgb(0, 255, 9) !important;
    color: white !important;
    margin-top: 20px;
    font-weight: 600 !important;
    border-radius: 6px !important;
    height: 40px !important;
    font-size: 14px !important;
    border-width: 1px;
}
div[data-testid="stDownloadButton"] button:hover {
    background-color: #009505 !important;
}

/* st.metric value text */
div[data-testid="stMetricValue"] {
    color: rgb(0, 255, 9) !important;
    font-weight: 700 !important;
    text-align: center;
}
</style>

<div class="instructions-box">
<strong>Quick Start:</strong><br>
• Add positions with your <em>Margin</em> &amp; <em>Leverage</em>.<br>
• (Optional) Add Stop Loss &amp; Take Profit.<br>
• All calculations update automatically when you change values.<br>
• Review <strong>Exposure</strong> and run <strong>Scenario Simulations</strong>.
</div>
""", unsafe_allow_html=True)

# -----------------------
# Global Settings
# -----------------------
with st.expander("⚙️ Global Settings", expanded=False):
    prices, source = get_prices()
    st.caption(f"Price data source: {source}")
    maintenance_margin = st.number_input(
        "Maintenance Margin (%)",
        min_value=0.1,
        max_value=5.0,
        value=0.5,
        step=0.1,
        help="Used for calculating liquidation prices for all positions."
    )

# -----------------------
# Manage Positions (Save/Load)
# -----------------------
with st.expander("📂 Manage Positions (Save & Load)", expanded=False):
    if st.session_state.positions:
        positions_json = json.dumps(st.session_state.positions, indent=2)
        st.download_button(
            "💾 Download Positions",
            positions_json,
            file_name="positions.json",
            mime="application/json",
            key="download_positions"
        )
    uploaded_file = st.file_uploader("Upload Positions (JSON)", type="json",
                                     key=f"positions_upload_{st.session_state.uploader_key}")
    if uploaded_file is not None and not st.session_state.positions_uploaded:
        try:
            uploaded_positions = json.load(uploaded_file)
            for pos in uploaded_positions:
                if "id" not in pos:
                    pos["id"] = str(uuid.uuid4())
            st.session_state.positions = uploaded_positions
            st.session_state.last_added_coin = uploaded_positions[0]["coin"] if uploaded_positions else None
            st.session_state.positions_uploaded = True
            st.success("Positions loaded successfully! Refreshing...")
            st.session_state.uploader_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error loading positions: {e}")

if st.session_state.positions_uploaded:
    st.session_state.positions_uploaded = False

# -----------------------
# Summary Metrics
# -----------------------
if st.session_state.positions:
    total_margin = sum(pos["margin"] for pos in st.session_state.positions)
    total_exposure = sum(pos["margin"] * pos["leverage"] for pos in st.session_state.positions)
    weighted_leverage = (total_exposure / total_margin) if total_margin > 0 else 0

    exposures_by_coin = {}
    for pos in st.session_state.positions:
        exposures_by_coin[pos["coin"]] = exposures_by_coin.get(pos["coin"], 0) + (pos["margin"] * pos["leverage"])
    total_exposure_for_pct = sum(exposures_by_coin.values())
    sorted_exposures = sorted(exposures_by_coin.items(), key=lambda x: x[1], reverse=True) if total_exposure_for_pct > 0 else []
    top3_summary = "No exposure"
    if total_exposure_for_pct > 0:
        top3 = sorted_exposures[:3]
        top3_summary = ", ".join([f"{coin} {100*val/total_exposure_for_pct:.1f}%" for coin, val in top3])
        if len(sorted_exposures) > 3:
            others_pct = 100 - sum(100*val/total_exposure_for_pct for _, val in top3)
            top3_summary += f", Others {others_pct:.1f}%"

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💰 Total Margin", f"${total_margin:,.2f}")
    with c2: st.metric("📈 Total Exposure", f"${total_exposure:,.2f}")
    with c3: st.metric("⚖ Weighted Avg. Leverage", f"{weighted_leverage:.2f}x")
    with c4: st.metric("📂 Open Positions", len(st.session_state.positions))

    if sorted_exposures:
        with st.expander("📊 View Full Portfolio Composition"):
            for coin, val in sorted_exposures:
                pct = 100 * val / total_exposure_for_pct
                st.write(f"- **{coin}**: {pct:.1f}%")

# -----------------------
# Add Position
# -----------------------
if st.button("✛ Add Position", type="primary", key="add_position_btn"):
    st.session_state.positions.insert(0, {
        "coin": "BTC",
        "margin": 0.0,
        "leverage": 0.0,
        "stop_loss_pct": 0,
        "take_profit_pct": 0
    })
    st.session_state.last_added_coin = "BTC"

# -----------------------
# Coin map & IDs
# -----------------------
coin_map = get_top_coins(50)
for pos in st.session_state.positions:
    if "id" not in pos:
        pos["id"] = str(uuid.uuid4())

# -----------------------
# Positions Rendering
# -----------------------
remove_index = None
for idx, pos in enumerate(st.session_state.positions):
    pos_id = pos["id"]
    header_col1, header_col2 = st.columns([10, 1])
    with header_col1:
        st.markdown(
            f"""
            <div style='background:#38b8f247; padding:8px 12px; margin-top:20px; border-radius: 0.5rem;'>
                <span style='font-size: 0.95rem; font-weight:400; color:#00ff09;'>
                    Position {idx+1}
                    <span style='font-weight:400; color:#ffffff;'>
                        ({pos['coin']} – ${pos['margin']:,.2f} × {pos['leverage']:.2f}x)
                    </span>
                </span>
            </div>
            """, unsafe_allow_html=True
        )
    with header_col2:
        if st.button("Delete", key=f"remove_{pos_id}"):
            remove_index = idx

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: pos["coin"] = st.selectbox("Coin", list(coin_map.keys()), index=list(coin_map.keys()).index(pos["coin"]), key=f"coin_{pos_id}")
    with c2: pos["margin"] = st.number_input("Margin ($)", min_value=0.0, value=float(pos["margin"]), step=1.0, format="%.2f", key=f"m_{pos_id}")
    with c3: pos["leverage"] = st.number_input("Leverage (x)", min_value=0.0, value=float(pos["leverage"]), step=0.1, format="%.2f", key=f"l_{pos_id}")
    with c4: pos["stop_loss_pct"] = st.number_input("Stop-Loss %", min_value=0, max_value=100, value=int(pos["stop_loss_pct"]), step=1, key=f"sl_{pos_id}")
    with c5: pos["take_profit_pct"] = st.number_input("Take-Profit %", min_value=0, max_value=100, value=int(pos["take_profit_pct"]), step=1, key=f"tp_{pos_id}")

if remove_index is not None:
    remove_position(remove_index)
    st.rerun()

# -----------------------
# Calculations & Charts
# -----------------------
data = []
total_margin = total_exposure = 0.0
skipped_positions = 0
for pos in st.session_state.positions:
    if pos["margin"] == 0 or pos["leverage"] == 0:
        skipped_positions += 1
        continue
    cid, price = coin_map[pos["coin"]]
    ps = pos["margin"] * pos["leverage"]
    tok = ps / price if price else 0.0
    liq_price = price * (1 - (1 / pos["leverage"]) + (maintenance_margin / 100))
    slp = round((price * (1 - pos["stop_loss_pct"]/100) - price) * tok, 2) if pos["stop_loss_pct"] > 0 else None
    tpp = round((price * (1 + pos["take_profit_pct"]/100) - price) * tok, 2) if pos["take_profit_pct"] > 0 else None
    data.append({
        "Coin": pos["coin"], "Price (USD)": price, "Tokens": tok,
        "Position Size (USD)": ps, "Margin (USD)": pos["margin"],
        "Liquidation Price (USD)": liq_price,
        "Stop Loss P/L (USD)": slp, "Take Profit P/L (USD)": tpp,
        "Coin ID": cid
    })
    total_margin += pos["margin"]
    total_exposure += ps

if skipped_positions:
    st.warning(f"{skipped_positions} position(s) skipped because Margin or Leverage = 0")

if data:
    df = pd.DataFrame(data)
    for col in ["Stop Loss P/L (USD)", "Take Profit P/L (USD)"]:
        if df[col].isna().all():
            df.drop(columns=[col], inplace=True)

    def hl_pl(v):
        if isinstance(v, (int, float)):
            return "color:#00f100" if v > 0 else "color:#D50000" if v < 0 else "color:#000000"
        return "color:#000000"

    def hl_liq(row):
        liq = row["Liquidation Price (USD)"]
        price = row["Price (USD)"]
        return ["background-color:#482727; color:white"] * len(row) if pd.notna(liq) and liq >= price * 0.95 else [""] * len(row)

    styled = (df.drop(columns="Coin ID")
              .style.hide(axis="index")
              .format({
                  "Price (USD)": "{:,.4f}", "Tokens": "{:,.2f}",
                  "Position Size (USD)": "${:,.2f}", "Margin (USD)": "${:,.2f}",
                  "Liquidation Price (USD)": "{:,.4f}",
                  "Stop Loss P/L (USD)": "${:,.2f}", "Take Profit P/L (USD)": "${:,.2f}"
              })
              .apply(hl_liq, axis=1))
    pl_cols = [c for c in df.columns if "P/L" in c]
    if pl_cols:
        styled = styled.map(hl_pl, subset=pl_cols)

    st.markdown("<p style='font-size:24px; font-weight:600; margin-top: 20px; margin-bottom: 20px;'>Positions Breakdown</p>", unsafe_allow_html=True)
    st.dataframe(styled, use_container_width=True)

    csv = df.drop(columns="Coin ID").to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "positions.csv", "text/csv")

    with st.expander("Exposure", expanded=False):
        st.bar_chart(df.set_index("Coin")[["Position Size (USD)"]])
    if pl_cols:
        with st.expander("P/L Impact", expanded=False):
            st.bar_chart(df.set_index("Coin")[pl_cols])
    with st.expander("Scenario Simulation", expanded=False):
        if st.button("Reset All to Zero"):
            st.session_state.scenario_moves = {coin: 0 for coin in df["Coin"].unique()}
        scenario_results, total_portfolio_pnl = [], 0.0
        for coin in df["Coin"].unique():
            move = st.slider(f"{coin} Move (%)", -50, 50, st.session_state.scenario_moves.get(coin, 0), key=f"move_{coin}")
            st.session_state.scenario_moves[coin] = move
            combined_pnl = sum(
                (row["Price (USD)"] * (1 + move / 100) - row["Price (USD)"]) * row["Tokens"]
                for _, row in df[df["Coin"] == coin].iterrows()
            )
            total_portfolio_pnl += combined_pnl
            scenario_results.append({"Coin": coin, "Move (%)": move, "P/L (USD)": round(combined_pnl, 2)})
        st.dataframe(pd.DataFrame(scenario_results)
                     .style.map(lambda v: "color:green" if isinstance(v, (int, float)) and v > 0
                                else "color:red" if isinstance(v, (int, float)) and v < 0 else "",
                                subset=["P/L (USD)"]),
                     use_container_width=True)
        st.markdown(f"### **Net Portfolio P/L: ${total_portfolio_pnl:,.2f}**")

    with st.expander("Historical Price (7d)", expanded=False):
        unique_positions = df[["Coin", "Coin ID"]].drop_duplicates().reset_index(drop=True)
        default_coin = st.session_state.last_added_coin or unique_positions.iloc[0]["Coin"]
        default_index = int(unique_positions.index[unique_positions["Coin"] == default_coin][0]) if default_coin in unique_positions["Coin"].values else 0
        sel = st.selectbox("Coin", unique_positions["Coin"].tolist(), index=default_index)
        cid = unique_positions.loc[unique_positions["Coin"] == sel, "Coin ID"].iloc[0]
        hist, real = get_history(cid)
        st.write("Source:", "Live" if real else "Sample")
        st.line_chart(hist.set_index("time")["price"])
else:
    st.info("No valid positions calculated. Fill margin & leverage values to include them.")
