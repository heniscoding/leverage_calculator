import streamlit as st
import requests
import pandas as pd
import datetime
import numpy as np

# -----------------------
# Fallback Static Prices
# -----------------------
fallback_prices = {
    "bitcoin": {"usd": 67000},
    "ethereum": {"usd": 3500},
    "solana": {"usd": 180},
    "cardano": {"usd": 0.45},
    "sui": {"usd": 4.3},
    "chainlink": {"usd": 15},
    "pepe": {"usd": 0.000011},
    "aave": {"usd": 90},
    "ondo-finance": {"usd": 0.85},
    "paal-ai": {"usd": 0.35},
}

# -----------------------
# Fetch live prices (with fallback & caching)
# -----------------------
@st.cache_data(ttl=60)
def get_prices(live=True):
    if not live:
        return fallback_prices
    try:
        ids = ",".join(fallback_prices.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        data = response.json()
        if not data or any(v["usd"] == 0 for v in data.values()):
            raise ValueError("Invalid price response")
        return data
    except Exception as e:
        st.warning(f"Live price fetch failed ({e}). Using fallback static prices.")
        return fallback_prices

# -----------------------
# Historical prices (with fallback)
# -----------------------
@st.cache_data(ttl=300)
def get_history(coin_id, days=7):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        prices = res.json().get("prices", [])
        if not prices:
            raise ValueError("No prices returned")
        df = pd.DataFrame(prices, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df.sort_values("time"), True
    except Exception as e:
        st.warning(f"Failed to fetch real history for {coin_id}: {e}. Showing sample data.")
        now = datetime.datetime.now()
        times = [now - datetime.timedelta(days=i) for i in reversed(range(days))]
        sample_prices = [[int(t.timestamp() * 1000), 1 + 0.05 * np.sin(i)] for i, t in enumerate(times)]
        df = pd.DataFrame(sample_prices, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df.sort_values("time"), False

# -----------------------
# Risk scoring
# -----------------------
def risk_score(total_exposure, total_margin, stop_loss_list):
    leverage_ratio = total_exposure / total_margin if total_margin else 0
    valid_stop_losses = [sl for sl in stop_loss_list if sl > 0]
    avg_stop_loss = np.mean(valid_stop_losses) if valid_stop_losses else None

    if avg_stop_loss is None:
        return "High", "No stop-loss set on any position. High risk!"
    if leverage_ratio <= 2 and avg_stop_loss <= 5:
        return "Low", "Risk is well managed. Stop-loss usage is disciplined."
    elif leverage_ratio <= 3 or avg_stop_loss <= 10:
        return "Medium", "Consider reducing leverage or tightening stop-loss."
    else:
        return "High", "Risk is very high. Adjust stop-loss or leverage."

def funding_fee_estimate(total_exposure, rate=0.0002):
    return total_exposure * rate

# -----------------------
# Initialize session state
# -----------------------
if "positions" not in st.session_state:
    st.session_state.positions = []

# -----------------------
# Layout
# -----------------------
st.title("Crypto Leverage Trade Calculator (Dynamic Positions)")
st.markdown("Add positions dynamically, set per-position stop-loss/take-profit, and analyze risk and outcomes.")

use_live = st.checkbox("Use live prices (uncheck for static)", value=True)

# Button to add a new position
if st.button("Add Position"):
    st.session_state.positions.append({
        "coin": "BTC",
        "margin": 1000,
        "leverage": 2,
        "stop_loss_pct": 5,
        "take_profit_pct": 5
    })

# Button to clear all positions
if st.button("Clear All Positions"):
    st.session_state.positions = []

# Get live/static prices
prices = get_prices(live=use_live)
coins_available = {
    "BTC": ("bitcoin", prices.get("bitcoin", {}).get("usd", 1)),
    "ETH": ("ethereum", prices.get("ethereum", {}).get("usd", 1)),
    "SOL": ("solana", prices.get("solana", {}).get("usd", 1)),
    "ADA": ("cardano", prices.get("cardano", {}).get("usd", 1)),
    "SUI": ("sui", prices.get("sui", {}).get("usd", 1)),
    "LINK": ("chainlink", prices.get("chainlink", {}).get("usd", 1)),
    "PEPE": ("pepe", prices.get("pepe", {}).get("usd", 1)),
    "AAVE": ("aave", prices.get("aave", {}).get("usd", 1)),
    "ONDO": ("ondo-finance", prices.get("ondo-finance", {}).get("usd", 1)),
    "PAAL": ("paal-ai", prices.get("paal-ai", {}).get("usd", 1)),
}

# -----------------------
# Position inputs
# -----------------------
data = []
total_margin, total_exposure = 0, 0
stop_loss_list = []

for i, pos in enumerate(st.session_state.positions):
    st.markdown(f"### Position {i+1}")
    col1, col2, col3, col4, col5, col6 = st.columns([1,1,1,1,1,1])

    with col1:
        pos["coin"] = st.selectbox("Coin", list(coins_available.keys()), index=list(coins_available.keys()).index(pos["coin"]), key=f"coin_{i}")
    with col2:
        pos["margin"] = st.number_input("Margin ($)", value=pos["margin"], key=f"margin_{i}")
    with col3:
        pos["leverage"] = st.number_input("Leverage (x)", value=pos["leverage"], key=f"leverage_{i}")
    with col4:
        pos["stop_loss_pct"] = st.number_input("Stop-loss %", min_value=0, max_value=100, value=pos["stop_loss_pct"], key=f"stoploss_{i}")
    with col5:
        pos["take_profit_pct"] = st.number_input("Take-profit %", min_value=0, max_value=100, value=pos["take_profit_pct"], key=f"takeprofit_{i}")
    with col6:
        if st.button("Remove", key=f"remove_{i}"):
            st.session_state.positions.pop(i)
            st.experimental_rerun()

    coin_id, price = coins_available[pos["coin"]]
    position_size = pos["margin"] * pos["leverage"]
    tokens = position_size / price if price > 0 else 0
    stop_loss_price = price * (1 - pos["stop_loss_pct"] / 100) if pos["stop_loss_pct"] > 0 else None
    take_profit_price = price * (1 + pos["take_profit_pct"] / 100) if pos["take_profit_pct"] > 0 else None

    stop_loss_pl = (stop_loss_price - price) * tokens if stop_loss_price else None
    take_profit_pl = (take_profit_price - price) * tokens if take_profit_price else None

    data.append({
        "Coin": pos["coin"],
        "Price (USD)": price,
        "Tokens": tokens,
        "Position Size (USD)": position_size,
        "Margin (USD)": pos["margin"],
        "Liquidation Price (USD)": price * (1 - (pos["margin"] / position_size)) if position_size else None,
        "Stop Loss Price (USD)": stop_loss_price,
        "Stop Loss P/L (USD)": stop_loss_pl,
        "Take Profit Price (USD)": take_profit_price,
        "Take Profit P/L (USD)": take_profit_pl,
        "Coin ID": coin_id
    })

    total_margin += pos["margin"]
    total_exposure += position_size
    stop_loss_list.append(pos["stop_loss_pct"])

# -----------------------
# Summary & risk score
# -----------------------
if data:
    df = pd.DataFrame(data)
    risk, advice = risk_score(total_exposure, total_margin, stop_loss_list)
    st.markdown(f"### **Risk Score: {risk}**")
    st.write(advice)
    st.write(f"**Total Margin:** ${total_margin:,.2f} | **Total Exposure:** ${total_exposure:,.2f}")
    st.write(f"**Est. 8h Funding Fee:** ${funding_fee_estimate(total_exposure):.2f}")

    # Remove unused columns if all stop-loss or take-profit are None
    if df["Stop Loss Price (USD)"].isna().all():
        df = df.drop(columns=["Stop Loss Price (USD)", "Stop Loss P/L (USD)"])
    if df["Take Profit Price (USD)"].isna().all():
        df = df.drop(columns=["Take Profit Price (USD)", "Take Profit P/L (USD)"])

    # Styling
    def highlight_pl(val):
        color = "green" if isinstance(val, (int, float)) and val > 0 else "red" if isinstance(val, (int, float)) and val < 0 else "black"
        return f"color: {color}"

    def highlight_liquidation(row):
        if row.get("Liquidation Price (USD)") and row["Liquidation Price (USD)"] >= row["Price (USD)"] * 0.9:
            return ["background-color: #ffcccc"] * len(row)
        else:
            return [""] * len(row)

    styled_df = df.drop(columns="Coin ID").style.format(precision=2).apply(highlight_liquidation, axis=1)
    if "Stop Loss P/L (USD)" in df.columns and "Take Profit P/L (USD)" in df.columns:
        styled_df = styled_df.map(highlight_pl, subset=["Stop Loss P/L (USD)", "Take Profit P/L (USD)"])
    elif "Stop Loss P/L (USD)" in df.columns:
        styled_df = styled_df.map(highlight_pl, subset=["Stop Loss P/L (USD)"])
    elif "Take Profit P/L (USD)" in df.columns:
        styled_df = styled_df.map(highlight_pl, subset=["Take Profit P/L (USD)"])

    st.subheader("Position Summary (Styled)")
    st.dataframe(styled_df, use_container_width=True, height=600)

    # CSV export
    export_df = df.drop(columns="Coin ID").copy()
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Position Summary as CSV", csv_data, "position_summary.csv", "text/csv")

    # Charts
    st.subheader("Exposure Per Coin")
    st.bar_chart(df.set_index("Coin")[["Position Size (USD)"]])

    chart_cols = []
    if "Stop Loss P/L (USD)" in df.columns:
        chart_cols.append("Stop Loss P/L (USD)")
    if "Take Profit P/L (USD)" in df.columns:
        chart_cols.append("Take Profit P/L (USD)")
    if chart_cols:
        st.subheader("P/L Impact")
        st.bar_chart(df.set_index("Coin")[chart_cols])

    # Scenario simulation
    st.subheader("Scenario Simulation")
    scenario_pct = st.slider("Market move (%)", -50, 50, 0)
    if scenario_pct != 0:
        scenario_data = []
        for _, row in df.iterrows():
            new_price = row["Price (USD)"] * (1 + scenario_pct / 100)
            pnl = (new_price - row["Price (USD)"]) * row["Tokens"]
            scenario_data.append({"Coin": row["Coin"], "New Price (USD)": round(new_price, 4), "P/L (USD)": round(pnl, 2)})
        st.dataframe(pd.DataFrame(scenario_data))

    # Historical chart
    st.subheader("Historical Price (7 Days)")
    coin_selected = st.selectbox("Select Coin for History", df["Coin"].tolist())
    coin_id = df[df["Coin"] == coin_selected]["Coin ID"].iloc[0]
    hist, real_data = get_history(coin_id)
    st.write("**Data Source:**", "Real Coingecko data" if real_data else "Fallback sample data")
    st.line_chart(hist.set_index("time")["price"])
else:
    st.info("No positions added yet. Click **Add Position** to start.")
