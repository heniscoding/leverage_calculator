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
def risk_score(total_exposure, total_margin, stop_loss_pct):
    leverage_ratio = total_exposure / total_margin if total_margin else 0
    if leverage_ratio <= 2 and stop_loss_pct <= 5:
        return "Low", "Risk is well managed. Continue disciplined stop-loss use."
    elif leverage_ratio <= 3 or stop_loss_pct <= 10:
        return "Medium", "Consider reducing leverage or tightening stop-loss to lower risk."
    else:
        return "High", "Risk is very high. Reduce position size or leverage to protect capital."

def funding_fee_estimate(total_exposure, rate=0.0002):
    return total_exposure * rate

# -----------------------
# Streamlit Layout
# -----------------------
st.title("Crypto Leverage Trade Calculator")
st.markdown("Analyze multi-coin leveraged trades with risk scoring, scenario simulation, historical charts, and export.")

use_live = st.checkbox("Use live prices (uncheck for static)", value=True)
stop_loss_pct = st.slider("Stop-loss %", 1, 20, 5)
take_profit_pct = st.slider("Take-profit %", 1, 20, 5)
margin_default = 1000
leverage_default = 2

prices = get_prices(live=use_live)
coins = {
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

st.subheader("Coin Positions")
data = []
total_margin, total_exposure = 0, 0

for coin, (coin_id, price) in coins.items():
    col1, col2 = st.columns(2)
    with col1:
        margin = st.number_input(f"{coin} Margin ($)", value=margin_default, key=f"margin_{coin}")
    with col2:
        leverage = st.number_input(f"{coin} Leverage (x)", value=leverage_default, key=f"leverage_{coin}")
    
    position_size = margin * leverage
    tokens = position_size / price if price > 0 else 0
    liquidation_price = price * (1 - (margin / position_size)) if position_size > 0 else 0
    stop_loss_price = price * (1 - stop_loss_pct / 100)
    take_profit_price = price * (1 + take_profit_pct / 100)
    stop_loss_pl = (stop_loss_price - price) * tokens
    take_profit_pl = (take_profit_price - price) * tokens

    data.append({
        "Coin": coin,
        "Price (USD)": price,
        "Tokens": tokens,
        "Position Size (USD)": position_size,
        "Margin (USD)": margin,
        "Liquidation Price (USD)": liquidation_price,
        "Stop Loss Price (USD)": stop_loss_price,
        "Stop Loss P/L (USD)": stop_loss_pl,
        "Take Profit Price (USD)": take_profit_price,
        "Take Profit P/L (USD)": take_profit_pl,
        "Coin ID": coin_id
    })
    
    total_margin += margin
    total_exposure += position_size

df = pd.DataFrame(data)

# --- Risk scoring
risk, advice = risk_score(total_exposure, total_margin, stop_loss_pct)
st.markdown(f"### **Risk Score: {risk}**")
st.write(advice)
st.write(f"**Total Margin:** ${total_margin:,.2f} | **Total Exposure:** ${total_exposure:,.2f}")
st.write(f"**Est. 8h Funding Fee:** ${funding_fee_estimate(total_exposure):.2f}")

# --- Styled Position Summary
def highlight_pl(val):
    color = "green" if val > 0 else "red" if val < 0 else "black"
    return f"color: {color}"

def highlight_liquidation(row):
    if row["Liquidation Price (USD)"] >= row["Price (USD)"] * 0.9:
        return ["background-color: #ffcccc"] * len(row)
    else:
        return [""] * len(row)

styled_df = (
    df.drop(columns="Coin ID")
    .style.format({
        "Price (USD)": "{:,.4f}",
        "Tokens": "{:,.2f}",
        "Position Size (USD)": "${:,.2f}",
        "Margin (USD)": "${:,.2f}",
        "Liquidation Price (USD)": "{:,.4f}",
        "Stop Loss Price (USD)": "{:,.4f}",
        "Stop Loss P/L (USD)": "${:,.2f}",
        "Take Profit Price (USD)": "{:,.4f}",
        "Take Profit P/L (USD)": "${:,.2f}"
    })
    .map(highlight_pl, subset=["Stop Loss P/L (USD)", "Take Profit P/L (USD)"])
    .apply(highlight_liquidation, axis=1)
)

st.subheader("Position Summary (Styled)")
st.dataframe(styled_df, use_container_width=True, height=600)

# --- CSV Export
export_df = df.drop(columns="Coin ID").copy()

# Apply same formatting as UI
export_df["Price (USD)"] = export_df["Price (USD)"].round(4)
export_df["Tokens"] = export_df["Tokens"].round(2)
export_df["Position Size (USD)"] = export_df["Position Size (USD)"].map("${:,.2f}".format)
export_df["Margin (USD)"] = export_df["Margin (USD)"].map("${:,.2f}".format)
export_df["Liquidation Price (USD)"] = export_df["Liquidation Price (USD)"].round(4)
export_df["Stop Loss Price (USD)"] = export_df["Stop Loss Price (USD)"].round(4)
export_df["Stop Loss P/L (USD)"] = export_df["Stop Loss P/L (USD)"].map("${:,.2f}".format)
export_df["Take Profit Price (USD)"] = export_df["Take Profit Price (USD)"].round(4)
export_df["Take Profit P/L (USD)"] = export_df["Take Profit P/L (USD)"].map("${:,.2f}".format)

csv_data = export_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Position Summary as CSV",
    data=csv_data,
    file_name="position_summary.csv",
    mime="text/csv",
)

# --- Charts
st.subheader("Exposure Per Coin")
st.bar_chart(df.set_index("Coin")[["Position Size (USD)"]])

st.subheader("Stop-loss vs Take-profit Impact")
st.bar_chart(df.set_index("Coin")[["Stop Loss P/L (USD)", "Take Profit P/L (USD)"]])

# --- Scenario Simulation
st.subheader("Scenario Simulation")
scenario_pct = st.slider("Market move (%)", -50, 50, 0)
if scenario_pct != 0:
    scenario_data = []
    for _, row in df.iterrows():
        new_price = row["Price (USD)"] * (1 + scenario_pct / 100)
        pnl = (new_price - row["Price (USD)"]) * row["Tokens"]
        scenario_data.append({"Coin": row["Coin"], "New Price (USD)": round(new_price, 4), "P/L (USD)": round(pnl, 2)})
    st.dataframe(pd.DataFrame(scenario_data))

# --- Historical Chart
st.subheader("Historical Price (7 Days)")
coin_selected = st.selectbox("Select Coin for History", df["Coin"].tolist())
coin_id = df[df["Coin"] == coin_selected]["Coin ID"].iloc[0]
hist, real_data = get_history(coin_id)
st.write("**Data Source:**", "Real Coingecko data" if real_data else "Fallback sample data")
st.line_chart(hist.set_index("time")["price"])
