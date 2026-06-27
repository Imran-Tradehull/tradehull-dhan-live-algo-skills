# Portfolio — Output Signatures

## `tsl.get_holdings()`

**Return:** `pd.DataFrame` — 13 columns

```
exchange           str       always 'ALL'
tradingSymbol      str       e.g. 'TRIDENT'
securityId         str       Dhan internal ID
isin               str       e.g. 'INE064C01022'
totalQty           int64     total shares held
dpQty              int64     settled shares — CAN sell today
t1Qty              int64     T+1 pending — CANNOT sell yet
mtf_t1_qty         int64     MTF T+1 shares
mtf_qty            int64     MTF settled
availableQty       int64     = dpQty — what you can sell right now
collateralQty      int64     pledged as collateral
avgCostPrice       float64   average buy price
lastTradedPrice    float64   current LTP
```

**⚠️ dpQty vs t1Qty:** shares bought recently sit in `t1Qty` and cannot be sold until settled. Always use `availableQty` for sell logic.

```python
holdings = tsl.get_holdings()
holdings['pnl']     = (holdings['lastTradedPrice'] - holdings['avgCostPrice']) * holdings['totalQty']
holdings['pnl_pct'] = ((holdings['lastTradedPrice'] - holdings['avgCostPrice']) / holdings['avgCostPrice']) * 100
sellable = holdings[holdings['availableQty'] > 0]
```

---

## `tsl.get_positions()`

**Return:** `pd.DataFrame`
- **Empty DataFrame with no columns** when no open intraday positions
- Always check `positions.empty` before accessing columns

```python
positions = tsl.get_positions()
if positions.empty:
    print("No open positions")
else:
    print(positions[['tradingSymbol', 'netQty', 'avgBuyPrice', 'lastTradedPrice']])
```

> 📝 Full column schema pending — will update with live positions data.

---

## `tsl.get_orderbook()`

**Return:** `pd.DataFrame` — 32 columns (ALL orders today)

```
dhanClientId           str
orderId                str       13-digit order ID
exchangeOrderId        str       '0' if not yet acknowledged by exchange
correlationId          str
orderStatus            str       TRANSIT/PENDING/TRADED/REJECTED/CANCELLED/EXPIRED
transactionType        str       BUY/SELL
exchangeSegment        str       NSE_EQ/NSE_FNO/MCX_COMM etc.
productType            str       MIS/CNC/MARGIN/MTF
orderType              str       LIMIT/MARKET/STOPLIMIT/STOPMARKET
validity               str       DAY/IOC
tradingSymbol          str
securityId             str
quantity               int64
disclosedQuantity      int64
price                  float64
triggerPrice           float64
afterMarketOrder       bool
boProfitValue          float64
boStopLossValue        float64
legName                str       ENTRY_LEG/TARGET_LEG/STOP_LOSS_LEG (super orders only)
createTime             str
updateTime             str
exchangeTime           str
drvExpiryDate          str
drvOptionType          str       CE/PE (blank for equity)
drvStrikePrice         float64   0.0 for equity
omsErrorCode           str       blank on success, populated on REJECTED
omsErrorDescription    str       blank on success, populated on REJECTED
algoId                 str
remainingQuantity      int64
averageTradedPrice     float64   0.0 if not yet executed
filledQty              int64     0 if not yet executed
```

```python
pending  = orderbook[orderbook['orderStatus'] == 'PENDING']
rejected = orderbook[orderbook['orderStatus'] == 'REJECTED']
print(rejected[['tradingSymbol', 'omsErrorCode', 'omsErrorDescription']])
```

---

## `tsl.get_trade_book()`

**Return:** `pd.DataFrame` — same 32 columns as `get_orderbook()`

| | `get_orderbook()` | `get_trade_book()` |
|--|------------------|--------------------|
| Contains | ALL orders | Only **TRADED** orders |
| Use for | Status checks, rejections | P&L, confirmed fills |

---

## `tsl.get_balance()` → `float`
```python
available_balance = tsl.get_balance()
# 94644.69
```
- Available cash in INR
- Does not include margin from pledged holdings
- Check before every order in automated algos

---

## `tsl.get_live_pnl()` → `int` or `float`
```python
PNL = tsl.get_live_pnl()
# 0   (int when no positions)
```
- Returns `int 0` (not `float 0.0`) when no positions open
- Returns `float` when positions exist (e.g. `-450.50` or `1200.75`)
- For automated kill-switch prefer `enable_pnl_based_exit()` over polling this
