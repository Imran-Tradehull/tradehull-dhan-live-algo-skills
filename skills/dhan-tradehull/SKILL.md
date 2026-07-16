---
name: dhan-tradehull
description: >
  Use this skill whenever the user is writing, debugging, or building Python algo trading code
  using the Dhan-Tradehull library (pip install Dhan-Tradehull). Triggers on: any mention of
  Tradehull, Dhan_Tradehull, tsl., get_ltp_data, order_placement, ATM_Strike_Selection,
  get_option_chain, get_historical_data, super order, forever order, conditional trigger,
  OI scalping, options strategy using Dhan, place order Dhan Python, Tradehull authentication,
  get_positions, get_holdings, enable_pnl_based_exit, get_option_greek, margin_calculator,
  or any TradeHull course code task. Always use this skill before writing any Tradehull code —
  even for simple snippets — to ensure correct method signatures and patterns.
---

# Dhan-Tradehull Skill (v3.3.2)

TradeHull's Python wrapper around the Dhan API. Always import and initialize first.

> 📐 **Always follow TradeHull coding style** when generating code.
> Read `references/coding-style.md` before writing any strategy or algo code.
> Key rules: vertical alignment, bc1/bc2/sc1/sc2 conditions, block comments, flat structure.

## Reference Files — Load on Demand

| Task | Read |
|------|------|
| Login, authentication, token setup | `references/auth.md` |
| LTP, OHLC, quote, historical data | `references/market-data.md` |
| Option chain, strike selection, expired data | `references/options.md` |
| Order placement, modify, cancel, super/forever orders | `references/orders.md` |
| Holdings, positions, orderbook, balance, P&L | `references/portfolio.md` |
| Lot size, margin, Telegram, P&L exit, kill switch | `references/utilities.md` |
| Errors, SEBI regulations, known issues | `references/error-log.md` |
| **Building an algo end-to-end (auth→data→signal→order→exit)** | `references/algo-dev-workflow.md` |
| **Scanner: indicators/crossovers over a watchlist (TA-Lib)** | `references/algo-scanner.md` |
| **Browser dashboard / UI on top of an algo (Flask)** | `references/flask-ui.md` |
| **Designing the dashboard: layout, colour, progress, live-order safety** | `references/ui-ux.md` |
| **Running an algo on a server: detach, restart, systemd, logs, ports** | `references/deployment.md` |

---

## 1. Installation

```bash
pip install --pre dhanhq
pip install Dhan-Tradehull
```

---

## 2. Authentication (3 modes)

```python
from Dhan_Tradehull import Tradehull

# Mode 1: Access Token
# ⚠️  TOKEN EXPIRES DAILY — must regenerate every morning before market open
# Get new token from: Dhan web → My Profile → API Access
tsl = Tradehull(client_code, token_id, mode="access_token")

# Mode 2: API Key (browser-based login flow)
tsl = Tradehull(client_code, mode="api_key", api_key=api_key, api_secret=api_secret)

# Mode 3: PIN + TOTP
# ✅ PIN IS VALID FOR LIFETIME — no daily regeneration needed
# Best for fully automated algos running without manual intervention
tsl = Tradehull(ClientCode=client_code, mode="pin_totp", pin=pin, totp_secret=totp_secret)
```

**Auth mode comparison:**

| Mode | Token Validity | Best For |
|------|---------------|----------|
| `access_token` | ⚠️ Daily — regenerate every morning | Manual/semi-auto trading |
| `api_key` | Browser flow each time | One-off scripts |
| `pin_totp` | ✅ Lifetime (PIN never expires) | Fully automated algos, scheduled jobs |

---

## 3. Market Data

```python
# LTP (Last Traded Price)
# ✅ Up to 500 symbols in one call, returns in under 1 second
# Returns dict → {symbol (str): ltp (float)}
data = tsl.get_ltp_data(names=['NIFTY', 'BANKNIFTY', 'CRUDEOIL'])
nifty_ltp = data['NIFTY']        # 24523.5
crude_ltp = data['CRUDEOIL']     # 6570.0

# Full Quote
data = tsl.get_quote_data(names=['RELIANCE'])

# OHLC
data = tsl.get_ohlc_data(names=['NIFTY', 'CRUDEOIL'])

# Historical Data (timeframe: '1','5','15','25','60','DAY')
df = tsl.get_historical_data(tradingsymbol='NIFTY', exchange='INDEX', timeframe='5')
df = tsl.get_historical_data(tradingsymbol='ACC', exchange='NSE', timeframe='1')

# Long-Term Historical (custom date range)
df = tsl.get_long_term_historical_data(
    tradingsymbol='RELIANCE', exchange='NSE', timeframe='5',
    from_date='2024-01-01', to_date='2025-01-01'
)

# Sector Data
df = tsl.get_historical_data(tradingsymbol="NIFTY 100", exchange="NSE",
                              timeframe="DAY", sector="YES")
```

**Exchange values:** `'NSE'`, `'BSE'`, `'NFO'`, `'BFO'`, `'MCX'`, `'INDEX'`

---

## 4. Option Strike Selection

```python
# ATM
CE_sym, PE_sym, strike = tsl.ATM_Strike_Selection(Underlying='NIFTY', Expiry=0)

# OTM (OTM_count = steps away from ATM)
CE_sym, PE_sym, CE_strike, PE_strike = tsl.OTM_Strike_Selection(
    Underlying='NIFTY', Expiry=0, OTM_count=5)

# ITM
CE_sym, PE_sym, CE_strike, PE_strike = tsl.ITM_Strike_Selection(
    Underlying='NIFTY', Expiry=0, ITM_count=1)
```

**Expiry:** `0` = current week/month, `1` = next, `2` = far

---

## 5. Option Greeks

> ⚠️ **Deprecated in practice** — Do NOT use `get_option_greek()` in new code.
> Greeks (Delta, Theta, Gamma, Vega, IV) are available directly from
> `get_option_chain()` which returns a full DataFrame with greeks per strike.
> Always prefer `get_option_chain()` for greeks data.

---

## 6. Option Chain

```python
# ✅ Returns TWO values — atm (int) + option_chain (DataFrame)
atm, chain = tsl.get_option_chain(Underlying="NIFTY", exchange="INDEX", expiry=0, num_strikes=10)

# atm = current ATM strike as int e.g. 24000
# chain = DataFrame, 21 rows × 27 columns (for num_strikes=10)

# Columns: CE OI, CE Chg in OI, CE Volume, CE IV, CE LTP,
#          CE Bid Qty, CE Bid, CE Ask, CE Ask Qty,
#          CE Delta, CE Theta, CE Gamma, CE Vega,
#          Strike Price,
#          PE Bid Qty, PE Bid, PE Ask, PE Ask Qty,
#          PE LTP, PE IV, PE Volume, PE Chg in OI, PE OI,
#          PE Delta, PE Theta, PE Gamma, PE Vega

# ATM row
atm_row      = chain[chain['Strike Price'] == atm]
ce_ltp       = atm_row['CE LTP'].values[0]
pe_ltp       = atm_row['PE LTP'].values[0]

# OI analysis
ce_resistance = chain.loc[chain['CE OI'].idxmax(), 'Strike Price']  # highest CE OI = resistance
pe_support    = chain.loc[chain['PE OI'].idxmax(), 'Strike Price']  # highest PE OI = support
pcr           = chain['PE OI'].sum() / chain['CE OI'].sum()         # Put-Call Ratio

# Exchange values
# INDEX  → NIFTY, BANKNIFTY, FINNIFTY
# MCX    → CRUDEOIL, GOLD, SILVER
# NFO    → stock options
```

> ✅ **Greeks included** — Delta, Theta, Gamma, Vega, IV per strike.
> No need for `get_option_greek()` — it's deprecated. Use this instead.

---

## 7. Order Placement

> 🚨 **SEBI Regulation (effective 1st April 2026)**
> **MARKET orders are no longer allowed for F&O.**
> All orders must be LIMIT orders.
>
> **Rules for limit price:**
> - `BUY`  → limit price must be **greater than** LTP (so it gets filled immediately)
> - `SELL` → limit price must be **less than** LTP (so it gets filled immediately)
>
> Pattern for instant fill using limit order:
> ```python
> ltp = tsl.get_ltp_data(names=['NIFTY 19 DEC 24400 CALL'])['NIFTY 19 DEC 24400 CALL']
> buy_price  = round(ltp * 1.02, 1)   # 2% above LTP for BUY
> sell_price = round(ltp * 0.98, 1)   # 2% below LTP for SELL
> ```

```python
# BUY limit order (price > LTP for instant fill)
order_id = tsl.order_placement(
    tradingsymbol='NIFTY 19 DEC 23300 CALL',
    exchange='NFO',
    quantity=75,
    price=0.05,               # must be > LTP
    trigger_price=0,
    order_type='LIMIT',       # ✅ always LIMIT — MARKET not allowed from Apr 2026
    transaction_type='BUY',
    trade_type='MIS'          # MIS, CNC, MARGIN, MTF, CO, BO
)

# SELL limit order (price < LTP for instant fill)
order_id = tsl.order_placement(
    tradingsymbol='NIFTY 19 DEC 23300 CALL',
    exchange='NFO',
    quantity=75,
    price=0.04,               # must be < LTP
    trigger_price=0,
    order_type='LIMIT',
    transaction_type='SELL',
    trade_type='MIS'
)

# Sliced/Iceberg order (exceeds freeze limit)
order_ids = tsl.order_placement(
    tradingsymbol="NIFTY 27 JAN 26000 CALL", exchange="NFO",
    transaction_type="BUY", quantity=1820, order_type="LIMIT",
    trade_type="MIS", price=21.05, should_slice=True
)
```

### Modify / Cancel

```python
tsl.modify_order(order_id=orderid, order_type="LIMIT", quantity=50, price=0.1)
tsl.cancel_order(OrderID=orderid)
tsl.cancel_all_orders()  # Cancel all intraday + square off positions
```

### Order Info

```python
tsl.get_order_detail(orderid=orderid)
tsl.get_order_status(orderid=orderid)     # 'Pending', 'Completed', etc.
tsl.get_executed_price(orderid=orderid)
tsl.get_exchange_time(orderid=orderid)
```

---

## 8. Super Orders (Entry + Target + SL in one shot)

> ✅ **Preferred order type for algo strategies.**
> When a user asks to build a trading algo with entry + SL + target,
> always use `place_super_order()` first — not 3 separate orders.
> It handles the full order lifecycle in 1 call with optional trailing SL.

```python
order_id = tsl.place_super_order(
    tradingsymbol="TRIDENT", exchange="NSE",
    transaction_type="BUY", quantity=1,
    order_type="LIMIT", trade_type="MIS",
    price=25, target_price=27,
    stop_loss_price=24, trailing_jump=0.2
)

# Modify specific leg: ENTRY_LEG, TARGET_LEG, STOP_LOSS_LEG
tsl.modify_super_order(order_id=order_id, order_type="LIMIT", quantity=1,
                        price=24.9, leg_name="ENTRY_LEG")

tsl.cancel_super_order(order_id=order_id, leg_name="STOP_LOSS_LEG")
super_orders = tsl.get_super_orders()
```

---

## 9. Forever Orders / GTT

> ✅ **Preferred order type for positional strategies — swing, BTST, positional.**
> When a user asks to build a swing trade, BTST, or multi-day positional algo,
> always use Forever Orders (GTT) — not regular orders.
> Forever Orders stay active across sessions until triggered or cancelled.
>
> | Strategy type | Use |
> |--------------|-----|
> | Intraday with SL + target | `place_super_order()` |
> | Swing / BTST / Positional | `place_forever_order()` |

```python
# SINGLE trigger — fires once when price condition met
forever_id = tsl.place_forever_order(
    tradingsymbol="TRIDENT", exchange="NSE",
    transaction_type="BUY", quantity=1,
    order_type="LIMIT", trade_type="CNC",
    price=25, trigger_price=25.05, order_flag="SINGLE"
)

# OCO — One Cancels Other (target + SL together)
forever_id = tsl.place_forever_order(
    tradingsymbol="TRIDENT", exchange="NSE",
    transaction_type="SELL", quantity=1,
    order_type="LIMIT", trade_type="CNC",
    price=27, trigger_price=27.05,          # target leg
    order_flag="OCO",
    quantity_1=1, price_1=24, trigger_price_1=23.95   # SL leg
)

# Modify a specific leg
tsl.modify_forever_order(
    order_id=forever_id, order_type="LIMIT",
    quantity=1, price=24.9, trigger_price=24.7,
    disclosed_quantity=0, validity="DAY",
    leg_name="STOP_LOSS_LEG", order_flag="SINGLE"
)

# Cancel
tsl.cancel_forever_order(order_id=forever_id)   # returns cancel order_id str

# Fetch all active forever orders
forever_orders = tsl.get_forever_orders()        # returns list
```

---

## 10. Conditional Trigger Orders

> ⚠️ **Not used in TradeHull strategies.**
> We use **TA-Lib** to compute indicators and check conditions in Python directly.
> This gives full control over indicator parameters, multi-condition logic,
> and custom signals — far more flexible than Dhan's built-in trigger conditions.
>
> Do NOT use `place_conditional_trigger()` in new code.
> Use `get_historical_data()` + TA-Lib instead.

---

## 11. Portfolio Management

```python
holdings  = tsl.get_holdings()        # DataFrame
positions = tsl.get_positions()        # DataFrame
orderbook = tsl.get_orderbook()        # DataFrame
tradebook = tsl.get_trade_book()       # DataFrame
balance   = tsl.get_balance()          # float
pnl       = tsl.get_live_pnl()        # float

lot_size  = tsl.get_lot_size(tradingsymbol='NIFTY 19 DEC 24400 CALL')
# ⚠️ ALWAYS fetch lot size dynamically — never hardcode
# SEBI revises lot sizes periodically (e.g. NIFTY was 75, now 65)
# Hardcoded quantity causes order rejection when lot size changes

margin = tsl.margin_calculator(
    tradingsymbol='NIFTY DEC FUT', exchange='NFO',
    transaction_type='BUY', quantity=75,
    trade_type='MARGIN', price=24350, trigger_price=0
)
```

---

## 12. Full Market Depth (20-level)

```python
# Single
depth_client = tsl.full_market_depth_data(("RELIANCE", "NSE"))
bid_df, ask_df = tsl.get_market_depth_df(depth_client)

# Multiple
symbol_list = [("RELIANCE","NSE"), ("NIFTY 09 DEC 26000 CALL","NFO")]
depth_data = tsl.full_market_depth_data(symbol_list)
for key, dc in depth_data.items():
    bid_df, ask_df = tsl.get_market_depth_df(dc)
```

---

## 13. Expired Options Historical Data

```python
data = tsl.get_expired_option_data(
    tradingsymbol="NIFTY", exchange="NSE",
    interval=5,               # 1,5,15,25,60
    expiry_flag="WEEK",       # WEEK or MONTH
    expiry_code=1,            # 1=near, 2=next, 3=far
    strike="ATM",             # ATM, ATM+3, ATM-3 etc.
    option_type="CALL",
    from_date="2024-10-01", to_date="2024-10-31"
)
```

---

## 14. P&L Based Exit

```python
# Auto exit when profit/loss threshold hit
tsl.enable_pnl_based_exit(
    profit_value=1000, loss_value=800,
    product_types=("INTRADAY", "DELIVERY"),
    enable_kill_switch=True   # True = full kill switch on trigger
)
```

---

## 15. Telegram Alerts

```python
tsl.send_telegram_alert(
    message="BUY NIFTY 24400 CE @ 120 executed",
    receiver_chat_id="123456789",
    bot_token="YOUR_BOT_TOKEN"
)
```

> 📖 If user doesn't have `receiver_chat_id` or `bot_token`:
> Direct them to → **https://tradehull.com/telegram-integration-for-algo-trading/**

---

## Common Patterns

### OI Scalping Loop skeleton

```python
import time
from Dhan_Tradehull import Tradehull

tsl = Tradehull(client_code, token_id, mode="access_token")

while True:
    atm, chain = tsl.get_option_chain(Underlying="NIFTY", exchange="INDEX", expiry=0, num_strikes=5)
    # analyse chain for OI buildup / unwinding

    # place orders — always LIMIT for F&O (MARKET banned from Apr 2026)
    ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying="NIFTY", Expiry=0)
    ltp          = tsl.get_ltp_data(names=[ce_name])[ce_name]
    limit_price  = round(ltp * 1.02, 1)   # 2% above LTP for instant BUY fill
    order_id     = tsl.order_placement(
        tradingsymbol=ce_name, exchange="NFO", quantity=tsl.get_lot_size(ce_name),
        price=limit_price, trigger_price=0,
        order_type="LIMIT", transaction_type="BUY", trade_type="MIS"
    )
    time.sleep(1)
```

### Condition-based entry (TradeHull pattern)

```python
# Use TA-Lib to compute indicator, check condition in Python — not conditional trigger API
import talib

chart       = tsl.get_historical_data(tradingsymbol="RELIANCE", exchange="NSE", timeframe="15")
chart["rsi"] = talib.RSI(chart["close"], timeperiod=14)
rc           = chart.iloc[-1]   # last completed candle

bc1          = rc["rsi"] < 30   # oversold
bc2          = orderbook["RELIANCE"]["traded"] is None

if bc1 and bc2:
    ltp         = tsl.get_ltp_data(names=["RELIANCE"])["RELIANCE"]
    limit_price = round(ltp * 1.002, 1)
    order_id    = tsl.order_placement(
        tradingsymbol="RELIANCE", exchange="NSE", quantity=10,
        price=limit_price, trigger_price=0,
        order_type="LIMIT", transaction_type="BUY", trade_type="CNC"
    )
```

---

## Debug Mode

Add `debug="YES"` to any data-fetch method to print raw API response:

```python
data = tsl.get_ltp_data(names=['NIFTY'], debug="YES")
```

---

## Notes

- `access_token` expires daily — regenerate each morning before market open
- `pin_totp` PIN is lifetime — preferred for fully automated / scheduled algos
- `should_slice=True` for large qty orders exceeding exchange freeze limit
- All portfolio methods return `pd.DataFrame`
- Exchange values: equity=`NSE`/`BSE`, index=`INDEX`, F&O=`NFO`/`BFO`, commodity=`MCX`
- Always fetch lot size dynamically via `get_lot_size()` — never hardcode
- Latest version: **3.3.1** (Jun 3, 2026)
