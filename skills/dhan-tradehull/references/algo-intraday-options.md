# Intraday Options Algo — Anatomy

Reference implementation: `examples/intraday_options_algo.py`

A live intraday algo that buys ATM CE/PE based on Supertrend + Support/Resistance.
This is a **real production algo** — use as template for similar strategies.

---

## Architecture

```
SETUP
├── Read config from Excel (Algo1.xlsx)
├── Initialize tsl
├── Build watchlist from Excel
├── Pre-calculate S/R levels for all stocks (daily data)

MAIN LOOP (while True)
├── Time guards (before ENTRY_TIME → wait)
├── Exit guards (market_over / panic_exit / max_loss_hit)
│   └── cancel_all_orders → save logs → break
│
└── FOR each name in watchlist:
    ├── Fetch 5-min chart → compute RSI + Supertrend
    ├── Get completed candle (floor to 5-min)
    ├── Evaluate BUY conditions (bc1..bc5)
    ├── Evaluate SELL conditions (sc1..sc5)
    ├── ENTRY → place order + SL order
    └── POSITION MANAGEMENT
        ├── Check SL hit / TG hit / time exit / trailing exit
        ├── Trailing SL logic (breakeven at ₹2000 PnL, then trail every ₹500)
        └── Exit → update orderbook → re-entry if enabled
```

---

## Config (from Excel — Algo1.xlsx)

```python
client_code   = config_sheet.range('B1').value   # Dhan client code
access_token  = config_sheet.range('B2').value   # access token
max_loss_pct  = config_sheet.range('B9').value   # e.g. 0.05 = 5%
max_orders    = config_sheet.range('B10').value  # max concurrent trades
panic_exit    = config_sheet.range('B8').value   # any value = exit now
watchlist     = config_sheet.range('D2:D1000')   # stock names
```

---

## Orderbook Structure

Every stock in watchlist gets an entry:
```python
orderbook = {
    name: {
        'traded':            None,        # None / True / "TRADE_NOT_POSSIBLE"
        'options_name':      None,        # e.g. 'RELIANCE 27 JUN 1400 CALL'
        'qty':               None,        # lot_size * 6
        'buy_sell':          None,        # 'BUY_CE' or 'BUY_PE'
        'date':              None,        # str date
        'entry_time':        None,        # str time
        'entry_datetime':    None,        # datetime object
        'entry_orderid':     None,        # str
        'entry_price':       None,        # float (via LTP, not executed price)
        'sl_orderid':        None,        # str
        'sl_price':          None,        # float trigger price
        'tg_price':          None,        # entry * 1.3
        'exit_orderid':      None,        # str
        'exit_price':        None,        # float
        'exit_time':         None,        # str
        'pnl':               None,        # float
        'remark':            None,        # 'sl_hit'/'tg_hit'/'time_exit'/'trailing_exit'
        'breaked_even':      False,       # bool
        'next_trailing_pnl': None,        # float threshold for next trail step
    }
}
```

---

## Entry Conditions

```python
# BUY CE (bullish)
bc1 = True                                 # RSI > 60 (commented out)
bc2 = comp_candle['STX_15_3'] == 'up'     # Supertrend bullish
bc3 = orderbook[name]['traded'] is None   # not already in trade
bc4 = comp_candle['close'] > sr['r1']     # price above resistance
bc5 = total_active_trades < max_orders    # within order limit

# BUY PE (bearish)
sc1 = True                                 # RSI < 40 (commented out)
sc2 = comp_candle['STX_15_3'] == 'down'
sc3 = orderbook[name]['traded'] is None
sc4 = comp_candle['close'] < sr['s1']     # price below support
sc5 = total_active_trades < max_orders
```

---

## Completed Candle — Key Pattern

```python
# Get the LAST COMPLETED 5-min candle (not the forming one)
comp_candle = pd.Series(datetime.datetime.now()).dt.floor('5min')[0] \
              - datetime.timedelta(minutes=5)
comp_candle = comp_candle.strftime("%Y-%m-%d %H:%M:%S+05:30")
comp_candle = chart.loc[comp_candle]
```

**Why:** Avoids trading on incomplete candle signals. Always use the candle that has fully closed.

---

## Entry Flow

```python
# 1. Get ATM strike
ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=0)
lot_size = tsl.get_lot_size(ce_name)

# 2. Place entry order
entry_orderid = tsl.order_placement(
    tradingsymbol=ce_name, exchange='NFO',
    quantity=lot_size, price=0, trigger_price=0,
    order_type='MARKET', transaction_type='BUY', trade_type='MIS')

# 3. Get entry price via LTP (not executed price — faster)
entry_price = tsl.get_ltp_data(names=[ce_name])[ce_name]

# 4. Place SL order immediately (30% below entry)
trigger_price = round(entry_price * 0.7, 1)
price         = max(trigger_price - 0.5, 0.1)
sl_orderid    = tsl.order_placement(
    tradingsymbol=ce_name, exchange='NFO',
    quantity=lot_size, price=price, trigger_price=trigger_price,
    order_type='STOPLIMIT', transaction_type='SELL', trade_type='MIS')
```

**Note:** Entry price uses `get_ltp_data()` instead of `get_executed_price()` — faster, avoids waiting for fill confirmation.

---

## SL Price Formula

```python
trigger_price = round(entry_price * 0.7, 1)   # 30% below entry
price         = max(trigger_price - 0.5, 0.1) # price = trigger - 0.5 (STOPLIMIT needs price < trigger)
```

---

## Exit Conditions

```python
options_ltp   = tsl.get_ltp_data(names=[options_name])[options_name]
time_exit     = datetime.datetime.now() > entry_datetime + timedelta(minutes=30)
sl_hit        = options_ltp < sl_price
tg_hit        = options_ltp > tg_price           # entry * 1.3
trailing_exit = comp_candle['STX_15_3'] == 'down'  # for BUY_CE
trailing_exit = comp_candle['STX_15_3'] == 'up'    # for BUY_PE
```

**Exit priority:**
- `trailing_exit` or `sl_hit` → use existing SL order as exit
- `time_exit` or `tg_hit` → cancel SL order → place fresh MARKET exit

---

## Trailing SL Logic

```python
# Phase 1: Breakeven at ₹2000 PnL
if not breaked_even and pnl > 2000:
    new_trigger = entry_price                    # move SL to breakeven
    tsl.modify_order(sl_orderid, 'STOPLIMIT', qty, price, trigger)
    breaked_even      = True
    next_trailing_pnl = 2500                     # next trail at 2000+500

# Phase 2: Trail every ₹500 after breakeven
if breaked_even and pnl > next_trailing_pnl:
    new_trigger = entry_price + (500 / qty)      # lock in ₹500 more
    tsl.modify_order(sl_orderid, ...)
    next_trailing_pnl += 500

# Fallback if modify fails → cancel + replace SL
try:
    tsl.modify_order(...)
except:
    tsl.cancel_order(sl_orderid)
    sl_orderid = tsl.order_placement(..., order_type='STOPLIMIT', ...)
```

---

## Exit Guards (top of loop)

```python
market_over  = current_time > EXIT_TIME          # 15:35:59
panic_exit   = config_sheet.range('B8').value is not None  # any value in cell
max_loss_hit = current_pnl < max_loss            # pnl < opening_balance * max_loss_pct * -1

if market_over or panic_exit or max_loss_hit:
    tsl.cancel_all_orders()
    # save logs to CSV
    break
```

---

## Re-entry Pattern

```python
re_entry = True   # config flag

if trailing_exit or sl_hit or time_exit or tg_hit:
    if re_entry:
        complted_orderbook.append(orderbook[name])
        orderbook[name] = status.copy()   # reset to None → allows re-entry same day
```

---

## Log Saving Pattern

```python
path = f"Logs/{str(datetime.datetime.now().date())}"
os.makedirs(path, exist_ok=True)
tsl.get_orderbook().to_csv(f"{path}/dhan_orderbook.csv")
pd.DataFrame(orderbook).T.to_csv(f"{path}/logs.csv")
tsl.get_positions().to_csv(f"{path}/positionbook.csv")
```

---

## Dependencies Used

| Library | Purpose |
|---------|---------|
| `Dhan_Tradehull` | All broker API calls |
| `talib` | RSI calculation |
| `tradehull_backtesting` | Supertrend + S/R levels (TradeHull internal) |
| `xlwings` | Excel config + live orderbook display |
| `rich` | Coloured terminal print |
| `pretty_errors` | Cleaner error display |
| `pandas`, `datetime`, `time`, `os` | Standard |

---

## Key Design Decisions (learn from these)

1. **LTP over executed price for entry** — faster, no API wait
2. **STOPLIMIT not STOPMARKET** — required for options (STOPMARKET rejected)
3. **SL placed immediately after entry** — within same try/except block
4. **Entry rollback on SL failure** — cancel entry if SL order fails
5. **Completed candle via floor+shift** — not `iloc[-1]` (avoids incomplete candle)
6. **Orderbook dict tracks full state** — single source of truth per symbol
7. **Panic exit via Excel cell** — operator can trigger emergency exit without touching code
8. **Logs saved on every exit** — full audit trail per day
9. **Re-entry by resetting orderbook** — `status.copy()` resets to `None`
