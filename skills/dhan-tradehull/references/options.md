# Options — Output Signatures

## Strike Selection Comparison

| Method | Returns | Strike type | Direction |
|--------|---------|-------------|-----------|
| `ATM_Strike_Selection` | `CE_sym, PE_sym, strike` | `int` | Same strike |
| `OTM_Strike_Selection` | `CE_sym, PE_sym, CE_strike, PE_strike` | `float` | Away from spot |
| `ITM_Strike_Selection` | `CE_sym, PE_sym, CE_strike, PE_strike` | `float` | Toward/past spot |

---

## `tsl.ATM_Strike_Selection(Underlying, Expiry)`

**Version:** 3.3.1
```python
CE_sym, PE_sym, strike = tsl.ATM_Strike_Selection(Underlying='NIFTY', Expiry=0)
# 'NIFTY 30 JUN 24000 CALL', 'NIFTY 30 JUN 24000 PUT', 24000
```
**Return:** `tuple(str, str, int)`
- Symbol format: `'{UNDERLYING} {DD} {MON} {STRIKE} {CALL/PUT}'`
- Pass directly to `order_placement()` as `tradingsymbol` — no reformatting needed
- `Expiry=0` = current, `1` = next, `2` = far

---

## `tsl.OTM_Strike_Selection(Underlying, Expiry, OTM_count)`

**Version:** 3.3.1
```python
CE_sym, PE_sym, CE_strike, PE_strike = tsl.OTM_Strike_Selection(
    Underlying='CRUDEOIL', Expiry=0, OTM_count=5)
# 'CRUDEOIL 16 JUL 6800 CALL', 'CRUDEOIL 16 JUL 6300 PUT', 6800.0, 6300.0
```
**Return:** `tuple(str, str, float, float)`
- CE goes **above** ATM, PE goes **below** ATM
- `OTM_count` = steps away from ATM (step size depends on instrument)

---

## `tsl.ITM_Strike_Selection(Underlying, Expiry, ITM_count)`

**Version:** 3.3.1
```python
CE_sym, PE_sym, CE_strike, PE_strike = tsl.ITM_Strike_Selection(
    Underlying='CRUDEOIL', Expiry=0, ITM_count=1)
# 'CRUDEOIL 16 JUL 6500 CALL', 'CRUDEOIL 16 JUL 6600 PUT', 6500.0, 6600.0
```
**Return:** `tuple(str, str, float, float)`
- ITM CE → **below** ATM (Call ITM when strike < spot)
- ITM PE → **above** ATM (Put ITM when strike > spot)
- Opposite direction vs OTM

**CRUDEOIL example (ATM ~6570):**
```
ATM:        CE=6600,  PE=6600   ← same strike
OTM(5):     CE=6800↑, PE=6300↓ ← away from spot
ITM(1):     CE=6500↓, PE=6600↑ ← toward/past spot
```

---

## `tsl.get_option_chain(Underlying, exchange, expiry, num_strikes)`

**Version:** 3.3.1
```python
atm, chain = tsl.get_option_chain(
    Underlying="CRUDEOIL", exchange="MCX", expiry=0, num_strikes=10)
```

**Returns TWO values:**
- `atm` = `int` — current ATM strike (e.g. `6550`)
- `chain` = `pd.DataFrame` — 21 rows × 27 columns (for `num_strikes=10`)

**All 27 columns:**
```
CE OI             int64     Call Open Interest
CE Chg in OI      int64     Call OI change from prev close
CE Volume         int64     Call volume today
CE IV           float64     Call Implied Volatility (%)
CE LTP          float64     Call Last Traded Price
CE Bid Qty        int64     Call best bid qty
CE Bid          float64     Call best bid price
CE Ask          float64     Call best ask price
CE Ask Qty        int64     Call best ask qty
CE Delta        float64     Call Delta (0 to 1)
CE Theta        float64     Call Theta
CE Gamma        float64     Call Gamma
CE Vega         float64     Call Vega
Strike Price    float64     Strike price
PE Bid Qty        int64     Put best bid qty
PE Bid          float64     Put best bid price
PE Ask          float64     Put best ask price
PE Ask Qty        int64     Put best ask qty
PE LTP          float64     Put Last Traded Price
PE IV           float64     Put Implied Volatility (%)
PE Volume         int64     Put volume today
PE Chg in OI      int64     Put OI change from prev close
PE OI             int64     Put Open Interest
PE Delta        float64     Put Delta (-1 to 0)
PE Theta        float64     Put Theta
PE Gamma        float64     Put Gamma
PE Vega         float64     Put Vega
```

**Rows:** `num_strikes=10` → 21 rows (10 below ATM + ATM + 10 above ATM)

**Notes:**
- ✅ Replaces `get_option_greek()` — Greeks + IV included per strike
- `CE IV = 0.0` for deep ITM/OTM where IV not computable
- Index (row number) ≠ Strike Price — always filter by `chain['Strike Price'] == value`
- Exchange: `'INDEX'` for NIFTY/BANKNIFTY, `'MCX'` for CRUDEOIL/GOLD, `'NFO'` for stock options

**Common patterns:**
```python
atm, chain = tsl.get_option_chain(Underlying='NIFTY', exchange='INDEX', expiry=0, num_strikes=10)

atm_row       = chain[chain['Strike Price'] == atm]
ce_ltp        = atm_row['CE LTP'].values[0]
pe_ltp        = atm_row['PE LTP'].values[0]
atm_delta     = atm_row['CE Delta'].values[0]    # ~0.5

pcr           = chain['PE OI'].sum() / chain['CE OI'].sum()
ce_resistance = chain.loc[chain['CE OI'].idxmax(), 'Strike Price']
pe_support    = chain.loc[chain['PE OI'].idxmax(), 'Strike Price']
chain['IV Skew'] = chain['PE IV'] - chain['CE IV']
```

---

## `tsl.get_expired_option_data(...)`

**Version:** 3.3.1
```python
data = tsl.get_expired_option_data(
    tradingsymbol="RELIANCE", exchange="NSE",
    interval=1, expiry_flag="MONTH", expiry_code=1,
    strike="ATM", option_type="CALL",
    from_date="2024-10-10", to_date="2024-11-10"
)
```

**Return:** `pd.DataFrame` — 3136 rows × 10 columns

**Columns:**
```
datetime    datetime64[us]   already parsed, no tz offset
open               float64
high               float64
low                float64
close              float64
volume               int64   contracts traded that minute
iv                 float64   Implied Volatility — 0.0 if not computable
oi                   int64   Open Interest at that candle (intraday OI history)
spot               float64   underlying spot price at each candle
strike             float64   actual strike (changes as ATM moves over time)
```

**Unique vs `get_historical_data`:** includes `iv`, `oi` (intraday), `spot`, `strike`

**Timestamp note:** `datetime64[us]` — NO timezone offset (unlike `get_long_term_historical_data` which has `+05:30`)

**Parameters:**
- `interval` → `1, 5, 15, 25, 60`
- `expiry_flag` → `'MONTH'` or `'WEEK'`
- `expiry_code` → `1`=near, `2`=next, `3`=far
- `strike` → `'ATM'`, `'ATM+1'`, `'ATM-3'` etc.
- `option_type` → `'CALL'` or `'PUT'`
- Only works for **expired** contracts — use `get_option_chain()` for live
