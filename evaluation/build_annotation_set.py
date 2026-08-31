"""
Build a blind annotation set for validating the chunk-removal audit.

The thesis rests on this inference: removing a cited chunk left the answer largely
unchanged, therefore the model never actually needed that chunk. That has never been
checked against human judgment. This script builds the material to check it.

Sampling is stratified across similarity bands, deliberately over-weighting the region
either side of the 0.85 threshold, since that is where the measure is most likely to be
wrong and where nearly half of all real verdicts fall.

Verdicts and similarity scores are stripped from the output. The annotator sees only the
question, the chunk under test, the original answer, the answer after removal, and the
other retrieved chunks.

    python evaluation/build_annotation_set.py --n 30
    open experiments/results/validation/annotate.html
"""
import argparse
import glob
import hashlib
import html
import json
import random
from pathlib import Path

LOG_DIR = Path("experiments/logs")
OUT_DIR = Path("experiments/results/validation")

# Over-sample either side of the threshold: that is where the measure is fragile.
BANDS = [
    ("far_below", 0.00, 0.70, 0.15),
    ("below", 0.70, 0.85, 0.30),
    ("above", 0.85, 0.92, 0.35),
    ("far_above", 0.92, 1.01, 0.20),
]


def collect(tag):
    """Every tested (chunk, removal) pair across all conditions."""
    items = []
    for path in sorted(LOG_DIR.glob(f"C*_{tag}_*.jsonl")):
        cond = path.name.split("_")[0]
        for line in path.open():
            r = json.loads(line)
            audit = r.get("audit_before") or {}
            chunks = r.get("chunks") or []
            answer = r.get("answer") or r.get("original_answer") or ""
            verdicts = {v["cited_index"]: v["verdict"] for v in audit.get("results", [])}

            for rnd in audit.get("rounds", []):
                removed = rnd.get("removed_set") or []
                if not removed:
                    continue
                # The chunk under test is the one added this round.
                target = removed[-1]
                chunk = next((c for c in chunks if c.get("index") == target), None)
                if not chunk or rnd.get("similarity") is None:
                    continue
                items.append({
                    "condition": cond,
                    "query_id": r["query_id"],
                    "query_type": r.get("query_type"),
                    "query": r.get("query", ""),
                    "target_index": target,
                    "target_chunk": chunk,
                    "other_chunks": [c for c in chunks if c.get("index") != target],
                    "original_answer": answer,
                    "removed_answer": rnd.get("new_answer", ""),
                    "removed_set": removed,
                    # withheld from the annotator, kept for scoring
                    "_similarity": rnd["similarity"],
                    "_verdict": verdicts.get(target, "unknown"),
                })
    return items


def dedupe(items):
    """One row per (query, chunk). Identical answers recur across conditions."""
    seen, out = set(), []
    for it in items:
        key = (it["query_id"], it["target_index"],
               hashlib.md5(it["removed_answer"].encode()).hexdigest()[:8])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def stratify(items, n, seed=42):
    rng = random.Random(seed)
    picked = []
    for name, lo, hi, share in BANDS:
        pool = [i for i in items if lo <= i["_similarity"] < hi]
        want = max(1, round(n * share))
        rng.shuffle(pool)
        for it in pool[:want]:
            it["_band"] = name
        picked += pool[:want]
    rng.shuffle(picked)          # so band order leaks nothing
    return picked[:n]


def other_chunk_overlap(item):
    """Crude lexical overlap between the target chunk and the best other chunk.

    The main way the audit could be wrong: another retrieved chunk carried
    near-equivalent information, so the answer stayed similar even though the
    citation was genuine. Precomputed here so disagreement analysis can test it.
    Content words only, cheap by design; it is a flag, not a measurement.
    """
    def words(t):
        return {w for w in t.lower().split() if len(w) > 4}
    tgt = words(item["target_chunk"].get("text", ""))
    if not tgt:
        return 0.0
    best = 0.0
    for c in item["other_chunks"]:
        o = words(c.get("text", ""))
        if o:
            best = max(best, len(tgt & o) / len(tgt))
    return round(best, 3)


def render(items):
    payload = []
    for i, it in enumerate(items):
        payload.append({
            "n": i + 1,
            # Condition included: the same (query, chunk) pair recurs across
            # conditions with different answers, so it is a distinct item and
            # must not collide in localStorage or in scoring.
            "id": f"{it['query_id']}_c{it['target_index']}_{it['condition']}",
            "query": it["query"],
            "type": it["query_type"],
            "chunk": it["target_chunk"].get("text", ""),
            "chunk_name": it["target_chunk"].get("name", ""),
            "index": it["target_index"],
            "original": it["original_answer"],
            "removed": it["removed_answer"],
            "others": [{"i": c.get("index"), "name": c.get("name", ""),
                        "text": c.get("text", "")} for c in it["other_chunks"]],
        })

    data = json.dumps(payload).replace("</", "<\\/")

    return """<!doctype html><html><head><meta charset="utf-8">
<title>Audit validation</title>
<style>
 :root{--bg:#fbfaf7;--card:#fff;--ink:#1d1f22;--mut:#6b7178;--line:#e2e0da;
  --accent:#3b6ea5;--warm:#b4622d;--ok:#3f7d4e;--pad:2rem}
 @media(prefers-color-scheme:dark){:root{--bg:#16181c;--card:#1e2126;--ink:#e4e6e9;
  --mut:#9aa1a9;--line:#2e3238;--accent:#7aa8d8;--warm:#d98a52;--ok:#6aab78}}
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--ink);font:16px/1.6 Charter,Georgia,serif;
  padding:var(--pad) 1rem 6rem}
 .wrap{max-width:820px;margin:0 auto}
 header{display:flex;justify-content:space-between;align-items:baseline;
  border-bottom:1px solid var(--line);padding-bottom:.75rem;margin-bottom:1.5rem}
 h1{font-size:1.05rem;font-weight:600;letter-spacing:.01em}
 .count{font:600 .85rem ui-monospace,monospace;color:var(--mut)}
 .bar{height:3px;background:var(--line);border-radius:9px;margin-bottom:2rem}
 .fill{height:100%;background:var(--accent);border-radius:9px;transition:width .3s}
 .q{font-size:1.15rem;line-height:1.45;margin-bottom:.35rem}
 .meta{font:.72rem ui-monospace,monospace;color:var(--mut);text-transform:uppercase;
  letter-spacing:.08em;margin-bottom:1.5rem}
 .card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:1.1rem 1.3rem;margin-bottom:1rem}
 .lbl{font:600 .68rem ui-monospace,monospace;text-transform:uppercase;
  letter-spacing:.1em;color:var(--mut);margin-bottom:.6rem}
 .card.target{border-color:var(--warm);border-left:3px solid var(--warm)}
 .card.target .lbl{color:var(--warm)}
 .txt{font-size:.94rem;line-height:1.65}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
 @media(max-width:700px){.two{grid-template-columns:1fr}}
 details{margin-bottom:1.5rem}
 summary{cursor:pointer;font:.8rem ui-monospace,monospace;color:var(--accent);
  padding:.5rem 0}
 .oth{border-left:2px solid var(--line);padding:.5rem 0 .5rem .9rem;margin:.6rem 0;
  font-size:.85rem}
 .oth b{font-size:.75rem;color:var(--mut);font-family:ui-monospace,monospace}
 .ask{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:1.2rem 1.3rem;margin-top:1.5rem}
 .ask p{font-size:1.02rem;margin-bottom:1rem}
 .btns{display:flex;gap:.6rem;flex-wrap:wrap}
 button{font:inherit;font-size:.9rem;padding:.6rem 1.1rem;border-radius:7px;
  border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
 button:hover{border-color:var(--accent)}
 button.y{border-color:var(--ok);color:var(--ok)}
 button.n{border-color:var(--warm);color:var(--warm)}
 kbd{font:.7rem ui-monospace,monospace;opacity:.55;margin-left:.3rem}
 textarea{width:100%;margin-top:.9rem;padding:.6rem;border:1px solid var(--line);
  border-radius:7px;background:var(--bg);color:var(--ink);font:inherit;
  font-size:.85rem;resize:vertical;min-height:2.6rem}
 .nav{position:fixed;bottom:0;left:0;right:0;background:var(--card);
  border-top:1px solid var(--line);padding:.7rem 1rem;display:flex;
  justify-content:center;gap:.6rem;align-items:center}
 .nav button{font-size:.82rem;padding:.4rem .9rem}
 .done{text-align:center;padding:3rem 1rem}
 .done h2{font-size:1.3rem;margin-bottom:.8rem}
 .done p{color:var(--mut);margin-bottom:1.5rem}
</style></head><body><div class="wrap">
<header><h1>Chunk removal validation</h1><span class="count" id="c"></span></header>
<div class="bar"><div class="fill" id="f"></div></div>
<div id="main"></div>
</div>
<div class="nav">
 <button onclick="go(-1)">Back</button>
 <button onclick="go(1)">Skip</button>
 <button onclick="dl()">Export CSV</button>
</div>
<script>
const DATA = """ + data + """;
const KEY = 'audit_validation_v1';
let ans = JSON.parse(localStorage.getItem(KEY) || '{}');
let i = 0;
while (i < DATA.length && ans[DATA[i].id]) i++;

const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function draw(){
  if (i >= DATA.length) return finish();
  const d = DATA[i];
  const prev = ans[d.id] || {};
  document.getElementById('c').textContent = (i+1) + ' / ' + DATA.length;
  document.getElementById('f').style.width = ((i)/DATA.length*100) + '%';
  document.getElementById('main').innerHTML = `
    <div class="q">${esc(d.query)}</div>
    <div class="meta">item ${d.n} &middot; type ${d.type||'?'} &middot; source [${d.index}]</div>

    <div class="card target">
      <div class="lbl">The source under test &mdash; [${d.index}] ${esc(d.chunk_name)}</div>
      <div class="txt">${esc(d.chunk)}</div>
    </div>

    <div class="two">
      <div class="card">
        <div class="lbl">Answer with this source present</div>
        <div class="txt">${esc(d.original)}</div>
      </div>
      <div class="card">
        <div class="lbl">Answer after removing it</div>
        <div class="txt">${esc(d.removed)}</div>
      </div>
    </div>

    <details><summary>Show the other retrieved sources (${d.others.length})</summary>
      ${d.others.map(o => `<div class="oth"><b>[${o.i}] ${esc(o.name)}</b><br>${esc(o.text)}</div>`).join('')}
    </details>

    <div class="ask">
      <p>Did the model actually need source [${d.index}] to write its original answer?</p>
      <div class="btns">
        <button class="y" onclick="rec('needed')">Yes, it was needed<kbd>1</kbd></button>
        <button class="n" onclick="rec('not_needed')">No, not needed<kbd>2</kbd></button>
        <button onclick="rec('unclear')">Unclear<kbd>3</kbd></button>
      </div>
      <textarea id="note" placeholder="Optional note, especially useful when unclear">${esc(prev.note||'')}</textarea>
    </div>`;
}

function rec(v){
  const d = DATA[i];
  ans[d.id] = {judgment: v, note: document.getElementById('note').value, n: d.n};
  localStorage.setItem(KEY, JSON.stringify(ans));
  i++; draw();
}
function go(d){
  const n = document.getElementById('note');
  if (n && ans[DATA[i]?.id]) ans[DATA[i].id].note = n.value;
  i = Math.max(0, Math.min(DATA.length, i + d)); draw();
}
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA') return;
  if (e.key === '1') rec('needed');
  if (e.key === '2') rec('not_needed');
  if (e.key === '3') rec('unclear');
});
function finish(){
  document.getElementById('f').style.width = '100%';
  document.getElementById('main').innerHTML = `<div class="done">
    <h2>All ${DATA.length} done</h2>
    <p>Export the CSV and save it to<br>
    <code>experiments/results/validation/annotations.csv</code></p>
    <button onclick="dl()">Export CSV</button>
    <button onclick="if(confirm('Erase all answers?')){localStorage.removeItem(KEY);location.reload()}">Reset</button>
  </div>`;
}
function dl(){
  let csv = 'item_id,judgment,note\\n';
  for (const [k,v] of Object.entries(ans))
    csv += `${k},${v.judgment},"${(v.note||'').replace(/"/g,'""')}"\\n`;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  a.download = 'annotations.csv'; a.click();
}
draw();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="38k_v7")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    items = dedupe(collect(args.tag))
    if not items:
        print(f"No audit rounds found for tag '{args.tag}'")
        return

    sample = stratify(items, args.n, args.seed)
    for it in sample:
        it["_other_chunk_overlap"] = other_chunk_overlap(it)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "annotate.html").write_text(render(sample))

    # Answer key. Do not open before annotating.
    key = [{
        "item_id": f"{it['query_id']}_c{it['target_index']}_{it['condition']}",
        "query_id": it["query_id"], "condition": it["condition"],
        "query_type": it["query_type"], "target_index": it["target_index"],
        "similarity": it["_similarity"], "audit_verdict": it["_verdict"],
        "band": it.get("_band"), "other_chunk_overlap": it["_other_chunk_overlap"],
    } for it in sample]
    (OUT_DIR / "answer_key.json").write_text(json.dumps(key, indent=2))

    print(f"{len(items)} unique tested pairs available, sampled {len(sample)}")
    print("\nby band:")
    for name, lo, hi, _ in BANDS:
        n = sum(1 for it in sample if it.get("_band") == name)
        print(f"  {name:<10} {lo:.2f}-{hi:.2f}  {n}")
    pr = sum(1 for it in sample if it["_verdict"] == "post_rationalised")
    print(f"\nhidden verdicts: {pr} post-rationalised, {len(sample)-pr} genuine")
    print(f"\n  open {OUT_DIR}/annotate.html")
    print(f"  answer key at {OUT_DIR}/answer_key.json (do not open first)")


if __name__ == "__main__":
    main()
