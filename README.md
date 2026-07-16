# Tradehull Dhan Live Algo Skills

> Agent skills for Indian algo trading with the [Dhan-Tradehull](https://pypi.org/project/Dhan-Tradehull/) Python library.
> Works with Claude Code, Cursor, Codex, and any [SKILL.md](https://agentskills.io)-compatible agent.

---

## Install

### Claude Code
```bash
npx skills add Imran-Tradehull/tradehull-dhan-live-algo-skills --skill dhan-tradehull
```

### Cursor
```bash
npx skills add Imran-Tradehull/tradehull-dhan-live-algo-skills --skill dhan-tradehull --agent cursor
```

### Codex
```bash
npx skills add Imran-Tradehull/tradehull-dhan-live-algo-skills --skill dhan-tradehull --agent codex
```

### Manual
```bash
git clone https://github.com/Imran-Tradehull/tradehull-dhan-live-algo-skills.git
cp -r tradehull-dhan-live-algo-skills/skills/dhan-tradehull .cursor/skills/
```

---

## Requirements

```bash
pip install dhanhq==2.2.0
pip install Dhan-Tradehull==3.3.2
```

---

## What's inside

```
skills/dhan-tradehull/
│
├── SKILL.md                              ← entry point · quick reference · routing table
│
├── references/
│   ├── coding-style.md                   ← TradeHull coding style · read before writing any code
│   ├── auth.md                           ← login modes · token validity · Dependencies folder
│   ├── market-data.md                    ← LTP · OHLC · quote · historical · long-term
│   ├── options.md                        ← option chain · ATM/OTM/ITM · greeks · expired data
│   ├── orders.md                         ← order placement · SEBI rules · super · forever orders
│   ├── portfolio.md                      ← holdings · positions · orderbook · balance · P&L
│   ├── utilities.md                      ← lot size · margin · Telegram · kill switch
│   ├── instruments.md                    ← 225k-row instrument file schema · security IDs
│   ├── common-patterns.md                ← real code patterns from student support sessions
│   ├── answer-patterns.md                ← common mistakes · FAQ · answer style
│   ├── algo-intraday-options.md          ← intraday algo anatomy (Supertrend + S/R)
│   ├── algo-positional-spread.md         ← positional spread algo anatomy (delta-based)
│   ├── dhanhq-raw.md                     ← raw dhanhq fallback (position convert · eDIS · exit all)
│   └── error-log.md                      ← known errors · SEBI regulations
│
└── examples/
    ├── intraday_options_algo.py          ← real production intraday algo
    └── positional_spread_algo.py        ← real production positional algo
```

---

## What the skill covers

| Domain | Details |
|--------|---------|
| **Authentication** | `access_token`, `pin_totp`, `api_key` modes · token validity rules |
| **Market Data** | LTP · OHLC · full quote · historical · long-term · sector indices · India VIX |
| **Options** | Option chain with greeks · ATM/OTM/ITM strike selection · expired options data |
| **Orders** | LIMIT · STOPLIMIT · super orders · forever/GTT orders · slicing · AMO |
| **SEBI Rules** | MARKET orders banned for F&O from Apr 2026 · correct LIMIT price patterns |
| **Portfolio** | Holdings · open positions · orderbook · tradebook · live P&L · balance |
| **Utilities** | Dynamic lot size · margin calculator · Telegram alerts · P&L exit · kill switch |
| **Instruments** | 225k-row CSV schema · security ID lookup · expiry flags · tick size |
| **Algo Patterns** | Completed candle · orderbook state machine · trailing SL · re-entry · JSON persistence |
| **Coding Style** | Vertical alignment · bc/sc conditions · block comments · flat structure |
| **Fallback** | Raw `dhanhq` access for position conversion · eDIS · exit-all · trade history |

---

## How it works

Skills are loaded progressively — `SKILL.md` is the entry point and routes the agent to specific reference files only when needed. This keeps context lean while giving the agent deep knowledge on demand.

```
Agent receives task
       ↓
Loads SKILL.md  (always)
       ↓
Loads relevant reference file(s)  (on demand)
  e.g. options.md + orders.md for a spread strategy task
       ↓
Writes code in TradeHull style with correct signatures
```

---

## Key rules baked into the skill

- **MARKET orders banned for F&O** — SEBI regulation Apr 1 2026. Skill always generates LIMIT orders for NFO/BFO
- **`get_option_chain()` returns two values** — `atm, chain = tsl.get_option_chain(...)` — skill enforces this
- **Lot size always dynamic** — `tsl.get_lot_size()` never hardcoded — SEBI revises periodically
- **`get_intraday_data()` deprecated** — skill always uses `get_historical_data()`
- **Conditional triggers not used** — TradeHull uses TA-Lib for all signal logic
- **Super orders for intraday · Forever orders for positional** — skill picks the right one

---

## About TradeHull

[TradeHull](https://tradehull.com) is India's algo trading education and tooling platform — building courses, frameworks, and tools for retail traders on the Dhan API.

- Website: [tradehull.com](https://tradehull.com)
- Python library: [pypi.org/project/Dhan-Tradehull](https://pypi.org/project/Dhan-Tradehull/)
- Dhan API docs: [docs.dhanhq.co](https://docs.dhanhq.co)

---

## License

MIT — free to use, modify, and distribute.
