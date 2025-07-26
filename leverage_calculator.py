import streamlit as st
import requests
import pandas as pd
import datetime
import numpy as np

# -----------------------
# Session State Init
# -----------------------
if "positions" not in st.session_state:
    st.session_state.positions = []
if "last_added_coin" not in st.session_state:
    st.session_state.last_added_coin = None
if "scenario_moves" not in st.session_state:
    st.session_state.scenario_moves = {}

# -----------------------
# Fallback Prices
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
# Price Fetchers
# -----------------------
@st.cache_data(ttl=60)
def get_prices(live=True):
    if not live:
        return fallback_prices
    try:
        ids = ",".join(fallback_prices.keys())
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd",
            timeout=5
        )
        data = r.json()
        if not data or any(v["usd"] == 0 for v in data.values()):
            raise ValueError("Invalid price response")
        return data
    except Exception as e:
        st.warning(f"Live price fetch failed ({e}). Using fallback prices.")
        return fallback_prices

@st.cache_data(ttl=300)
def get_history(coin_id, days=7):
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            f"?vs_currency=usd&days={days}",
            timeout=5
        )
        r.raise_for_status()
        prices = r.json().get("prices", [])
        if not prices:
            raise ValueError("No prices")
        df = pd.DataFrame(prices, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df.sort_values("time"), True
    except Exception:
        now = datetime.datetime.now()
        times = [now - datetime.timedelta(days=i) for i in reversed(range(days))]
        sample = [[int(t.timestamp() * 1000), 1 + 0.05 * np.sin(i)]
                  for i, t in enumerate(times)]
        df = pd.DataFrame(sample, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df.sort_values("time"), False

# -----------------------
# Risk Scoring
# -----------------------
def risk_score(total_exposure, total_margin, stop_losses):
    lr = total_exposure / total_margin if total_margin else float("inf")
    valid = [sl for sl in stop_losses if sl > 0]
    avg_sl = np.mean(valid) if valid else None

    if avg_sl is None:
        return "High", "No stop-loss set on any position. High risk!"
    if lr <= 2 and avg_sl <= 5:
        return "Low", "Disciplined stop-loss + low leverage."
    elif lr <= 3 or avg_sl <= 10:
        return "Medium", "Consider lowering leverage or tightening stop-loss."
    else:
        return "High", "High leverage or wide stop-loss. Adjust settings."

def funding_fee(total_exposure, rate=0.0002):
    return total_exposure * rate

def remove_position(idx):
    if "positions" in st.session_state and idx < len(st.session_state.positions):
        st.session_state.positions.pop(idx)

# -----------------------
# Layout
# -----------------------
st.title("Crypto Leverage Trade Calculator")
# Custom CSS for max width
st.markdown(
    """
    <style>
    .block-container {
        max-width: 980px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown("Build and analyze dynamic leveraged crypto positions.")

use_live = st.checkbox("Use live prices", value=True,
                       help="Fetch live prices from CoinGecko or use fallback static prices")

maintenance_margin = st.slider("Maintenance Margin (%)", 0.1, 5.0, 0.5, step=0.1,
                               help="Minimum equity required to maintain your leveraged position. Default is 0.5%.")

col_add, col_clear = st.columns(2)
with col_add:
    if st.button("Add Position", help="Add a new position with blank fields"):
        st.session_state.positions.append({
            "coin": "BTC",
            "margin": 0.0,
            "leverage": 0.0,
            "stop_loss_pct": 0,
            "take_profit_pct": 0
        })
        st.session_state.last_added_coin = "BTC"
with col_clear:
    if st.button("Clear All Positions", help="Remove all positions from the table"):
        st.session_state.positions.clear()
        st.session_state.last_added_coin = None
        st.session_state.scenario_moves.clear()

prices = get_prices(use_live)
coin_map = {
    sym: (cid, prices.get(cid, {}).get("usd", 1.0))
    for sym, cid in [
        ("BTC","bitcoin"),("ETH","ethereum"),("SOL","solana"),
        ("ADA","cardano"),("SUI","sui"),("LINK","chainlink"),
        ("PEPE","pepe"),("AAVE","aave"),("ONDO","ondo-finance"),
        ("PAAL","paal-ai")
    ]
}

# -----------------------
# Form for positions
# -----------------------
with st.form("positions_form"):
    remove_index = None
    for i, pos in enumerate(st.session_state.positions):
        st.markdown(f"#### Position {i+1}")
        c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 0.4])

        with c1:
            pos["coin"] = st.selectbox("Coin", list(coin_map.keys()),
                                       index=list(coin_map.keys()).index(pos["coin"]),
                                       key=f"coin_{i}", help="Select the cryptocurrency")
        with c2:
            pos["margin"] = st.number_input("Margin ($)", min_value=0.0,
                                            value=float(pos["margin"]), step=1.0,
                                            format="%.2f", key=f"m_{i}",
                                            help="Amount of your own funds allocated")
            if pos["margin"] == 0:
                st.markdown("<span style='color:red'>⚠ Fill Margin</span>", unsafe_allow_html=True)
        with c3:
            pos["leverage"] = st.number_input("Leverage (x)", min_value=0.0,
                                              value=float(pos["leverage"]), step=0.1,
                                              format="%.2f", key=f"l_{i}",
                                              help="How many times your margin is multiplied")
            if pos["leverage"] == 0:
                st.markdown("<span style='color:red'>⚠ Fill Leverage</span>", unsafe_allow_html=True)
        with c4:
            pos["stop_loss_pct"] = st.number_input("Stop-Loss %", min_value=0, max_value=100,
                                                   value=int(pos["stop_loss_pct"]), step=1, key=f"sl_{i}",
                                                   help="Percentage drop from entry price where you exit")
        with c5:
            pos["take_profit_pct"] = st.number_input("Take-Profit %", min_value=0, max_value=100,
                                                     value=int(pos["take_profit_pct"]), step=1, key=f"tp_{i}",
                                                     help="Percentage gain from entry price where you exit")
        with c6:
            if st.form_submit_button(f"✖ {i+1}", help="Remove this position"):
                remove_index = i

    update_clicked = st.form_submit_button("Update Positions") if st.session_state.positions else False

if remove_index is not None:
    remove_position(remove_index)
    st.rerun()

# -----------------------
# Calculations
# -----------------------
data = []
total_margin = total_exposure = 0.0
stop_losses = []
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
        "Coin": pos["coin"],
        "Price (USD)": price,
        "Tokens": tok,
        "Position Size (USD)": ps,
        "Margin (USD)": pos["margin"],
        "Liquidation Price (USD)": liq_price,
        "Stop Loss P/L (USD)": slp,
        "Take Profit P/L (USD)": tpp,
        "Coin ID": cid
    })
    total_margin += pos["margin"]
    total_exposure += ps
    stop_losses.append(pos["stop_loss_pct"])

if skipped_positions:
    st.warning(f"{skipped_positions} position(s) skipped because Margin or Leverage = 0")

# -----------------------
# Summary & Charts
# -----------------------
if data:
    df = pd.DataFrame(data)

    risk, advice = risk_score(total_exposure, total_margin, stop_losses)
    st.markdown(f"**Risk Score:** {risk}")
    st.write(advice)
    st.write(f"Total Margin: ${total_margin:,.2f} | Total Exposure: ${total_exposure:,.2f}")
    st.write(f"Est. 8h Funding Fee: ${funding_fee(total_exposure):.2f}")
    st.caption("Exposure = Margin × Leverage (total position size)")

    for col in ["Stop Loss P/L (USD)", "Take Profit P/L (USD)"]:
        if df[col].isna().all():
            df.drop(columns=[col], inplace=True)

    def hl_pl(v):
        if isinstance(v, (int, float)):
            if v > 0:
                return "color:#00f100"   # Bright green
            elif v < 0:
                return "color:#D50000"   # Bright red
            else:
                return "color:#000000"   # Black
        return "color:#000000"

    def hl_liq(row):
        liq = row["Liquidation Price (USD)"]
        price = row["Price (USD)"]
        if pd.notna(liq) and liq >= price * 0.95:
            return ["background-color:#482727; color:white"] * len(row)
        else:
            return [""] * len(row)

    styled = (
        df.drop(columns="Coin ID")
        .style
        .hide(axis="index")  # <--- this hides the index
        .format({
            "Price (USD)": "{:,.4f}",
            "Tokens": "{:,.2f}",
            "Position Size (USD)": "${:,.2f}",
            "Margin (USD)": "${:,.2f}",
            "Liquidation Price (USD)": "{:,.4f}",
            "Stop Loss P/L (USD)": "${:,.2f}",
            "Take Profit P/L (USD)": "${:,.2f}"
        })
        .apply(hl_liq, axis=1)
    )

    pl_cols = [c for c in df.columns if "P/L" in c]
    if pl_cols:
        styled = styled.map(hl_pl, subset=pl_cols)

    st.subheader(
        "Positions",
        help="This section lists all your positions, calculated exposure, and risk metrics. "
            "Rows highlighted in dark red indicate positions with liquidation prices close to the current market price. "
            "Consider reducing leverage, adding margin, or using a stop-loss to lower risk."
    )
    st.dataframe(styled, use_container_width=True)

    # CSV export
    exp = df.drop(columns="Coin ID").copy()
    exp["Price (USD)"] = exp["Price (USD)"].round(4)
    exp["Tokens"] = exp["Tokens"].round(2)
    exp["Position Size (USD)"] = exp["Position Size (USD)"].map("${:,.2f}".format)
    exp["Margin (USD)"] = exp["Margin (USD)"].map("${:,.2f}".format)
    if "Liquidation Price (USD)" in exp:
        exp["Liquidation Price (USD)"] = exp["Liquidation Price (USD)"].round(4)
    if "Stop Loss P/L (USD)" in exp:
        exp["Stop Loss P/L (USD)"] = exp["Stop Loss P/L (USD)"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
    if "Take Profit P/L (USD)" in exp:
        exp["Take Profit P/L (USD)"] = exp["Take Profit P/L (USD)"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "")

    csv = exp.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "positions.csv", "text/csv")

    st.subheader(
        "Exposure",
        help="Shows the total notional position size for each coin (Margin × Leverage)."
    )
    st.bar_chart(df.set_index("Coin")[["Position Size (USD)"]])

    if pl_cols:
        st.subheader(
            "P/L Impact",
            help="Displays estimated P/L outcomes for Stop Loss and Take Profit levels."
        )
        st.bar_chart(df.set_index("Coin")[pl_cols])

    st.subheader(
        "Scenario Simulation",
        help="Simulate market moves per coin. Each slider controls all positions for that coin and calculates the combined P/L impact."
    )

    if st.button("Reset All to Zero", help="Reset all per-coin sliders to 0%"):
        st.session_state.scenario_moves = {coin: 0 for coin in df["Coin"].unique()}

    scenario_results = []
    total_portfolio_pnl = 0.0

    for coin in df["Coin"].unique():
        current_move = st.session_state.scenario_moves.get(coin, 0)
        move = st.slider(f"{coin} Move (%)", -50, 50, current_move,
                        key=f"move_{coin}", help=f"Market move for {coin}")
        st.session_state.scenario_moves[coin] = move

        # Filter positions for this coin
        coin_positions = df[df["Coin"] == coin]
        combined_pnl = 0.0
        for _, row in coin_positions.iterrows():
            new_price = row["Price (USD)"] * (1 + move / 100)
            pnl = (new_price - row["Price (USD)"]) * row["Tokens"]
            combined_pnl += pnl
        total_portfolio_pnl += combined_pnl
        scenario_results.append({
            "Coin": coin,
            "Move (%)": move,
            "P/L (USD)": round(combined_pnl, 2)
        })

    scenario_df = pd.DataFrame(scenario_results)
    scenario_styled = scenario_df.style.map(
        lambda v: "color:green" if isinstance(v, (int, float)) and v > 0 else
                "color:red" if isinstance(v, (int, float)) and v < 0 else "",
        subset=["P/L (USD)"]
    )
    st.dataframe(scenario_styled, use_container_width=True)

    # --- Total portfolio P/L
    st.markdown(f"### **Net Portfolio P/L: ${total_portfolio_pnl:,.2f}**")

    # -----------------------
    # Historical Price
    # -----------------------
    st.subheader(
        "Historical Price (7d)",
        help="Displays the last 7 days of price history for the selected coin (from CoinGecko)."
    )
    unique_positions = df[["Coin", "Coin ID"]].drop_duplicates().reset_index(drop=True)
    default_coin = st.session_state.last_added_coin or unique_positions.iloc[0]["Coin"]
    default_index = 0 if default_coin not in unique_positions["Coin"].values else \
                    int(unique_positions.index[unique_positions["Coin"] == default_coin][0])
    sel = st.selectbox("Coin", unique_positions["Coin"].tolist(), index=default_index)
    cid = unique_positions.loc[unique_positions["Coin"] == sel, "Coin ID"].iloc[0]
    hist, real = get_history(cid)
    st.write("Source:", "Live" if real else "Sample")
    st.line_chart(hist.set_index("time")["price"])

else:
    st.info("No valid positions calculated. Fill margin & leverage values to include them.")
