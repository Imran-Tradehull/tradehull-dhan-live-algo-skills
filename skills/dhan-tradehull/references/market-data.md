# Market Data — Output Signatures

## Method Comparison

| Method | Returns | Use when |
|--------|---------|----------|
| `get_ltp_data` | `{symbol: float}` | Just need price — up to 500 symbols, <1 sec |
| `get_ohlc_data` | `{symbol: {last_price, ohlc}}` | Need OHLC + LTP, lightweight |
| `get_quote_data` | Full snapshot dict | Need OI, depth, volume, circuits |
| `get_historical_data` | DataFrame 7 cols | Live strategy, indicators (~1 yr) |
| `get_long_term_historical_data` | DataFrame 7 cols | Backtesting, up to 5 years |

---

## `tsl.get_ltp_data(names=[...])`

**Version:** 3.3.1
```python
data = tsl.get_ltp_data(names=['CRUDEOIL'])
# {'CRUDEOIL': 6570.0}
```
**Return:** `dict {str: float}`
- Up to **500 symbols** per call, returns in **under 1 second**
- Key = symbol name passed in, Value = LTP as float

```python
data = tsl.get_ltp_data(names=['NIFTY', 'BANKNIFTY', 'CRUDEOIL', 'RELIANCE'])
nifty_ltp = data['NIFTY']      # 24523.5
crude_ltp = data['CRUDEOIL']   # 6570.0
```

---

## `tsl.get_ohlc_data(names=[...])`

**Version:** 3.3.1
```python
ohlc = tsl.get_ohlc_data(names=['CRUDEOIL'])
# {'CRUDEOIL': {'last_price': 6570, 'ohlc': {'open': 6685, 'high': 6689, 'low': 6497, 'close': 6577}}}
```
**Return:** `dict {str: {last_price, ohlc}}`

```python
ltp   = ohlc['CRUDEOIL']['last_price']
open_ = ohlc['CRUDEOIL']['ohlc']['open']
high  = ohlc['CRUDEOIL']['ohlc']['high']
low   = ohlc['CRUDEOIL']['ohlc']['low']
close = ohlc['CRUDEOIL']['ohlc']['close']   # prev day close
```

---

## `tsl.get_quote_data(names=[...])`

**Version:** 3.3.1
```python
quote = tsl.get_quote_data(names=['CRUDEOIL'])
```
**Return:** `dict {str: dict}` — full snapshot

**All keys in quote_data:**
```
last_price          int/float   LTP
last_quantity       int         last traded qty
last_trade_time     str         'DD/MM/YYYY HH:MM:SS'
average_price       float       VWAP-style average
volume              int         total volume today
net_change          int/float   change from prev close
ohlc                dict        {open, close, high, low}
oi                  int         Open Interest
oi_day_high         int         OI day high
oi_day_low          int         OI day low
buy_quantity        int         total buy qty in book
sell_quantity       int         total sell qty in book
upper_circuit_limit int/float   upper circuit price
lower_circuit_limit int/float   lower circuit price
52_week_high        int/float   (0 if not available)
52_week_low         int/float   (0 if not available)
depth               dict        5-level bid/ask book
```

**depth structure:** `buy/sell` → list of 5 dicts: `{quantity, orders, price}`
Note: depth shows `0` for MCX outside market hours

**`names` accepts ANY instrument:** equity, index, MCX commodity, futures, options

```python
ltp   = quote['CRUDEOIL']['last_price']
oi    = quote['CRUDEOIL']['oi']
high  = quote['CRUDEOIL']['ohlc']['high']
bid1  = quote['CRUDEOIL']['depth']['buy'][0]   # {'quantity':0,'orders':0,'price':0}
ucc   = quote['CRUDEOIL']['upper_circuit_limit']
```

---

## `tsl.get_historical_data(tradingsymbol, exchange, timeframe)`

**Version:** 3.3.1
```python
data = tsl.get_historical_data(tradingsymbol='NIFTY', exchange='INDEX', timeframe="DAY")
```

**Return:** `pd.DataFrame` — 246 rows × 7 columns (~1 year, DAY timeframe)

**Columns:**
```
open             float64
high             float64
low              float64
close            float64
volume           float64
timestamp         object    ← string: 'YYYY-MM-DD' (DAY) or 'YYYY-MM-DD HH:MM:SS' (intraday)
open_interest    float64    ← 0.0 for indices
```

**Timeframe → approx rows:**
| timeframe | Rows |
|-----------|------|
| `'DAY'` | ~246 (1 year) |
| `'60'` | ~1500+ |
| `'15'` | ~3000+ |
| `'5'` | ~6000+ |
| `'1'` | ~30000+ |

**Notes:**
- `timestamp` is `object` (string) — convert: `pd.to_datetime(data['timestamp'])`
- `open_interest = 0.0` for indices — populated for F&O contracts
- Exchange: `'INDEX'` for NIFTY/BANKNIFTY, `'NSE'`/`'BSE'` for equity, `'MCX'` for commodity

---

## `tsl.get_long_term_historical_data(...)`

**Version:** 3.3.1
```python
data = tsl.get_long_term_historical_data(
    tradingsymbol='RELIANCE', exchange='NSE', timeframe='5',
    from_date='2021-01-01', to_date='2025-10-17'
)
```

**Console (auto-paginates in ~90 day chunks):**
```
Warning: from_date 2021-01-01 exceeds Dhan's 5-year limit. Resetting to 2021-06-28
Fetching data for RELIANCE from 2021-06-28 to 2021-09-25
Fetching data for RELIANCE from 2021-09-26 to 2021-12-24
...
```

**Return:** `pd.DataFrame` — 80,196 rows × 7 columns (5-min, ~4 years)

**Columns — same as `get_historical_data` EXCEPT timestamp:**
```
timestamp    datetime64 with timezone   ← '2021-06-28 09:15:00+05:30'  (IST)
```

**Comparison:**
| Feature | `get_historical_data` | `get_long_term_historical_data` |
|---------|----------------------|--------------------------------|
| Date range | Default ~1yr | Custom `from_date` → `to_date` |
| Max history | ~1 year | **5 years** (Dhan hard limit) |
| Chunking | Single call | Auto-paginates ~90 day chunks |
| Timestamp dtype | `object` string | `datetime64` with IST tz `+05:30` |
| Use case | Live strategy | **Backtesting, CSV download** |

```python
# Convert timezone
data['timestamp'] = pd.to_datetime(data['timestamp']).dt.tz_convert('Asia/Kolkata')

# Save to CSV — avoid re-downloading every run
data.to_csv('reliance_5min_4yr.csv', index=False)
```
