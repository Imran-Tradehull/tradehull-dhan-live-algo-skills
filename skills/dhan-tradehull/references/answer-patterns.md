# Answer Patterns & Student Coding Patterns

Common patterns observed from TradeHull student support sessions.

> Note: Codebase has been upgraded multiple times.
> Some older errors were fixed by upgrades. Error types remain valid reference.

---

## How TradeHull Answers

### Response structure (always)
```
Hi @username ,
[1-2 line diagnosis]
[Code snippet or solution link]
[One follow-up question or ask for more info if needed]
```

### Style characteristics
- Direct, concise — no long preamble
- Always greets with `Hi @username`
- Code first, explanation second
- If unclear → asks for complete code + full error text
- If market is closed → defers to next trading day
- For complex issues → asks student to share full folder as zip

### When to ask for more info
```
"Do share your code and complete error as well"
"Send a detailed explanation of the rulesets"
"Do send complete zip of your folder and share it via Google Drive"
```

### When to defer
```
"I will require live market to check the code.
 So do expect the answer on Monday for the same."
```

### Upgrade-first response pattern
When a student is on old version:
```
"Do upgrade the codebase:
 pip install dhanhq==2.2.0
 pip install Dhan-Tradehull==3.3.1"
```

---

## Student Coding Patterns (Common Mistakes)

### 1. Using deprecated `get_intraday_data()`
**Most common mistake.**
```python
# ❌ Student writes this
chart = tsl.get_intraday_data(stock_name, 'NSE', 2)

# ✅ Correct
chart = tsl.get_historical_data(stock_name, 'NSE', '5')
```
**Root cause:** Old tutorial videos showed `get_intraday_data`. Students copy from old videos.

---

### 2. Wrong timeframe type (int instead of string)
```python
# ❌ Student writes this
data = tsl.get_historical_data('NIFTY', 'INDEX', 1)   # int
data = tsl.get_historical_data('ACC', 'NSE', 12)       # unsupported value

# ✅ Correct
data = tsl.get_historical_data('NIFTY', 'INDEX', '1')  # string
```

---

### 3. Not unpacking get_option_chain correctly
```python
# ❌ Student writes this — gets tuple, not DataFrame
option_chain = tsl.get_option_chain(Underlying="NIFTY", exchange="INDEX", expiry=0)

# ✅ Correct
atm_strike, option_chain = tsl.get_option_chain(Underlying="NIFTY", exchange="INDEX", expiry=0)
```

---

### 4. Using old import
```python
# ❌ Old — causes ModuleNotFoundError in v3.x
from Dhan_Tradehull_V2 import Tradehull

# ✅ Correct for v3.x
from Dhan_Tradehull import Tradehull
```

---

### 5. Expired contract in watchlist/code
```python
# ❌ Expired contracts cause "out of bounds" errors
watchlist = ['NIFTY 05 SEP 24400 CALL', ...]   # expired

# Also wrong symbol format
'NIFTY 02 JAN 22500 CE'    # ❌ wrong format
'NIFTY 02 JAN 22500 CALL'  # ✅ correct
```

---

### 6. Multiple sell orders (no position tracking)
**Common in loop-based algos:**
```python
# ❌ This sends a SELL order every loop iteration
while True:
    if signal:
        tsl.order_placement(..., 'SELL', ...)  # fires every 10 seconds

# ✅ Use orderbook to track state
if orderbook[name]['entry_orderid'] is None:
    orderid = tsl.order_placement(...)
    orderbook[name]['entry_orderid'] = orderid
```

---

### 7. Wrong client_code / token
```python
# ❌ Using Tradehull test account credentials
client_code = "YOUR_CLIENT_CODE"   # always use your own credentials

# ✅ Use your own Dhan credentials
client_code = "YOUR_CLIENT_CODE"
token_id    = "YOUR_FRESH_TOKEN"
```

---

### 8. Calling LTP too frequently without sleep
```python
# ❌ Hits rate limit (DH-904)
for name in watchlist:
    ltp = tsl.get_ltp_data([name])       # LTP call
    otm = tsl.OTM_Strike_Selection(...)  # another LTP call internally

# ✅ Add sleep between calls
for name in watchlist:
    otm = tsl.OTM_Strike_Selection(...)
    time.sleep(1)
    ltp = tsl.get_ltp_data([name])
    time.sleep(1)
```

---

### 9. Using STOPMARKET for options
```python
# ❌ STOPMARKET not supported for options
tsl.order_placement(..., order_type='STOPMARKET', ...)

# ✅ Use STOPLIMIT
tsl.order_placement(..., price=29, trigger_price=30, order_type='STOPLIMIT', ...)
```

---

### 10. Not converting timestamp for filtering
```python
# ❌ Won't filter correctly — timestamp is string in get_historical_data
today_data = data[data['timestamp'] == '2026-06-27']

# ✅ Convert first
data['ts'] = pd.to_datetime(data['timestamp'])
today_data = data[data['ts'].dt.date == pd.Timestamp.today().date()]
```

---

### 11. Using wrong exchange for index historical data
```python
# ❌
data = tsl.get_historical_data('NIFTY', 'NSE', '5')    # NSE not valid for index
data = tsl.get_historical_data('BANKNIFTY', 'NFO', '5') # NFO not valid for index

# ✅
data = tsl.get_historical_data('NIFTY', 'INDEX', '5')
data = tsl.get_historical_data('BANKNIFTY', 'INDEX', '5')
```

---

### 12. DAY timeframe on futures
```python
# ❌ Not supported
data = tsl.get_historical_data('NIFTY JAN FUT', 'NFO', 'DAY')

# ✅ Use intraday and resample
data = tsl.get_historical_data('NIFTY JAN FUT', 'NFO', '60')
```

---

## Frequently Asked Questions (FAQ)

**Q: Can I run two algos simultaneously on same Dhan account?**
A: Yes but you'll hit rate limits. Use two Dhan accounts with different APIs, or share data via Excel/JSON file between both algos.

**Q: Is the code tied to Python 3.8?**
A: No. v3.x supports Python 3.10+. Only old v2.x was tied to 3.8.

**Q: Can I add new stocks without restarting the code?**
A: Yes — if using `get_ltp_data` with a dynamic watchlist, no restart needed.

**Q: Can MCX options be traded via Tradehull?**
A: MCX commodity options (OPTFUT) are supported in v3.x via `ATM_Strike_Selection` and `order_placement` with `exchange='MCX'`.

**Q: How to get 2-min or 30-min candles?**
A: Dhan doesn't support 2/3/10/30-min natively. Fetch 1-min and use `tsl.resample_timeframe(df, '2T')`.

**Q: How to get weekly/monthly candles?**
A: Fetch `'DAY'` timeframe and resample with pandas `resample('W')` or `resample('M')`.

**Q: INDIA VIX historical data available?**
A: No. Only LTP is available: `tsl.get_ltp_data(["INDIA VIX"])`. Historical OHLC not provided by Dhan.

**Q: How to place order + SL + target together?**
A: Use `tsl.place_super_order()` — handles entry + target + SL in one API call with optional trailing.

**Q: For Telegram alerts, where do I get chat_id and bot_token?**
A: Follow guide: https://tradehull.com/telegram-integration-for-algo-trading/

**Q: How to get option greeks (delta, theta, etc.)?**
A: Use `get_option_chain()` — greeks are included in the DataFrame for every strike. No need for separate `get_option_greek()` call.

**Q: DAY timeframe gives how many candles?**
A: ~246 rows (~1 year of daily data).

**Q: Intraday timeframe gives how many days?**
A: Last 5 trading days of intraday data.

**Q: How to get more than 5 days of intraday?**
A: Use `tsl.get_long_term_historical_data()` with `from_date` and `to_date`.
