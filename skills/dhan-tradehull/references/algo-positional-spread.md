# Positional Spread Algo — Anatomy

Reference implementation: `examples/positional_spread_algo.py`

A live positional algo that sells options spreads (Bull Put Spread / Bear Call Spread)
based on Supertrend on 60-min chart. State persists across sessions via JSON.

**Key difference from intraday:** Trades last days to weeks, not hours.

---

## Strategy Type

| | Intraday Options Algo | Positional Spread Algo |
|--|----------------------|----------------------|
| Direction | Buy CE or PE | Sell PUT spread (bullish) or CALL spread (bearish) |
| Legs | 1 (long option) | 2 (short + hedge) |
| Timeframe | 5-min chart | 60-min chart |
| Expiry | Current week | **Next month** expiry |
| State persistence | In-memory (resets on restart) | **JSON file** (survives restart) |
| Entry order type | MARKET | **AMO LIMIT** (after market hours) |
| Strike selection | ATM | **Delta-based** (0.10–0.16 delta) |
| PnL basis | Options LTP | Spread PnL (sell - buy) |

---

## Architecture

```
SETUP
├── Hardcoded credentials (not Excel)
├── Initialize tsl
├── Load orderbook from JSON (persists across days/restarts)

MAIN LOOP
├── Time guard (before ENTRY_TIME)
├── Market over → save JSON → save logs → break
│
└── FOR each name in watchlist:
    ├── Fetch 60-min NIFTY chart → Supertrend
    ├── Use LAST candle (iloc[-1]) — positional, not tick-precise
    ├── IF bullish + not traded → Bull Put Spread entry (AMO)
    ├── IF bearish + not traded → Bear Call Spread entry
    └── IF in trade → check exit conditions
        ├── trailing_exit (Supertrend flip)
        ├── sl_hit (PnL < sl_pnl)
        ├── tg_hit (PnL > tg_pnl)
        └── only_few_days_left (< 30 days to expiry after 14:30)
```

---

## JSON Persistence — Cross-Session State

```python
# Load at startup
with open("positional_orderbook.json", "r") as f:
    loaded_data         = json.load(f)
    orderbook           = loaded_data['orderbook']
    complted_orderbook  = loaded_data['complted_orderbook']

# Save on exit (market_over)
with open("positional_orderbook.json", "w") as f:
    send_data = {'orderbook': orderbook, 'complted_orderbook': complted_orderbook}
    json.dump(send_data, f, indent=4)
```

**Why:** Positional trades span multiple days. Script restarts (server reboot, crash) must not lose trade state. JSON file bridges sessions.

---

## Expiry Selection — Next Month via get_expiry_list

```python
# Get index of next-month NFO expiry in the INDEX expiry list
expiry_no = tsl.get_expiry_list('NIFTY', 'INDEX').index(
            tsl.get_expiry_list('NIFTY', 'NFO')[1])   # [1] = next expiry

# Then fetch chain at that expiry
atm, oc = tsl.get_option_chain(
    Underlying="NIFTY", exchange="INDEX",
    expiry=expiry_no, num_strikes=50)   # wide chain — 50 strikes each side
```

**Pattern:** Cross-reference INDEX expiry list with NFO expiry list to get the correct `expiry` integer for `get_option_chain`.

---

## Delta-Based Strike Selection

```python
# Bull Put Spread — sell PE with delta 0.10-0.16, hedge with 0.07-0.09
oc['PE Delta']  = abs(oc['PE Delta'])   # PE delta is negative — abs first

selling_strike  = str(int(
    oc[oc['PE Delta'].between(0.10, 0.16)]
    .sort_values('PE OI')
    .iloc[-1]['Strike Price']            # highest OI in delta range
))
hedging_strike  = str(int(
    oc[oc['PE Delta'].between(0.07, 0.09)]
    .sort_values('PE OI')
    .iloc[-1]['Strike Price']
))

# Bear Call Spread — sell CE with delta 0.10-0.16
selling_strike  = str(int(
    oc[oc['CE Delta'].between(0.10, 0.16)]
    .sort_values('CE OI')
    .iloc[-1]['Strike Price']
))
```

**Why highest OI:** More liquid strike in the delta range — better fills.

---

## Build Symbol Name from ATM Parts

```python
ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=expiry_no)
nap = ce_name.split(" ")   # e.g. ['NIFTY', '28', 'JUN', '24000', 'CALL']

selling_name = f"{name} {nap[1]} {nap[2]} {selling_strike} PUT"
# e.g. 'NIFTY 28 JUN 23500 PUT'

hedging_name = f"{name} {nap[1]} {nap[2]} {hedging_strike} PUT"
# e.g. 'NIFTY 28 JUN 23300 PUT'
```

**Pattern:** Use ATM strike selection to extract expiry `DD MON` format, then substitute the delta-selected strike.

---

## AMO Entry (After Market Order)

```python
hedging_orderid = tsl.order_placement(
    tradingsymbol=hedging_name, exchange='NFO',
    quantity=lot_size,
    price=hedging_entry_price,   # LTP * 1.03 (slightly above for buy)
    trigger_price=0,
    order_type='LIMIT',
    transaction_type='BUY',
    trade_type='MARGIN',
    after_market_order=True,
    amo_time='OPEN'
)
```

**Why AMO:** Positional entry signals often fire after market hours. AMO queues the order for next market open.

---

## Spread Entry with Rollback

```python
# Hedge first (buy protection), then sell
hedging_orderid = tsl.order_placement(hedging_name, ..., 'BUY', ...)
hedging_status  = tsl.get_order_status(orderid=hedging_orderid)

if hedging_status == 'TRADED':
    selling_orderid = tsl.order_placement(selling_name, ..., 'SELL', ...)
    selling_status  = tsl.get_order_status(orderid=selling_orderid)

    if selling_status != 'TRADED':
        # Rollback — exit hedge if sell leg failed
        tsl.order_placement(hedging_name, ..., 'SELL', ...)   # exit hedge
else:
    continue   # hedge didn't fill — skip this symbol
```

**Rule:** Always enter hedge (buy) before sell leg. If sell fails → exit hedge immediately.

---

## Spread PnL Calculation

```python
# Both legs tracked separately
ltps        = tsl.get_ltp_data(names=[selling_name, hedging_name])
sold_ltp    = ltps[selling_name]
hedged_ltp  = ltps[hedging_name]

selling_pnl = (selling_price - sold_ltp) * qty   # sold higher, ltp fell = profit
hedging_pnl = (hedged_ltp - hedging_price) * qty  # bought lower, ltp rose = profit

total_pnl   = selling_pnl + hedging_pnl

# Max profit = premium collected at entry
max_profit  = (selling_price - hedging_price) * qty

# SL = lose 70% of max profit
sl_pnl      = round(max_profit * 0.7 * -1, 2)

# Target = make 70% of max profit
tg_pnl      = round(max_profit * 0.7 * 1, 2)
```

---

## Exit Conditions

```python
sl_hit             = pnl < sl_pnl
tg_hit             = pnl > tg_pnl
trailing_exit      = STX flipped (Supertrend reversal)
only_few_days_left = (days_to_expiry < 30) and (time > 14:30)
```

**`only_few_days_left`** — unique to positional: close before theta accelerates near expiry.

```python
only_few_days_left = (
    (pd.to_datetime(orderbook[name]['expiry']) - datetime.datetime.now()).days < 30
) and (datetime.datetime.now().time() > datetime.time(14, 30))
```

---

## Exit Execution

```python
if trailing_exit or sl_hit or tg_hit or only_few_days_left:
    # Buy back the short leg (close sell)
    selling_exit_orderid = tsl.order_placement(
        selling_name, 'NFO', qty, 0, 0, 'LIMIT', 'BUY', 'MARGIN')
    time.sleep(2)
    # Sell the hedge leg (close buy)
    hedging_exit_orderid = tsl.order_placement(
        hedging_name, 'NFO', qty, 0, 0, 'LIMIT', 'SELL', 'MARGIN')
```

**Note:** Close in reverse — buy back the short first, then sell the hedge.

---

## Orderbook Structure

```python
orderbook[name] = {
    'traded':               True,
    'view':                 'Bullish' or 'Bearish',
    'selling_name':         str,        # option symbol sold
    'hedging_name':         str,        # option symbol bought (hedge)
    'selling_orderid':      str,
    'hedging_orderid':      str,
    'qty':                  int,
    'selling_price':        float,      # executed price of sell leg
    'hedging_price':        float,      # executed price of hedge leg
    'max_profit':           float,      # (sell - hedge) * qty
    'sl_pnl':               float,      # max_profit * -0.7
    'tg_pnl':               float,      # max_profit * 0.7
    'pnl':                  float,      # live PnL
    'expiry':               str,        # expiry date string
    'date':                 str,        # entry datetime
    'exit_time':            str,
    'selling_exit_orderid': str,
    'hedging_exit_orderid': str,
    'selling_exit_price':   float,
    'hedging_exit_price':   float,
    'remark':               str,        # exit reason
}
```

---

## Key Design Decisions

1. **JSON persistence** — orderbook survives script restarts across days
2. **AMO orders** — signal fires after hours, order executes at next open
3. **Delta-based strike selection** — not ATM, but specific delta range (0.10-0.16)
4. **Highest OI in delta range** — most liquid strike for better fills
5. **Hedge before sell** — rollback if sell leg fails
6. **Next-month expiry** — uses `get_expiry_list` cross-reference pattern
7. **Symbol name built from ATM parts** — extract `DD MON` from ATM result
8. **`iloc[-1]` candle** — positional doesn't need completed-candle precision
9. **`only_few_days_left` exit** — time-based close before expiry theta burn
10. **`re_entry = False`** — positional positions not re-entered same day
11. **`get_executed_price()`** — used here (vs LTP in intraday) — positional can wait

---

## Known Bug in File (for awareness)

```python
# ❌ Bug: passing hedging_price (float) instead of hedging_name (str)
hedging_exit_orderid = tsl.order_placement(
    tradingsymbol=orderbook[name]['hedging_price'],  # should be 'hedging_name'
    ...
)
```

---

## Intraday vs Positional — Decision Guide

| If strategy is... | Use |
|-------------------|-----|
| Same-day entry + exit | `examples/intraday_options_algo.py` |
| Multi-day / swing / BTST | `examples/positional_spread_algo.py` |
| Buying options | Intraday pattern |
| Selling options (premium collection) | Positional pattern |
| ATM strike | Intraday pattern |
| Delta-selected strike | Positional pattern |
| State resets daily | Intraday (in-memory) |
| State persists across days | Positional (JSON file) |
