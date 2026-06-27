# TradeHull Agent Skills

Agent skills for Indian algo trading with the [Dhan-Tradehull](https://pypi.org/project/Dhan-Tradehull/) library.

Works with Claude Code, Cursor, Codex, and any agent that supports the [SKILL.md standard](https://agentskills.io).

---

## Available Skills

| Skill | Description |
|-------|-------------|
| [`dhan-tradehull`](./skills/dhan-tradehull/) | Deep knowledge of the Dhan-Tradehull v3.3.1 Python wrapper — order placement, market data, option chain, strike selection, portfolio, live algos, and TradeHull coding style |

---

## Install

### Claude Code
```bash
npx skills add tradehull/tradehull-skills --skill dhan-tradehull
```

### Cursor / Windsurf / Codex
```bash
npx skills add tradehull/tradehull-skills --skill dhan-tradehull --agent cursor
```

### Manual
Clone this repo and copy `skills/dhan-tradehull/` into your project:
```bash
# Project-level (recommended)
git clone https://github.com/tradehull/tradehull-skills.git
cp -r tradehull-skills/skills/dhan-tradehull .cursor/skills/
```

---

## What's inside `dhan-tradehull`

```
skills/dhan-tradehull/
├── SKILL.md                        ← entry point, quick reference, routing table
├── references/
│   ├── coding-style.md             ← TradeHull coding style — read before writing any code
│   ├── auth.md                     ← login modes, token validity
│   ├── market-data.md              ← LTP, OHLC, quote, historical data
│   ├── options.md                  ← option chain, strike selection, greeks
│   ├── orders.md                   ← order placement, SEBI rules, super/forever orders
│   ├── portfolio.md                ← holdings, positions, orderbook, P&L
│   ├── utilities.md                ← lot size, margin, Telegram, kill switch
│   ├── instruments.md              ← 225k-row instrument file schema
│   ├── common-patterns.md          ← real code patterns from student sessions
│   ├── answer-patterns.md          ← common mistakes, FAQ
│   ├── algo-intraday-options.md    ← intraday algo anatomy (Supertrend + S/R)
│   ├── algo-positional-spread.md   ← positional spread algo anatomy (delta-based)
│   ├── dhanhq-raw.md               ← raw dhanhq fallback (position convert, eDIS, etc.)
│   └── error-log.md                ← known errors + SEBI regulations
└── examples/
    ├── intraday_options_algo.py    ← real production intraday algo
    └── positional_spread_algo.py  ← real production positional algo
```

---

## Requirements

```bash
pip install dhanhq==2.2.0
pip install Dhan-Tradehull==3.3.1
```

---

## About TradeHull

[TradeHull](https://tradehull.com) is India's algo trading education and tooling platform. We build courses, tools, and frameworks for retail traders using the Dhan API.

- Website: [tradehull.com](https://tradehull.com)
- Skills docs: [tradehull.com/skills](https://tradehull.com/skills)
- Python library: [pypi.org/project/Dhan-Tradehull](https://pypi.org/project/Dhan-Tradehull/)

---

## License

MIT — free to use, modify, and distribute.
