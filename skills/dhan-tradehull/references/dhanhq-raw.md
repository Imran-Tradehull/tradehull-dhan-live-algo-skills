# dhanhq Raw API — Fallback Reference

Use this file ONLY when `Dhan_Tradehull` wrapper doesn't expose what's needed.
Reference: https://docs.dhanhq.co/skills/ | https://github.com/dhan-oss/dhanhq-skills

**Always try `tsl.*` first. Drop to raw `dhan.*` only for gaps below.**

---

## When to use raw dhanhq

| Need | Tradehull covers? | Raw dhanhq needed? |
|------|------------------|-------------------|
| Order placement, modify, cancel | ✅ | No |
| LTP, OHLC, Quote | ✅ | No |
| Historical data | ✅ | No |
| Option chain + greeks | ✅ | No |
| Strike selection (ATM/OTM/ITM) | ✅ | No |
| Portfolio, holdings, positions | ✅ | No |
| Super orders, forever orders | ✅ | No |
| P&L exit, kill switch | ✅ | No |
| Telegram alerts | ✅ | No |
| **Position conversion (MIS → CNC)** | ❌ | ✅ |
| **eDIS authorization (sell holdings)** | ❌ | ✅ |
| **Exit ALL positions in one call** | ❌ | ✅ |
| **Trade history / ledger report** | ❌ | ✅ |
| **Static IP management** | ❌ | ✅ |
| **WebSocket live order updates** | ❌ | ✅ |
| **200-level full market depth** | Partial (20-level via FullDepth) | ✅ for 200-level |

---

## Raw dhanhq Access (already inside tsl)

Tradehull wraps `dhanhq` internally. You can access the raw client via:

```python
# tsl.Dhan is the raw dhanhq object
# tsl.dhan_context is the DhanContext object

dhan = tsl.Dhan          # raw dhanhq instance
ctx  = tsl.dhan_context  # DhanContext
```

**No need to re-authenticate** — just use `tsl.Dhan` directly.

---

## Position Conversion (MIS → CNC or CNC → MIS)

Not exposed in Tradehull. Use raw API:

```python
# Convert intraday position to delivery
response = tsl.Dhan.convert_position(
    dhan_client_id=tsl.ClientCode,
    from_product_type=tsl.Dhan.INTRA,    # MIS
    exchange_segment=tsl.Dhan.NSE,
    position_type="LONG",                 # LONG or SHORT
    security_id="2885",                   # RELIANCE security ID
    convert_qty=10,
    to_product_type=tsl.Dhan.CNC
)
```

**API:** `POST /v2/positions/convert`
`positionType`: `LONG`, `SHORT`, `CLOSED`
`fromProductType` → `toProductType`: `CNC`, `INTRADAY`, `MARGIN`

---

## Exit All Positions

Closes all open positions + cancels open orders in one call:

```python
response = tsl.Dhan.exit_all_positions()
# Returns 202 Accepted on success
```

**API:** `DELETE /v2/positions`

---

## Trade History

```python
# Get trade history for a date range
response = tsl.Dhan.get_trade_history(
    from_date="2026-06-01",
    to_date="2026-06-27",
    page_number=0
)
trades = response['data']
```

**API:** `GET /v2/trades/{from-date}/{to-date}/{page-number}`

---

## Ledger Report

```python
response = tsl.Dhan.get_ledger_report(
    from_date="2026-06-01",
    to_date="2026-06-27"
)
```

**API:** `GET /v2/ledger/{from-date}/{to-date}`

---

## eDIS — Authorize Holdings for Sell

Required before selling demat holdings (T+1 or older):

```python
# Step 1: Generate T-PIN on registered mobile
tsl.Dhan.edis_tpin()

# Step 2: Generate eDIS form for specific ISINs
response = tsl.Dhan.edis_form(
    isin=["INE002A01018"],   # list of ISINs (from holdings['isin'])
    exchange="NSE",
    segment="EQ"
)
html_form = response['data']['edisFormHtml']   # render this in browser

# Step 3: Check eDIS status
status = tsl.Dhan.edis_inquiry(isin="INE002A01018")
# or check ALL holdings
status = tsl.Dhan.edis_inquiry(isin="ALL")
```

---

## Rate Limits (raw API)

| API Type | Per Second | Per Minute | Per Hour | Per Day |
|----------|-----------|------------|---------|---------|
| Order APIs | 10 | 250 | 1,000 | 7,000 |
| Data APIs | 5 | — | — | 100,000 |
| Quote APIs | 1 | Unlimited | Unlimited | Unlimited |
| Non-Trading | 20 | Unlimited | Unlimited | Unlimited |

**Note:** Order modifications capped at **25 per order**.

---

## WebSocket — Live Order Updates

Tradehull doesn't wrap this. For real-time order status updates:

```python
from dhanhq import orderupdate

order_feed = orderupdate.OrderSocket(
    client_id=tsl.ClientCode,
    access_token=tsl.token_id
)
order_feed.run_forever()
# Callback fires on every order status change
```

---

## 200-Level Full Market Depth

Tradehull's `full_market_depth_data()` gives 20-level via `FullDepth`.
For the 200-level depth (dhanhq v2.2.0+):

```python
# Access via raw dhan_context
dhan_http = tsl.dhan_context.get_dhan_http()
response = dhan_http.post("/marketfeed/quote", {
    "NSE_EQ": [2885]
})
# depth field will have up to 200 bid/ask levels
```

---

## Key Raw dhanhq Constants (on tsl.Dhan)

```python
# Exchange segments
tsl.Dhan.NSE        # NSE equity
tsl.Dhan.NSE_FNO    # NSE F&O
tsl.Dhan.BSE        # BSE equity
tsl.Dhan.BSE_FNO    # BSE F&O
tsl.Dhan.MCX        # MCX commodity
tsl.Dhan.INDEX      # Index
tsl.Dhan.IDX_I      # Index (alternate)

# Order types
tsl.Dhan.LIMIT      # Limit
tsl.Dhan.MARKET     # Market
tsl.Dhan.SL         # Stop Loss Limit
tsl.Dhan.SLM        # Stop Loss Market

# Product types
tsl.Dhan.INTRA      # MIS / Intraday
tsl.Dhan.CNC        # CNC / Delivery
tsl.Dhan.MARGIN     # Margin
tsl.Dhan.MTF        # MTF

# Transaction
tsl.Dhan.BUY
tsl.Dhan.SELL

# Validity
tsl.Dhan.DAY
tsl.Dhan.IOC
```

---

## Useful Links

| Resource | URL |
|----------|-----|
| DhanHQ Skills docs | https://docs.dhanhq.co/skills/ |
| DhanHQ API docs | https://docs.dhanhq.co/api/v2/ |
| dhanhq-skills GitHub | https://github.com/dhan-oss/dhanhq-skills |
| DhanHQ-py GitHub | https://github.com/dhan-oss/DhanHQ-py |
| Rate limits | https://docs.dhanhq.co/api/v2/guides/rate-limits |
| Error codes | https://docs.dhanhq.co/api/v2/guides/annexure |
