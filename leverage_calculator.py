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
# Funding fee
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
    padding: 10px 15px;
    border: 1px solid #444;
    border-radius: 6px;
    font-size: 0.95rem;
    line-height: 1.4;
    margin-bottom: 20px;
    background-color: #1e1e1e;
    color: #ffffff;
}
.instructions-box strong { color: #4CAF50; }

/* Keep button height consistent */
div[data-testid="stButton"] button {
    height: 38px !important;
}

/* Container max width */
.block-container {
    max-width: 980px;
    padding-left: 2rem;
    padding-right: 2rem;
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
# Add Position Toolbar Styles
# -----------------------
st.markdown("""
<style>
/* Reduce spacing between columns */
div[data-testid="stHorizontalBlock"] {
    gap: 0.5rem !important;
}

/* Reduce vertical gap between stacked elements */
.st-emotion-cache-ko87jo {
    gap: 0.2rem !important;
}

/* Remove extra bottom margin on number inputs and checkboxes */
div[data-testid="stNumberInputContainer"],
div[data-testid="stCheckbox"] {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
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

/* Vertically center the trash button column */
div[data-testid="stColumn"]:last-child > div[data-testid="stVerticalBlock"] {
    justify-content: center !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #00b106 !important;  /* your primary green */
    color: white !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    height: 40px !important;
    font-size: 14px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #009505 !important;
}
/* Remove orange focus outline from all Streamlit buttons */
div[data-testid="stButton"] > button:focus,
div[data-testid="stDownloadButton"] > button:focus {
    outline: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# --- Toolbar row ---
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    add = st.button("✛ Add Position", type="primary", key="add_position_btn")

with col2:
    use_live = st.checkbox("Use live prices", value=True,
                           help="Fetch live prices from CoinGecko or use fallback static prices")

with col3:
    maintenance_margin = st.number_input(
        "Maintenance Margin (%)",
        min_value=0.1,
        max_value=5.0,
        value=0.5,
        step=0.1,
        label_visibility="collapsed"  # hides label above input
    )
    st.caption("Maintenance Margin (%)")  # caption under input for clarity

# --- Handle button click ---
if add:
    st.session_state.positions.append({
        "coin": "BTC",
        "margin": 0.0,
        "leverage": 0.0,
        "stop_loss_pct": 0,
        "take_profit_pct": 0
    })
    st.session_state.last_added_coin = "BTC"

prices = get_prices(use_live)

# --- Summary Card (only if positions exist)
if st.session_state.positions:
    total_margin = sum(pos["margin"] for pos in st.session_state.positions)
    total_exposure = sum(pos["margin"] * pos["leverage"] for pos in st.session_state.positions)
    funding = funding_fee(total_exposure)
    
    st.markdown(f"""
        <div style="background-color:#2a2a2a; border:1px solid #444; border-radius:6px; 
                    padding:15px; margin:15px 0; color:white;">
            <strong>Total Margin:</strong> ${total_margin:,.2f} &nbsp; | &nbsp;
            <strong>Total Exposure:</strong> ${total_exposure:,.2f}<br>
            <strong>Est. 8h Funding Fee:</strong> ${funding:,.2f}
            <div style="font-size:0.9rem; color:#aaa; margin-top:4px;">
                Exposure = Margin × Leverage (total position size)
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

# -----------------------
# Prices & Coin Map
# -----------------------
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
# Positions (auto-update)
# -----------------------
remove_index = None
for i, pos in enumerate(st.session_state.positions):
    coin_value = st.session_state.get(f"coin_{i}", pos["coin"])
    margin_value = st.session_state.get(f"m_{i}", pos["margin"])
    leverage_value = st.session_state.get(f"l_{i}", pos["leverage"])
    margin_fmt = f"${margin_value:,.0f}" if margin_value.is_integer() else f"${margin_value:,.2f}"
    leverage_fmt = f"{leverage_value:.0f}x" if leverage_value.is_integer() else f"{leverage_value:.2f}x"
    st.markdown(
        f"<p style='font-size:18px; font-weight:700;'>"
        f"Position {i+1} "
        f"<span style='font-size:16px; font-weight:400;'>({coin_value} – {margin_fmt} Margin × {leverage_fmt})</span>"
        f"</p>",
        unsafe_allow_html=True
    )

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
        if st.button("🗑️", key=f"remove_{i}", help="Remove this position"):
            remove_index = i

    st.divider()

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
        "Coin": pos["coin"], "Price (USD)": price, "Tokens": tok,
        "Position Size (USD)": ps, "Margin (USD)": pos["margin"],
        "Liquidation Price (USD)": liq_price,
        "Stop Loss P/L (USD)": slp, "Take Profit P/L (USD)": tpp,
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
        return ["background-color:#482727; color:white"] * len(row) \
            if pd.notna(liq) and liq >= price * 0.95 else [""] * len(row)

    styled = (
        df.drop(columns="Coin ID")
        .style
        .hide(axis="index")
        .format({
            "Price (USD)": "{:,.4f}", "Tokens": "{:,.2f}",
            "Position Size (USD)": "${:,.2f}", "Margin (USD)": "${:,.2f}",
            "Liquidation Price (USD)": "{:,.4f}",
            "Stop Loss P/L (USD)": "${:,.2f}", "Take Profit P/L (USD)": "${:,.2f}"
        })
        .apply(hl_liq, axis=1)
    )
    pl_cols = [c for c in df.columns if "P/L" in c]
    if pl_cols:
        styled = styled.map(hl_pl, subset=pl_cols)

    st.markdown("<p style='font-size:20px; font-weight:800;'>Positions Breakdown</p>", unsafe_allow_html=True)
    st.dataframe(styled, use_container_width=True)

    csv = df.drop(columns="Coin ID").to_csv(index=False).encode("utf-8")

    # Custom style for download button
    st.markdown("""
    <style>
    div[data-testid="stDownloadButton"] > button {
        background-color: #495057 !important;
        color: white !important;
        border-radius: 6px !important;
        height: 40px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #32373d !important;
        color: #fff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.download_button("Download CSV", csv, "positions.csv", "text/csv")

    # --- Exposure (collapsible)
    with st.expander("Exposure", expanded=False):
        st.bar_chart(df.set_index("Coin")[["Position Size (USD)"]])

    # --- P/L Impact (collapsible)
    if pl_cols:
        with st.expander("P/L Impact", expanded=False):
            st.bar_chart(df.set_index("Coin")[pl_cols])

    # --- Scenario Simulation (collapsible)
    with st.expander("Scenario Simulation", expanded=False):
        if st.button("Reset All to Zero"):
            st.session_state.scenario_moves = {coin: 0 for coin in df["Coin"].unique()}
        scenario_results = []
        total_portfolio_pnl = 0.0
        for coin in df["Coin"].unique():
            current_move = st.session_state.scenario_moves.get(coin, 0)
            move = st.slider(f"{coin} Move (%)", -50, 50, current_move, key=f"move_{coin}")
            st.session_state.scenario_moves[coin] = move
            coin_positions = df[df["Coin"] == coin]
            combined_pnl = sum(
                (row["Price (USD)"] * (1 + move / 100) - row["Price (USD)"]) * row["Tokens"]
                for _, row in coin_positions.iterrows()
            )
            total_portfolio_pnl += combined_pnl
            scenario_results.append({"Coin": coin, "Move (%)": move, "P/L (USD)": round(combined_pnl, 2)})
        scenario_df = pd.DataFrame(scenario_results)
        st.dataframe(
            scenario_df.style.map(
                lambda v: "color:green" if isinstance(v, (int, float)) and v > 0 else
                          "color:red" if isinstance(v, (int, float)) and v < 0 else "",
                subset=["P/L (USD)"]
            ),
            use_container_width=True
        )
        st.markdown(f"### **Net Portfolio P/L: ${total_portfolio_pnl:,.2f}**")

    # --- Historical Price (collapsible)
    with st.expander("Historical Price (7d)", expanded=False):
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
