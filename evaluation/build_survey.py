"""
Build the distributable survey for multiple annotators.

Same items, same order, same seed as build_annotation_set.py, so the answer key
already on disk stays valid and every annotator judges an identical set. That is
required: inter-annotator agreement is undefined if people see different items.

The difference is the interface. annotate.html was written for one expert reader
who already knows the study. This is written for ten people who do not, so it
carries its own instructions, two practice items with feedback, plain language
throughout, and a word-level diff between the two answers.

    python evaluation/build_survey.py
    # send experiments/results/validation/survey.html to each annotator

Each annotator opens the file, works through it, and exports one CSV carrying
their name. Collect the CSVs into experiments/results/validation/annotations/
and run score_annotations.py.
"""
import argparse
import json
import random
import re
from pathlib import Path

from build_annotation_set import (
    BANDS, OUT_DIR, collect, dedupe, other_chunk_overlap, stratify,
)

# Verbs that mark the start of the human-written prose in a company profile.
# Everything before the first of these is scraped metadata: founding year,
# headcount, city list, category tags. It is noise for this judgment.
PROSE_MARKERS = (
    " is a ", " is an ", " is the ", " provides ", " develops ", " offers ",
    " builds ", " designs ", " operates ", " produces ", " enables ",
)


def split_profile(text, name=""):
    """Separate a company profile into scraped metadata and human prose.

    Conservative: if no prose marker is found the whole text is returned as
    prose and nothing is hidden. Better to show too much than to hide the
    sentence the judgment turns on.
    """
    lowered = text.lower()
    cut = min((lowered.find(m) for m in PROSE_MARKERS if m in lowered), default=-1)
    if cut < 0:
        return "", text
    # Rewind to the start of that sentence.
    start = text.rfind(". ", 0, cut)
    if start < 0:
        return "", text
    meta, prose = text[:start + 1].strip(), text[start + 2:].strip()
    # The profile repeats the company name first; it is already the heading.
    if name and meta.startswith(name + "."):
        meta = meta[len(name) + 1:].strip()
    return meta, prose


def paragraphs(prose):
    """Break the profile into the separate descriptions it was built from.

    These records concatenate two or three scraped description fields, leaving a
    ".." at each join. Splitting there is presentation only — not one word is
    added, removed or reordered. The annotator must judge the text the model
    actually saw, so nothing here may paraphrase it; a 265-word wall simply
    becomes three readable paragraphs.
    """
    parts = [p.strip(" .") for p in re.split(r"\.\.+\s*", prose)]
    return [p + "." for p in parts if p]


# Two worked examples, shown before the real items. Invented, not drawn from the
# corpus, so they leak nothing. One is clearly needed, one clearly is not; the
# second also teaches that citation numbers are renumbered after removal.
PRACTICE = [
    {
        "n": "P1",
        "id": "__practice_1",
        "query": "Which Berlin startup manufactures solar roof tiles that replace "
                 "conventional roofing?",
        "chunk_name": "Helios Dach GmbH",
        "chunk_meta": "Founded in 2019. Company size: 11-50. Startup. Germany. Berlin.",
        "chunk_prose": "Helios Dach GmbH manufactures integrated photovoltaic roof "
                       "tiles that replace conventional roofing material rather than "
                       "mounting on top of it. Each tile generates power while forming "
                       "part of the weatherproof layer.",
        "index": 1,
        "original": "Helios Dach GmbH, based in Berlin, manufactures integrated "
                    "photovoltaic roof tiles that replace conventional roofing "
                    "material rather than being mounted on top of it. [1]",
        "removed": "Based on the provided sources, I cannot identify a Berlin startup "
                   "that manufactures solar roof tiles.",
        "others": [],
        "answer": "needed",
        # pick task: one option plainly matches
        "answer_pick": 1,
        "options": [
            {"i": 1, "name": "Helios Dach GmbH",
             "paras": ["Helios Dach GmbH manufactures integrated photovoltaic roof "
                       "tiles that replace conventional roofing material rather than "
                       "mounting on top of it."]},
            {"i": 2, "name": "Nordwind Analytics GmbH",
             "paras": ["Nordwind Analytics GmbH builds dashboard and reporting "
                       "software for logistics fleet operators."]},
            {"i": 3, "name": "Backwerk Robotics",
             "paras": ["Backwerk Robotics automates dough handling and oven loading "
                       "for industrial bakeries."]},
            {"i": 4, "name": "Alpine Zell GmbH",
             "paras": ["Alpine Zell GmbH operates a battery recycling plant "
                       "recovering lithium, cobalt and nickel."]},
        ],
        "why_pick": "Helios Dach makes solar roof tiles in Berlin, which is exactly "
                    "what the question asks for. The other three are nothing to do "
                    "with it. Most questions are this clear.",
        "why": "Take the description away and the answer collapses completely — the "
               "model goes from naming the company and describing its product to "
               "saying it cannot answer at all. Nothing else it could see carried "
               "that information. The AI really was using this description.",
    },
    {
        "n": "P2",
        "id": "__practice_2",
        "query": "Which Austrian startup recovers lithium from used electric "
                 "vehicle batteries?",
        "chunk_name": "Nordwind Analytics GmbH",
        "chunk_meta": "Founded in 2020. Company size: 1-10. Startup. Austria. Vienna.",
        "chunk_prose": "Nordwind Analytics GmbH builds dashboard and reporting "
                       "software for logistics fleet operators, covering vehicle "
                       "utilisation, fuel spend and driver scheduling.",
        "index": 1,
        "original": "Alpine Zell GmbH, based in Graz, recovers lithium and cobalt "
                    "from used electric vehicle batteries using a hydrometallurgical "
                    "process. [1] [2]",
        "removed": "Alpine Zell GmbH, based in Graz, recovers lithium and cobalt "
                   "from used electric vehicle batteries using a hydrometallurgical "
                   "process. [1]",
        "others": [{"i": 2, "name": "Alpine Zell GmbH", "meta":
                    "Founded in 2017. Company size: 11-50. Startup. Austria. Graz.",
                    "text": "Alpine Zell GmbH operates a battery recycling plant in "
                            "Graz recovering lithium, cobalt and nickel from end-of-life "
                            "electric vehicle packs through a hydrometallurgical process."}],
        "answer": "not_needed",
        # pick task: nothing matches, so "None of these" is correct
        "answer_pick": "none",
        "options": [
            {"i": 1, "name": "Nordwind Analytics GmbH",
             "paras": ["Nordwind Analytics GmbH builds dashboard and reporting "
                       "software for logistics fleet operators, covering vehicle "
                       "utilisation, fuel spend and driver scheduling."]},
            {"i": 2, "name": "Wienerwald Sensorik",
             "paras": ["Wienerwald Sensorik develops soil moisture sensors for "
                       "vineyards and orchards."]},
            {"i": 3, "name": "Donau Fintech GmbH",
             "paras": ["Donau Fintech GmbH provides payment reconciliation software "
                       "for small retailers."]},
        ],
        "why_pick": "None of these three recovers lithium from batteries — one does "
                    "logistics software, one soil sensors, one payments. \"None of "
                    "these\" was the right answer. It will be right fairly often, so "
                    "do not be afraid to use it.",
        "why": "The answer is word-for-word the same apart from the citation "
               "numbers. Every fact in it came from the Alpine Zell description. The "
               "logistics-software company has nothing to do with battery recycling "
               "— the AI tacked its number on without using it. Note also that "
               "[2] on the left became [1] on the right: the remaining descriptions get "
               "renumbered after one is taken away, so never compare the numbers "
               "across the two answers.",
    },
    {
        "n": "P3",
        "id": "__practice_3",
        "modes": ["full"],
        "query": "Which Swiss startup flies medical samples between hospitals by "
                 "drone?",
        "chunk_name": "AlpMed Drone AG",
        "chunk_meta": "Founded in 2019. Company size: 11-50. Startup. Switzerland. Bern.",
        "chunk_prose": "AlpMed Drone AG operates scheduled drone flights carrying "
                       "blood samples and medical supplies between Swiss hospitals.",
        "index": 1,
        "original": "AlpMed Drone AG operates scheduled drone flights carrying blood "
                    "samples between Swiss hospitals. [1]",
        "removed": "AlpMed Drones runs medical drone logistics connecting Swiss "
                   "hospitals and diagnostic laboratories. [2]",
        "others": [
            {"i": 2, "name": "Seetal Robotik",
             "text": "Seetal Robotik builds warehouse picking arms for grocery "
                     "distribution centres."},
            {"i": 3, "name": "AlpMed Drones",
             "text": "AlpMed Drones is a Swiss operator of medical drone logistics "
                     "connecting hospitals and diagnostic laboratories across the "
                     "cantons."},
        ],
        "answer": "unclear",
        "why": "The content survived — answer 2 still says a Swiss company flies "
               "medical samples between hospitals. So you go and look at the other "
               "descriptions, and there is [3] AlpMed Drones: the same business under "
               "a slightly different name. The AI may well have used [1] genuinely "
               "and simply switched to [3] when [1] was taken away. The two answers "
               "cannot tell you which. That is Can't tell, with a note naming [3]. "
               "Several real items in this set look like this — it is exactly what "
               "the study is trying to count, so do not force a Yes or No.",
    },
]

# One attention check, inserted mid-run. Friends and family click through things;
# this is the cheapest way to know who did. Excluded from all scoring.
ATTENTION = {
    "n": 0,
    "id": "__attention_check",
    "query": "Which German startup produces cultivated meat from cell cultures "
             "for the retail market?",
    "chunk_name": "Reading check",
    "chunk_meta": "",
    "chunk_prose": "This one is not a real item — it is a check that the page is "
                   "being read rather than clicked through. Please choose "
                   "“Can't tell” for this item and carry on. Nothing else "
                   "about it matters.",
    "index": 1,
    "original": "Not a real question — this is just a check that the page is being "
                "read rather than clicked through. Please choose “Can't tell” "
                "and carry on.",
    "removed": "Not a real question — this is just a check that the page is being "
               "read rather than clicked through. Please choose “Can't tell” "
               "and carry on.",
    "others": [],
    "options": [
        {"i": 1, "name": "Please pick this one",
         "paras": ["This is not a real question. It is a check that the page is "
                   "being read rather than clicked through. Pick this option and "
                   "carry on — nothing else about it matters."]},
        {"i": 2, "name": "Himmelblau Foods GmbH",
         "paras": ["Himmelblau Foods GmbH produces plant-based dairy alternatives."]},
        {"i": 3, "name": "Zellkraft AG",
         "paras": ["Zellkraft AG researches cell culture media for laboratory use."]},
    ],
    "is_check": True,
}

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
 :root{--bg:#fbfaf7;--card:#fff;--ink:#1d1f22;--mut:#6b7178;--line:#e2e0da;
  --accent:#3b6ea5;--warm:#b4622d;--ok:#3f7d4e;--no:#a8443a;
  --del:#fbe6d8;--delink:#8a4620;--ins:#dcecdd;--insink:#2e6039}
 @media(prefers-color-scheme:dark){:root{--bg:#16181c;--card:#1e2126;--ink:#e4e6e9;
  --mut:#9aa1a9;--line:#2e3238;--accent:#7aa8d8;--warm:#d98a52;--ok:#6aab78;
  --no:#d9776c;--del:#43301f;--delink:#f0b98c;--ins:#25382a;--insink:#9fd0aa}}
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--ink);
  font:16px/1.65 Charter,Georgia,'Times New Roman',serif;padding:1.5rem 1rem 7rem}
 .wrap{max-width:860px;margin:0 auto}
 header{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;
  border-bottom:1px solid var(--line);padding-bottom:.7rem;margin-bottom:1rem}
 h1{font-size:1rem;font-weight:600}
 h2{font-size:1.3rem;font-weight:600;margin-bottom:.8rem;line-height:1.3}
 h3{font-size:1rem;font-weight:600;margin:1.6rem 0 .5rem}
 .count{font:600 .82rem ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mut);
  white-space:nowrap}
 .bar{height:3px;background:var(--line);border-radius:9px;margin-bottom:1.8rem}
 .fill{height:100%;background:var(--accent);border-radius:9px;transition:width .3s}
 p{margin-bottom:.9rem}
 ul,ol{margin:0 0 .9rem 1.2rem}li{margin-bottom:.35rem}
 .q{font-size:1.12rem;line-height:1.45;margin-bottom:.3rem;font-weight:600}
 .qlead{font:.72rem ui-monospace,monospace;color:var(--mut);text-transform:uppercase;
  letter-spacing:.09em;margin-bottom:.45rem}
 .meta{font:.72rem ui-monospace,monospace;color:var(--mut);margin-bottom:1.4rem}
 .card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:1rem 1.2rem;margin-bottom:.9rem}
 .lbl{font:600 .68rem ui-monospace,monospace;text-transform:uppercase;
  letter-spacing:.09em;color:var(--mut);margin-bottom:.55rem}
 .card.target{border-color:var(--warm);border-left:3px solid var(--warm)}
 .card.target .lbl{color:var(--warm)}
 .cname{font-weight:600;font-size:1rem}
 .cmeta{margin:.15rem 0 .6rem}
 .cmeta summary{font:.72rem ui-monospace,monospace;color:var(--mut);padding:.2rem 0}
 .cmetatxt{font:.72rem/1.5 ui-monospace,monospace;color:var(--mut);
  padding:.4rem 0 .1rem}
 .txt{font-size:.93rem;line-height:1.6}
 .card p.txt + p.txt,.oth p.txt + p.txt{margin-top:.6rem}
 .guide{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:.2rem 1.1rem;margin-bottom:1.3rem}
 .guide summary{color:var(--accent)}
 .guide ol{margin:.4rem 0 .2rem 1.2rem;font-size:.9rem}
 .guide ul{margin:.4rem 0 .4rem 1rem}
 .guide p{margin:.5rem 0 .6rem}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:.9rem;align-items:start}
 @media(max-width:760px){.two{grid-template-columns:1fr}}
 del,ins{text-decoration:none;border-radius:3px;padding:.05em .12em}
 del{background:var(--del);color:var(--delink)}
 ins{background:var(--ins);color:var(--insink)}
 .legend{font:.74rem ui-monospace,monospace;color:var(--mut);margin:-.3rem 0 1rem;
  display:flex;gap:1rem;flex-wrap:wrap;align-items:center}
 .sw{display:inline-block;width:.75rem;height:.75rem;border-radius:2px;
  vertical-align:-1px;margin-right:.3rem}
 details{margin-bottom:1.3rem}
 summary{cursor:pointer;font:.82rem ui-monospace,monospace;color:var(--accent);
  padding:.45rem 0}
 .oth{border-left:2px solid var(--line);padding:.45rem 0 .45rem .9rem;margin:.55rem 0;
  font-size:.86rem}
 .oth b{font-size:.78rem;color:var(--mut);font-family:ui-monospace,monospace}
 .ask{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:1.1rem 1.2rem;margin-top:1.4rem}
 .ask p{font-size:1.02rem;font-weight:600;margin-bottom:.9rem}
 .btns{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:.8rem}
 button{font:inherit;font-size:.92rem;padding:.65rem 1.1rem;border-radius:8px;
  border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;
  display:flex;align-items:center;gap:.5rem}
 button:hover{border-color:var(--accent)}
 button.y{border-color:var(--ok)}button.y:hover{background:var(--ins)}
 button.n{border-color:var(--no)}button.n:hover{background:var(--del)}
 button.sel{background:var(--accent);color:#fff;border-color:var(--accent)}
 kbd{font:.7rem ui-monospace,monospace;border:1px solid var(--line);border-radius:4px;
  padding:.05rem .3rem;opacity:.65}
 textarea{width:100%;min-height:3.2rem;font:inherit;font-size:.88rem;padding:.6rem;
  border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);
  resize:vertical}
 input[type=text]{font:inherit;font-size:1rem;padding:.6rem .75rem;border-radius:8px;
  border:1px solid var(--line);background:var(--card);color:var(--ink);width:min(320px,100%)}
 .nav{display:flex;justify-content:space-between;margin-top:1.4rem;
  font:.8rem ui-monospace,monospace}
 .nav a{color:var(--mut);cursor:pointer;text-decoration:none}
 .nav a:hover{color:var(--accent)}
 .big{font-size:1rem;padding:.8rem 1.6rem;background:var(--accent);color:#fff;
  border-color:var(--accent);display:inline-flex}
 .note{background:var(--card);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;
  padding:.8rem 1.1rem;margin-bottom:1rem;font-size:.9rem}
 .fb{border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;font-size:.93rem}
 .fb.right{background:var(--ins);color:var(--insink)}
 .fb.wrong{background:var(--del);color:var(--delink)}
 .opts{margin-top:1.4rem}
 .opt{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:.85rem 1.1rem;margin-bottom:.6rem;cursor:pointer;transition:border-color .12s}
 .opt:hover{border-color:var(--accent)}
 .opt.sel{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
 .opt.locked{cursor:default;opacity:.75}
 .opt.locked:hover{border-color:var(--line)}
 .opt.locked.sel{opacity:1}
 .opt.none{border-style:dashed}
 .optname{font-weight:600;font-size:1rem;margin-bottom:.15rem}
 .optprev{font-size:.88rem;color:var(--mut);line-height:1.5}
 .more{color:var(--accent);cursor:pointer;font-size:.8rem;
  font-family:ui-monospace,monospace;white-space:nowrap;margin-left:.3rem}
 .optfull{font-size:.88rem;line-height:1.6;margin-top:.6rem;
  border-top:1px solid var(--line);padding-top:.6rem}
 .optfull p + p{margin-top:.5rem}
 .done{text-align:center;padding:3rem 1rem}
 .hint{font-size:.85rem;color:var(--mut)}
 .warn{border-left-color:var(--warm)}
</style></head><body><div class="wrap">
<header><h1>__TITLE__</h1><span class="count" id="c"></span></header>
<div class="bar"><div class="fill" id="f"></div></div>
<div id="main"></div>
</div>
<script>
const DATA = __DATA__;
const PRACTICE = __PRACTICE__;
const MODE = __MODE__;
const KEY = 'audit_survey_v3_' + MODE;   // v3 = post-codebook pass

/* Wording differs between the two instruments because the question does.
   'same/different' is a perceptual comparison; 'used it / didn't need it' is a
   judgment about the AI. They are stored under the same two labels so one
   scorer handles both, but the CSV records which instrument produced them. */
const ASK = {q: 'Did the AI really use this description when it wrote answer 1?',
             needed: 'Yes, it used it', not_needed: "No, it didn't need it",
             unclear: "Can't tell"};

let S = JSON.parse(localStorage.getItem(KEY) || '{}');
if (!S.ans) S.ans = {};
if (!S.stage) S.stage = 'intro';
if (S.i == null) S.i = 0;
const save = () => localStorage.setItem(KEY, JSON.stringify(S));

const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

/* Word-level diff so the annotator can see at a glance what the removal
   actually changed. Without this you are asked to eyeball two walls of near
   identical prose, which is where the judgment goes wrong. */
function diff(a, b){
  const A = (a||'').split(/(\s+)/), B = (b||'').split(/(\s+)/);
  const n = A.length, m = B.length;
  if (n * m > 4e6) return [esc(a), esc(b), 1];       // pathological, skip
  const L = new Int32Array((n+1) * (m+1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      L[i*(m+1)+j] = A[i] === B[j] ? L[(i+1)*(m+1)+j+1] + 1
                   : Math.max(L[(i+1)*(m+1)+j], L[i*(m+1)+j+1]);
  let i = 0, j = 0, oa = '', ob = '', da = '', db = '', same = 0;
  const flush = () => {
    if (da) { oa += '<del>' + esc(da) + '</del>'; da = ''; }
    if (db) { ob += '<ins>' + esc(db) + '</ins>'; db = ''; }
  };
  while (i < n && j < m){
    if (A[i] === B[j]){ flush(); oa += esc(A[i]); ob += esc(B[j]); same++; i++; j++; }
    else if (L[(i+1)*(m+1)+j] >= L[i*(m+1)+j+1]) da += A[i++];
    else db += B[j++];
  }
  while (i < n) da += A[i++];
  while (j < m) db += B[j++];
  flush();
  // Proportion of tokens that are not shared. Used only to decide whether
  // highlighting is worth showing; never displayed.
  const ratio = (n + m) ? 1 - (2 * same) / (n + m) : 0;
  return [oa, ob, ratio];
}

/* The scraped facts — founding year, headcount, city list, category tags — are
   never what the judgment turns on, and they are the first thing that makes a
   profile look impenetrable. Folded away, one click from view, unaltered. */
function profile(name, meta, paras){
  return `<div class="cname">${esc(name)}</div>` +
    (meta ? `<details class="cmeta"><summary>company facts (year, size, location, categories)</summary>
             <div class="cmetatxt">${esc(meta)}</div></details>` : '') +
    (paras || []).map(p => `<p class="txt">${esc(p)}</p>`).join('');
}

/* The quick instrument. No description, no other sources, no decision guide:
   just the question and the two answers, and one perceptual judgment — do these
   say the same thing? That is deliberately a narrower claim than the full
   survey. It validates the audit's central inference (high similarity means the
   answer did not really change) without touching the redundancy question, which
   cannot be answered without reading all five descriptions. */
/* The quick instrument: a multiple choice over the companies the AI could see.
   No answers, no comparison, no instructions needed. It records only which
   company was picked; nothing in this file says which one the AI cited, so an
   annotator reading the source cannot find the thing being tested. Scoring
   resolves the pick against answer_key.json. */
function pickBody(d){
  const opts = d.options.map(o => `
    <div class="opt" onclick="pick(${o.i})">
      <div class="optname">${esc(o.name)}</div>
      <div class="optprev">${esc(o.preview)}
        <a class="more" onclick="event.stopPropagation();showFull(this,${o.i})">show full</a>
      </div>
      <div class="optfull" id="full${o.i}" hidden>${(o.paras||[]).map(
        p => `<p>${esc(p)}</p>`).join('')}</div>
    </div>`).join('');
  return `
    <div class="qlead">Which company is the answer?</div>
    <div class="q">${esc(d.query)}</div>
    <div class="opts">
      ${opts}
      <div class="opt none" onclick="pick('none')">
        <div class="optname">None of these answers the question</div>
      </div>
    </div>
    <p class="hint" style="text-align:center;margin-top:1rem">
      <a onclick="pick('unclear')" style="color:var(--mut);cursor:pointer">
      I really can't tell &mdash; skip this one</a></p>`;
}

function showFull(el, i){
  const box = document.getElementById('full' + i);
  box.hidden = !box.hidden;
  el.textContent = box.hidden ? 'show full' : 'show less';
}

function itemBody(d){
  if (MODE === 'simple') return pickBody(d);
  const [oa, ob, ratio] = diff(d.original, d.removed);
  /* When the two answers are largely rewritten, a word-level diff highlights
     nearly every word and tells the annotator nothing, so it starts off. Note
     that the proportion changed is never shown: it is a lexical proxy for the
     very thing being judged, and putting a number on screen would invite people
     to threshold on it, making agreement with the audit circular. */
  const noisy = ratio > 0.6;
  const showDiff = S.diff === undefined || S.diff === null ? !noisy : S.diff;
  const [la, lb] = showDiff ? [oa, ob] : [esc(d.original), esc(d.removed)];
  const others = (d.others || []);
  return `
    <div class="qlead">The question the AI was asked</div>
    <div class="q">${esc(d.query)}</div>
    <div class="meta">It could see ${others.length + 1} company descriptions. It said it used the one below.</div>

    <div class="card target">
      <div class="lbl">The description we took away</div>
      ${profile(d.chunk_name, d.chunk_meta, d.chunk_paras)}
    </div>

    <div class="two">
      <div class="card">
        <div class="lbl">1. Its answer &mdash; while it could see that description</div>
        <div class="txt">${la}</div>
      </div>
      <div class="card">
        <div class="lbl">2. Its answer &mdash; after we took the description away</div>
        <div class="txt">${lb}</div>
      </div>
    </div>
    ${showDiff ? `<div class="legend">
      <span><span class="sw" style="background:var(--del)"></span>only on the left</span>
      <span><span class="sw" style="background:var(--ins)"></span>only on the right</span>
      <a onclick="toggleDiff(false)" style="color:var(--accent);cursor:pointer">turn highlighting off</a>
    </div>` : `<div class="legend">
      ${noisy && (S.diff === undefined || S.diff === null)
        ? '<span>These two answers are worded very differently, so highlighting would cover almost every word. Read them side by side instead.</span>' : ''}
      <a onclick="toggleDiff(true)" style="color:var(--accent);cursor:pointer">highlight the differences anyway</a>
    </div>`}

    <div class="note warn"><b>Careful:</b> the numbers in square brackets are
    renumbered after a description is taken away, so <b>[1]</b> on the left is not
    <b>[1]</b> on the right. Compare the words, not the numbers.</div>

    ${others.length ? `<details><summary>Show the other ${others.length} descriptions &mdash; needed for step 4</summary>
      <p class="hint" style="margin:.4rem 0 .8rem">Scan the one-liners; open only any
      that look like they might carry the same information.</p>
      ${others.map(o => `<div class="opt locked">
        <div class="optname">${esc(o.name)}</div>
        <div class="optprev">${esc(o.preview)}
          <a class="more" onclick="showFull(this,${o.i})">show full</a></div>
        <div class="optfull" id="full${o.i}" hidden>${(o.paras||[]).map(
          x => `<p>${esc(x)}</p>`).join('')}</div>
      </div>`).join('')}
    </details>` : ''}

    <details class="guide" ${S.guideOpen ? 'open' : ''}
      ontoggle="S.guideOpen=this.open;save()">
      <summary>How to decide</summary>
      <ol>
        <li><b>Read answer 1.</b> What does it claim that came from this
        description? If nothing traces to it at all &rarr; <b>No</b>.</li>
        <li><b>Read answer 2</b>, written without it. Are those claims still there?
        Wording may differ; ignore the bracket numbers entirely. <b>The company named
        is part of the claim</b> &mdash; if a <i>different</i> company has taken its
        place, the original claim is gone, so that is step 3.</li>
        <li><b>Gone or clearly weakened &rarr; Yes, it used it.</b> Stop here &mdash;
        do not check the others. Removing it removed the content.</li>
        <li><b>Still there &rarr; open the other descriptions above</b> and ask
        whether one of them carries the same thing.
          <ul>
            <li>Another one does &mdash; usually the <i>same</i> company under a
            second name &rarr; <b>Can't tell</b>, and note which. The AI may have used this
            one and then switched. <i>This is the case the study is looking for, so
            it is a real answer, not a cop-out.</i></li>
            <li>None of them does &rarr; <b>No, it didn't need it.</b></li>
          </ul>
        </li>
      </ol>
      <p><b>If answer 1 is a refusal</b> ("none of these match"), a source can still
      have been used. Ask: does answer 1 say anything specific about <i>this</i>
      company? <b>If it does</b>, run steps 2&ndash;4 on that &mdash; answer 2 drops it
      &rarr; Yes. <b>If it names nobody at all</b> &rarr; <b>No</b>: a refusal that
      mentions nothing attributes nothing. Most refusals here do name the company, so
      "it's a refusal" is not a shortcut to No.</p>
      <p><b>If answer 1 lists several companies</b>, judge only this one's part. If
      answer 1 names it and answer 2 does not, that is <b>Yes</b> &mdash; even though
      the answer still reads fine with one fewer.</p>
      <p><b>Ignore how many sources each answer cites.</b> Answer 2 always has one
      fewer available, so a shorter citation list proves nothing. Compare the words.</p>
      <p class="hint">Not the question: whether the AI <i>read</i> this description (it
      read all five, every time), whether the answer is correct, whether the AI should
      have answered, or whether the company suits the question. A company can fit
      perfectly and still not be where the words came from.</p>
    </details>`;
}

function toggleDiff(on){ S.diff = on; save(); draw(); }

/* ---------- screens ---------- */

/* Deliberately short. Anything a person has to read before they can start is a
   reason not to start, and everything they actually need is repeated on the
   items themselves. */
function pick(v){
  const d = DATA[S.i];
  if (S.stage === 'practice') return pcheck(v);
  S.ans[d.id] = {pick: String(v), note: '', n: d.n};
  S.i++; save(); draw();
  window.scrollTo(0, 0);
}

function introSimple(){
  document.getElementById('main').innerHTML = `
    <h2>A quick favour, about 10 minutes</h2>
    <p>This is for my Master's thesis. I am testing whether an AI picks the right
    source when it answers a question, and I need a few people to check its
    work.</p>
    <p>It is a multiple choice quiz. <b>${DATA.length} questions</b>, each one a
    question about a European startup, with a short list of companies underneath.
    Pick the one that answers it.</p>
    <div class="note">Each company shows one line. If that is not enough, press
    <b>show full</b> to read its whole description.<br><br>
    If none of them fits, say so &mdash; <b>"None of these"</b> is often the right
    answer, and picking it when it is true is just as useful to me as picking a
    company.</div>
    <p>You need no knowledge of computers, startups or these companies. Everything
    you need is on the screen.</p>
    <p>Your progress saves as you go, so you can stop and come back. At the end,
    press the download button and send me the small file it gives you.</p>
    <h3>Your name</h3>
    <p class="hint">So I can tell the files apart. Initials are fine.</p>
    <p><input type="text" id="who" placeholder="e.g. SA, or Priya"
       value="${esc(S.who||'')}"></p>
    <p id="whoerr" class="hint" style="color:var(--no)"></p>
    <button class="big" onclick="startPractice()">Start with two quick examples</button>`;
  const el = document.getElementById('who');
  el.focus();
  el.addEventListener('keydown', e => { if (e.key === 'Enter') startPractice(); });
}

function intro(){
  document.getElementById('c').textContent = '';
  document.getElementById('f').style.width = '0%';
  if (MODE === 'simple') return introSimple();
  document.getElementById('main').innerHTML = `
    <h2>Did the student really read the book?</h2>
    <p>Thank you for helping. This takes about <b>30 to 40 minutes</b>, you can stop
    and come back whenever you like, and <b>you need to know nothing at all about
    computers, companies or artificial intelligence</b>. If you can read two
    paragraphs and say whether they differ, you can do this.</p>

    <h3>The idea, with no jargon</h3>
    <p>Imagine a student writing an essay. You give them five short articles and ask
    a question. They hand back an answer and, at the bottom, list which articles they
    used.</p>
    <p>But listing an article is not the same as reading it. Students pad out their
    bibliographies. So here is how you catch them: <b>take one of those articles
    away and make them write the answer again.</b> If the new answer is missing
    things, they really were using it. If they write more or less the same answer
    without it, they were never really using it &mdash; they just put it on the
    list.</p>
    <p>We did exactly that, except the student is a computer program &mdash; an AI,
    which is what we call it from here on &mdash; and the articles are short
    company descriptions. A second computer program then decided,
    for each case, whether the first one had really used the article.</p>
    <p><b>Nobody has ever checked whether that second program's decisions match what
    an ordinary thoughtful person would say.</b> That is what you are here for. You
    are the person it gets compared against.</p>

    <h3>What you do</h3>
    <div class="note">You will see the question, the company description that was
    taken away, and the two answers &mdash; one written while the computer could see
    that description, one written after we hid it. You decide one thing:
    <b>was the computer really using that description, or had it just put it on the
    list?</b><br><br>Three buttons: <b>Yes, it used it</b> &middot;
    <b>No, it didn't need it</b> &middot; <b>Can't tell</b>.</div>

    <h3>How to decide</h3>
    <ol>
      <li>Read the question, then read answer 1 and answer 2.</li>
      <li><b>Is something important in answer 1 missing from answer 2?</b> If the
      answer falls apart without the description, the computer was really using
      it &mdash; <b>Yes</b>.</li>
      <li><b>Does answer 2 say much the same thing?</b> Then check the other
      descriptions before you decide. There is a button to show them.
        <ul>
          <li>None of the others contain those facts &rarr; the computer was not
          really using this one. <b>No</b>.</li>
          <li>Another description has the same facts &rarr; the computer may have
          simply switched to that one, and you genuinely cannot tell from the
          answers. <b>Can't tell</b>, and please write a line saying why.</li>
        </ul>
      </li>
    </ol>
    <p class="hint">This third point is the whole reason we need a person rather
    than a program, so it is worth the extra few seconds.</p>

    <h3>Four things that catch people out</h3>
    <ul>
      <li><b>You are not marking the answer right or wrong.</b> The computer may be
      correct, badly wrong, or may refuse to answer. None of that matters here. The
      only question is whether it used that one description.</li>
      <li><b>Sometimes refusing is the correct answer.</b> A few questions were
      written so that nothing in the material answers them. If the computer says
      "none of these match", that can be perfectly right &mdash; but still ask
      whether it needed <i>that particular description</i> to say so.</li>
      <li><b>Two descriptions are sometimes the same company</b> under slightly
      different names. That is not a mistake in this page. Notice it, and mention it
      in the note box.</li>
      <li><b>"Can't tell" is a real answer</b>, not a cop-out. Use it instead of
      guessing, and say what made it hard.</li>
    </ul>
    <p class="hint">The instructions above stay available on every page under
    "Remind me how to decide".</p>

    <h3>Your name</h3>
    <p class="hint">Only so your answers do not get mixed up with someone else's,
    and so we can see how often people helping agreed with each other. Initials or
    a nickname are fine.</p>
    <p><input type="text" id="who" placeholder="e.g. SA, or Priya"
       value="${esc(S.who||'')}"></p>
    <p id="whoerr" class="hint" style="color:var(--no)"></p>
    <button class="big" onclick="startPractice()">Start with two practice items</button>`;
  const el = document.getElementById('who');
  el.focus();
  el.addEventListener('keydown', e => { if (e.key === 'Enter') startPractice(); });
}

function startPractice(){
  const v = document.getElementById('who').value.trim();
  if (!v){ document.getElementById('whoerr').textContent = 'Please enter a name first.'; return; }
  S.who = v; S.stage = 'practice'; S.i = 0; save(); draw();
}

function practice(){
  const d = PRACTICE[S.i];
  document.getElementById('c').textContent = 'practice ' + (S.i+1) + ' / ' + PRACTICE.length;
  document.getElementById('f').style.width = '0%';
  const note = `<div class="note">Practice question &mdash; not counted. Answer it,
    then you will be told what we were looking for.</div>`;
  document.getElementById('main').innerHTML = MODE === 'simple'
    ? note + `<div id="ask">${itemBody(d)}</div>`
    : note + itemBody(d) + `
      <div class="ask" id="ask">
        <p>${ASK.q}</p>
        <div class="btns">
          <button class="y" onclick="pcheck('needed')">${ASK.needed}<kbd>1</kbd></button>
          <button class="n" onclick="pcheck('not_needed')">${ASK.not_needed}<kbd>2</kbd></button>
          <button onclick="pcheck('unclear')">${ASK.unclear}<kbd>3</kbd></button>
        </div>
      </div>`;
}

function pcheck(v){
  const d = PRACTICE[S.i];
  const want = String(MODE === 'simple' ? d.answer_pick : d.answer);
  const why = MODE === 'simple' ? d.why_pick : d.why;
  const right = String(v) === want;
  const named = k => {
    if (k === 'none') return 'None of these';
    if (k === 'unclear') return "Can't tell";
    const o = (d.options || []).find(x => String(x.i) === k);
    return o ? o.name : k;
  };
  if (MODE === 'simple'){
    document.querySelectorAll('#ask .opt').forEach(o => o.classList.add('locked'));
    document.querySelectorAll('#ask .opt').forEach(o => {
      const oc = o.getAttribute('onclick') || '';
      if (oc === `pick(${v})` || oc === `pick('${v}')`) o.classList.add('sel');
    });
  } else {
    // Lock the choice buttons BEFORE adding the continue button, or the selector
    // catches that one too and the practice screen dead-ends.
    document.querySelectorAll('#ask .btns button').forEach(b => {
      b.disabled = true;
      if (b.getAttribute('onclick') === `pcheck('${v}')`) b.classList.add('sel');
    });
  }
  document.getElementById('ask').insertAdjacentHTML('beforeend',
    `<div class="fb ${right ? 'right' : 'wrong'}">
      <b>${right ? 'That is the one we were looking for.'
                 : 'We would have said: ' + esc(MODE === 'simple' ? named(want)
                                                                  : ASK[want])
                   + '.'}</b><br>${esc(why)}
     </div>
     <div class="btns" style="margin-top:1rem">
       <button class="big" onclick="pnext()">${S.i + 1 < PRACTICE.length
         ? 'Next practice question' : 'Start the real questions'}</button>
     </div>`);
}

function pnext(){
  S.i++;
  if (S.i >= PRACTICE.length){ S.stage = 'main'; S.i = 0; }
  save(); draw();
}

function main(){
  if (S.i >= DATA.length) return finish();
  const d = DATA[S.i];
  const prev = S.ans[d.id] || {};
  document.getElementById('c').textContent = (S.i+1) + ' / ' + DATA.length;
  document.getElementById('f').style.width = (S.i / DATA.length * 100) + '%';
  const nav = `<div class="nav">
      <a onclick="go(-1)">${S.i > 0 ? '← back' : ''}</a>
      <a onclick="go(1)">${prev.judgment || prev.pick ? 'skip forward →' : ''}</a>
    </div>`;
  if (MODE === 'simple'){
    document.getElementById('main').innerHTML = itemBody(d) + nav;
    if (prev.pick) document.querySelectorAll('.opt').forEach(o => {
      const oc = o.getAttribute('onclick') || '';
      if (oc === `pick(${prev.pick})` || oc === `pick('${prev.pick}')`)
        o.classList.add('sel');
    });
    return;
  }
  document.getElementById('main').innerHTML = `
    ${itemBody(d)}
    <div class="ask">
      <p>${ASK.q}</p>
      <textarea id="note" placeholder="Optional note — write it first, then choose below. Useful if you pick Can't tell, or if you spot something odd.">${esc(prev.note||'')}</textarea>
      <div class="btns" style="margin-top:.8rem;margin-bottom:0">
        <button class="y ${prev.judgment==='needed'?'sel':''}"
          onclick="rec('needed')">${ASK.needed}<kbd>1</kbd></button>
        <button class="n ${prev.judgment==='not_needed'?'sel':''}"
          onclick="rec('not_needed')">${ASK.not_needed}<kbd>2</kbd></button>
        <button class="${prev.judgment==='unclear'?'sel':''}"
          onclick="rec('unclear')">${ASK.unclear}<kbd>3</kbd></button>
      </div>
      <p class="hint" style="font-weight:400;margin:.7rem 0 0">Choosing saves your
      answer and moves on. Keys 1, 2 and 3 work too, except while typing a note.</p>
    </div>` + nav;
}

function stashNote(){
  const n = document.getElementById('note');
  const d = DATA[S.i];
  if (n && d && S.ans[d.id]) S.ans[d.id].note = n.value;
}

function rec(v){
  const d = DATA[S.i];
  S.ans[d.id] = {judgment: v, note: (document.getElementById('note')||{}).value || '',
                 n: d.n};
  S.i++; save(); draw();
  window.scrollTo(0, 0);
}

function go(k){
  stashNote();
  S.i = Math.max(0, Math.min(DATA.length, S.i + k));
  save(); draw();
  window.scrollTo(0, 0);
}

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
  if (MODE === 'simple'){
    if (S.stage === 'practice' && document.querySelector('.fb')) return;
    const opts = [...document.querySelectorAll('.opt')];
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= opts.length) opts[n - 1].click();
    return;
  }
  if (S.stage === 'main'){
    if (e.key === '1') rec('needed');
    if (e.key === '2') rec('not_needed');
    if (e.key === '3') rec('unclear');
  } else if (S.stage === 'practice'){
    const b = {1:'needed', 2:'not_needed', 3:'unclear'}[e.key];
    if (b && !document.querySelector('.fb')) pcheck(b);
  }
});

function finish(){
  document.getElementById('c').textContent = 'done';
  document.getElementById('f').style.width = '100%';
  const n = Object.keys(S.ans).length;
  document.getElementById('main').innerHTML = `<div class="done">
    <h2>All ${DATA.length} done &mdash; thank you</h2>
    <p>${n} judgments recorded. Press the button, then send the downloaded file
    back to Srihari.</p>
    <p><button class="big" onclick="dl()">Download my answers</button></p>
    <p class="hint" style="margin-top:2rem">
      <a onclick="S.i=0;S.stage='main';save();draw()" style="cursor:pointer">review my answers</a>
      &nbsp;&middot;&nbsp;
      <a onclick="if(confirm('Erase everything and start over?')){localStorage.removeItem(KEY);location.reload()}" style="cursor:pointer">start over</a>
    </p></div>`;
}

function dl(){
  const q = s => '"' + String(s == null ? '' : s).replace(/"/g, '""') + '"';
  // The mode column matters: the two instruments ask different questions, and
  // pooling their judgments would mix two constructs.
  let csv = 'annotator,item_id,judgment,note,mode,pick\n';
  for (const [k, v] of Object.entries(S.ans))
    csv += [q(S.who), q(k), q(v.judgment || ''), q(v.note), q(MODE),
            q(v.pick || '')].join(',') + '\n';
  const safe = (S.who || 'anon').replace(/[^A-Za-z0-9_-]+/g, '_').slice(0, 24);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + csv], {type: 'text/csv;charset=utf-8'}));
  a.download = 'answers_' + MODE + '_' + safe + '.csv';
  document.body.appendChild(a); a.click(); a.remove();
}

function draw(){
  if (S.stage === 'intro') return intro();
  if (S.stage === 'practice') return practice();
  return main();
}
draw();
</script></body></html>"""


def build_payload(items, seed=42):
    """Annotator-facing records. Verdicts and similarity never enter this."""
    # Spread the cited chunk evenly over the answer positions, then shuffle the
    # assignment so the cycle itself is not learnable.
    slots = [i % 5 for i in range(len(items))]
    random.Random(seed).shuffle(slots)
    out = []
    for i, it in enumerate(items):
        meta, prose = split_profile(it["target_chunk"].get("text", ""),
                                    it["target_chunk"].get("name", ""))
        others = []
        for c in it["other_chunks"]:
            om, op = split_profile(c.get("text", ""), c.get("name", ""))
            op_paras = paragraphs(op)
            others.append({
                "i": c.get("index"),
                "name": c.get("name", ""),
                "meta": om,
                "preview": preview_line(op_paras),
                "paras": op_paras,
            })
        out.append({
            "n": i + 1,
            # Must match build_annotation_set.py exactly, condition included:
            # the same (query, chunk) pair recurs across conditions with
            # different answers and is a distinct item.
            "id": f"{it['query_id']}_c{it['target_index']}_{it['condition']}",
            "query": it["query"],
            "chunk_name": it["target_chunk"].get("name", ""),
            "chunk_meta": meta,
            "chunk_paras": paragraphs(prose),
            "index": it["target_index"],
            "original": it["original_answer"],
            "removed": it["removed_answer"],
            "others": others,
            "options": pick_options(it, seed + i, slots[i]),
        })
    return out


def preview_line(paras, limit=135):
    """First sentence of the description, for the one-line option summary.

    Truncated only for display; the full text is one click away in the same
    card, so nothing is withheld.
    """
    first = (paras or [""])[0]
    m = re.match(r"(.{0,220}?[.!?])(?:\s|$)", first)
    line = (m.group(1) if m else first).strip()
    if len(line) > limit:
        line = line[:limit - 1].rsplit(" ", 1)[0] + "…"
    return line


def pick_options(it, seed, target_slot=None):
    """The multiple-choice list for one item.

    Order is randomised so the cited chunk is not identifiable by position, and
    fixed by seed so every annotator sees the same list. `target_slot` places
    the cited chunk at a chosen position: the caller spreads those evenly across
    items, because a plain shuffle over only 29 items leaves a visible lean (it
    put the cited company last 10 times) that a quick annotator could learn.

    Nothing here records which option was cited. The survey stores only the
    pick, and scoring resolves it against answer_key.json, so an annotator
    reading the page source cannot find the answer.
    """
    rng = random.Random(seed)

    def entry(c):
        _, prose = split_profile(c.get("text", ""), c.get("name", ""))
        paras = paragraphs(prose)
        return {"i": c.get("index"), "name": c.get("name", ""),
                "preview": preview_line(paras), "paras": paras}

    target = entry(it["target_chunk"])
    rest = [entry(c) for c in it["other_chunks"]]
    rng.shuffle(rest)
    slot = rng.randrange(len(rest) + 1) if target_slot is None \
        else target_slot % (len(rest) + 1)
    rest.insert(slot, target)
    return rest


def normalise(d):
    """Put the hand-written practice and check items into the same shape the
    real items use, so the template only has to know one format."""
    d = dict(d)
    if "chunk_prose" in d:
        d["chunk_paras"] = paragraphs(d.pop("chunk_prose"))
    d["others"] = [
        {"i": o.get("i"), "name": o.get("name", ""), "meta": o.get("meta", ""),
         "paras": o.get("paras") or paragraphs(o.get("text", "")),
         "preview": o.get("preview") or preview_line(
             o.get("paras") or paragraphs(o.get("text", "")))}
        for o in d.get("others", [])
    ]
    d["options"] = [
        {**o, "preview": o.get("preview") or preview_line(o.get("paras"))}
        for o in d.get("options", [])
    ]
    return d


def render(payload, practice, mode):
    enc = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    if mode == "simple":
        # The pick task shows neither the answers nor which chunk was cited, so
        # neither may be present in the file. Stripping them here is what makes
        # the instrument blind rather than merely hiding things visually.
        keep = {"n", "id", "query", "options", "is_check"}
        payload = [{k: v for k, v in p.items() if k in keep} for p in payload]
    return (TEMPLATE
            .replace("__DATA__", enc(payload))
            .replace("__PRACTICE__", enc(practice))
            .replace("__MODE__", json.dumps(mode))
            .replace("__TITLE__", "Which company answers this?" if mode == "simple"
                                  else "Did the AI really use this description?"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="38k_v7")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--attention-at", type=int, default=12,
                    help="1-based position for the attention check, 0 to omit")
    args = ap.parse_args()

    items = dedupe(collect(args.tag))
    if not items:
        print(f"No audit rounds found for tag '{args.tag}'")
        return
    sample = stratify(items, args.n, args.seed)

    payload = build_payload(sample, args.seed)

    # Cross-check against the key already on disk. If these ever diverge, the
    # annotators are judging a different set from the one being scored.
    kpath = OUT_DIR / "answer_key.json"
    if kpath.exists():
        key_ids = [r["item_id"] for r in json.loads(kpath.read_text())]
        if key_ids != [p["id"] for p in payload]:
            print("WARNING: item order differs from the existing answer_key.json.")
            print("         Re-run build_annotation_set.py with the same seed, or")
            print("         scoring will misalign. Nothing written.")
            return

    if args.attention_at:
        at = max(1, min(len(payload), args.attention_at)) - 1
        payload.insert(at, normalise(ATTENTION))
    for i, p in enumerate(payload):
        p["n"] = i + 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prac = [normalise(p) for p in PRACTICE]
    real = sum(1 for p in payload if not p.get("is_check"))

    written = []
    for mode, fname in (("full", "survey.html"), ("simple", "survey_simple.html")):
        out = OUT_DIR / fname
        # The redundancy example only makes sense where the other descriptions
        # are on screen, so it is shown in the detailed survey only.
        shown = [q for q in prac if mode in q.get("modes", ["full", "simple"])]
        out.write_text(render(payload, shown, mode), encoding="utf-8")
        written.append(out)

    # Company names per item, so the scorer can report which one people picked.
    # Names only — this holds no verdict and no indication of what was cited.
    (OUT_DIR / "pick_options.json").write_text(json.dumps(
        {p["id"]: {str(o["i"]): o["name"] for o in p.get("options", [])}
         for p in payload if not p.get("is_check")}, indent=2, ensure_ascii=False))

    print(f"{real} items"
          + (f" + 1 attention check at position {args.attention_at}"
             if args.attention_at else ""))
    print(f"\n  {written[1]}   the quick one — send this to people")
    print("      asks: which company answers this question?  ~10 min")
    print(f"\n  {written[0]}          the detailed one — for you")
    print("      asks: did the AI really use this description?  ~40 min")
    print(f"\nCollect the exported CSVs into {OUT_DIR}/annotations/ and run")
    print("score_annotations.py. It keeps the two instruments apart.")


if __name__ == "__main__":
    main()
