# Flask Web UI on Top of a Dhan Algo

How to put a browser dashboard on a scanner or algo — a "Run Scan" button,
a live positions table, a P&L monitor. Minimal Flask, no framework churn.

> ✅ Keep the **algo logic in its own module** (e.g. `scanner.py`) and let
> Flask (`app.py`) just call it and return JSON. Never mix broker calls into
> route handlers directly — it keeps the algo testable from the CLI too.

---

## 1. Requirements

```bash
pip install flask
```

---

## 2. Project layout

```
my_algo/
├── config.py            # client_code + token_id (keep private)
├── scanner.py           # algo logic: run_scan() -> list[dict]
├── app.py               # Flask app: serves UI + /scan JSON endpoint
└── templates/
    └── index.html       # the page + fetch() JavaScript
```

---

## 3. app.py

```python
from flask import Flask, render_template, jsonify
from scanner import run_scan          # your algo module

app = Flask(__name__)


@app.after_request
def no_cache(resp):
    # stop the browser serving stale HTML/JS between edits
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan")
def scan():
    results = run_scan()
    return jsonify({"count": len(results), "results": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
```

`host="0.0.0.0"` binds all interfaces so the app is reachable from outside
the server (subject to the firewall — see §6).

---

## 4. templates/index.html (the fetch bit)

```html
<button id="btn" onclick="runScan()">Run Scan</button>
<div id="status"></div>
<table id="tbl"><tbody id="rows"></tbody></table>

<script>
async function runScan() {
  // IMPORTANT: relative path so it works behind a reverse proxy (see §5)
  const base = window.location.pathname.replace(/\/?$/, '/');
  const res  = await fetch(base + 'scan');
  const data = await res.json();

  document.getElementById('status').textContent =
    data.count ? `${data.count} signal(s)` : 'no signals right now';

  const rows = document.getElementById('rows');
  rows.innerHTML = '';
  data.results.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.symbol}</td><td>${r.signal}</td><td>${r.ltp}</td>`;
    rows.appendChild(tr);
  });
}
</script>
```

---

## 5. ⚠️ The reverse-proxy path gotcha (most common bug)

When the app is opened **directly** (`http://server:5001/`), an absolute
`fetch('/scan')` works fine.

But when it is served through a **reverse proxy** — VS Code / code-server
"Forward a Port", nginx sub-path, Jupyter proxy — the page lives under a
prefix like `http://host/proxy/5001/`. An absolute `fetch('/scan')` then
requests `http://host/scan`, which escapes the proxy and returns the proxy's
own **"Not found"** HTML. In the browser this shows up as:

```
Error: Unexpected token 'N', "Not found." is not valid JSON
```

**Fix — always build the URL relative to the current page:**
```javascript
const base = window.location.pathname.replace(/\/?$/, '/');
const res  = await fetch(base + 'scan');   // /proxy/5001/scan  ✅
```

This works both direct and behind any proxy prefix.

---

## 6. Reaching the UI from your browser

The app binds a port on the server; you still have to reach it. Three ways,
easiest first:

| Method | When to use |
|--------|-------------|
| **code-server / VS Code PORTS tab → Forward a Port** | Best. Tunnels the port through the existing secure connection — works even if the port is firewalled. Gives a `.../proxy/<port>/` URL (see §5). |
| **Run on an already-open port** | If a port is already whitelisted in the cloud firewall, bind to it directly: `http://<server-ip>:<port>`. |
| **Open the firewall** | `ufw allow 5001` **and** open the port in the cloud firewall (e.g. DigitalOcean). Then `http://<server-ip>:5001` works directly. |

**Diagnosing "can't connect":**
- `curl http://127.0.0.1:5001` **on the server** works, but the browser
  times out (~20s, not instant refuse) → **firewall** is blocking the port.
- Even local `curl` fails → the **app isn't running** (or crashed on import;
  check the log).

> 🧠 Note: a headless server has no desktop browser — *your laptop's* browser
> is the client. You only need to route the port to it (proxy or firewall).

---

## 7. Running it as a long-lived process

`python app.py` dies when the terminal closes. To keep it up:

```bash
# quick + dirty
nohup python app.py > app.log 2>&1 &

# better: a systemd service, or
tmux new -s algo 'python app.py'
```

**Port already in use?** Find and free it:
```bash
ss -ltnp | grep ':5001'      # shows the PID holding the port
kill -9 <pid>
```
A silent "restart didn't take effect" is almost always an **old process still
bound to the port** — the new one fails to bind and the old page keeps
serving. Kill by PID, confirm the port is free, then relaunch.

See also: `references/algo-scanner.md`, `examples/nifty50_scanner_algo.py`.
