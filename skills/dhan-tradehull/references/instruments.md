# Instrument Master Reference

Source: `Dependencies/all_instrument_2026-06-27.csv`
Total rows: 225,632 | Updated: daily at login

---

## File Schema

```
Column                  dtype      Description
──────────────────────────────────────────────────────────────────
Unnamed: 0              int64      Row index (ignore)
SEM_EXM_EXCH_ID         str        Exchange: 'NSE', 'BSE', 'MCX'
SEM_SEGMENT             str        Segment code (see below)
SEM_SMST_SECURITY_ID    int64      ← Dhan's internal security ID (used in all API calls)
SEM_INSTRUMENT_NAME     str        Instrument type (see below)
SEM_EXPIRY_CODE         int64      Always 0 in this file
SEM_TRADING_SYMBOL      str        Exchange trading symbol (e.g. 'NIFTY-Jul2026-24000-CE')
SEM_LOT_UNITS           float64    Lot size
SEM_CUSTOM_SYMBOL       str        ← Human-readable symbol used in Tradehull methods
SEM_EXPIRY_DATE         str        Expiry datetime string
SEM_STRIKE_PRICE        float64    Strike price (0.0 for futures/equity)
SEM_OPTION_TYPE         str        'CE', 'PE', 'XX' (futures/equity), NaN
SEM_TICK_SIZE           float64    Minimum price movement
SEM_EXPIRY_FLAG         str        Expiry frequency (see below)
SEM_EXCH_INSTRUMENT_TYPE str       Exchange-level instrument type
SEM_SERIES              str        BSE/NSE series (EQ, BE, etc.)
SM_SYMBOL_NAME          str        Underlying name (e.g. 'CRUDEOIL', 'SILVER')
```

---

## SEM_INSTRUMENT_NAME Values

| Value | Meaning | Exchange |
|-------|---------|----------|
| `EQUITY` | Cash equity stock | NSE, BSE |
| `INDEX` | Index (no expiry) | NSE, BSE |
| `FUTIDX` | Index futures | NSE, BSE |
| `FUTCOM` | Commodity futures | MCX |
| `FUTSTK` | Stock futures | NSE, BSE |
| `FUTCUR` | Currency futures | NSE, BSE |
| `OPTIDX` | Index options | NSE, BSE |
| `OPTSTK` | Stock options | NSE, BSE |
| `OPTFUT` | Commodity options | MCX |
| `OPTCUR` | Currency options | NSE, BSE |

---

## SEM_SEGMENT Values

| Code | Meaning |
|------|---------|
| `E` | Equity (cash segment) |
| `D` | Derivatives (F&O) |
| `C` | Currency |
| `M` | MCX / Commodity |
| `I` | Index |

---

## SEM_EXPIRY_FLAG Values

| Flag | Meaning |
|------|---------|
| `W` | Weekly expiry |
| `M` | Monthly expiry |
| `Q` | Quarterly expiry |
| `H` | Half-yearly expiry |
| NaN | No expiry (equity, index) |

---

## Symbol Format

**Two key columns — always use `SEM_CUSTOM_SYMBOL` in Tradehull:**

| | `SEM_TRADING_SYMBOL` | `SEM_CUSTOM_SYMBOL` |
|--|---------------------|---------------------|
| Format | Exchange format | Tradehull format |
| Example | `NIFTY-Jul2026-24000-CE` | `NIFTY 28 JUL 24000 CALL` |
| Used in | Internal filtering | `order_placement()`, `get_ltp_data()` |

**Pattern:** `'{UNDERLYING} {DD} {MON} {STRIKE} {CALL/PUT}'`

---

## Major Index Security IDs

| Index | `SEM_SMST_SECURITY_ID` | `SEM_TRADING_SYMBOL` | Lot Size |
|-------|----------------------|---------------------|---------|
| NIFTY | **13** | `NIFTY` | 65 |
| BANKNIFTY | **25** | `BANKNIFTY` | 30 |
| FINNIFTY | **27** | `FINNIFTY` | 60 |
| MIDCPNIFTY | **442** | `MIDCPNIFTY` | 120 |
| SENSEX | **51** | `SENSEX` | 20 |
| INDIA VIX | **21** | `INDIA VIX` | — |

---

## Lot Sizes (as of Jun 2026)

**Index F&O:**
```
NIFTY       → 65    (revised from 75)
BANKNIFTY   → 30
FINNIFTY    → 60
MIDCPNIFTY  → 120
SENSEX      → 20
```

**⚠️ Always use `tsl.get_lot_size()` — never hardcode. SEBI revises these.**

---

## Expiry Times

| Exchange | Segment | Expiry Time |
|----------|---------|-------------|
| NSE/BSE | Equity F&O (OPTIDX, OPTSTK, FUTIDX, FUTSTK) | **15:30 IST** |
| NSE/BSE | Currency (FUTCUR, OPTCUR) | **14:30 IST** |
| MCX | Commodity (FUTCOM, OPTFUT) | **23:30 IST** |

---

## Tick Sizes

| Instrument | Tick Size |
|-----------|----------|
| NSE OPTIDX (index options) | 5.0 |
| NSE EQUITY | 1.0 – 100.0 (varies by stock) |

---

## Common Filter Patterns (used in strategy code)

```python
df = tsl.instrument_df   # access the loaded instrument file

# Get security ID for a symbol
row = df[(df['SEM_CUSTOM_SYMBOL'] == 'NIFTY 28 JUL 24000 CALL') |
         (df['SEM_TRADING_SYMBOL'] == 'NIFTY-Jul2026-24000-CE')]
security_id = row.iloc[-1]['SEM_SMST_SECURITY_ID']

# All NSE equity stocks
equities = df[(df['SEM_INSTRUMENT_NAME'] == 'EQUITY') &
              (df['SEM_EXM_EXCH_ID'] == 'NSE')]

# All NIFTY weekly options (current month)
nifty_weekly = df[(df['SEM_INSTRUMENT_NAME'] == 'OPTIDX') &
                  (df['SEM_TRADING_SYMBOL'].str.startswith('NIFTY')) &
                  (df['SEM_EXPIRY_FLAG'] == 'W')]

# MCX CRUDEOIL futures
crude_fut = df[(df['SEM_EXM_EXCH_ID'] == 'MCX') &
               (df['SM_SYMBOL_NAME'] == 'CRUDEOIL') &
               (df['SEM_INSTRUMENT_NAME'] == 'FUTCOM')]
# Sort by expiry to get nearest contract
crude_near = crude_fut.sort_values('SEM_EXPIRY_DATE').iloc[0]

# All stock options for a specific stock
reliance_opts = df[(df['SEM_INSTRUMENT_NAME'] == 'OPTSTK') &
                   (df['SEM_TRADING_SYMBOL'].str.startswith('RELIANCE-')) &
                   (df['SEM_EXM_EXCH_ID'] == 'NSE')]

# Get lot size from instrument file directly
lot = df[df['SEM_CUSTOM_SYMBOL'] == 'NIFTY 28 JUL 24000 CALL'].iloc[0]['SEM_LOT_UNITS']
```

---

## MCX Commodity Symbols (SM_SYMBOL_NAME)

```
ALUMINI, ALUMINIUM, CARDAMOM, COPPER, COTTON, COTTONOIL,
CRUDEOIL, CRUDEOILM, GOLD, GOLDGUINEA, GOLDM, GOLDPETAL,
GOLDTEN, KAPAS, LEAD, LEADMINI, MENTHAOIL, NATGASMINI,
NATURALGAS, NICKEL, SILVER, SILVER100, SILVERM, SILVERMIC,
STEELREBAR, ZINC, ZINCMINI
```

**Note:** MCX lot size is always `1.0` in the instrument file — actual contract size differs per commodity.

---

## Key Notes

- `SEM_EXPIRY_CODE` is always `0` — not useful for filtering
- For NSE equity: use `SEM_SERIES == 'EQ'` to get main board stocks (excludes BE, BT series)
- `SEM_CUSTOM_SYMBOL` is stripped and space-normalized at login (`str.strip().replace(r'\s+', ' ')`)
- Always use `.iloc[-1]` when filtering by symbol — multiple rows may exist for same symbol across exchanges
- `SEM_OPTION_TYPE == 'XX'` means futures/non-option (not a real option type)
