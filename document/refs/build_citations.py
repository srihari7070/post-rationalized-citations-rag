"""
Convert in-text citations to the footnote style the SRH template requires, and
generate the three reference lists it asks for.

The template is explicit: references go in Word footnotes (Alt+Ctrl+F), Times New
Roman 10pt single-spaced, containing a short reference of author surname, year and
page range. Indirect quotations take a "cf." prefix. In-text (Author, Year) is not
the required format.

python-docx cannot create real Word footnotes. So this writes markdown footnote
markers and a per-chapter short-reference block, which convert to Word footnotes
in one mechanical pass. That manual step is documented rather than hidden.

    python document/refs/build_citations.py --check     # what would change
    python document/refs/build_citations.py --apply     # rewrite v2 in place
    python document/refs/build_citations.py --lists     # write the three lists
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "document/refs/references.yaml"
DRAFT = ROOT / "document/dictation/dictated"
OUT = ROOT / "document/refs"


def load():
    return yaml.safe_load(REFS.read_text())


def surname(a):
    return a.split(",")[0].strip()


def _y(e):
    return f"{e['year']}{e.get('suffix','')}"


def short_ref(e, pages=None, cf=True):
    """Short reference for the footnote. Template: surname, year, page range.
    More than one author collapses to the first plus 'et al.'."""
    names = e["authors"]
    if len(names) == 1:
        who = surname(names[0])
    elif len(names) == 2:
        who = f"{surname(names[0])} and {surname(names[1])}"
    else:
        who = surname(names[0]) + " et al."
    core = f"{who} {_y(e)}"
    pg = pages or e.get("pages")
    if pg:
        pg = str(pg)
        # journals that number by article rather than page
        core += f", {pg}" if pg.lower().startswith("article") else f", pp. {pg}"
    # Every citation in this thesis is an indirect quotation, so all take the
    # "cf." prefix the template prescribes. Direct quotations would omit it.
    return ("cf. " if cf else "") + core


def full_ref(e):
    """Full entry for the reference lists."""
    names = e["authors"]
    if len(names) > 6:
        auth = ", ".join(names[:6]) + ", et al."
    else:
        auth = ", ".join(names)
    s = f"{auth} ({_y(e)}). {e['title']}."
    if e.get("venue"):
        s += f" {e['venue']}"
        if e.get("volume"):
            s += f", {e['volume']}"
            if e.get("number"):
                s += f"({e['number']})"
        if e.get("pages"):
            s += f", {e['pages']}"
        s += "."
    return s


# in-text patterns the draft currently uses
PAREN = re.compile(r"\(([A-Z][A-Za-z\-\.]+(?:\s*(?:and|&)\s*[A-Z][A-Za-z\-\.]+)?"
                   r"(?:\s+et\s+al\.)?),\s*((?:19|20)\d{2}[a-z]?)"
                   r"(?:,[^)]*)?\)")
NARRATIVE = re.compile(r"\b((?:van |de |von |del |della )?[A-Z][A-Za-z\-]+"
                       r"(?:\s*(?:and|&)\s*(?:van |de |von )?[A-Z][A-Za-z\-]+)?"
                       r"(?:\s+et\s+al\.)?)\s+\(((?:19|20)\d{2}[a-z]?)\)")


def index_by_author_year(entries):
    """Index on surname and year. Names with a particle (van Dort, de Rijke) are
    registered under both the full surname and the particle-stripped form, since
    in-text usage varies."""
    idx = {}
    for e in entries:
        first = surname(e["authors"][0]).lower()
        y = str(e["year"])
        idx[(first, y)] = e
        if e.get("suffix"):
            idx[(first, y + str(e["suffix"]))] = e
        parts = first.split()
        if len(parts) > 1 and parts[0] in {"van", "de", "von", "del", "della"}:
            idx[(" ".join(parts[1:]), y)] = e
    return idx


def resolve(name, year, idx):
    """Match an in-text citation to a database entry."""
    n = re.sub(r"\s+et\s+al\.$", "", re.sub(r"\s+", " ", name)).strip()
    n = re.sub(r"^[A-Z]\.\s+", "", n)                  # strip disambiguating initials
    first = n.split(" and ")[0].split(" & ")[0].strip().lower()
    if (first, year) in idx:
        return idx[(first, year)]
    parts = first.split()
    if len(parts) > 1 and parts[0] in {"van", "de", "von", "del", "della"}:
        return idx.get((" ".join(parts[1:]), year))
    return None


# System/method names used in place of author-year in this thesis's own prose
# (RAGAS, CiteFix, SR-NLE, ...). The in-text form never becomes "Author (Year)" --
# the template still needs a footnote at first mention, so this maps the name
# actually spoken to the database key that names it.
SYSTEM_ALIASES = {
    "RAGAS": "es2024", "ALCE": "gao2023alce", "CiteFix": "maheshwari2025",
    "Trust-Align": "song2025trustalign", "SynCheck": "wu2024syncheck",
    "Self-RAG": "asai2024selfrag", "ATM": "zhu2024atm", "RARR": "gao2023rarr",
    "Self-Refine": "madaan2023", "Constitutional AI": "bai2022",
    "SR-NLE": "wang2025srnle", "LIME": "ribeiro2016", "SHAP": "lundberg2017",
    "FActScore": "min2023factscore", "LongCite": "zhang2024longcite",
    "CUE-R": "jain2026cuer", "RAGonite": "roy2025", "VeriCite": "ma2026vericite",
    "FACTUM": "dassen2026factum", "Sentence-BERT": "reimers2019",
    "Cohen's kappa": "cohen1960", "Cohen's h": "cohen1988",
    "Benjamini-Hochberg": "benjamini1995", "G-Cite": "saxena2025",
}


def convert(text, idx, entries_by_key, counter, used):
    """Replace in-text citations with footnote markers."""
    def sub(m, narrative):
        name, year = m.group(1), m.group(2)
        e = resolve(name, year, idx)
        if not e:
            return m.group(0)                          # leave unresolved, reported later
        counter[0] += 1
        n = counter[0]
        used.append((n, e, narrative))
        # narrative form keeps the author visible in the sentence
        return f"{name} ({year})[^{n}]" if narrative else f"[^{n}]"

    text = NARRATIVE.sub(lambda m: sub(m, True), text)
    text = PAREN.sub(lambda m: sub(m, False), text)

    # system-named citations: footnote only the first mention per file, so a
    # name used six times in one section doesn't get six footnote numbers
    for name, key in SYSTEM_ALIASES.items():
        e = entries_by_key.get(key)
        if not e:
            continue
        pattern = re.compile(r"\b" + re.escape(name) + r"\b(?!\[\^\d+\])")
        done = [False]
        def sub_alias(m):
            if done[0]:
                return m.group(0)
            done[0] = True
            counter[0] += 1
            n = counter[0]
            used.append((n, e, True))
            return f"{m.group(0)}[^{n}]"
        text = pattern.sub(sub_alias, text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--lists", action="store_true")
    a = ap.parse_args()

    entries = load()
    idx = index_by_author_year(entries)
    entries_by_key = {e["key"]: e for e in entries}

    if a.check or a.apply:
        cited_keys = set()
        for f in sorted(DRAFT.glob("*.md")):
            txt = f.read_text()
            counter, used = [0], []
            new = convert(txt, idx, entries_by_key, counter, used)

            # unresolved citations
            leftover = set()
            for m in list(PAREN.finditer(new)) + list(NARRATIVE.finditer(new)):
                if not resolve(m.group(1), m.group(2), idx):
                    leftover.add(f"{m.group(1)} {m.group(2)}")

            if used:
                block = ["", "---", "", "### Footnotes",
                         "", "*Convert each to a Word footnote (Alt+Ctrl+F), "
                         "Times New Roman 10pt, single-spaced.*", ""]
                for n, e, narrative in used:
                    block.append(f"[^{n}]: {short_ref(e, cf=True)}")
                new = new.rstrip() + "\n" + "\n".join(block) + "\n"

            for _, e, _ in used:
                cited_keys.add(e["key"])

            status = "would write" if a.check else "wrote"
            print(f"{f.name:<26} {len(used):>3} citations  "
                  + (f"UNRESOLVED: {', '.join(sorted(leftover))}" if leftover else ""))
            if a.apply:
                f.write_text(new)

        uncited = [e["key"] for e in entries if e["key"] not in cited_keys]
        print(f"\ncited: {len(cited_keys)}/{len(entries)}")
        if uncited:
            print(f"in database but not yet cited ({len(uncited)}):")
            for k in uncited:
                e = next(x for x in entries if x["key"] == k)
                print(f"  {k:<22} -> {e['job'][:88]}")

    if a.lists:
        # 1. alphabetical
        alpha = sorted(entries, key=lambda e: (surname(e["authors"][0]).lower(), e["year"]))
        lines = ["# Alphabetical List of References", ""]
        lines += [f"{full_ref(e)}\n" for e in alpha]
        (OUT / "references_alphabetical.md").write_text("\n".join(lines))

        # 2. chronological
        chrono = sorted(entries, key=lambda e: (e["year"], surname(e["authors"][0]).lower()))
        lines = ["# Chronological List of References", ""]
        cur = None
        for e in chrono:
            if e["year"] != cur:
                cur = e["year"]
                lines += [f"## {cur}", ""]
            lines.append(f"{full_ref(e)}\n")
        (OUT / "references_chronological.md").write_text("\n".join(lines))

        # 3. by bibliography type
        names = {"journal": "Journal Articles", "conference": "Conference Papers",
                 "preprint": "Preprints", "book": "Books", "web": "Online Sources"}
        groups = defaultdict(list)
        for e in entries:
            groups[e["type"]].append(e)
        lines = ["# Reference List by Bibliography Type", ""]
        for t in ["journal", "conference", "preprint", "book", "web"]:
            if not groups[t]:
                continue
            lines += [f"## {names[t]} ({len(groups[t])})", ""]
            for e in sorted(groups[t], key=lambda x: surname(x["authors"][0]).lower()):
                lines.append(f"{full_ref(e)}\n")
        (OUT / "references_by_type.md").write_text("\n".join(lines))

        print(f"wrote three reference lists to {OUT}/  ({len(entries)} entries)")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--check")
    main()
