"""
Build the fast validation survey: same 30 sampled items as survey.html, same
scoring format, but each of the five retrieved chunks is compressed to two short
bullets instead of full paragraphs, and the question is simplified to a single
side-by-side comparison.

Reuses survey.html's DATA rather than re-sampling, so item ids and the attention
check stay identical and score_annotations.py needs no changes.

    python evaluation/build_survey_fast.py
    open experiments/results/validation/survey_fast.html
"""
import json
import re
from pathlib import Path

VAL = Path("experiments/results/validation")


def bullets_from_meta(meta):
    """'Founded in 2018. Company size: 11-50. Startup. Switzerland. Prilly. tag1, tag2, ...'
    -> ('Switzerland, founded 2018', 'Engineering, Cleantech')"""
    parts = [p.strip() for p in meta.split(".") if p.strip()]
    year = next((p.replace("Founded in ", "") for p in parts if p.startswith("Founded in")), "")
    country = next((p for p in parts if p and p[0].isupper() and "," not in p
                     and not p.startswith(("Founded", "Company size"))
                     and p not in ("Startup", "Scaleup", "SME", "Enterprise")), "")
    tags_part = parts[-1] if parts else ""
    tags = [t.strip() for t in tags_part.split(",") if t.strip()][:2]
    line1 = ", ".join(x for x in [country, f"founded {year}" if year else ""] if x)
    line2 = ", ".join(tags)
    return line1, line2


def first_sentence(paras):
    if not paras:
        return ""
    text = paras[0]
    m = re.match(r"(.{20,140}?[.!?])(\s|$)", text)
    s = m.group(1) if m else text[:140]
    return s.strip()


def compress_chunk(name, meta, paras):
    line1, line2 = bullets_from_meta(meta)
    return {"name": name, "b1": line1, "b2": line2, "b3": first_sentence(paras)}


def transform(item):
    tested = compress_chunk(item["chunk_name"], item["chunk_meta"], item["chunk_paras"])
    others = []
    for o in item["others"]:
        line1, line2 = bullets_from_meta(o["meta"])
        others.append({"name": o["name"], "b1": line1, "b2": line2, "b3": o.get("preview", "")})
    return {
        "id": item["id"],
        "query": item["query"],
        "tested": tested,
        "others": others,
        "original": item["original"],
        "removed": item["removed"],
    }


def main():
    survey_html = (VAL / "survey.html").read_text()
    m = re.search(r"const DATA\s*=\s*(\[.*?\]);", survey_html, re.S)
    data = json.loads(m.group(1))
    items = [transform(it) for it in data]

    template = (VAL / "survey_fast_template.html").read_text()
    out = template.replace("__ITEMS__", json.dumps(items, ensure_ascii=False))
    (VAL / "survey_fast.html").write_text(out)
    print(f"survey_fast.html written, {len(items)} items")


if __name__ == "__main__":
    main()
