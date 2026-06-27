# Common Patterns & Student FAQ

Common patterns from TradeHull student support sessions.

---

## ⚠️ Deprecated Method — `get_intraday_data()`

**Most common mistake.** Old method that only fetches today's data.

```python
# ❌ OLD — deprecated, gives only today's data
chart = tsl.get_intraday_data('ACC', 'NSE', 5)

# ✅ NEW — use this always
chart = tsl.get_historical_data('ACC', 'NSE', '5')
```

**Timeframe must be a string, not int:**
- `'1'`, `'5'`, `'15'`, `'25'`, `'60'`, `'DAY'` ✅
- `1`, `5`, `12`, `2` ❌ — unsupported

---

## ATM Strike → LTP pattern

```python
CE_symbol_name, PE_symbol_name, atm_strike = tsl.ATM_Strike_Selection(Underlying='NIFTY', Expiry=0)
ltp_data = tsl.get_ltp_data([CE_symbol_name, PE_symbol_name])
ce_ltp   = ltp_data[CE_symbol_name]
pe_ltp   = ltp_data[PE_symbol_name]
```

---

## OTM Strike with LTP — add sleep to avoid rate limits

```python
# LTP API = 1 request/second rate limit
# OTM_Strike_Selection internally calls LTP once
# Then get_ltp_data calls LTP again
# = 2 LTP calls → need sleep between them

for name in watchlist:
    otm_ce, otm_pe, ce_strike, pe_strike = tsl.OTM_Strike_Selection(
        Underlying='NIFTY', Expiry=0, OTM_count=5)
    time.sleep(1)   # ← required after OTM_Strike_Selection

    ltp = tsl.get_ltp_data([otm_ce, otm_pe])
    time.sleep(1)   # ← required after get_ltp_data
```

---

## Find first OTM strike below a price threshold

```python
for number in range(1, 11):
    otm_ce, otm_pe, ce_strike, pe_strike = tsl.OTM_Strike_Selection(
        Underlying='NIFTY', Expiry=0, OTM_count=number)
    ce_ltp_data = tsl.get_ltp_data(otm_ce)
    ce_ltp = ce_ltp_data[otm_ce]
    if ce_ltp < 5:
        print(f"Found strike < ₹5: {otm_ce} @ {ce_ltp}")
        break
```

---

## Option Chain — get OI at specific strike

```python
atm_strike, option_chain = tsl.get_option_chain(
    Underlying="NIFTY", exchange="INDEX", expiry=0, num_strikes=10)

# Get OI at a specific strike
strike = 24000.0
filtered = option_chain[option_chain['Strike Price'] == strike]
ce_oi = filtered['CE OI'].values[0]
pe_oi = filtered['PE OI'].values[0]

# Get delta at ATM
ce_delta = option_chain.loc[option_chain['Strike Price'] == atm_strike, 'CE Delta'].values[0]
pe_delta = option_chain.loc[option_chain['Strike Price'] == atm_strike, 'PE Delta'].values[0]
```

**Note: `get_option_chain` returns TWO values — always unpack both:**
```python
# ✅ Correct
atm_strike, option_chain = tsl.get_option_chain(...)

# ❌ Wrong — option_chain will be a tuple, not DataFrame
option_chain = tsl.get_option_chain(...)
```

---

## Get OI from quote data (for futures)

```python
# For options
name = 'NIFTY 27 MAR 23100 CALL'
quote_data = tsl.get_quote_data(name)
oi = quote_data[name]['oi']

# For futures OI
name = 'NIFTY APR FUT'
quote_data = tsl.get_quote_data(name)
oi = quote_data[name]['oi']

# Bid/Ask depth
bids = quote_data[name]['depth']['buy']   # list of 5 dicts
asks = quote_data[name]['depth']['sell']
```

---

## Get today's data only from historical

```python
data = tsl.get_historical_data('TCS', 'NSE', '1')
today_data = data[pd.to_datetime(data['timestamp']).dt.date == pd.Timestamp.today().date()]
```

---

## Correct EMA calculation

```python
chart = tsl.get_historical_data('ZYDUSLIFE', 'NSE', '5')
chart['ema_200'] = chart['close'].ewm(span=200, adjust=False).mean()
```

---

## Range breakout (time-based)

```python
chart = tsl.get_historical_data(tradingsymbol='NIFTY', exchange='INDEX', timeframe="5")
chart = chart.set_index(chart['timestamp'])

today_date = datetime.datetime.now().strftime("%Y-%m-%d")
start_time = today_date + " 09:20:00"
end_time   = today_date + " 09:40:00"

range_chart = chart[start_time:end_time]
range_high  = range_chart['high'].max()
range_low   = range_chart['low'].min()
```

---

## Order entry + SL + target (manual, no super order)

```python
# Entry
entry_orderid = tsl.order_placement(
    tradingsymbol=name, exchange='NSE', quantity=qty,
    price=0, trigger_price=0,
    order_type='LIMIT', transaction_type='BUY', trade_type='MIS')
orderbook[name]['entry_orderid'] = entry_orderid

# Wait for fill
if tsl.get_order_status(orderid=entry_orderid) == 'TRADED':
    entry_price = tsl.get_executed_price(orderid=entry_orderid)
    orderbook[name]['entry_price'] = entry_price

    # SL order (STOPLIMIT — STOPMARKET not allowed)
    sl_price     = round(entry_price * 0.998, 1)    # 0.2% SL
    trigger_sl   = round(sl_price * 1.001, 1)
    sl_orderid   = tsl.order_placement(
        tradingsymbol=name, exchange='NSE', quantity=qty,
        price=sl_price, trigger_price=trigger_sl,
        order_type='STOPLIMIT', transaction_type='SELL', trade_type='MIS')
    orderbook[name]['sl_orderid'] = sl_orderid
    orderbook[name]['sl']         = sl_price
    orderbook[name]['tg']         = round(entry_price * 1.004, 1)  # 0.4% target
```

---

## Check SL hit / target hit in loop

```python
while True:
    ltp = tsl.get_ltp_data([name])[name]

    sl_hit = tsl.get_order_status(orderid=orderbook[name]['sl_orderid']) == 'TRADED'
    tg_hit = ltp > orderbook[name]['tg']

    if sl_hit or tg_hit:
        if tg_hit:
            tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
            tsl.order_placement(name, 'NSE', qty, 0, 0, 'LIMIT', 'SELL', 'MIS')
        break

    time.sleep(1)
```

---

## STOPLIMIT order (options — STOPMARKET not allowed)

```python
# ⚠️ STOPMARKET is NOT supported for options — use STOPLIMIT
sl_orderid = tsl.order_placement(
    tradingsymbol='NIFTY 19 DEC 24400 CALL',
    exchange='NFO', quantity=75,
    price=29, trigger_price=30,        # price < trigger for SELL SL
    order_type='STOPLIMIT',
    transaction_type='SELL',
    trade_type='MIS'
)
```

---

## Bracket Order (BO)

```python
bo_orderid = tsl.order_placement(
    tradingsymbol='ACC', exchange='NSE', quantity=1,
    price=0, trigger_price=0,
    order_type='MARKET', transaction_type='BUY',
    trade_type='BO',
    bo_profit_value=50,     # points profit target
    bo_stop_loss_value=50   # points stop loss
)
```

---

## AMO (After Market Order)

```python
orderid = tsl.order_placement(
    tradingsymbol="ACC", exchange="NSE", quantity=1,
    price=0, trigger_price=0,
    order_type='MARKET', transaction_type='BUY', trade_type='MIS',
    after_market_order=True,
    amo_time='OPEN'    # 'PRE_OPEN', 'OPEN', 'OPEN_30', 'OPEN_60'
)
```

---

## MCX Order (MARKET allowed for commodity futures)

```python
# ✅ MARKET orders are allowed for MCX commodity futures (SEBI ban applies to NSE/BSE F&O only)
orderid = tsl.order_placement(
    tradingsymbol='GOLDPETAL JAN FUT', exchange='MCX', quantity=1,
    price=0, trigger_price=0,
    order_type='MARKET', transaction_type='BUY',
    trade_type='margin'    # lowercase works, maps to MARGIN
)
```

---

## Tick size correct rounding (avoid exchange error)

**Error:** `EXCH:16283: The order price is not multiple of the tick size`

```python
# Get tick size from instrument file
df = tsl.instrument_df[
    (tsl.instrument_df['SEM_CUSTOM_SYMBOL'] == option_symbol) |
    (tsl.instrument_df['SEM_TRADING_SYMBOL'] == option_symbol)
]
tick_size = df.iloc[-1]['SEM_TICK_SIZE']   # e.g. 5.0 for NIFTY options

# Correct price rounding
price         = round((sl_price - 0.5) / tick_size) * tick_size
trigger_price = round(sl_price / tick_size) * tick_size
```

---

## Rate limit retry pattern

```python
try:
    data = tsl.get_ltp_data(names=[CE_symbol_name])
    ltp  = data.get(CE_symbol_name)
except Exception as e:
    print(e)
    time.sleep(1)
    try:
        data = tsl.get_ltp_data(names=[CE_symbol_name])
        ltp  = data.get(CE_symbol_name)
    except Exception as e:
        continue
```

---

## Resample to higher timeframe

```python
df_1min = tsl.get_historical_data('NIFTY', 'INDEX', '1')
df_2min = tsl.resample_timeframe(df_1min, timeframe='2T')   # 2-min
df_5min = tsl.resample_timeframe(df_1min, timeframe='5T')   # 5-min
df_15min = tsl.resample_timeframe(df_1min, timeframe='15T') # 15-min
df_1hr   = tsl.resample_timeframe(df_1min, timeframe='1H')  # hourly

# Monthly resample from DAY data
def resample_to_monthly(df):
    logic = {'open': 'first', 'high': 'max', 'low': 'min',
             'close': 'last', 'volume': 'sum'}
    df = df.set_index(pd.to_datetime(df['timestamp']))
    return df.resample('M').agg(logic)
```

---

## ATR-based stop loss (options)

```python
options_chart = tsl.get_historical_data(
    tradingsymbol=options_name, exchange='NFO', timeframe="5")
options_chart['atr'] = talib.ATR(
    options_chart['high'], options_chart['low'],
    options_chart['close'], timeperiod=14)

rc = options_chart.iloc[-1]
sl_points = rc['atr'] * atr_multiple   # e.g. atr_multiple = 1.5
sl_price  = entry_price - sl_points
```

---

## BTST memory — persist trade across sessions

```python
import json

def save_trade(trade: dict, file="BTSTmemory.json"):
    json.dump(trade, open(file, "w"), indent=4)

def load_trade(file="BTSTmemory.json"):
    try:    return json.load(open(file))
    except: return {}

# Save at entry
save_trade({
    "symbol": name, "qty": qty,
    "entry_price": entry_price, "sl": sl, "tg": tg
})

# Next day — load and continue
trade = load_trade()
if trade:
    name = trade['symbol']
    sl   = trade['sl']
    tg   = trade['tg']
```

---

## India VIX LTP

```python
ltp_data = tsl.get_ltp_data(["INDIA VIX"])
india_vix = ltp_data["INDIA VIX"]
```

---

## Sector index historical data

```python
# Requires sector="YES"
data = tsl.get_historical_data("NIFTY 100", "NSE", timeframe="DAY", sector="YES")
data = tsl.get_historical_data("NIFTY IT", "NSE", timeframe="1", sector="YES")
```

---

## Futures LTP

```python
ltp = tsl.get_ltp_data(names=['NIFTY APR FUT'])
nifty_fut_ltp = ltp['NIFTY APR FUT']
```

---

## MCX Gold option chain

```python
atm_strike, option_chain = tsl.get_option_chain("GOLD", "MCX", 0, 10)
```

---

## INDIA VIX note

> ⚠️ Dhan does not provide INDIA VIX **historical data**.
> LTP is available via `get_ltp_data(["INDIA VIX"])` but historical OHLC is not.

---

## Orderbook pattern (prevent duplicate orders)

```python
orderbook = {}

for name in watchlist:
    if name not in orderbook:
        orderbook[name] = {
            'entry_orderid': None,
            'entry_price': None,
            'sl': None, 'tg': None,
            'sl_orderid': None,
            'entry_time': None,
            'exit_time': None,
            'qty': lot_size
        }

    # Only place entry if not already in trade
    if orderbook[name]['entry_orderid'] is None:
        # place order...
        pass
```

---

## Correct import (v3.x)

```python
from Dhan_Tradehull import Tradehull   # ✅ v3.x

# ❌ Old — do not use
from Dhan_Tradehull_V2 import Tradehull
```

---

## Installation command (v3.3.1)

```bash
pip install dhanhq==2.2.0
pip install Dhan-Tradehull==3.3.1
```
