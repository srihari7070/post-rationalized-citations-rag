# Pilot pass: the 0.85 threshold does not survive human judgment

> **Status: superseded as a headline result.** The annotator reported afterwards that
> refusals and list-answers had no clear rule, and the data confirmed it — see "What
> this does not yet establish". `CODEBOOK.md` was written in response and a second
> pass is pending. The threshold analysis below stands on its own, since it does not
> depend on the ambiguous items; the agreement figure does not.

One annotator (Srihari), 29 items, detailed survey, blind to verdicts and similarity.
Scored 2026-08-15. Raw output in `validation_results_full.json`.

## Headline

| | at the 0.85 threshold used throughout the thesis |
|---|---|
| Agreement | **17/29 (58.6%)** |
| Cohen's kappa | **0.209**, CI [−0.089, 0.508] |

The README set 60% as the line below which "the measure does not track the construct".
This falls below it. The kappa interval includes zero, so on this evidence the audit
cannot be shown to beat chance at 0.85.

## But the measure is not dead — the cutoff is wrong

The disagreements are not scattered. They are almost entirely one-directional:

| | human: genuine | human: post-rationalised |
|---|---:|---:|
| **audit: genuine** | 11 | 2 |
| **audit: post-rationalised** | **10** | 6 |

Ten of the twelve disagreements are the audit calling a citation fake where the reader
judged it real. The audit over-flags post-rationalisation.

Similarity itself still carries real signal about the human's judgment — AUC 0.774,
where 0.50 would mean none at all. Mean similarity was 0.911 where the reader said
"not really used" against 0.787 where they said "genuinely used". The ordering is
right; the cutoff is in the wrong place.

Every one of the twelve disagreements sits at similarity ≥ 0.845. Below that, reader
and audit agree on 11 of 13.

## Moving the threshold fixes the agreement

| Threshold | Agreement | Kappa |
|---|---|---|
| 0.85 (current) | 17/29 (59%) | +0.209 [−0.09, +0.51] |
| 0.88 | 22/29 (76%) | +0.418 [+0.02, +0.75] |
| **0.90** | **23/29 (79%)** | **+0.439 [+0.01, +0.79]** |
| 0.92 | 23/29 (79%) | +0.439 [+0.01, +0.79] |
| 0.95 | 23/29 (79%) | +0.387 [−0.06, +0.79] |

At 0.90 the kappa interval clears zero and agreement reaches the "partly valid" band.

## The collision

Section 4.7 reports that the correction-loop effect is maximal at exactly 0.85 and
collapses on either side: **Mistral's −12.8pp becomes −1.1pp at 0.90, and zero at
0.95.**

So the threshold at which the measure agrees with human judgment is the threshold at
which the thesis's only statistically significant finding disappears. The two cannot
both be defended. This needs to be resolved before the results chapter stands.

A second consequence: because a lower threshold classifies more citations as
post-rationalised, the baseline PRR figures in Table 4.1 (24.6 / 22.2 / 20.6%) are
over-estimates relative to what a reader would call post-rationalisation.

## Where it fails, by query type

| Type | Agreement |
|---|---|
| A answerable | 7/8 (88%) |
| B broad/ambiguous | **2/8 (25%)** |
| C hard/paraphrased | 3/6 (50%) |
| D unanswerable | 5/7 (71%) |

Type B is where it breaks. Those answers cite four or five sources and synthesise
them. Remove any one and the other four still carry the answer, so similarity stays
high and the audit calls every citation fake — while the reader judges that each one
genuinely contributed its part.

That is a structural limit, not noise. B and D fail by the same mechanism, which is
worth stating as one limitation rather than two:

- **Type B**: the answer lists five companies. Remove one, four remain, similarity
  stays high.
- **Type D**: the refusal enumerates five companies. Remove one, four remain,
  similarity stays high.

**Whole-answer cosine similarity cannot detect the loss of one item from an
enumeration.** The removal test works where a single source carries the answer and
fails where the answer enumerates, whether that enumeration is an answer or a refusal.
That covers 15 of the 29 items. Agreement by number of sources cited: 8/10 (80%)
single-source, 2/7 (29%) multi-source.

A reporting caveat follows for Type D. On 4 of those 7 items the codebook's refusal
convention determines the outcome with no judgement left: answer 1 names the company,
answer 2 does not, no duplicate record exists, so the rule gives "Yes" while the audit
says post-rationalised on 6 of the 7. Those items inflate inter-annotator agreement
(everyone applies the same rule) and depress human-vs-audit agreement for a structural
rather than empirical reason. Report Type D separately and say that its figure reflects
the convention, not judgement.

## What this does not yet establish

This is one annotator on 29 items, and that limits it hard.

- The reader called 21 of 29 citations genuine (72%). Always answering "genuine"
  would score 72% — better than the audit at 0.85, and only 7pp below it at 0.90. On
  n=29 that margin is thin.
- With one annotator there is no way to separate "the audit is mis-calibrated" from
  "this annotator was lenient". A reader shown the description alongside the answers
  can drift into judging whether the description is *reflected in* the answer
  (relevance) rather than whether the answer *changed without it* (necessity). That
  drift would produce exactly this one-directional pattern.

Both readings predict the same data. Two more annotators on the detailed survey
separate them: if independent readers also land near 72% genuine, the audit is
mis-calibrated; if they scatter, the signal is annotator noise.

## Pass 2 under the codebook — the codebook is not a discriminating instrument

Same annotator, same 29 items, now following `CODEBOOK.md`.

| | pass 1, no codebook | pass 2, with codebook |
|---|---|---|
| Agreement | 17/29 (58.6%) | **14/28 (50.0%)** |
| Kappa | 0.209 [−0.089, 0.508] | **0.062 [0.000, 0.214]** |
| "genuine" | 21/29 (72%) | **27/28 (96%)** |

Worse, and for a reason that has nothing to do with the annotator or the audit: the
response is now nearly constant. Ninety-six per cent of one label makes kappa
approximately zero whatever the audit does.

**The cause is the codebook, not the annotator.** Its Steps 1–3 mechanically yield
"needed" on 24 of the 29 items, and pass 2 matches that mechanical prediction on 25 of
29. The annotator applied the rules faithfully; the rules have almost no variance to
give.

The reason is structural. Step 1 asks whether answer 1 contains something from this
description; Step 3 asks whether it is gone from answer 2. But the model normally
mentions a company because it read that company's description, and once the description
is removed it can no longer mention it. "Did content disappear" is therefore true almost
by construction, and the instrument cannot discriminate.

The blind/leaked split cannot be read as evidence about the blinding breach: the leaked
set is exactly the pass-1 disagreements plus Type D, so it was selected for items where
the audit says post-rationalised. Any agreement difference across that split is
selection, not contamination.

### What this actually shows: the construct is underdetermined

Three readings of "did the model use this source" have been in play, and they give
wildly different answers on the same data:

| Reading | Operationalisation | PRR it implies |
|---|---|---|
| Did the model attend to it | all five are in context | ~0%, vacuous |
| Did any content trace to it and vanish | the codebook | ~4% (1 of 28) |
| Did the whole answer materially change | the audit, cosine ≥ 0.85 | 20–25% |

None is obviously wrong. They differ in **granularity**: at the level of a single
company mention almost every citation is load-bearing; at the level of the whole answer
many are not. The 0.85 cosine threshold silently picks a coarse granularity that a
human tracing content does not share, and that — not annotator error — is what both
passes have been measuring.

A fourth framing, closer to what the annotator's own instinct kept reaching for across
both passes, is *"would the answer to the user's question have been materially worse
without this source?"* It has variance where the codebook has none: dropping one of five
hedged mentions leaves the answer no worse, while losing the only company that answers
the question plainly does. It has not been tested.

**This is a decision about the thesis's central measurement and should not be settled
by another unilateral rewrite of the codebook.** Two passes have now been spent on two
different construct definitions. Take it to supervision before spending a third.

## Blinding breach — who can annotate pass 2

While preparing the second pass, 17 of the 29 items had their similarity score or audit
verdict displayed to the pilot annotator: 12 through the disagreement table above, 7
more through a Type D breakdown printed during a discussion of the codebook. The audit
verdict is exactly `similarity >= 0.85`, so a score is a verdict.

The pilot annotator is therefore no longer blind on 59% of the set and **cannot provide
independent judgements for pass 2**. Their appropriate role is now adjudicator: after
the blind annotators finish, they resolve disagreements and characterise them, which
does not require blinding and uses the understanding of the corpus they have built.

Pass 2 needs **three annotators who have seen none of this analysis**. The instruments,
the codebook and the practice items are all self-contained, so no briefing is required
beyond sending the file.

## Next

1. **Settle the construct first, in supervision.** Which granularity does PRR claim to
   measure? Until that is answered, no annotation pass can validate anything, because
   the instrument's answer depends entirely on the choice. Two passes have been lost to
   this.
2. **Then three blind annotators on `survey.html`**, all 29 items — not including the
   pilot annotator, per the blinding breach below.
3. Re-run `threshold_sensitivity.py` and report the full results table at 0.90
   alongside 0.85, rather than 0.85 alone.
4. Add the enumeration limit to §3.4 as a stated scope condition: the removal test is
   valid where one source carries the answer, and insensitive where the answer
   enumerates several (types B and D, 15 of 29 items here).
5. Do not present PRR as validated until 1 is done.
