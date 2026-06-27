# Skill Metadata — Dhan-Tradehull

**Package:** Dhan-Tradehull
**PyPI:** https://pypi.org/project/Dhan-Tradehull/
**Version:** 3.3.1 (released Jun 3, 2026)
**Author:** TradeHull (contact.tradehull@gmail.com)
**License:** MIT
**Requires:** Python >=3.10

---

## Skill File Index

```
dhan-tradehull/
├── SKILL.md                      Entry point. Quick reference + routing table.
│                                 Read this first — contains method signatures,
│                                 deprecated methods, and which reference to load.
│
└── references/
    ├── metadata.md               ← YOU ARE HERE. Skill schema + index.
    │
    ├── dhanhq-raw.md             Raw dhanhq fallback layer.
    │                             Use ONLY when Tradehull wrapper doesn't cover it.
    │                             Covers: position conversion, eDIS, exit all positions,
    │                             trade history, ledger, WebSocket order updates,
    │                             200-level depth, rate limits, raw dhan constants.
    │
    ├── instruments.md            Instrument master reference.
    │                             File schema (17 columns), instrument types,
    │                             segment codes, expiry flags, major security IDs,
    │                             lot sizes, expiry times, filter patterns.
    │
    ├── auth.md                   Authentication.
    │                             Login modes, token validity, console output,
    │                             tsl object type, access_token vs pin_totp rules.
    │
    ├── market-data.md            Market data methods.
    │                             get_ltp_data, get_ohlc_data, get_quote_data,
    │                             get_historical_data, get_long_term_historical_data.
    │                             Output schemas, dtypes, timestamp quirks, use cases.
    │
    ├── options.md                Options methods.
    │                             ATM/OTM/ITM strike selection, get_option_chain,
    │                             get_expired_option_data.
    │                             Return types, column schemas, greeks, PCR patterns.
    │
    ├── orders.md                 Order management.
    │                             order_placement, modify_order, cancel_order,
    │                             cancel_all_orders, get_order_status,
    │                             get_executed_price, get_exchange_time,
    │                             place_super_order, place_forever_order.
    │                             SEBI MARKET order ban, super vs forever decision.
    │
    ├── portfolio.md              Portfolio and account data.
    │                             get_holdings, get_positions, get_orderbook,
    │                             get_trade_book, get_balance, get_live_pnl.
    │                             DataFrame schemas, column dtypes, access patterns.
    │
    ├── utilities.md              Utility methods.
    │                             get_lot_size, margin_calculator,
    │                             enable_pnl_based_exit, send_telegram_alert.
    │                             Kill switch behaviour, Telegram setup link.
    │
    ├── coding-style.md           TradeHull coding style guide — ALWAYS READ FIRST.
    │                             Vertical alignment, bc/sc conditions, block comments,
    │                             flat structure, try/except placement, orderbook reset.
    │
    ├── algo-positional-spread.md  Real production algo anatomy (positional).
    │                             Bull Put Spread / Bear Call Spread via Supertrend 60-min.
    │                             Covers: JSON persistence, AMO orders, delta-based strike
    │                             selection, spread PnL, next-month expiry, only_few_days_left.
    │                             Source file: examples/positional_spread_algo.py
    │
    ├── algo-intraday-options.md  Real production algo anatomy (intraday).
    │                             Intraday options (CE/PE) with Supertrend + S/R.
    │                             Covers: completed candle pattern, entry/exit flow,
    │                             trailing SL, panic exit, re-entry, log saving.
    │                             Source file: examples/intraday_options_algo.py
    │
    ├── answer-patterns.md        TradeHull answer style + 12 common student mistakes + FAQ.
    │                             Use when writing code or answering algo trading questions.
    │
    ├── common-patterns.md        Common patterns from TradeHull student sessions.
    │                             Covers: deprecated methods,
    │                             ATM→LTP flow, OTM with rate limits, option chain OI,
    │                             STOPLIMIT orders, bracket orders, AMO, tick size rounding,
    │                             BTST memory, resample, India VIX, orderbook pattern.
    │
    └── error-log.md              Known errors + regulations.
                                  ERROR-001: DH-901 invalid token.
                                  ERROR-002: DH-904 rate limit.
                                  ERROR-003: expired contract.
                                  ERROR-004: tick size mismatch.
                                  ERROR-005: STOPMARKET not allowed.
                                  ERROR-006: DAY timeframe for futures.
                                  ERROR-007: module not found.
                                  ERROR-008: unsupported timeframe.
                                  ERROR-009: SSL certificate error.
                                  ERROR-010: get_option_chain tuple unpack.
                                  REGULATION-001: SEBI MARKET order ban.
                                  ERROR-001: DH-901 invalid/expired token.
                                  REGULATION-001: SEBI MARKET order ban Apr 2026.

```

---

## Deprecated Methods — Do Not Use

| Method | Reason | Use Instead |
|--------|--------|-------------|
| `get_option_greek()` | Greeks now in option chain | `get_option_chain()` |
| `place_conditional_trigger()` | We use TA-Lib for conditions | `get_historical_data()` + TA-Lib |

---

## Key Rules (Always Apply)

| Rule | Detail |
|------|--------|
| No MARKET orders | SEBI ban from Apr 1, 2026 — use LIMIT only |
| BUY limit price | Must be **> LTP** for instant fill |
| SELL limit price | Must be **< LTP** for instant fill |
| Lot size | Always fetch via `get_lot_size()` — never hardcode |
| Token | `access_token` expires daily. `pin_totp` PIN is lifetime |
| Super order | Default for intraday algos with SL + target |
| Forever order | Default for swing / BTST / positional |
| TA-Lib | Used for all indicator/signal logic — not Dhan conditionals |

---

## Return Type Quick Reference

| Method | Returns |
|--------|---------|
| `get_ltp_data()` | `dict {str: float}` |
| `get_ohlc_data()` | `dict {str: {last_price, ohlc}}` |
| `get_quote_data()` | `dict {str: dict}` — full snapshot |
| `get_historical_data()` | `DataFrame` 7 cols, timestamp=`object` |
| `get_long_term_historical_data()` | `DataFrame` 7 cols, timestamp=`datetime64+IST` |
| `ATM_Strike_Selection()` | `tuple(str, str, int)` |
| `OTM_Strike_Selection()` | `tuple(str, str, float, float)` |
| `ITM_Strike_Selection()` | `tuple(str, str, float, float)` |
| `get_option_chain()` | `int (atm), DataFrame 27 cols` ← TWO values |
| `get_expired_option_data()` | `DataFrame` 10 cols, datetime=`datetime64[us]` |
| `order_placement()` | `str` — 13-digit order ID |
| `order_placement(should_slice=True)` | `list[str]` — multiple IDs |
| `modify_order()` | `str` — same order ID |
| `cancel_order()` | `str` — same order ID |
| `get_order_status()` | `str` — TRANSIT/PENDING/TRADED/REJECTED/CANCELLED/EXPIRED |
| `get_executed_price()` | `float` — avg fill price |
| `get_exchange_time()` | `str` — `'0001-01-01 00:00:00'` if not yet traded |
| `place_super_order()` | `str` — single ID for all 3 legs |
| `place_forever_order()` | `str` — forever order ID |
| `get_holdings()` | `DataFrame` 13 cols |
| `get_positions()` | `DataFrame` (empty if no open positions) |
| `get_orderbook()` | `DataFrame` 32 cols — all orders today |
| `get_trade_book()` | `DataFrame` 32 cols — executed only |
| `get_balance()` | `float` — available cash INR |
| `get_live_pnl()` | `int` 0 or `float` |
| `get_lot_size()` | `int` |
| `enable_pnl_based_exit()` | `dict` |
| `send_telegram_alert()` | `None` |

---

## Hidden Methods (discovered from source, not in PyPI docs)

| Method | Description |
|--------|-------------|
| `resample_timeframe(df, timeframe)` | Resample 1-min data to higher TF (pandas offset strings) |
| `heikin_ashi(df)` | Convert OHLC to Heikin Ashi candles |
| `renko_bricks(data, box_size)` | Convert OHLC to Renko bricks |
| `get_executed_price_and_time(orderid)` | Single call → `(float, str)` price + time |
| `order_report()` | Bulk → `(status_dict, price_dict, time_dict)` for all orders |
| `kill_switch(action)` | `'ON'`/`'OFF'` — standalone kill switch |
| `get_future_script(underlying, expiry)` | Get futures symbol name |
| `get_expiry_list(Underlying, exchange)` | List of available expiry dates |
| `get_expiry_date(Underlying, opt_fut)` | Sorted expiry dates for options/futures |

All documented in `references/utilities.md`

---

## Dependencies Folder Structure

Auto-created in working directory at login:
```
Dependencies/
├── log_files/
│   └── logs2026-06-27.log              ← daily log (DEBUG level)
├── all_instrument 2026-06-27.csv       ← instrument master (27,982 KB, 225,632 rows)
└── token_<client_id>_<date>.txt        ← cached access token (format: date|token|expiry)
```
- Token cached so same-day re-runs skip login
- Old token/instrument files auto-deleted when new ones created
- Instrument file re-downloaded only if today's file missing

---

## Pending — Real Output Not Yet Captured

| Method | Status |
|--------|--------|
| `get_positions()` | Empty during capture — need live intraday positions |
| `margin_calculator()` | Not yet run |
| `modify_super_order()` | Docs only — no Pdb++ output |
| `cancel_super_order()` | Docs only — no Pdb++ output |
| `modify_forever_order()` | Docs only — no Pdb++ output |
| `cancel_forever_order()` | Docs only — no Pdb++ output |
| `get_forever_orders()` | Docs only — no Pdb++ output |

---

## Useful Links

| Resource | URL |
|----------|-----|
| PyPI | https://pypi.org/project/Dhan-Tradehull/ |
| GitHub | https://github.com/TradeHull/Dhan_Tradehull |
| Telegram setup | https://tradehull.com/telegram-integration-for-algo-trading/ |
| TradeHull | https://tradehull.in |
