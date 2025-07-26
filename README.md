# Crypto Leverage Trade Calculator

&#x20;

A **Streamlit-based web application** for calculating leveraged crypto positions across multiple coins, complete with risk scoring, scenario simulation, historical price charts, and CSV export functionality.

---

## Features

- Multi-coin leverage & margin calculator
- Risk scoring (Low / Medium / High) with actionable advice
- Stop-loss & take-profit scenario P/L analysis
- Market move simulation (percentage-based)
- Historical 7-day price charts using Coingecko API
- Downloadable CSV export of position summary

---

## Screenshot



*(Place your own screenshot at **``**)*

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<YOUR_USERNAME>/leverage_calculator.git
cd leverage_calculator
```

### 2. Create and Activate a Virtual Environment

#### On Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

#### On macOS / Linux

```bash
python3 -m venv .venv
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

Open your browser and navigate to [http://localhost:8501](http://localhost:8501).

---

## Exported Files

- **CSV Export**: Download your position summary directly from the app.
- **Requirements**: Minimal, portable dependencies listed in `requirements.txt`.

---

## Project Structure

```
leverage_calculator/
├─ leverage_calculator.py   # Main Streamlit application
├─ requirements.txt         # Minimal dependencies
├─ README.md                # Project documentation (this file)
└─ docs/
   └─ screenshot.png        # App screenshot placeholder
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for more details.

---

## Contributing

Pull requests are welcome! For significant changes, please open an issue first to discuss your ideas.

