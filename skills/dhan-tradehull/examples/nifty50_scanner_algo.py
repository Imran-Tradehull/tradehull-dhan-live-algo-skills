# -------------------------------------------------------------------
# NIFTY 50 Scanner  —  EMA20/50 crossover confirmed by RSI
#
# Timeframe : 5 minute
# Bullish   : EMA20 crosses ABOVE EMA50  AND  RSI > 60
# Bearish   : EMA20 crosses BELOW EMA50  AND  RSI < 40
#
# Requires  : pip install Dhan-Tradehull TA-Lib
# See       : references/algo-scanner.md, references/flask-ui.md
# -------------------------------------------------------------------

import talib
from Dhan_Tradehull import Tradehull

# ---- credentials --------------------------------------------------
# Put these in a private config.py and `from config import ...` instead
# of hardcoding. access_token expires DAILY — regenerate each morning.
client_code = "YOUR_CLIENT_CODE"
token_id    = "YOUR_ACCESS_TOKEN"

# ---- single shared broker session ---------------------------------
tsl = Tradehull(client_code, token_id)

# ---- NIFTY 50 constituents (edit when the index reshuffles) -------
nifty50_stocks = [
    "ADANIENT",   "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL",        "BHARTIARTL",
    "CIPLA",      "COALINDIA",  "DRREDDY",    "EICHERMOT",  "GRASIM",
    "HCLTECH",    "HDFCBANK",   "HDFCLIFE",   "HEROMOTOCO", "HINDALCO",
    "HINDUNILVR", "ICICIBANK",  "INDUSINDBK", "INFY",       "ITC",
    "JSWSTEEL",   "KOTAKBANK",  "LT",         "M&M",        "MARUTI",
    "NESTLEIND",  "NTPC",       "ONGC",       "POWERGRID",  "RELIANCE",
    "SBILIFE",    "SBIN",       "SHRIRAMFIN", "SUNPHARMA",  "TATACONSUM",
    "TATAMOTORS", "TATASTEEL",  "TCS",        "TECHM",      "TITAN",
    "TRENT",      "ULTRACEMCO", "WIPRO",      "JIOFIN",
]


def scan_stock(symbol):
    """Scan one stock. Return a signal dict, or None if no signal / error."""

    # ---- pull 5-min candles, skip on error ------------------------
    try:
        chart = tsl.get_historical_data(tradingsymbol=symbol, exchange="NSE", timeframe="5")
    except Exception:
        return None

    if chart is None or len(chart) < 60:      # need enough bars for EMA50
        return None

    # ---- indicators -----------------------------------------------
    chart["ema20"] = talib.EMA(chart["close"], timeperiod=20)
    chart["ema50"] = talib.EMA(chart["close"], timeperiod=50)
    chart["rsi"]   = talib.RSI(chart["close"], timeperiod=14)

    rc             = chart.iloc[-1]     # last completed candle
    pc             = chart.iloc[-2]     # previous candle

    # ---- crossover state flip -------------------------------------
    bull_cross     = (pc["ema20"] <= pc["ema50"]) and (rc["ema20"] > rc["ema50"])
    bear_cross     = (pc["ema20"] >= pc["ema50"]) and (rc["ema20"] < rc["ema50"])

    # ---- buy conditions -------------------------------------------
    bc1            = bull_cross
    bc2            = rc["rsi"] > 60

    # ---- sell conditions ------------------------------------------
    sc1            = bear_cross
    sc2            = rc["rsi"] < 40

    if bc1 and bc2:
        signal = "BULLISH"
    elif sc1 and sc2:
        signal = "BEARISH"
    else:
        return None

    return {
        "symbol": symbol,
        "signal": signal,
        "ltp":    round(float(rc["close"]), 2),
        "ema20":  round(float(rc["ema20"]), 2),
        "ema50":  round(float(rc["ema50"]), 2),
        "rsi":    round(float(rc["rsi"]),   2),
    }


def run_scan():
    """Scan the whole NIFTY 50 list. Return list of signal dicts."""

    signals = []
    for symbol in nifty50_stocks:
        row = scan_stock(symbol)
        if row is not None:
            signals.append(row)
    return signals


if __name__ == "__main__":
    hits = run_scan()
    print(f"Signals found: {len(hits)}")
    for r in hits:
        print(r)
