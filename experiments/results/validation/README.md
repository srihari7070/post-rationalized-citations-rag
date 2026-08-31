# Audit Construct Validation

Checks whether the chunk-removal audit measures what the thesis claims it measures.

## Why

The thesis rests on this inference: removing a cited chunk left the answer largely
unchanged, therefore the model never needed that chunk. That has never been tested
against human judgment. Right now it is an assumption presented as a measurement.

One specific way it could be wrong: the answer may have stayed similar because a
*different* retrieved chunk carried equivalent information, so the model simply switched
to that one. In that case the original citation was genuine and the audit is wrong.
Nothing in the pipeline distinguishes these cases.

## Three instruments, two claims

The same 29 items (30 with the attention check) are asked about in three different
ways.

| | `survey_simple.html` | `survey_fast.html` | `survey.html` |
|---|---|---|---|
| Asks | Which company answers this question? | Is this detail still in Answer 2? | Did the AI really use this description? |
| Shows | question + 5 company names, one line each, full text a click away | the tested chunk + 4 others, each compressed to 2-3 bullets; both answers with word-level diff highlighting | the two answers, all five descriptions, the lot |
| Answer | pick one, or "none of these" | Still there / Gone / Not sure | Yes / No / Can't tell |
| Time | ~20 sec an item, ~10 min total | ~15-20 sec an item, ~10 min total | ~40 min |
| For | anyone | anyone | you, and anyone who will read closely |

**The quick one is a convergent check, not a replication.** People pick the company a
reader would use; agreement means the AI cited the source a reader would have picked.
That validates citation correctness — the CCR figures in Table 4.11, currently
unvalidated — and it surfaces the duplicate-company problem directly, because you can
see when several people independently choose a company the AI did not cite. It does
**not** validate PRR. Only the detailed survey does that.

**`survey_fast.html` asks the actual PRR question, compressed for speed.** Unlike the
simple survey, it targets the same construct as the detailed one — did the answer lose
this chunk's specific content — but narrows the codebook's three-step reasoning down to
one glance: does the highlighted detail from the tested chunk still show up in Answer
2. It's built from `evaluation/build_survey_fast.py`, which reuses the exact same 29
sampled items and item ids as `survey.html` (so `score_annotations.py` needs no
changes and `mode` is reported as `"full"` for both), just rendering each retrieved
company as two or three compressed bullets instead of full paragraphs, and diffing the
two answers word-by-word instead of asking the annotator to spot the difference
unaided. Regenerate it with `python evaluation/build_survey_fast.py` any time
`survey.html`'s underlying sample changes.

It is **not a replacement for `survey.html`, it's a faster attempt at the same
question**, and it trades away some rigor for speed: it does not show the other four
chunks' full text (so an annotator can't independently verify a surviving detail isn't
*also* available from a different chunk — the redundancy question CUE-R raises), and
it collapses the codebook's three-step reasoning into a single recognition judgment.
Whether that trade is acceptable is itself an empirical question — compare its
agreement-with-audit and inter-annotator agreement against `survey.html`'s once both
have real annotators, not just assumed.

Report them as two separate results. The scoring script refuses to pool them.

Option order is randomised, and the cited company is spread evenly across the five
positions (6/6/6/6/5), so it cannot be found by position. `survey_simple.html`
contains no answers and no record of which company was cited — scoring resolves each
pick against `answer_key.json` — so an annotator reading the page source finds
nothing.

## Read this first

`CODEBOOK.md` defines how to answer. It was written after a first pass showed two
classes of item had no clear rule, and it must be read before annotating and not
changed once a pass has begun. The rules are also on every item screen under
"How to decide".

The first pass is preserved at `pass1_no_codebook/` and reported as a pilot. See
`FINDING.md` for what it showed and why it is not interpretable on its own.

## How to run it

```
python evaluation/build_annotation_set.py --n 30   # sample + answer key
python evaluation/build_survey.py                  # writes both survey files
```

Send `survey_simple.html` around. It is one self-contained file: no server, no
install, works offline. People open it, give a name, do two worked examples with
feedback, then answer 29 multiple-choice questions. Number keys work. Progress saves
in their browser. At the end one button gives them `answers_simple_<name>.csv`.

Do `survey.html` yourself. Same items, same order, full context.

Drop every returned CSV into `annotations/` and run:

```
python evaluation/score_annotations.py
```

It splits by the `mode` column and reports each instrument separately.

### Blinding is fragile — protect it

`answer_key.json` is not the only leak. The audit verdict is exactly
`similarity >= 0.85`, so **showing an annotator a similarity score shows them the
verdict**. That includes the disagreement table in `FINDING.md`, the per-band and
per-type breakdowns, and any ad-hoc analysis printed per item id.

Anyone who will annotate must not see diagnostic output for items they have not yet
judged. Keep the analyst and annotator roles separate, or run the analysis only after
all annotation is complete.

This was breached during the pilot: 17 of 29 items had their similarity or verdict
shown to the pilot annotator while the second pass was being prepared. That annotator
is therefore no longer blind and cannot contribute independent judgements to pass 2;
see `FINDING.md`.

**Nobody should open `answer_key.json` before annotating** — it holds the verdicts and
similarity scores, and seeing them destroys the blinding.

## How many annotators

Aim for at least three. One annotator gives agreement with the machine but no way to
show the judgments are reproducible, which is the first thing a reviewer will ask.
Three or more also yields Fleiss' kappa between annotators, and the pooled majority
vote is a far more defensible ground truth than one person's opinion.

The scoring script handles any number, reports per-annotator and pairwise agreement,
and flags anyone who failed the attention check planted at position 12.

Annotators need no background in computing, AI or the project. `survey_simple.html`
is a multiple-choice quiz that needs no explanation at all; `survey.html` builds up
from an everyday analogy (a student padding a bibliography) to a three-branch decision
rule. Both open with two worked examples that give feedback. Mixed expertise is fine
and arguably better: if agreement holds across people who do and do not know the
study, the measure is not resting on a shared prior.

What is written for lay readers is the framing. **The stimulus is not touched** — the
questions, the company descriptions and the answers appear exactly as the model saw
and produced them, word for word. Only presentation changes: scraped metadata folded
behind a toggle, concatenated description fields split at their `..` joins into
paragraphs, one-line previews with the full text one click away, and consistent plain
vocabulary ("description", never "chunk" or "source"). This was verified rather than
assumed: a check across all 145 chunks in the item set confirms every word still
appears, unaltered.

## What you see, and what is hidden

Shown: the question, the source under test, the answer with that source present, the
answer after it was removed, and the other retrieved sources behind a toggle. The other
sources matter, because without them you cannot judge whether the information was
uniquely in the chunk being tested.

Hidden: the similarity score, the audit verdict, the condition.

Not shown: the individual rounds of the sequential audit. That is the machine's working,
and it would leak the answer you are meant to reach independently.

## Reading load

A detailed item is a median of 392 words on screen: the description under test, the two
answers, and one line for each of the other four descriptions. Opening all four in full
takes it to 857, which is why they start collapsed — step 4 usually resolves from the
one-liners.

Shortening the descriptions themselves was tested and rejected: removing every sentence
that repeats one already shown saves 4%. The text only looks padded.

Highlighting which description sentences echo answer 1 was also rejected, though it
would save more. On many items nothing would be highlighted, and that single cue
effectively answers the question — a lexical proxy standing in for the judgment being
validated.

## Two things that confuse people

**Citation numbers are renumbered after removal.** Take source [1] away and the
remaining four become [1]–[4]. So [1] in the left answer is not [1] in the right one.
Compare the words, never the numbers. The survey warns about this on every item.

**The corpus contains near-duplicate company records.** D05, for instance, retrieves
both "Rigi Technologies SA" and "RigiTech" — the same company twice. Remove one and
the answer can still name the company from the other. That is not a bug in the
interface; it is exactly the redundancy confound this study exists to detect, so
annotators should notice it and say so in the note box.

## Type D items are a different construct

Seven of the 29 items come from Type D, unanswerable queries, where the answer is a
refusal that cites sources while saying none of them match. The removal test is not
well defined there: you can argue every source was needed to justify the refusal, or
that none was, since removing any one leaves the refusal standing. The audit always
returns the second.

`score_annotations.py` therefore reports agreement for refusals and assertions
separately. If they diverge, report them separately in the thesis rather than pooling
them into one PRR figure. See section 3.4 of the methodology.

## Sampling

Stratified across similarity bands, over-weighting either side of the 0.85 threshold,
because that is where the measure is most fragile and where roughly half of all real
verdicts fall.

| Band | Range | Share |
|---|---|---|
| far_below | 0.00–0.70 | 15% |
| below | 0.70–0.85 | 30% |
| above | 0.85–0.92 | 35% |
| far_above | 0.92–1.01 | 20% |

Order is shuffled so band membership leaks nothing.

## Interpreting the result

| Agreement | Meaning | Action |
|---|---|---|
| ≥ 80% | Measure is valid | Report kappa in methodology. Also weakens the threshold objection |
| 60–80% | Partly valid | Report honestly, characterise disagreements, soften claims |
| < 60% | Does not track the construct | Stop. Every PRR claim rests on this |

The scoring script also tests whether disagreements cluster at high other-chunk overlap.
If they do, the redundancy explanation above is confirmed and becomes a concrete,
reportable failure mode rather than unexplained noise.

## Note on who annotates

This must be done by a person, not by an AI. The thesis's own Finding 3 is that language
models cannot detect post-rationalisation from text alone, 8.5% recall on the
deterministic run.
Validating an LLM-based measure with an LLM would use precisely the capability the thesis
shows does not work.

Optionally, after finishing, run an AI annotator over the same items as a clearly-labelled
comparison. If human agreement is high and AI agreement is low, that replicates the
discriminator finding on a fresh task and strengthens the discussion chapter.

## Files

| File | Contents |
|---|---|
| `survey_simple.html` | **The one you send around.** Multiple choice, ~10 min |
| `survey.html` | The detailed one. ~40 min, full context, for you |
| `annotations/` | Drop every returned `answers_<mode>_<name>.csv` here |
| `CODEBOOK.md` | **How to answer.** Read before annotating |
| `FINDING.md` | What the pilot pass showed |
| `pass1_no_codebook/` | The pilot pass, kept for the record |
| `answer_key.json` | Verdicts and similarity scores. Do not open before annotating |
| `pick_options.json` | Company names per item, so scoring can report what people chose |
| `validation_results_simple.json`, `validation_results_full.json` | Written by the scoring script, one per instrument |
| `annotate.html` | The original single-reader interface, superseded by `survey.html` |

Item IDs carry the condition (`D05_c1_C12`), because the same query and chunk recur
across conditions with different answers and are distinct items. An earlier version
omitted it and three pairs collided.
