# Dhan-Tradehull Error Log

Real errors from production and student support sessions.
Version tracked per entry. Add new errors at the top.

> ⚠️ **Codebase has been upgraded many times** — some errors below were fixed in
> earlier versions and may not occur in v3.3.1. They are kept as reference because:
> 1. The error TYPE and debugging pattern is still valid
> 2. Students on older versions may still face them
> 3. Understanding root causes helps write better code from the start
>
> **Always ensure you are on latest version before debugging:**
> ```bash
> pip install dhanhq==2.2.0
> pip install Dhan-Tradehull==3.3.1
> ```

---

## REGULATION-001 — MARKET Orders Not Allowed (SEBI, Apr 2026)

**Effective:** 1st April 2026
**Applies to:** F&O orders via Dhan API

**Rule:**
SEBI has banned MARKET order type for F&O from 1st April 2026.
Passing `order_type='MARKET'` will be rejected by the exchange.

**Fix — always use LIMIT with a favorable price:**

```python
# Get LTP first
ltp = tsl.get_ltp_data(names=['NIFTY 19 DEC 24400 CALL'])['NIFTY 19 DEC 24400 CALL']

# BUY → limit price must be GREATER than LTP (ensures instant fill)
buy_price = round(ltp * 1.02, 1)
order_id  = tsl.order_placement(tradingsymbol, exchange, qty,
                                 buy_price, 0, 'LIMIT', 'BUY', 'MIS')

# SELL → limit price must be LESS than LTP (ensures instant fill)
sell_price = round(ltp * 0.98, 1)
order_id   = tsl.order_placement(tradingsymbol, exchange, qty,
                                  sell_price, 0, 'LIMIT', 'SELL', 'MIS')
```

**Summary:**
| Transaction | Limit Price Rule | Why |
|-------------|-----------------|-----|
| `BUY` | price **>** LTP | Maker takes the ask — fills instantly |
| `SELL` | price **<** LTP | Maker hits the bid — fills instantly |

---

## ERROR-001 — Invalid or Expired Access Token

**Version:** 3.3.1
**Error Code:** `DH-901`
**Error Type:** `Invalid_Authentication`

**Full traceback:**
```
Attempting authentication using ACCESS TOKEN.
Access token login failed: Access token profile validation failed:
Profile validation failed: HTTP 401 ->
{'errorType': 'Invalid_Authentication', 'errorCode': 'DH-901',
'errorMessage': 'Client ID or user generated access token is invalid or expired.'}
Login failed. Please retry with valid credentials.

Traceback (most recent call last):
  File "Dhan_Tradehull.py", line 61, in __init__
    raise Exception("Login failed. Please retry with valid credentials.")
Exception: Login failed. Please retry with valid credentials.
```

**Cause:**
- Access token has expired (tokens are valid for 1 trading day only)
- Wrong `token_id` passed — copy-paste error or stale token from previous session
- Wrong `client_code` passed

**Fix:**
1. Log in to [Dhan web](https://web.dhan.co) → My Profile → API Access → generate a new access token
2. Replace `token_id` in your script with the new token
3. Re-run

**Code pattern:**
```python
client_code = "YOUR_CLIENT_CODE"   # numeric, from Dhan profile
token_id    = "YOUR_NEW_TOKEN"     # regenerate daily before market open

tsl = Tradehull(client_code, token_id, mode="access_token")
```

**Prevention:**
- Never hardcode the token — read from a `.env` file or `config.py`
- Regenerate token every morning before running any algo
- Add a try/except around init to catch this gracefully:

```python
try:
    tsl = Tradehull(client_code, token_id, mode="access_token")
except Exception as e:
    print(f"Auth failed: {e}")
    # send Telegram alert or exit cleanly
```

---

*Add new errors below this line in the same format*

---

## ERROR-002 — Rate Limit Hit (DH-904)

**Error:**
```
{'status': 'failure', 'remarks': {'error_code': 'DH-904', 'error_type': 'Rate_Limit', ...}}
Exception in Getting OHLC data as {'status': 'failure', ...}
```

**Cause:** Too many API calls per second. LTP API = 1 request/second limit.

**Fix:**
```python
time.sleep(1)   # after every get_ltp_data / get_ohlc_data call
# OTM_Strike_Selection internally calls LTP — add sleep after it too
```

---

## ERROR-003 — Expired Contract in Watchlist

**Error:**
```
single positional indexer is out-of-bounds for NIFTY 05 SEP 24400 CALL
single positional indexer is out-of-bounds for SENSEX 06 SEP 77000 PUT
```

**Cause:** Expired F&O contracts still in watchlist or code.

**Fix:** Remove expired contracts. Check expiry date before using symbol.

```python
# Correct symbol format
# ❌ Wrong: 'NIFTY 02 JAN 22500 CE'
# ✅ Correct: 'NIFTY 02 JAN 22500 CALL'
```

---

## ERROR-004 — Tick Size Mismatch

**Error:**
```
EXCH:16283: The order price is not multiple of the tick size
```

**Cause:** price not rounded to the instrument's tick size. **Two traps:**

1. **`SEM_TICK_SIZE` is in PAISE, not rupees.** `5.0` = ₹0.05, `10.0` = ₹0.10.
   Divide by 100 before using it as the rounding step.
2. **Tick varies per symbol.** RELIANCE/TCS = ₹0.10, YESBANK = ₹0.01,
   NIFTY options = ₹0.05. Hardcoding one value rejects the others.

**Fix:**
```python
def get_tick(symbol, exchange="NSE"):
    """Tick size in RUPEES."""
    row = tsl.instrument_df[
        (tsl.instrument_df["SEM_EXM_EXCH_ID"] == exchange)
        & (tsl.instrument_df["SEM_TRADING_SYMBOL"] == symbol)
    ]
    if row.empty:
        return 0.05
    return float(row.iloc[-1]["SEM_TICK_SIZE"]) / 100.0    # ⚠️ paise -> rupees


def round_tick(price, symbol):
    tick = get_tick(symbol)
    return round(round(price / tick) * tick, 2)

# BUY limit 0.2% above LTP, rounded to the symbol's real tick
price = round_tick(ltp * 1.002, "RELIANCE")     # 1307.2894 -> 1307.30 ✅
```

For options, match on `SEM_CUSTOM_SYMBOL` instead of `SEM_TRADING_SYMBOL`.

> ⚠️ **Do NOT use the raw value as the step** — `round(price / 5.0) * 5.0`
> rounds to the nearest **₹5**. It won't be rejected (₹120.00 is a valid 0.05
> multiple), so the bug is silent — but a ₹3.40 option becomes **₹5.00**, a
> 47% price error. Always divide by 100 first.

---

## ERROR-005 — STOPMARKET Not Supported for Options

**Error:** Order rejected silently or with exchange error.

**Cause:** `order_type='STOPMARKET'` is not supported for F&O options.

**Fix:** Use `STOPLIMIT` instead:
```python
tsl.order_placement(..., price=29, trigger_price=30,
                    order_type='STOPLIMIT', ...)  # ✅
# ❌ order_type='STOPMARKET' — not allowed for options
```

---

## ERROR-006 — DAY Timeframe Not Supported for Futures/Commodities

**Error:**
```
Exception in Getting OHLC data as For Future or Commodity, DAY - Timeframe not supported by API
```

**Cause:** `timeframe='DAY'` not supported for futures/commodity contracts (only for equity/index).

**Fix:** Use intraday timeframe `'60'` and resample if needed:
```python
data = tsl.get_historical_data('NIFTY JAN FUT', 'NFO', '60')  # ✅
# data = tsl.get_historical_data('NIFTY JAN FUT', 'NFO', 'DAY')  ❌
```

---

## ERROR-007 — ModuleNotFoundError: Dhan_Tradehull

**Error:**
```
ModuleNotFoundError: No module named 'Dhan_Tradehull'
```

**Cause:** Either library not installed, or old `Dhan_Tradehull_V2` import used.

**Fix:**
```bash
pip install Dhan-Tradehull
```
```python
from Dhan_Tradehull import Tradehull   # ✅ v3.x
# from Dhan_Tradehull_V2 import Tradehull  ❌ old — do not use
```

---

## ERROR-008 — Unsupported Timeframe Value

**Error:**
```
Exception: interval value must be ['1','5','15','25','60','DAY']
```

**Cause:** Passing unsupported timeframe like `2`, `3`, `10`, `12`, `30`.

**Fix:** Only use: `'1'`, `'5'`, `'15'`, `'25'`, `'60'`, `'DAY'`
- For 2-min data: fetch `'1'` and use `tsl.resample_timeframe(df, '2T')`
- For 30-min: fetch `'5'` and resample to `'30T'`
- Always pass as **string**, not int

---

## ERROR-009 — SSL Certificate Error

**Error:**
```
WebSocket connection error: [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: unable to get local issuer certificate
```

**Fix:**
```bash
pip install certifi --upgrade
```
If still failing, manually install certifi .whl from PyPI.

---

## ERROR-010 — get_option_chain returns tuple, not DataFrame

**Error:**
```
AttributeError: 'tuple' object has no attribute 'columns'
```

**Cause:** `get_option_chain()` returns TWO values — `(atm_strike, dataframe)`.

**Fix:**
```python
atm_strike, option_chain = tsl.get_option_chain(...)   # ✅
# option_chain = tsl.get_option_chain(...)              # ❌ gets tuple
```

---

## ERROR-011 — SELL CNC Rejected (cannot short in delivery)

**Error:** sell order rejected / insufficient holdings, on a stock you don't own.

**Cause:** `trade_type="CNC"` is **delivery** — you can only sell what you
already hold. Shorting is not possible in CNC.

**Fix:** use `MIS` to short intraday, or skip sell signals when running CNC:

```python
# CNC cannot short — only act on the long side
if trade_type == "CNC" and signal != "BULLISH":
    return {"placed": False, "note": "sell skipped (CNC = no short)"}
```

| Product | Long | Short | Squares off |
|---------|------|-------|-------------|
| `MIS`   | ✅ | ✅ | auto ~15:15–15:20 |
| `CNC`   | ✅ | ❌ | never — real delivery, needs full cash |

> ⚠️ **MIS entries stop working after ~15:20** (auto square-off window).
> Late-session algos must switch to CNC — and therefore go long-only.

---

## ERROR-012 — Scanner returns 0 signals (state vs crossover)

**Not an error — a logic misunderstanding.** A *crossover* and a *state* are
different conditions, and mixing them up causes both "no signals ever" and
"every stock signals at once".

```python
# CROSSOVER — the exact candle EMA20 flips above EMA50. Rare, precise entry.
bull_cross = (pc["ema20"] <= pc["ema50"]) and (rc["ema20"] > rc["ema50"])

# STATE — EMA20 is simply above EMA50. True for ~half the universe, every candle.
bull_state = rc["ema20"] > rc["ema50"]
```

| Use | Signals per scan (200 stocks) | Meaning |
|-----|------|---------|
| Crossover | ~0–3 | fresh trend flip — an entry trigger |
| State | ~80–100 | trend alignment — a filter, not a trigger |

**Rule:** a crossover needs **two candles** (`iloc[-2]` and `iloc[-1]`) — the
state must flip between them. Checking only `rc` gives a state, not a cross.

If using **state** to fire orders, cap the entries — otherwise one scan tries
to enter half the market. And note a cap fills in **iteration order**
(alphabetical), not by quality: rank the signals first if you want the *best*
N rather than the *first* N.

---

## ERROR-013 — Test call places a REAL order

**Cause:** an endpoint/function that auto-fires orders will fire them when you
call it to "just check the data". Curling a live `/scan_one` in dev = a real
position on the account.

**Fix:** make dry-run the default and require an explicit opt-in to trade.

```python
def scan_stock(symbol, place_order=False):     # ✅ safe default
    ...
    if place_order and signal in ("BULLISH", "BEARISH"):
        row["order"] = place_signal_order(row)
```

```python
# testing — never fires
scan_stock("RELIANCE", place_order=False)
# live path — explicit
scan_stock("RELIANCE", place_order=True)
```

Also expose a dry flag on any HTTP route that can trade:
`/scan_one?symbol=X&dry=1`. A safe default costs nothing; an armed default
costs real money.
