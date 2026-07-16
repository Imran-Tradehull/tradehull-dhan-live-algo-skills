# Scanner Algo — Indicator Signals Across a Watchlist

How to build a **scanner**: loop a basket of symbols, compute technical
indicators with TA-Lib on `get_historical_data()`, and flag entry/exit
signals. This is the foundation of most equity/index algos.

> ✅ **Pattern:** `get_historical_data()` → TA-Lib indicator → named `bc/sc`
> booleans → collect signals. Do NOT use Dhan's conditional-trigger orders;
> compute conditions in Python for full control (see `references/orders.md`).

---

## 1. Requirements

```bash
pip install TA-Lib          # needs the TA-Lib C library on the system first
pip install Dhan-Tradehull
```

If `pip install TA-Lib` fails, install the C library first:
```bash
# Debian/Ubuntu
sudo apt-get install -y ta-lib          # or build from source (ta-lib-0.4.0-src.tar.gz)
```

---

## 2. Minimal single-symbol scan

```python
import talib
from Dhan_Tradehull import Tradehull

tsl = Tradehull(client_code, token_id)

# ---- pull candles (timeframe: '1','5','15','25','60','DAY') --------
chart          = tsl.get_historical_data(tradingsymbol="RELIANCE", exchange="NSE", timeframe="5")

# ---- indicators ---------------------------------------------------
chart["ema20"] = talib.EMA(chart["close"], timeperiod=20)
chart["ema50"] = talib.EMA(chart["close"], timeperiod=50)
chart["rsi"]   = talib.RSI(chart["close"], timeperiod=14)

rc             = chart.iloc[-1]     # last completed candle
pc             = chart.iloc[-2]     # previous candle

# ---- named conditions (see coding-style.md) -----------------------
bull_cross     = (pc["ema20"] <= pc["ema50"]) and (rc["ema20"] > rc["ema50"])
bc1            = bull_cross
bc2            = rc["rsi"] > 60

if bc1 and bc2:
    print("BULLISH", rc["close"])
```

> ⚠️ **Always signal off the *last completed* candle.** `chart.iloc[-1]` is the
> most recent candle; on live data it may still be forming. For strict
> confirmation use `chart.iloc[-2]` as the signal candle and `-3` as previous.

---

## 3. Crossover detection

A crossover needs **two candles** — the state must flip between them:

```python
# EMA20 crosses ABOVE EMA50  (golden cross)
bull_cross = (pc["ema20"] <= pc["ema50"]) and (rc["ema20"] > rc["ema50"])

# EMA20 crosses BELOW EMA50  (death cross)
bear_cross = (pc["ema20"] >= pc["ema50"]) and (rc["ema20"] < rc["ema50"])
```

Checking only `rc["ema20"] > rc["ema50"]` flags a *state*, not a *cross* —
it would fire on every candle while EMA20 stays above. Use the two-candle
flip to catch the exact crossover bar.

---

## 4. Full watchlist scanner

```python
import talib
from Dhan_Tradehull import Tradehull

tsl = Tradehull(client_code, token_id)

watchlist = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]


def scan_stock(symbol):
    """Scan one symbol. Return a signal dict, or None if no signal."""

    # ---- pull candles, skip on error / thin data ------------------
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

    rc             = chart.iloc[-1]
    pc             = chart.iloc[-2]

    # ---- buy / sell conditions ------------------------------------
    bull_cross     = (pc["ema20"] <= pc["ema50"]) and (rc["ema20"] > rc["ema50"])
    bear_cross     = (pc["ema20"] >= pc["ema50"]) and (rc["ema20"] < rc["ema50"])

    bc1            = bull_cross
    bc2            = rc["rsi"] > 60

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
        "rsi":    round(float(rc["rsi"]),   2),
    }


def run_scan():
    signals = []
    for symbol in watchlist:
        row = scan_stock(symbol)
        if row is not None:
            signals.append(row)
    return signals


if __name__ == "__main__":
    for r in run_scan():
        print(r)
```

Full runnable version (NIFTY 50 basket): `examples/nifty50_scanner_algo.py`.

---

## 5. Common indicators (TA-Lib)

```python
chart["rsi"]                          = talib.RSI(chart["close"], timeperiod=14)
chart["ema20"]                        = talib.EMA(chart["close"], timeperiod=20)
chart["sma50"]                        = talib.SMA(chart["close"], timeperiod=50)
chart["macd"], chart["sig"], _        = talib.MACD(chart["close"])
chart["atr"]                          = talib.ATR(chart["high"], chart["low"], chart["close"], timeperiod=14)
chart["upper"], chart["mid"], chart["lower"] = talib.BBANDS(chart["close"], timeperiod=20)
chart["adx"]                          = talib.ADX(chart["high"], chart["low"], chart["close"], timeperiod=14)
```

`get_historical_data()` returns columns: `open, high, low, close, volume,
timestamp, open_interest`. Pass the raw pandas Series into TA-Lib.

---

## 6. Turning a signal into an order

A scanner *finds* signals; entry is a separate step. For intraday with
SL + target, place a super order (see `references/orders.md`):

```python
signals = run_scan()
for s in signals:
    if s["signal"] == "BULLISH":
        ltp        = tsl.get_ltp_data(names=[s["symbol"]])[s["symbol"]]
        buy_price  = round(ltp * 1.002, 1)     # limit > LTP for instant fill
        tsl.place_super_order(
            tradingsymbol=s["symbol"], exchange="NSE",
            transaction_type="BUY", quantity=1,
            order_type="LIMIT", trade_type="MIS",
            price=buy_price,
            target_price=round(ltp * 1.01, 1),
            stop_loss_price=round(ltp * 0.995, 1),
        )
```

> 🚨 F&O MARKET orders banned from 1 Apr 2026 — always LIMIT. BUY limit
> must be **above** LTP, SELL limit **below** LTP, for an instant fill.

---

## 7. Performance notes

- **One shared `tsl` session** for the whole scan — never re-init per symbol.
- `get_historical_data()` is ~1 call/symbol. A 50-symbol scan is 50 calls;
  budget a few seconds and avoid hammering it in a tight loop.
- **Skip bad symbols gracefully** (`try/except` + `len < 60` guard). Index
  reshuffles and symbol renames (e.g. a demerger) cause "no data" — the scan
  should log and continue, never crash.
- To scan continuously, wrap `run_scan()` in a loop with `time.sleep(300)` for
  5-min candles (re-scan once per new candle, not every second).

See also: `references/market-data.md`, `references/algo-dev-workflow.md`,
`references/flask-ui.md` (browser dashboard on top of a scanner).
