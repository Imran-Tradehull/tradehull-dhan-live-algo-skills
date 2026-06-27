# Orders — Output Signatures

## 🚨 SEBI Regulation (effective 1st April 2026)
MARKET orders are NOT allowed for F&O. Always use LIMIT.
- **BUY** → limit price must be **greater than** LTP
- **SELL** → limit price must be **less than** LTP

```python
ltp = tsl.get_ltp_data(names=['NIFTY 19 DEC 24400 CALL'])['NIFTY 19 DEC 24400 CALL']
buy_price  = round(ltp * 1.02, 1)   # 2% above LTP
sell_price = round(ltp * 0.98, 1)   # 2% below LTP
```

## Order Type Decision

| Strategy | Use |
|----------|-----|
| Intraday with SL + target | ✅ `place_super_order()` first |
| Swing / BTST / Positional | ✅ `place_forever_order()` |
| Simple entry only | `order_placement()` |

---

## `tsl.order_placement(...)`

**Return:** `str` — 13-digit order ID
```python
orderid = tsl.order_placement('NIFTY 21 NOV 24400 CALL', 'NFO', 75, 0.05, 0, 'LIMIT', 'BUY', 'MIS')
# '2452606277130'
```
- Returns `None` on failure — always check before using
- With `should_slice=True` → returns `list[str]` (multiple IDs for large qty)

```python
# Sliced order (qty > freeze limit)
order_ids = tsl.order_placement(..., quantity=1820, should_slice=True)
# ['2452606277130', '2452606277131']
for oid in order_ids:
    print(tsl.get_order_status(orderid=oid))
```

## `tsl.modify_order(...)` → `str` same ID (silent, no console log)
## `tsl.cancel_order(OrderID)` → `str` same ID
## `tsl.cancel_all_orders()` → cancels all open intraday + squares off positions

---

## `tsl.get_order_status(orderid)`

**Return:** `str` — one of 6 states:

| Status | Meaning |
|--------|---------|
| `'TRANSIT'` | Sent to exchange, not yet acknowledged |
| `'PENDING'` | Live at exchange, waiting to fill |
| `'TRADED'` | ✅ Fully executed |
| `'REJECTED'` | Exchange rejected |
| `'CANCELLED'` | Cancelled |
| `'EXPIRED'` | DAY order not filled by EOD |

- Accepts `orderid` as `str` or `int`

## `tsl.get_executed_price(orderid)` → `float` (avg fill price)
- Only meaningful when status == `'TRADED'`

## `tsl.get_exchange_time(orderid)` → `str` datetime
- `'0001-01-01 00:00:00'` = not yet executed (sentinel null value — not an error)
- Always gate on `'TRADED'` before calling

---

## `tsl.place_super_order(...)` ✅ Preferred for intraday algos

**Return:** `str` — single order ID covering all 3 legs

```python
order_id = tsl.place_super_order(
    tradingsymbol="TRIDENT", exchange="NSE",
    transaction_type="BUY", quantity=1,
    order_type="LIMIT", trade_type="MIS",
    price=25, target_price=27,
    stop_loss_price=24, trailing_jump=0.2
)
# '2452606277130'
```

**3 legs under 1 order ID:**
```
order_id
├── ENTRY_LEG      → BUY @ 25
├── TARGET_LEG     → SELL @ 27
└── STOP_LOSS_LEG  → SELL @ 24 (trails by 0.2)
```

```python
# Modify specific leg
tsl.modify_super_order(order_id=order_id, order_type="LIMIT", quantity=1,
                        price=24.9, leg_name="ENTRY_LEG")
# Cancel specific leg
tsl.cancel_super_order(order_id=order_id, leg_name="STOP_LOSS_LEG")
# Fetch all
super_orders = tsl.get_super_orders()
```

---

## `tsl.place_forever_order(...)` ✅ Preferred for swing/BTST/positional

**Return:** `str` — forever order ID

```python
# SINGLE trigger
forever_id = tsl.place_forever_order(
    tradingsymbol="TRIDENT", exchange="NSE",
    transaction_type="BUY", quantity=1,
    order_type="LIMIT", trade_type="CNC",
    price=25, trigger_price=25.05, order_flag="SINGLE"
)

# OCO — target + SL together
forever_id = tsl.place_forever_order(
    ..., order_flag="OCO",
    price=27, trigger_price=27.05,           # target leg
    quantity_1=1, price_1=24, trigger_price_1=23.95   # SL leg
)
```

- Stays active **across sessions** until triggered or cancelled
- `tsl.modify_forever_order(order_id, order_flag, order_type, quantity, price, trigger_price, leg_name)` → `str`
  - `order_flag` is **required** — `'SINGLE'` or `'OCO'`
  - `leg_name` → `'TARGET_LEG'` or `'STOP_LOSS_LEG'` only (not `ENTRY_LEG`)
- `tsl.cancel_forever_order(order_id)` → `str` cancel order ID
- `tsl.get_forever_orders()` → `list` of all active forever orders
