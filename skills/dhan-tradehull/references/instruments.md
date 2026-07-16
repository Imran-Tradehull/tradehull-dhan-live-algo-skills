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

> 🚨 **`SEM_TICK_SIZE` is in PAISE, not rupees.** Divide by 100 before using
> it as a rounding step. `5.0` means **₹0.05**, `10.0` means **₹0.10**.
> Using the raw value as the step rounds prices to the nearest ₹5 / ₹10.

| `SEM_TICK_SIZE` | Real tick | Seen on |
|-----|-----|-----|
| `1.0`   | ₹0.01 | Low-priced NSE equity (e.g. YESBANK) |
| `5.0`   | ₹0.05 | NSE index options (OPTIDX), some equity |
| `10.0`  | ₹0.10 | Most large-cap equity (RELIANCE, TCS, HEROMOTOCO) |
| `20.0`  | ₹0.20 | Some index futures |
| `50.0`+ | ₹0.50+ | High-priced instruments |

**Tick varies per symbol — never hardcode one.** RELIANCE is ₹0.10 while
YESBANK is ₹0.01; a price valid for one is rejected for the other.

```python
def get_tick(symbol, exchange="NSE"):
    """Tick size in RUPEES for a symbol."""
    row = tsl.instrument_df[
        (tsl.instrument_df["SEM_EXM_EXCH_ID"] == exchange)
        & (tsl.instrument_df["SEM_TRADING_SYMBOL"] == symbol)
    ]
    if row.empty:
        return 0.05
    return float(row.iloc[-1]["SEM_TICK_SIZE"]) / 100.0     # paise -> rupees


def round_tick(price, symbol):
    tick = get_tick(symbol)
    return round(round(price / tick) * tick, 2)

round_tick(1307.2894, "RELIANCE")   # -> 1307.30   (tick 0.10)
round_tick(21.4127,  "YESBANK")     # ->   21.41   (tick 0.01)
```

See `references/error-log.md` → ERROR-004.

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

# The NSE F&O stock universe (~208) — stocks that have a stock future AND
# trade as real equity. Self-updates when SEBI revises the F&O list.
fut = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') &
         (df['SEM_INSTRUMENT_NAME'] == 'FUTSTK')]
und = set(fut['SEM_TRADING_SYMBOL'].str.split('-').str[0].str.strip())

eq  = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') &
         (df['SEM_INSTRUMENT_NAME'] == 'EQUITY') &
         (df['SEM_SERIES'] == 'EQ')]           # ⚠️ 'EQ' series = real tradeable
eqs = set(eq['SEM_TRADING_SYMBOL'].str.strip())

fno_stocks = sorted(x for x in (und & eqs) if 'TEST' not in x)   # ~208
# ⚠️ The file contains exchange test symbols (011NSETEST ...) that pass both
#    filters — strip them, or your scanner wastes calls on fake instruments.

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
