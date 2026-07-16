# Deploying & Running Algos on a Server

Keeping an algo alive on a VPS: detaching the process, finding it again,
restarting it cleanly, surviving reboots, and running several algos at once.

> 🧠 **Run algos on the server whose IP is whitelisted with your broker.**
> Dhan (and most brokers) tie API access to an IP. Code that talks to the
> broker must run from that machine — not your laptop.

---

## 1. Keep it running after you close the terminal

`python app.py` dies with its terminal. Detach it:

```bash
# setsid — fully detaches from the shell session
setsid /path/to/venv/bin/python app.py > app.log 2>&1 < /dev/null &

# alternatives
nohup python app.py > app.log 2>&1 &
tmux new -s algo 'python app.py'     # reattach later: tmux attach -t algo
```

`setsid` survives the terminal, the SSH session, and the chat/IDE that started
it. It does **not** survive a reboot — see §5.

Always launch with the **venv's** python (`venv/bin/python`), not system
`python3`, or your imports and interpreter version will differ from what you
tested.

---

## 2. Find your algo again

PIDs change on every restart — **look it up by port**, which stays constant.

```bash
ss -ltnp | grep ':5001'          # -> users:(("python",pid=518686,fd=5))
pgrep -af "app.py"               # by script name
ps -o pid,etime,rss,cmd -p 518686   # uptime + memory of one process
```

```bash
# everything python you have running, biggest first
ps -eo pid,etime,rss,cmd --sort=-rss | grep python | grep -v grep
```

---

## 3. Restart cleanly — kill by port

```bash
kill -9 $(ss -ltnp | grep ':5001' | grep -o 'pid=[0-9]*' | cut -d= -f2)
sleep 1
setsid /path/to/venv/bin/python app.py > app.log 2>&1 < /dev/null &
```

> 🐛 **The silent-restart trap — costs hours.**
> `pkill -f "some/path/app.py"` only matches if the pattern appears in the
> process's **actual command line**. Launched via `cd dir && python app.py`,
> the cmdline is just `python app.py` — the path is *not* in it, so the pkill
> misses, the old process lives, and the **new one fails to bind the port and
> exits**. The old code keeps serving.
>
> You edit → restart → hard-refresh → *see no change*, and blame the browser
> cache. Symptom: the **served page lacks your edit**.
>
> ```bash
> curl -s http://127.0.0.1:5001/ | grep "something-you-just-added"   # empty = old process
> ss -ltnp | grep ':5001'    # is the PID the one you just started?
> ```
> **Always kill by port, confirm the port is free, then verify the new PID owns it.**

---

## 4. Logs

```bash
tail -f app.log              # follow live
tail -50 app.log             # last 50 lines
```

If an app dies instantly on launch, the reason is in the log — usually an
import error, a bad token, or `Address already in use`.

---

## 5. Survive reboots — systemd

`setsid`/`nohup` die on reboot. For a real deployment use a systemd unit:

```ini
# /etc/systemd/system/algo-scanner.service
[Unit]
Description=Dhan Algo Scanner
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/algos/scanner
ExecStart=/root/algos/scanner/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now algo-scanner
systemctl status algo-scanner
journalctl -u algo-scanner -f     # live logs
```

`Restart=always` also revives the algo if it crashes mid-session.

---

## 6. Running several algos

One **port per app** — 5001, 5002, 5003…

```bash
cd /root/algos/scanner   && setsid venv/bin/python app.py > app.log 2>&1 &   # 5001
cd /root/algos/oi_scalp  && setsid venv/bin/python app.py > app.log 2>&1 &   # 5002
```

**Budgeting (measured, Flask + Tradehull + pandas):**

| Resource | Per app | Implication |
|---|---|---|
| RAM | ~250 MB | a 4 GB box holds ~6–8 apps |
| CPU | scanning is CPU-bound | on 2 cores, only **2–3** should scan at once |

The binding limit is usually **CPU**, not RAM. Idle apps cost almost nothing;
three simultaneous 200-symbol scans will crawl.

> ⚠️ **Each app holds its own Dhan login.** Many parallel logins/instrument
> downloads can hit broker rate limits (see `error-log.md` ERROR-002). For
> several strategies, prefer **one app with multiple strategies inside** over
> many apps each with its own session.

---

## 7. The daily token restart

`access_token` **expires daily**. A long-running app holds the old session in
memory — it will keep failing until restarted.

**Each morning before market open:** paste the fresh token into `config.py`,
then restart (§3). Or avoid the chore entirely — use **`pin_totp`** auth, whose
PIN never expires (`references/auth.md`). That is the right choice for any
scheduled or always-on algo.

> ⚠️ An algo running 20+ hours is almost certainly running on a **dead token**
> and silently failing. Check `etime` in §2 against your last token refresh.

---

## 8. Reaching the UI

Binding a port isn't enough — traffic must reach it. See
`references/flask-ui.md` §6 (proxy vs firewall, and how to tell which is
blocking you).

---

See also: `references/flask-ui.md`, `references/auth.md`,
`references/algo-dev-workflow.md`.
