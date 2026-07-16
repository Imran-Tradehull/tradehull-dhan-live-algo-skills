# TradeHull Coding Style Guide

This is how TradeHull algo code is written. Cursor must follow this style
exactly when generating any Dhan_Tradehull strategy code.

---

## 1. Vertical Alignment of Assignments

All assignments in a block are vertically aligned at the `=` sign.
Use spaces (not tabs) to pad variable names to the same column.

```python
# ✅ TradeHull style
book                  = xw.Book('Algo1.xlsx')
orderbook_sheet       = book.sheets['Live Orderbook']
completed_sheet       = book.sheets['Completed_Orderbook']
config_sheet          = book.sheets['Strategy Config']
client_code           = str(int(config_sheet.range('B1').value))
access_token          = config_sheet.range('B2').value.replace(" ", "")
tsl                   = Tradehull(client_code, access_token)
watchlist             = [name for name in config_sheet.range('D2:D1000').value if name is not None]
status                = {'traded': None, 'options_name': None}
re_entry              = True
orderbook             = {name: status.copy() for name in watchlist}

# ❌ Not this
book = xw.Book('Algo1.xlsx')
orderbook_sheet = book.sheets['Live Orderbook']
tsl = Tradehull(client_code, access_token)
```

Same rule applies **inside loops**:
```python
ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=0)
lot_size                 = tsl.get_lot_size(ce_name)
options_ltp              = tsl.get_ltp_data(names=[selling_name, hedging_name])
selling_ltp              = options_ltp[selling_name]
hedging_ltp              = options_ltp[hedging_name]
```

---

## 2. Named Boolean Conditions (bc/sc pattern)

Every entry condition is a named boolean — never inline in `if` statement.

```python
# ✅ TradeHull style — named booleans
bc1 = comp_candle['STX_15_3'] == 'up'
bc2 = orderbook[name]['traded'] is None
bc3 = comp_candle['close'] > sr['r1']
bc4 = total_active_trades < max_orders

sc1 = comp_candle['STX_15_3'] == 'down'
sc2 = orderbook[name]['traded'] is None
sc3 = comp_candle['close'] < sr['s1']
sc4 = total_active_trades < max_orders

if bc1 and bc2 and bc3 and bc4:
    # entry logic

# ❌ Not this
if comp_candle['STX_15_3'] == 'up' and orderbook[name]['traded'] is None and ...:
```

**Naming convention:**
- `bc1`, `bc2`, `bc3`... = **b**uy **c**onditions
- `sc1`, `sc2`, `sc3`... = **s**ell **c**onditions

**Commented-out conditions** stay in code as `True` with comment:
```python
bc1 = True  # comp_candle['rsi'] > 60   ← disabled but visible
```

---

## 3. Block Comments with Divider Lines

Major logical sections are separated with long dashed comment lines:

```python
# -------------------------------------------- Bullish Block Sell Puts  --------------------------------------------

# ... bullish entry code ...

# -------------------------------------------- Bearish Block Sell Calls  --------------------------------------------

# ... bearish entry code ...

# -------------------------------------------- Trailing Stop Loss and Take Profit  --------------------------------------------
```

Inline comments are short and factual:
```python
nap = ce_name.split(" ")  # name parts
```

---

## 4. Flat, Sequential Structure — No Deep Nesting

Code flows top to bottom in each block. Logic is flat, not nested 3-4 levels deep.

```python
# ✅ Flat — easy to read
entry_orderid                    = tsl.order_placement(...)
orderbook[name]['entry_price']   = tsl.get_ltp_data(names=[ce_name])[ce_name]
orderbook[name]['options_name']  = ce_name
orderbook[name]['date']          = str(current_dt.date())
orderbook[name]['entry_time']    = str(current_dt.time())
orderbook[name]['sl_price']      = trigger_price
orderbook[name]['tg_price']      = round(orderbook[name]['entry_price'] * 1.3, 1)
orderbook[name]['traded']        = True

# ❌ Not this — unnecessary nesting
if entry_orderid is not None:
    price = tsl.get_ltp_data(names=[ce_name])[ce_name]
    if price is not None:
        orderbook[name]['entry_price'] = price
```

---

## 5. try/except for Order Placement Only

> 🚨 **`try/except` around `order_placement` DOES NOT catch a rejected order.**
> The library swallows the broker's reply and returns `None`:
> ```python
> except Exception as e:
>     print(f"'Got exception in place_order as {e}")   # <- reason goes to stdout
>     return None                                      # <- caller gets None
> ```
> Your `except` block never fires. `entry_orderid` is silently `None` and the
> real reason (`DH-906`, the exact rupee shortfall, ...) is printed and lost.
> **Always check `if not order_id:` — never rely on the exception.**
> To recover the reason, see §5b.

`try/except` wraps **order placement** blocks specifically — not the whole loop.
It catches *our* errors (bad symbol, lookup failure), not broker rejects.

```python
try:
    entry_orderid                    = tsl.order_placement(...)
    orderbook[name]['entry_price']   = tsl.get_ltp_data(names=[ce_name])[ce_name]
except Exception as e:
    print(f"Error placing entry order: {e}")
    continue

if not entry_orderid:                    # <- the branch that ACTUALLY fires
    print("Order rejected — see §5b to get the reason")
    continue

try:
    sl_orderid = tsl.order_placement(..., order_type='STOPLIMIT', ...)
except Exception as e:
    print(f"Error placing SL order: {e}")
    tsl.cancel_order(OrderID=entry_orderid)         # rollback entry
    orderbook[name] = {'traded': "TRADE_NOT_POSSIBLE", 'options_name': None}
    continue
```

---

## 5b. Exception Management — log what was SENT and what was RECEIVED

An **OMS reject never reaches the Dhan orderbook** — there is no row to look up
afterwards. Combined with §5 (the library prints the reason and returns `None`),
a rejected order leaves you with literally nothing to debug.

> 🚨 **Dhan frequently returns a failure with NO reason — every field `None`:**
> ```python
> {'status': 'failure',
>  'remarks': {'error_code': None, 'error_type': None, 'error_message': None},
>  'data': ''}
> ```
> There is nothing to parse. **Never build error handling that depends on
> `error_message` existing.** When Dhan says nothing, the ONLY evidence you have
> is what you sent and what came back — so log both, on every attempt, always.
> (This shape is usually rate limiting. See `error-log.md` ERROR-016.)

**Rule: capture stdout around the call. Log the exact request and the exact reply
on EVERY attempt — including when the reason is None.
Print details ONLY on error — a successful order needs one line, not a dump.**

```python
import contextlib, io, json, re
from datetime import datetime

def parse_broker_error(captured):
    """Pull the reason out of whatever the library printed.

    Dhan OFTEN returns no reason at all — every field None. Never assume a
    message exists; the request + raw reply is the real debug data.
    """
    if not captured:
        return "no output captured (check request params — see log)"

    msg  = re.search(r"'errorMessage':\s*'([^']+)'", captured)
    code = re.search(r"'errorCode':\s*'([^']+)'", captured)
    if msg:
        return f"{code.group(1)}: {msg.group(1)}" if code else msg.group(1)

    # Dhan gave a failure with EVERY field None:
    #   {'status':'failure','remarks':{'error_code':None,'error_type':None,
    #    'error_message':None},'data':''}
    # There is no reason to extract. This shape is almost always RATE LIMITING.
    if "'status': 'failure'" in captured or "'error_message': None" in captured:
        return ("Dhan returned failure with no reason (all fields None) — "
                "usually RATE LIMIT; see logged request/raw")

    return captured.replace("\n", " ").strip()[:180]   # unknown shape — keep raw


def place_and_log(tsl, request, log_path="order_log.jsonl"):
    """Place an order, returning (order_id, reason). Logs both sides."""

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):              # the ONLY way to see it
        order_id = tsl.order_placement(**request)
    captured = buf.getvalue().strip()

    record = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "request": request, "raw": captured}

    if order_id:
        record["ok"] = True
        record["order_id"] = str(order_id)
        print(f"FIRED {request['tradingsymbol']} id={order_id}")   # one line
    else:
        reason = parse_broker_error(captured) or "rejected (no reason given)"
        record["ok"]     = False
        record["reason"] = reason
        # replay snippet — an OMS reject has no orderbook row, so re-firing the
        # same params by hand is the ONLY way to reproduce it
        args = ",\n    ".join(f"{k}={v!r}" for k, v in request.items())
        record["replay"] = f"tsl.order_placement(\n    {args},\n)"

        print(f"REJECTED {request['tradingsymbol']}: {reason}")     # detail on error
        print(f"  sent: {request}")

    with open(log_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

    return (str(order_id) if order_id else None), record.get("reason")
```

**Why each piece:**

| Piece | Reason |
|-------|--------|
| `redirect_stdout` | the broker's reason exists ONLY as a `print` inside the library |
| log `request` verbatim | an OMS reject has no orderbook row — this is the only record |
| `replay` snippet | lets you re-fire the exact params by hand to retest |
| detail **only** on error | a working scan of 200 symbols must not dump 200 payloads |
| keep raw text on unknown shape | never invent a reason you did not parse |

**Real reasons this surfaces** (all seen in production):

```
DH-906: You have insufficient funds. Please add Rs.137370.62 to trade.
RMS:...:Intraday orders cannot be placed at this time.
RMS:...:You are trying to sell more than the quantity you currently hold.
EXCH:16283:The order price is not multiple of the tick size.
```

Without this you see `order rejected`. With it you see the rupee shortfall.

---

## 6. Orderbook Dict as State Machine

All trade state lives in `orderbook[name]`. Set every relevant key immediately after entry.

```python
# Set ALL keys at once — no drip-feeding
orderbook[name]['options_name']   = ce_name
orderbook[name]['date']           = str(current_dt.date())
orderbook[name]['entry_time']     = str(current_dt.time())
orderbook[name]['entry_datetime'] = current_dt
orderbook[name]['entry_orderid']  = entry_orderid
orderbook[name]['entry_price']    = entry_price
orderbook[name]['sl_orderid']     = sl_orderid
orderbook[name]['sl_price']       = trigger_price
orderbook[name]['tg_price']       = round(entry_price * 1.3, 1)
orderbook[name]['buy_sell']       = 'BUY_CE'
orderbook[name]['traded']         = True
orderbook[name]['breaked_even']   = False
```

**Reset on exit:**
```python
orderbook[name] = status.copy()   # clean reset to {traded: None, options_name: None}
```

---

## 7. Exit Conditions — Same bc/sc Pattern

Exit conditions follow identical naming style:
```python
sl_hit        = options_ltp < orderbook[name]['sl_price']
tg_hit        = options_ltp > orderbook[name]['tg_price']
time_exit     = datetime.datetime.now() > entry_datetime + timedelta(minutes=30)
trailing_exit = comp_candle['STX_15_3'] == 'down'   # for BUY_CE

if trailing_exit or sl_hit or time_exit or tg_hit:
    # exit logic
```

Remark set inline using conditional expression:
```python
remark = "trailing_exit" if trailing_exit else "sl_hit" if sl_hit else "tg_hit" if tg_hit else "time_exit"
orderbook[name]['remark'] = remark
```

---

## 8. Time Guards at Top of Loop

```python
current_time = datetime.datetime.now().time()

if current_time < ENTRY_TIME:
    print(f"{current_time} Waiting for the market to open")
    continue

market_over  = current_time > EXIT_TIME
panic_exit   = config_sheet.range('B8').value is not None
max_loss_hit = current_pnl < max_loss

if market_over or panic_exit or max_loss_hit:
    # save and break
```

---

## 9. Constants at Top — UPPERCASE

```python
EXIT_TIME  = datetime.time(15, 35, 59)
ENTRY_TIME = datetime.time(9, 35, 40)
re_entry   = True
max_orders = 5
```

---

## 10. Print Style

Use `f-string` with `current_time` prefix. No verbose logging framework.

```python
print(f"{current_time} Waiting for the market to open")
print(f"{name}  Uptrend")
print(f"{name}  Downtrend")
print(f"Error placing entry order: {e}")
print(f"Error placing SL order: {e}")
```

---

## 11. Log Saving Pattern

```python
path = f"Logs/{str(datetime.datetime.now().date())}"
os.makedirs(path, exist_ok=True)

tsl.get_orderbook().to_csv(f"{path}/dhan_orderbook.csv")
pd.DataFrame(orderbook).T.to_csv(f"{path}/logs.csv")
tsl.get_positions().to_csv(f"{path}/positionbook.csv")
```

---

## 12. Import Order

```python
from Dhan_Tradehull import Tradehull
from rich import print             # always use rich for coloured output
import talib
import pandas as pd
import datetime
import time
import xlwings as xw               # if Excel config used
import pretty_errors               # always include
import tradehull_backtesting as tb # if S/R or Supertrend needed
import os
import json                        # if JSON persistence needed
import pdb                         # always include for debugging
```

---

## Summary — When Cursor Generates Code

| Rule | Apply |
|------|-------|
| Vertical `=` alignment | Always in setup + inside loops |
| `bc1/bc2/sc1/sc2` named conditions | Always for entry/exit logic |
| Section divider comments `---` | For each logical block |
| Flat structure, no deep nesting | Always |
| `try/except` only on order calls | Never wrap entire loop |
| All orderbook keys set at once | After every entry |
| `status.copy()` to reset | After every exit |
| `f"{current_time} ..."` prints | For all loop logs |
| Logs saved to `Logs/YYYY-MM-DD/` | On every exit |
