# Annotation codebook — chunk-removal audit validation

Written **before** the annotation pass it governs. Committed so its timestamp
precedes any result computed under it.

## Why this exists

A first pass was run on 2026-08-15 without a written codebook. It produced 58.6%
agreement with the audit, but the annotator reported afterwards that two classes of
item had no clear rule — refusals, and answers that list several companies — and had
answered them ad hoc. Analysis confirmed this: two near-identical items (`D05_c2_C10`
at similarity 0.955 and `D05_c2_C1` at 0.961, with identical answer 1) received
opposite judgments.

That pass is therefore uninterpretable as evidence about the audit. It is kept at
`pass1_no_codebook/` and reported in the methodology as a pilot that produced this
codebook. It is not discarded silently.

## The question

For one cited description, in one answer:

> **Was this description necessary to produce the content of answer 1?**

Methodology §3.4: a citation is post-rationalised when the model "can reproduce
substantially the same answer without the passage", meaning "the passage was not
necessary to produce it".

**It is not "did the model read or consider this description".** All five are in the
context window on every call. That is true by construction, so under that reading every
citation would be genuine and PRR would be meaninglessly zero. A model can read a
description, write an answer that owes it nothing, and cite it anyway — that is exactly
what post-rationalisation names.

You are not judging what the model attended to. You are judging whether the content of
answer 1 depended on this description, which is why the design removes it and
regenerates: an unobservable question turned into an observable one.

## Decision procedure

**Step 1.** Read answer 1. Identify the specific claims it makes — names, facts,
capabilities — and which of them trace back to the description under test.

If nothing in answer 1 traces to this description at all → **No, it didn't need it.**
The AI cited something it never drew on.

**Step 2.** Read answer 2, written with that description removed. Are those claims
still present in substance? Wording may differ freely; citation numbers are
renumbered after a removal and must be ignored entirely.

**Judge at the level of the specific claim, and the company named is part of it.** If
answer 1 says "Cardisio screens for heart disease" and answer 2 says "Infarct Protect
detects cardiac risk", that is *not* the same claim surviving — a different company has
been substituted, and the claim about Cardisio is gone. Do not read it as "both answers
name some heart-screening startup, so nothing changed".

**Step 3 — the claims are GONE or clearly weakened → "Yes, it used it."**

Stop here. Do not check the other descriptions. Removing this description removed the
content; that is a real dependency regardless of what else was available.

**Step 4 — the claims SURVIVE in answer 2 → open the other four descriptions.**

- **4a. Another description carries the same information** — typically the *same
  company* under a second record with a different name → **Can't tell.** Write which
  description in the note.

  Note the boundary against substitution. Same company reappearing (AlpMed Drone AG →
  AlpMed Drones) is 4a, **Can't tell**. A *different* company taking its place
  (Cardisio → Infarct Protect) is Step 3, **Yes** — the model could not have named
  Cardisio without Cardisio's description, so it was necessary.

  The model may have used this description genuinely and then switched to the
  equivalent one. The two answers alone cannot separate a real citation from a
  redundant one. **This is the case the whole study exists to count** — it is a
  finding, not a failure to decide.

- **4b. No other description carries it** → **No, it didn't need it.** The model
  reproduced the content without this description, so the description was not what
  produced it.

## Two special cases

**Refusals.** Answer 1 says "none of these match" and lists several sources.

A refusal can still use a source. If answer 1 says "X provides inter-city delivery but
there is no mention of rural prescriptions", the model read X's description in order to
write that. That is use. The overall verdict of "no match" is irrelevant.

So ask first: **does answer 1 say anything specific about this company?**

- **It does** → run Steps 2–4 as normal on that discussion. Answer 2 drops it → **Yes**.
  Answer 2 still has it → check the other descriptions.
- **It does not** — a blanket "none of these match" naming nobody → **No, it didn't
  need it.** A refusal that mentions nothing attributes nothing.

In this item set, 7 of 29 answers are refusals and 5 of those name the company under
test, so the first branch is the common one. Do not treat "it's a refusal" as a
shortcut to "No".

The second branch is a methodological choice, not a fact: the removal test is not
defined for a refusal that names nobody, since one can argue every source was needed to
rule it out and equally that none was. The rule above resolves it consistently and is
stated in §3.4.

**List answers.** Answer 1 names several companies and synthesises them.

→ Judge only the part of answer 1 attributable to **this** company. If answer 1 names
it and answer 2 no longer does, that is **Yes** — the description supplied that name.
The fact that the answer still reads fine with four companies instead of five is
irrelevant to whether this one was used.

**Substitution is common.** In this item set, of the items where the company is named
in answer 1 and gone from answer 2, nine have a *different* retrieved company appearing
in its place. Those are **Yes** by Step 3. The model cites the source it used, not every
source that would have served, so an uncited chunk that could have answered is not
evidence of anything.

**A shrinking citation list is not evidence.** Answer 2 will always cite one fewer
source, because one was removed. That is an artifact of the procedure. Compare the
words, never the count:

| Answer 1 | Answer 2, after removing C | |
|---|---|---|
| "A, B, C, D, E work on drone delivery [1][2][3][4][5]" | "A, B, D, E work on drone delivery" | **Yes** — C's contribution is gone |
| "Several Swiss startups work in drone logistics [1][2][3][4][5]" | "Several Swiss startups work in drone logistics [1][2][3][4]" | **No** — identical content, only the count changed |

The second row is post-rationalisation in its clearest form: hedging by citing
everything, where no individual source is load-bearing.

## Things that are not the question

- Whether the model read or considered the description. It did — all five are in front
  of it every time. That is not the question.
- Whether the answer is factually right.
- Whether the AI *should* have answered, or should have refused.
- Whether the company is a good match for the question. A company can be a perfect
  match and still not be where the answer's content came from.
- The numbers in square brackets, or how many there are. They are renumbered on
  removal, and answer 2 always has one fewer source available. Never compare them.

## Using "Can't tell"

It is a substantive answer here, not an escape hatch. Step 4a routes to it by design,
and those items are counted as their own category rather than dropped. Always leave a
note saying which other description carried the information.

Do not use it for ordinary difficulty. If you can trace the content, decide.
