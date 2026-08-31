"""
Live progress dashboard for the v7 run.

    python3 progress_server.py           then open http://localhost:8765

Reads the log files directly on each request, so it reflects real state with no
writes and no interference with the run. Safe to start and stop at any time.
"""
import json
import re
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root (this script now lives in scripts/)
LOGS = ROOT / "experiments/logs"
BASELINES = ROOT / "experiments/baselines"
RUN_LOG = LOGS / "run_v7.log"

TAG = "38k_v7"
N_QUERIES = 75
PORT = 8765

STEPS = (
    [{"key": m, "kind": "baseline", "label": f"Baselines — {m}"}
     for m in ["gemini", "mistral", "llama3"]]
    + [{"key": f"C{i}", "kind": "condition", "label": f"C{i}"}
       for i in range(1, 13)]
)

COND_INFO = {
    "C1": ("gemini", "—"), "C2": ("gemini", "mistral"), "C3": ("mistral", "—"),
    "C4": ("mistral", "gemini"), "C5": ("gemini", "gemini"), "C6": ("mistral", "mistral"),
    "C7": ("llama3", "—"), "C8": ("llama3", "llama3"), "C9": ("llama3", "gemini"),
    "C10": ("gemini", "llama3"), "C11": ("mistral", "llama3"), "C12": ("llama3", "mistral"),
}


def count_lines(path):
    try:
        with path.open() as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def newest(pattern, directory):
    files = sorted(directory.glob(pattern))
    return files[-1] if files else None


def step_state(step):
    if step["kind"] == "baseline":
        f = newest(f"{step['key']}_{TAG}_*.jsonl", BASELINES)
    else:
        f = newest(f"{step['key']}_{TAG}_*.jsonl", LOGS)
    if not f:
        return {"done": 0, "mtime": None}
    return {"done": min(count_lines(f), N_QUERIES), "mtime": f.stat().st_mtime}


def is_running():
    """True if the runner script is still alive."""
    import subprocess
    try:
        out = subprocess.run(["pgrep", "-f", "run_v7_all_conditions"],
                             capture_output=True, text=True, timeout=3)
        return bool(out.stdout.strip())
    except Exception:
        return False


def current_activity():
    """Last meaningful line from the runner log."""
    try:
        tail = RUN_LOG.read_bytes()[-4000:].decode("utf-8", "replace")
    except Exception:
        return "waiting for log…"
    lines = [l.strip() for l in tail.replace("\r", "\n").split("\n") if l.strip()]
    for line in reversed(lines):
        if re.search(r"\d+%\|", line) or line.startswith(">>>") or "saved" in line.lower():
            return re.sub(r"\s+", " ", line)[:140]
    return lines[-1][:140] if lines else "starting…"


def collect():
    states = []
    total_done = 0
    active = None
    for s in STEPS:
        st = step_state(s)
        pct = st["done"] / N_QUERIES * 100
        complete = st["done"] >= N_QUERIES
        if not complete and st["done"] > 0 and active is None:
            active = s["key"]
        total_done += st["done"]
        gen, disc = COND_INFO.get(s["key"], ("", ""))
        states.append({**s, **st, "pct": pct, "complete": complete,
                       "generator": gen, "discriminator": disc})

    # if nothing partially done, the active step is the first incomplete one
    if active is None:
        for s in states:
            if not s["complete"]:
                active = s["key"]
                break
    for s in states:
        s["active"] = (s["key"] == active)

    overall = total_done / (len(STEPS) * N_QUERIES) * 100
    done_steps = sum(1 for s in states if s["complete"])

    # ETA from observed throughput
    eta = None
    mtimes = [s["mtime"] for s in states if s["mtime"]]
    if mtimes and total_done > 0:
        started = min(mtimes)
        elapsed = time.time() - started
        rate = total_done / elapsed if elapsed > 0 else 0
        remaining = len(STEPS) * N_QUERIES - total_done
        if rate > 0:
            eta = remaining / rate

    return {
        "steps": states, "overall": overall, "done_steps": done_steps,
        "total_steps": len(STEPS), "total_done": total_done,
        "total_queries": len(STEPS) * N_QUERIES,
        "running": is_running(), "activity": current_activity(), "eta": eta,
        "updated": datetime.now().strftime("%H:%M:%S"),
    }


def fmt_eta(seconds):
    if not seconds:
        return "—"
    h, m = divmod(int(seconds // 60), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def render(d):
    if d["running"]:
        status, colour = "RUNNING", "var(--accent)"
    elif d["overall"] >= 99.9:
        status, colour = "COMPLETE", "var(--green)"
    else:
        status, colour = "STOPPED", "var(--red)"

    rows = []
    for s in d["steps"]:
        if s["complete"]:
            cls, mark = "done", "●"
        elif s["active"]:
            cls, mark = "active", "◐"
        else:
            cls, mark = "idle", "○"

        sub = ""
        if s["kind"] == "condition":
            disc = s["discriminator"]
            sub = (f"gen {s['generator']}" if disc == "—"
                   else f"gen {s['generator']} · disc {disc}")

        rows.append(f"""
        <div class="row {cls}">
          <div class="mark">{mark}</div>
          <div class="label"><span class="name">{s['label']}</span>
            <span class="sub">{sub}</span></div>
          <div class="bar"><div class="fill" style="width:{s['pct']:.1f}%"></div></div>
          <div class="count">{s['done']}/{N_QUERIES}</div>
        </div>""")

    return f"""<!doctype html><html><head>
<meta charset="utf-8"><title>v7 run — {d['overall']:.0f}%</title>
<meta http-equiv="refresh" content="5">
<style>
  :root {{
    --bg:#0D1117; --surface:#161B22; --border:#2D333B; --text:#CDD9E5;
    --muted:#768390; --accent:#539BF5; --green:#57AB5A; --red:#E5534B;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#F6F8FA; --surface:#FFF; --border:#D0D7DE; --text:#1F2328;
             --muted:#57606A; --accent:#0969DA; --green:#1A7F37; --red:#CF222E; }}
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); min-height:100vh; padding:2rem 1.5rem;
    font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif; }}
  .wrap {{ max-width:820px; margin:0 auto; }}
  .head {{ display:flex; align-items:baseline; gap:.75rem; flex-wrap:wrap; margin-bottom:.35rem; }}
  h1 {{ font:600 1.15rem/1.2 inherit; }}
  .pill {{ font:700 .6rem/1 ui-monospace,monospace; letter-spacing:.1em; padding:.3rem .55rem;
    border-radius:99px; color:{colour}; border:1px solid {colour};
    background:color-mix(in srgb,{colour} 12%,transparent); }}
  .meta {{ color:var(--muted); font-size:.78rem; margin-bottom:1.5rem; }}
  .big {{ background:var(--surface); border:1px solid var(--border); border-radius:10px;
    padding:1.25rem 1.4rem; margin-bottom:1.25rem; }}
  .bignum {{ font:700 2.6rem/1 ui-monospace,monospace; font-variant-numeric:tabular-nums;
    color:{colour}; }}
  .bigbar {{ height:9px; background:var(--bg); border-radius:99px; overflow:hidden;
    margin:.85rem 0 .6rem; border:1px solid var(--border); }}
  .bigfill {{ height:100%; background:{colour}; border-radius:99px; transition:width .4s; }}
  .stats {{ display:flex; gap:1.75rem; flex-wrap:wrap; font-size:.8rem; color:var(--muted); }}
  .stats b {{ color:var(--text); font-family:ui-monospace,monospace; }}
  .activity {{ background:var(--surface); border:1px solid var(--border);
    border-left:2.5px solid {colour}; border-radius:8px; padding:.7rem .9rem;
    font:.72rem/1.45 ui-monospace,monospace; color:var(--muted);
    margin-bottom:1.5rem; word-break:break-all; }}
  .row {{ display:grid; grid-template-columns:1.2rem 1fr 150px 62px; gap:.75rem;
    align-items:center; padding:.5rem .3rem; border-bottom:1px solid var(--border); }}
  .row:last-child {{ border-bottom:none; }}
  .mark {{ text-align:center; font-size:.8rem; }}
  .row.done .mark {{ color:var(--green); }}
  .row.active .mark {{ color:var(--accent); }}
  .row.idle {{ opacity:.45; }}
  .idle .mark {{ color:var(--muted); }}
  .name {{ font-weight:600; font-size:.82rem; }}
  .sub {{ color:var(--muted); font-size:.7rem; margin-left:.5rem; }}
  .bar {{ height:5px; background:var(--bg); border:1px solid var(--border);
    border-radius:99px; overflow:hidden; }}
  .fill {{ height:100%; border-radius:99px; background:var(--muted); transition:width .4s; }}
  .done .fill {{ background:var(--green); }}
  .active .fill {{ background:var(--accent); }}
  .count {{ text-align:right; font:.72rem ui-monospace,monospace;
    font-variant-numeric:tabular-nums; color:var(--muted); }}
  @media (max-width:600px) {{
    .row {{ grid-template-columns:1.2rem 1fr 56px; }}
    .bar {{ display:none; }}
  }}
</style></head><body><div class="wrap">
  <div class="head"><h1>v7 deterministic run</h1><span class="pill">{status}</span></div>
  <div class="meta">12 conditions · temperature 0 · 75 queries each</div>

  <div class="big">
    <div class="bignum">{d['overall']:.1f}%</div>
    <div class="bigbar"><div class="bigfill" style="width:{d['overall']:.2f}%"></div></div>
    <div class="stats">
      <span>steps <b>{d['done_steps']}/{d['total_steps']}</b></span>
      <span>queries <b>{d['total_done']}/{d['total_queries']}</b></span>
      <span>eta <b>{fmt_eta(d['eta'])}</b></span>
      <span>updated <b>{d['updated']}</b></span>
    </div>
  </div>

  <div class="activity">{d['activity']}</div>
  {''.join(rows)}
</div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = collect()
        if self.path == "/status.json":
            body = json.dumps(data, indent=2).encode()
            ctype = "application/json"
        else:
            body = render(data).encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    print(f"Progress dashboard → http://localhost:{PORT}   (ctrl-c to stop)")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
