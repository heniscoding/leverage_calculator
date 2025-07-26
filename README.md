# Crypto Leverage Trade Calculator

&#x20;

A **Streamlit-based web app** to build and analyze leveraged crypto positions dynamically, with per-position stop-loss and take-profit settings, risk scoring, and visual analytics.

---

## Features

- **Dynamic position builder** – add/remove positions interactively
- **Per-position stop-loss & take-profit** – each position can have unique strategy parameters
- **Risk scoring** – based on leverage and stop-loss usage
- **Scenario simulation** – model price changes and see P/L impacts
- **Historical price charts** – powered by Coingecko API
- **CSV export** – clean output with only relevant columns

---

## Screenshot

&#x20;*(Add your screenshot under **`docs/screenshot.png`**)*

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<YOUR_USERNAME>/leverage_calculator.git
cd leverage_calculator
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
# On Windows
env\.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
streamlit run leverage_calculator.py
```

Open your browser and go to [http://localhost:8501](http://localhost:8501)

---

## Usage

1. Click **Add Position** to add your first trade
2. Choose a coin, margin, leverage, stop-loss %, and take-profit %
3. Add more positions as needed, or remove them individually
4. Use **Clear All Positions** to reset the portfolio
5. Review risk scoring, charts, and historical price data
6. Download a clean CSV of your positions

---

## Project Structure

```
leverage_calculator/
├─ leverage_calculator.py   # Main Streamlit application
├─ requirements.txt         # Minimal dependencies
├─ README.md                # Project documentation (this file)
└─ docs/
   └─ screenshot.png        # Optional app screenshot placeholder
```

---

## License

This project is licensed under the MIT License – see [LICENSE](LICENSE) for details.

---

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss your ideas.

