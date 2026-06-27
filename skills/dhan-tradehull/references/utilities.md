# Utilities — Output Signatures

## `tsl.get_lot_size(tradingsymbol)` → `int`

```python
lot_size = tsl.get_lot_size(tradingsymbol='NIFTY 30 JUN 24000 CALL')
# 65
```

**⚠️ ALWAYS fetch dynamically — NEVER hardcode lot size.**
SEBI revises lot sizes periodically (NIFTY was 75, revised to 65).
Hardcoded quantity causes order rejection when lot size changes.

```python
CE_sym, PE_sym, strike = tsl.ATM_Strike_Selection(Underlying='NIFTY', Expiry=0)
lot_size = tsl.get_lot_size(tradingsymbol=CE_sym)
order_id = tsl.order_placement(CE_sym, 'NFO', lot_size, ...)   # ✅ always dynamic
```

**Common lot sizes (subject to revision):**
| Instrument | Lot Size |
|-----------|---------|
| NIFTY | 65 (revised from 75) |
| BANKNIFTY | 30 |
| FINNIFTY | 40 |
| SENSEX | 10 |
| MIDCPNIFTY | 120 |

---

## `tsl.margin_calculator(...)`

> 📝 Real output pending — will update with live data.

```python
margin = tsl.margin_calculator(
    tradingsymbol='NIFTY DEC FUT', exchange='NFO',
    transaction_type='BUY', quantity=75,
    trade_type='MARGIN', price=24350, trigger_price=0
)
```

---

## `tsl.enable_pnl_based_exit(...)`

**Return:** `dict` — API response

```python
# Without kill switch — exits positions, can resume trading
tsl.enable_pnl_based_exit(profit_value=1000, loss_value=1200, product_types=("INTRADAY"))

# With kill switch — exits + LOCKED OUT for entire day
tsl.enable_pnl_based_exit(profit_value=1000, loss_value=800,
                           product_types=("INTRADAY","DELIVERY"),
                           enable_kill_switch=True)
```

**🚨 Kill switch is a Dhan platform-level lock:**

| `enable_kill_switch` | On trigger | Trade again today? |
|---------------------|-----------|-------------------|
| `False` (default) | Exit positions | ✅ Yes |
| `True` | Exit + lock | ❌ **Full day lockout — no override via API** |

- Config resets automatically at EOD
- At least one of `profit_value` or `loss_value` required
- May trigger immediately if thresholds already breached

---

## `tsl.send_telegram_alert(...)`

**Return:** `None` — prints success/failure to console

```python
tsl.send_telegram_alert(
    message="✅ BUY NIFTY 24000 CE @ 120 executed",
    receiver_chat_id="123456789",
    bot_token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
)
```

**If user doesn't have `receiver_chat_id` or `bot_token`:**
→ Direct to: **https://tradehull.com/telegram-integration-for-algo-trading/**

```python
# Common alert patterns
tsl.send_telegram_alert(f"✅ Entry filled @ {price}", CHAT_ID, BOT_TOKEN)
tsl.send_telegram_alert(f"🛑 SL Hit | Loss: ₹{abs(pnl)}", CHAT_ID, BOT_TOKEN)
tsl.send_telegram_alert(f"🎯 Target Hit | Profit: ₹{pnl}", CHAT_ID, BOT_TOKEN)
tsl.send_telegram_alert(f"📊 Day closed | P&L: ₹{pnl}", CHAT_ID, BOT_TOKEN)
```

---

## Hidden / Undocumented Methods (from source)

### `tsl.resample_timeframe(df, timeframe='5T')`
Resamples a DataFrame (from `get_historical_data`) to a higher timeframe.
```python
df_1min = tsl.get_historical_data('NIFTY', 'INDEX', '1')
df_5min = tsl.resample_timeframe(df_1min, timeframe='5T')
# Returns OHLCV DataFrame resampled from 09:15 origin
```
- `timeframe` uses pandas offset strings: `'5T'`=5min, `'15T'`=15min, `'1H'`=1hr
- Respects market hours (09:15–15:30) per day

---

### `tsl.heikin_ashi(df)`
Converts standard OHLC DataFrame to Heikin Ashi candles.
```python
df = tsl.get_historical_data('NIFTY', 'INDEX', '5')
ha_df = tsl.heikin_ashi(df)
# Returns DataFrame with: timestamp, open, high, low, close (HA values)
```

---

### `tsl.renko_bricks(data, box_size=7)`
Converts OHLC DataFrame to Renko bricks.
```python
df = tsl.get_historical_data('RELIANCE', 'NSE', '5')
renko_df = tsl.renko_bricks(df, box_size=10)
# Returns DataFrame with: timestamp, open, high, low, close, brick_color ('green'/'red')
```

---

### `tsl.get_executed_price_and_time(orderid)` → `tuple(float, str)`
Single call to get both executed price and exchange time.
```python
price, exec_time = tsl.get_executed_price_and_time(orderid='2452606277130')
# price     = 112.55  (float)
# exec_time = '2026-06-27 10:35:42'  (str)
```
More efficient than calling `get_executed_price()` + `get_exchange_time()` separately.

---

### `tsl.order_report()` → `tuple(dict, dict, dict)`
Bulk fetch of all order statuses, prices and times in one call.
```python
order_statuses, order_prices, order_times = tsl.order_report()
# order_statuses = {'2452606277130': 'TRADED', ...}  — orderId → status
# order_prices   = {'2452606277130': 112.55, ...}    — orderId → avg price
# order_times    = {'2452606277130': '10:35:42', ...} — orderId → exchange time
```
Use this instead of looping `get_order_status()` for multiple orders.

---

### `tsl.kill_switch(action)` → `str`
Standalone kill switch — separate from `enable_pnl_based_exit`.
```python
tsl.kill_switch('ON')    # Activate — blocks all new orders
tsl.kill_switch('OFF')   # Deactivate — re-enables trading
```
- `action`: `'ON'` or `'OFF'`
- Returns: kill switch status string

---

### `tsl.get_future_script(underlying, expiry)` → `str`
Get the futures contract symbol name.
```python
fut_symbol = tsl.get_future_script(underlying='NIFTY', expiry=0)
# 'NIFTY JUL FUT'   (ready to use in order_placement)
```
- `expiry`: `0`=near, `1`=next, `2`=far

---

### `tsl.get_expiry_list(Underlying, exchange)` → `list`
Get list of available expiry dates for an instrument.
```python
expiry_dates = tsl.get_expiry_list(Underlying='NIFTY', exchange='INDEX')
# ['2026-06-30', '2026-07-07', '2026-07-14', ...]
```

---

### `tsl.get_expiry_date(Underlying, opt_fut)` → `list`
Get sorted expiry dates for options or futures.
```python
dates = tsl.get_expiry_date(Underlying='NIFTY', opt_fut='OPTION')
dates = tsl.get_expiry_date(Underlying='RELIANCE', opt_fut='FUTURE')
# ['2026-06-30', '2026-07-31', ...]
```

---

## Instrument Step Sizes (from source)

Step sizes used internally for strike selection. Hardcoded in v3.3.1:

**Indices:**
```python
index_step_dict = {
    'NIFTY': 50, 'BANKNIFTY': 100, 'FINNIFTY': 50,
    'MIDCPNIFTY': 25, 'SENSEX': 100, 'BANKEX': 100
}
```

**Commodities:**
```python
commodity_step_dict = {
    'GOLD': 100, 'SILVER': 250, 'CRUDEOIL': 50,
    'NATURALGAS': 5, 'COPPER': 5, 'NICKEL': 10,
    'ZINC': 2.5, 'LEAD': 1, 'ALUMINIUM': 1,
    'COTTON': 100, 'MENTHAOIL': 10, ...
}
```

**Equity F&O:** Step sizes auto-computed from instrument file at login via `dhan_equity_step_creation()`

---

## Dependencies Folder (auto-created at login)

The library auto-creates a `Dependencies/` folder in your working directory:
```
Dependencies/
├── log_files/
│   └── logs2026-06-28.log     ← daily log file
├── token_<clientcode>_2026-06-28.txt  ← cached access token (today)
└── all_instrument 2026-06-28.csv      ← instrument master file (today)
```

- Token is cached so re-running script same day reuses token without re-login
- Instrument file is cached daily — re-downloaded only if date changes
- Old token/instrument files are auto-deleted when new ones are created
