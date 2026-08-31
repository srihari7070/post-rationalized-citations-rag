# References

## Files

| File | Contents |
|---|---|
| `references.yaml` | Master database. 46 entries, each with a `job` field naming the claim it supports and where |
| `references_alphabetical.md` | Template section: Alphabetical List of References |
| `references_chronological.md` | Template section: Chronological List of References |
| `references_by_type.md` | Template section: Reference List by Bibliography Type |
| `build_citations.py` | Converts in-text citations to footnote markers, generates the three lists |

## The job field

Every entry states the specific claim it supports and the chapter it belongs in. An entry
with no job does not go in the thesis. This is the filter against citing papers to reach a
count, and it means each of the 46 can be defended if asked why it is there.

One reference was removed during this process for exactly that reason. Liang et al. (2023)
on AI detector bias was in the database but has no job inside the thesis itself, since it
belongs to the writing process rather than the research. It was dropped rather than forced
into a section.

## Usage

```bash
python3 document/refs/build_citations.py --check    # report, change nothing
python3 document/refs/build_citations.py --apply    # rewrite drafts/v2 in place
python3 document/refs/build_citations.py --lists    # regenerate the three lists
```

`--apply` is not idempotent. Run it once on clean text. Re-running over already-converted
files will double-convert. Keep a copy before applying.

## Citation format, and the manual step that remains

The SRH template requires footnotes, not in-text author-year:

> For any reference, use the Insert footnote function in MS Word... Inside the footnote
> itself, incorporate a so-called short reference... the author's last name, the year of
> publication and the page range.

Footnotes are Times New Roman, 10pt, single-spaced. Indirect quotations take a `cf.` prefix.

The draft now carries footnote markers `[^1]` in the text and a short-reference block at the
end of each chapter. **These are not yet Word footnotes.** python-docx cannot create real
Word footnotes, so converting them is a manual pass in Word: place the cursor at each
marker, press Alt+Ctrl+F, and paste the corresponding short reference from the block at the
end of the chapter. Delete the block afterwards.

Every citation in this thesis is an indirect quotation, since nothing is quoted verbatim
from a source. All short references therefore carry `cf.`. A direct quotation would omit it.

## Known gaps

**Page ranges are missing for preprints.** The template asks for a page range in every short
reference. arXiv preprints have no stable pagination, so those short references carry author
and year only. Worth confirming with the supervisor whether that is acceptable or whether a
section number should be substituted.

**Article-numbered journals.** Two entries (Ji et al. 2023, Huang et al. 2025) are in
journals that number by article rather than page. Those render as `Article 248` and
`Article 42` rather than a page range.

**Verification status varies.** The `verified` field records how each entry was checked:
`full` means the paper's own text was read, `abstract` means the claim was checked against
an abstract or authoritative summary, `proposal` means it was carried from the research
proposal's reference list and verified on 14 August. Seven are `full`, most are `abstract`.
