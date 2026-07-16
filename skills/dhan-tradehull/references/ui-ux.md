# UI/UX for Trading Dashboards

How to make an algo dashboard people can actually trade from. This is not
general design advice — these are the rules that matter when the screen is
showing **money and live signals**.

Stack that gets you modern-looking fast: **Tailwind CSS via CDN** + vanilla JS.
One `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`, no build
step. (The CDN loads from the *user's* browser, so it works even when the app
is served through a server-side proxy.)

---

## The one rule: show the work, not just the answer

A scanner that prints only signals looks **broken** when there are no signals.
The user cannot tell "nothing qualified" from "your code is broken" — and will
assume the second.

**Always render every row it scanned, with the values behind the verdict:**

| Symbol | LTP | EMA 20 | EMA 50 | EMA Condition | RSI | RSI Condition | Signal |
|---|---|---|---|---|---|---|---|
| INDUSINDBK | 1014.25 | 1011.95 | 1011.85 | Bullish cross | 64.2 | RSI > 60 | **BULLISH** |
| ADANIENT | 3153.9 | 3154.0 | 3155.47 | EMA20 < EMA50 | 49.56 | RSI 40-60 | — |

Now "no signals" is *obviously* a real answer: the user can see 200 stocks were
checked and why each one failed. **Every verdict should be auditable from the
row itself** — show the inputs (EMA20, EMA50, RSI) *and* the conditions they
produced, not just the conclusion.

> 🧠 Trust is the product. A trader who cannot see *why* will not act on the
> signal — and will not trust the next one either.

---

## Progress: never a silent wait

Scanning 200 symbols takes minutes. A spinner for 3 minutes is indistinguishable
from a hang.

- **Stream results** — render each row as it arrives (see `flask-ui.md` §4b)
- **Name the current item** — "Scanning RELIANCE **47 / 208**"
- **Progress bar** — position in the run at a glance
- **Live counters** — tiles tick up as it goes, so the screen is never static

The perceived speed matters more than the actual speed. One-by-one is *slower*
in wall-clock and *feels* far faster.

---

## Always give an escape hatch

Any long-running or money-spending action needs a **Stop**.

```javascript
let ABORT = false;
function stopScan() { ABORT = true; }
// in the loop:  if (ABORT) break;
```

Show it **only while running**, and make it visually distinct (red) from the
primary action (blue). For an order-firing scanner, Stop is a **kill switch** —
be explicit in the UI about what it does and doesn't do: it stops *new* orders;
it does not cancel orders already at the exchange.

---

## Make real money look dangerous

If the dashboard can place live orders, say so — loudly, always visible:

```html
<div class="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 flex items-center gap-3">
  <span class="px-2 py-0.5 rounded-md bg-rose-500 text-white text-xs font-bold">LIVE</span>
  <span class="text-rose-200">Real money — a signal auto-fires a <b>1</b> qty
    <b>MIS</b> order. Capped at <b>3</b> per run; one entry per stock.</span>
</div>
```

State the **exact** terms: quantity, product, cap, dedupe rule. "Live trading
enabled" is not enough — the user must be able to predict what a click costs.

Drive the banner from the **server's actual config**, never a hardcoded string:

```python
@app.route("/symbols")
def symbols():
    return jsonify({"symbols": watchlist,
                    "orders_enabled": scanner.ORDERS_ENABLED,
                    "max_orders": scanner.MAX_ORDERS,
                    "quantity": scanner.QUANTITY})
```

A banner that says "3 orders max" while the code says 5 is worse than no banner.

---

## Show what the order actually did

A fired signal must show its receipt, inline on the row:

```
FIRED  BUY @ 1016.30
id 221260716565606
```

And when it *doesn't* fire, say why — `already in trade`, `max 3 orders
reached`, `sell skipped (CNC = no short)`, `dry-run`. A blank cell reads as a
bug; a reason reads as a decision.

---

## Layout

**Summary tiles first** — Scanned · Bullish · Bearish · Neutral · No-data ·
Orders fired. The whole run's state in one glance, before any scrolling.

**Then filters + search** — All / Bullish / Bearish / Neutral tabs, and a
symbol search. 200 rows is unusable without them.

**Then the table.** Sort **signals to the top** once the scan completes (not
during — rows jumping mid-scan is disorienting).

```javascript
const rank = r => r.status === 'ERROR' ? 3
               : (r.signal === 'NEUTRAL' ? 2 : (r.signal === 'BULLISH' ? 0 : 1));
list.sort((a, b) => rank(a) - rank(b));
```

---

## Numbers

- **`tabular-nums`** on every price/indicator column — otherwise digits jitter
  and columns fail to align down the page.
- **Right-align** numbers, **left-align** text. Decimals should stack.
- **Round in the backend**, not the template — `round(float(x), 2)`.
- Show the **timestamp of the data** ("Last scan: 16 Jul 2026 15:10:39").
  Stale numbers with no timestamp are dangerous.

---

## Colour

| Meaning | Colour | Tailwind |
|---|---|---|
| Bullish / long / buy | green | `text-emerald-400`, `bg-emerald-500/15` |
| Bearish / short / sell | red | `text-rose-400`, `bg-rose-500/15` |
| Neutral / no signal | grey | `text-slate-400`, `bg-slate-700/40` |
| Warning / no data | amber | `text-amber-400` |
| Live money / danger | red border + fill | `border-rose-500/40 bg-rose-500/10` |

Dark theme (`bg-slate-950`) is the norm for trading screens — long sessions,
and coloured signals pop against it.

**Never encode meaning in colour alone.** Ship the word too — `BULLISH` next to
the green, `EMA20 < EMA50` next to the red. Colour-blind users, screenshots,
and printouts all lose colour; the row must still be readable.

---

## Empty and error states

Write them as sentences, not blanks:

- Before first run → "Click **Run Scan** to fetch 5-minute data for all
  208 stocks."
- Zero signals → "Scan complete — no signals right now." **Not** an error.
- Filter matches nothing → "No stocks match this filter."
- Symbol had no data → render the row with a `SKIP` badge and the reason —
  never drop it silently. A stock vanishing from the list looks like a bug
  (and hides real problems like symbol renames).

---

## Dev-loop hygiene

Browsers cache HTML/JS aggressively. During development you *will* stare at a
stale page and debug code that isn't running:

```python
@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp
```

> ⚠️ Before blaming the browser cache, confirm the **server** is serving your
> edit — `curl -s http://127.0.0.1:5001/ | grep "your-new-code"`. An old
> process still bound to the port is the more common culprit
> (`references/deployment.md` §3).

---

## Checklist

- [ ] Every scanned row rendered, with the values behind the verdict
- [ ] Live progress: current symbol, count, bar, ticking counters
- [ ] Stop button while running
- [ ] LIVE banner if real orders — exact qty/product/cap, driven by server config
- [ ] Order receipt (or reason) inline on the row
- [ ] Summary tiles → filters/search → table
- [ ] Signals sorted to top after the run
- [ ] `tabular-nums`, right-aligned numbers, data timestamp
- [ ] Colour + word for every state
- [ ] Written empty/error states
- [ ] `Cache-Control: no-store`

See also: `references/flask-ui.md` (routes, proxy paths, progressive scanning),
`references/deployment.md`, `references/algo-scanner.md`.
