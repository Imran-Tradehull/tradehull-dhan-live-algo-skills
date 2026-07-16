# Algo Development Workflow

The end-to-end path for building a Dhan algo with Dhan-Tradehull, from a
blank file to a running, monitored strategy. Each step links to the deep-dive
reference. Follow this order — it mirrors how a live algo actually executes.

```
 auth → market data → signal → order → monitor/exit → (optional) UI
```

---

## 0. Setup

```bash
pip install --pre dhanhq
pip install Dhan-Tradehull
pip install TA-Lib          # only if computing indicators (needs C lib first)
```

Keep credentials out of the code — put them in `config.py` (git-ignored):
```python
# config.py
client_code = "1100000000"
token_id    = "your_daily_access_token"
```

---

## 1. Authenticate  → `references/auth.md`

```python
from Dhan_Tradehull import Tradehull
import config

tsl = Tradehull(config.client_code, config.token_id)   # one shared session
```

- `access_token` → expires **daily**, regenerate each morning. Fine for
  manual/semi-auto work.
- `pin_totp` → **lifetime** PIN, best for fully automated / scheduled algos.

Init the `tsl` session **once** and reuse it everywhere — never per symbol,
never per loop iteration.

---

## 2. Get market data  → `references/market-data.md`

```python
ltp   = tsl.get_ltp_data(names=["RELIANCE", "NIFTY"])        # up to 500 symbols
chart = tsl.get_historical_data(tradingsymbol="RELIANCE", exchange="NSE", timeframe="5")
```

Decide the **timeframe** up front — it defines your candle and how often the
algo should act ('1','5','15','25','60','DAY').

---

## 3. Compute the signal  → `references/algo-scanner.md`

Use TA-Lib on the candle DataFrame; express every condition as a **named
boolean** (`bc*` buy, `sc*` sell — see `references/coding-style.md`). Signal
off the **last completed candle**.

```python
import talib
chart["rsi"] = talib.RSI(chart["close"], timeperiod=14)
rc           = chart.iloc[-1]

bc1          = rc["rsi"] < 30       # oversold
bc2          = orderbook[name]["traded"] is None

if bc1 and bc2:
    ...   # go to step 4
```

Do the condition logic **in Python** — not Dhan conditional-trigger orders —
for full control over multi-condition signals.

---

## 4. Place the order  → `references/orders.md`

| Strategy type | Use |
|---------------|-----|
| Intraday with SL + target | `place_super_order()` |
| Swing / BTST / positional | `place_forever_order()` (GTT) |
| Plain entry | `order_placement()` |

```python
ltp        = tsl.get_ltp_data(names=[name])[name]
buy_price  = round(ltp * 1.002, 1)      # BUY limit ABOVE ltp for instant fill

tsl.place_super_order(
    tradingsymbol=name, exchange="NSE",
    transaction_type="BUY", quantity=tsl.get_lot_size(name),
    order_type="LIMIT", trade_type="MIS",
    price=buy_price,
    target_price=round(ltp * 1.01, 1),
    stop_loss_price=round(ltp * 0.995, 1),
)
```

> 🚨 **From 1 Apr 2026, F&O MARKET orders are banned — always LIMIT.**
> BUY limit above LTP, SELL limit below LTP → instant fill.
> Always fetch `get_lot_size()` dynamically — never hardcode quantity.

---

## 5. Track & exit  → `references/portfolio.md`, `references/utilities.md`

```python
positions = tsl.get_positions()        # DataFrame
pnl       = tsl.get_live_pnl()         # float

# auto square-off on profit/loss threshold
tsl.enable_pnl_based_exit(profit_value=1000, loss_value=800,
                          product_types=("INTRADAY",), enable_kill_switch=True)
```

Maintain an `orderbook` dict keyed by symbol so the algo knows what it is
already in and does not double-enter (the `traded is None` guard in step 3).

---

## 6. (Optional) Add a UI / monitoring  → `references/flask-ui.md`

Wrap the algo in a small Flask app for a browser dashboard — a "Run Scan"
button, live positions, P&L. Keep algo logic in its own module; Flask just
calls it and returns JSON.

---

## 7. Run it live

- **Scheduled / always-on:** `pin_totp` auth + `nohup`/`systemd`/`tmux` so it
  survives terminal close.
- **Loop cadence:** for a 5-min algo, act once per new candle
  (`time.sleep(300)`), not every second.
- **Fail safe:** wrap broker calls in `try/except`, log errors, and keep the
  loop alive — one bad symbol or a transient API error must not kill the algo.

---

## Reference map

| Step | Read |
|------|------|
| Auth | `references/auth.md` |
| Market data | `references/market-data.md` |
| Indicators / scanner | `references/algo-scanner.md` |
| Options strike selection | `references/options.md` |
| Orders (super / forever / plain) | `references/orders.md` |
| Portfolio / positions / P&L | `references/portfolio.md` |
| Lot size, margin, P&L exit, kill switch | `references/utilities.md` |
| Coding style (bc/sc, alignment) | `references/coding-style.md` |
| Browser UI | `references/flask-ui.md` |
| Errors & SEBI rules | `references/error-log.md` |

Worked examples: `examples/intraday_options_algo.py`,
`examples/positional_spread_algo.py`, `examples/nifty50_scanner_algo.py`.
