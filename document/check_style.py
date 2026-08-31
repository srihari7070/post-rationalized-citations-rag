"""
Measure a draft against the evidence-based markers in style/AI_WRITING_MARKERS.md.

Targets come from published findings on what separates machine from human prose, not
from folklore. The strongest single marker is nominalisation density, followed by
sentence-length variance and local repetition.

    python document/check_style.py                    # check draft v1
    python document/check_style.py --version v2
    python document/check_style.py --file some.md     # single file
    python document/check_style.py --worst            # show worst offending sentences
"""
import argparse
import glob
import re
import statistics as st
from pathlib import Path

HEDGES = ['maybe', 'might', 'perhaps', 'seems', 'appears', 'probably', 'possibly',
          'i think', 'kind of', 'sort of', 'roughly', 'fairly', 'somewhat', 'likely',
          'suggests', 'appear', 'tends', 'largely', 'partly', 'broadly']
BOOSTERS = ['definitely', 'clearly', 'obviously', 'certainly', 'really', 'actually',
            'of course', 'plainly']
ENGAGE = [r'\bwe\b', r'\bour\b', r'\byou\b', r'\bus\b']
NOMINAL = [r'\w{3,}tion\b', r'\w{3,}ment\b', r'\w{4,}ness\b', r'\w{4,}ity\b',
           r'\w{4,}ance\b', r'\w{4,}ence\b']
BANNED = ['delve', 'foster', 'crucial', 'underscore', 'meticulous', 'landscape',
          'realm', 'testament', 'pivotal', 'furthermore', 'moreover',
          'it is worth noting', 'in conclusion', 'additionally', 'notably',
          'seamless', 'robust solution', 'leverage']

# (label, key, target_low, target_high, higher_is_better)
TARGETS = [
    ("sentence stdev",      "stdev",   13,  16,  True),
    ("nominalisations /1k", "nominal", 0,   30,  False),
    ("hedges /1k",          "hedge",   8,   12,  True),
    ("local repetition %",  "repeat",  25,  30,  True),
    ("engagement /1k",      "engage",  35,  50,  True),
]


def clean(t):
    t = re.sub(r'```.*?```', '', t, flags=re.S)
    t = re.sub(r'\|.*\|', '', t)
    t = re.sub(r'^[#>].*$', '', t, flags=re.M)
    t = re.sub(r'`[^`]*`', '', t)
    return t


def measure(txt):
    words = re.findall(r"[a-z']+", txt.lower())
    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', txt) if len(s.split()) > 3]
    lens = [len(s.split()) for s in sents]
    n = max(len(words), 1)

    content = [w for w in words if len(w) > 4]
    rep = sum(1 for i, w in enumerate(content) if w in content[max(0, i - 50):i])

    def per1k(pats, raw=False):
        c = sum(len(re.findall(p if raw else r'\b' + p + r'\b', txt.lower()))
                for p in pats)
        return c / n * 1000

    return {
        "words": len(words), "sents": len(sents),
        "mean": st.mean(lens) if lens else 0,
        "stdev": st.stdev(lens) if len(lens) > 1 else 0,
        "short": sum(1 for l in lens if l < 10) / max(len(lens), 1) * 100,
        "long": sum(1 for l in lens if l > 35) / max(len(lens), 1) * 100,
        "repeat": rep / max(len(content), 1) * 100,
        "hedge": per1k(HEDGES),
        "boost": per1k(BOOSTERS),
        "engage": per1k(ENGAGE, raw=True),
        "nominal": per1k(NOMINAL, raw=True),
        "emdash": txt.count("—"),
        "semicolon": txt.count(";"),
        "banned": [(b, len(re.findall(r'\b' + b, txt.lower()))) for b in BANNED
                   if re.search(r'\b' + b, txt.lower())],
        "lens": lens, "sentences": sents,
    }


def bar(v, lo, hi, higher):
    if higher:
        return "PASS" if v >= lo else ("close" if v >= lo * 0.75 else "FAIL")
    return "PASS" if v <= hi else ("close" if v <= hi * 1.25 else "FAIL")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    ap.add_argument("--file")
    ap.add_argument("--worst", action="store_true",
                    help="show the most nominalised sentences")
    args = ap.parse_args()

    root = Path(__file__).parent
    if args.file:
        files = [Path(args.file)]
    else:
        files = sorted(Path(p) for p in glob.glob(str(root / "drafts" / args.version / "*.md")))
    if not files:
        print("nothing to check")
        return

    combined = ""
    print(f"{'file':<26}{'words':>7}{'stdev':>8}{'nom/1k':>9}{'hedge':>8}{'rep%':>7}")
    print("-" * 65)
    for f in files:
        t = clean(f.read_text())
        combined += t + "\n"
        m = measure(t)
        print(f"{f.name:<26}{m['words']:>7,}{m['stdev']:>8.1f}"
              f"{m['nominal']:>9.1f}{m['hedge']:>8.1f}{m['repeat']:>7.1f}")

    m = measure(combined)
    print("\n" + "=" * 65)
    print(f"WHOLE DRAFT   {m['words']:,} words, {m['sents']} sentences")
    print("=" * 65)
    print(f"\n{'marker':<24}{'value':>9}{'target':>14}   status")
    print("-" * 65)
    for label, key, lo, hi, higher in TARGETS:
        v = m[key]
        tgt = f"{lo}-{hi}" if higher else f"under {hi}"
        print(f"{label:<24}{v:>9.1f}{tgt:>14}   {bar(v, lo, hi, higher)}")

    print(f"\nsentence length   mean {m['mean']:.1f}   "
          f"short(<10w) {m['short']:.0f}%   long(>35w) {m['long']:.0f}%")
    print(f"em dashes {m['emdash']}   semicolons {m['semicolon']}")
    print("banned words:", ", ".join(f"{w}({c})" for w, c in m["banned"]) or "none")

    fails = [l for l, k, lo, hi, h in TARGETS if bar(m[k], lo, hi, h) == "FAIL"]
    if fails:
        print(f"\nFAILING: {', '.join(fails)}")
        if "nominalisations /1k" in fails:
            print("  Nominalisation is the strongest marker in the literature.")
            print("  Find the buried verb: 'the reduction of X' -> 'reducing X'.")
        if "sentence stdev" in fails:
            print("  Break the rhythm. After two long sentences, write a short one.")
    else:
        print("\nAll targets met.")

    if args.worst:
        print("\n" + "-" * 65)
        print("MOST NOMINALISED SENTENCES")
        print("-" * 65)
        scored = []
        for s in m["sentences"]:
            w = len(s.split())
            if w < 8:
                continue
            c = sum(len(re.findall(p, s.lower())) for p in NOMINAL)
            if c:
                scored.append((c / w, c, s))
        for r, c, s in sorted(scored, reverse=True)[:12]:
            print(f"\n  [{c} nom, {r*100:.0f}%] {s[:150]}")


if __name__ == "__main__":
    main()
