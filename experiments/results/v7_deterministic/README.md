# v7 — Deterministic Run (temperature 0, full 3×3 grid)

**Run completed:** 2026-08-04 · **Status: 12/12 conditions complete**
**Corpus:** 38,692 DACH companies · **Queries:** 75 typed (A/B/C/D) with ground truth
**Supersedes:** v4 — every pre-v7 PRR figure was measured under uncontrolled sampling

---

## Why this run exists

v4 contained a contradiction: C3 and C6 audit **byte-identical** answers yet reported PRR
of 22.1% and 16.0%. Neither model client set a temperature, so both ran at library defaults
(Gemini 1.0, Ollama 0.8). Because the audit regenerates an answer and thresholds cosine
similarity at 0.85, random wording — not chunk importance — was deciding roughly **half**
of all verdicts.

`GEN_TEMPERATURE = 0` makes local generation exactly reproducible. v7 re-runs everything
under that setting, adds Llama 3 as a third generator, and completes the 3×3
generator × discriminator grid.

Investigation detail: `../27_july_meeting_professor/MEETING_NOTES.md` → "Audit Determinism".

---

## All 12 conditions

| Cond | Generator | Discriminator | PRR before | PRR after | Delta | Sig |
|------|-----------|---------------|-----------:|----------:|------:|-----|
| C1  | Gemini  | — baseline | 24.6% | 24.6% | — | — |
| C2  | Gemini  | Mistral    | 24.2% | 24.2% | +0.0pp | ns |
| C5  | Gemini  | Gemini     | 26.0% | 22.4% | −3.5pp | ns |
| C10 | Gemini  | Llama 3    | 24.9% | 24.7% | −0.2pp | ns |
| C3  | Mistral | — baseline | 22.2% | 22.2% | — | — |
| C4  | Mistral | Gemini     | 22.2% | 9.4% | **−12.8pp** | * p=0.031 |
| C6  | Mistral | Mistral    | 22.2% | 9.4% | **−12.8pp** | * p=0.031 |
| C11 | Mistral | Llama 3    | 22.2% | 9.4% | **−12.8pp** | * p=0.031 |
| C7  | Llama 3 | — baseline | 20.6% | 20.6% | — | — |
| C8  | Llama 3 | Llama 3    | 20.6% | 14.1% | −6.4pp | ns |
| C9  | Llama 3 | Gemini     | 20.6% | 14.1% | −6.4pp | ns |
| C12 | Llama 3 | Mistral    | 20.6% | 14.1% | −6.4pp | ns |

Only the Mistral conditions reach significance at n=75.

---

## Finding 1 — The discriminator has zero causal influence (proven)

**Inter-model trust matrix — PRR delta (pp):**

| gen \ disc | Gemini | Mistral | Llama 3 |
|------------|-------:|--------:|--------:|
| **Gemini**  | −3.5 | +0.0 | −0.2 |
| **Mistral** | **−12.8** | **−12.8** | **−12.8** |
| **Llama 3** | **−6.4** | **−6.4** | **−6.4** |

Each row is constant. Swapping the discriminator changes nothing.

Verified at the per-query level across three generator families:

| Generator | Discriminators compared | Verdicts differed | **Outcomes differed** |
|---|---|---|---|
| Mistral | Gemini vs Mistral | 9/75 | **0/75** |
| Llama 3 | Llama 3 vs Gemini | 13/75 | **0/75** |

The discriminators genuinely disagree with each other — and none of that disagreement
reaches the output. Revised answers are byte-identical.

This is architecturally expected (re-prompting is triggered by the chunk-removal audit,
never by the discriminator's verbal judgment) but was previously only an assertion.
Under deterministic conditions it is now **proof**.

**Consequence for the original research question.** C2/C4/C5/C6 were designed to test
whether cross-model discrimination beats same-model discrimination. **That question is
unanswerable in this architecture** — the variable has no path to the outcome. v3's
"cross-model wins for Gemini" and v4's "same-model wins" were both artifacts of audit
noise, measuring nothing.

Discriminator *accuracy* does vary by pairing (59.5%–72.9%), so the discriminators behave
differently. They simply have no effect.

---

## Finding 2 — Generator Correction Receptivity (GCR)

**Of the answers the audit flagged, how often did re-prompting actually reduce PRR?**

| Generator | GCR | Improved / re-prompted | PRR delta |
|-----------|----:|-----------------------:|----------:|
| **Mistral 7B** | **59.1%** | 39/66 | **−12.8pp** |
| **Llama 3 8B** | 36.4% | 24/66 | −6.4pp |
| **Gemini 2.5 Flash** | 14.8% | 12/81 | −1.2pp (ns) |

GCR and PRR reduction rank identically — the more a generator acts on the audit's evidence,
the more post-rationalisation falls. The mechanism behaves as theory predicts, supporting
GCR as a real generator property.

**Gemini rewrites but does not fix.** 25 of 75 C2 answers were genuinely rewritten in
response to the re-prompt, yet PRR did not move. This is not refusal to follow instructions
— it is revision that fails to address the underlying problem.

**Caution.** Both open local models beat the hosted API model, suggesting "open models are
more correctable." With one API model in the sample this is a hypothesis, not a finding.
Mistral and Llama 3 also differ from each other by 23 points, so "local" is not one category.

---

## Finding 3 — Replicate analysis: Gemini's effect is zero

Because the discriminator provably cannot affect outcomes, conditions sharing a generator
are **replicates of one measurement**, not distinct conditions. This gives free error bars.

| Generator | Replicates | Deltas | Mean | Std dev |
|---|---|---|---|---|
| Mistral | C4, C6, C11 | −12.8, −12.8, −12.8 | **−12.8pp** | **0.00** |
| Llama 3 | C8, C9, C12 | −6.4, −6.4, −6.4 | **−6.4pp** | **0.00** |
| Gemini | C2, C5, C10 | +0.0, −3.5, −0.2 | −1.23pp | **2.00** |

Gemini: **95% CI −6.19 to +3.73pp** — spans zero.

**C5's −3.5pp is not a result.** It is the high draw of three noisy measurements of the
same null quantity. Reporting it as a same-model-discrimination advantage would be
reporting API noise — which is exactly what v3 and v4 each did, in opposite directions.

The local models show **exactly zero variance across replicates**, confirming the
temperature fix works for them.

---

## Finding 4 — Models fail in different places

| Generator | Overall | A Answerable | B Ambiguous | C Hard | D Unanswerable |
|-----------|--------:|-------------:|------------:|-------:|---------------:|
| Gemini  | 24.6% | 15.0% | **46.3%** | 6.7% | **57.0%** |
| Mistral | 22.2% | 25.0% | 29.0% | 10.0% | 28.0% |
| Llama 3 | 20.6% | 16.3% | 27.8% | **23.8%** | **16.0%** |

- **Gemini** is best on hard paraphrased retrieval (6.7%) but collapses when no correct
  answer exists — 57% on Type D. It fabricates support rather than declining.
- **Llama 3** is the mirror image: worst on hard retrieval (23.8%), best at not
  fabricating (16.0%).
- **Mistral** is mid-range on every type.

Three models within 4pp on aggregate PRR differ by **3.5×** on Type D. Reporting only the
headline number would make them look interchangeable. Citation counts are comparable
(1.41–1.75/answer), so these are behavioural differences, not citation-style artifacts.

---

## Finding 5 — Correction does not harm correctness

| Generator | CCR baseline → adversarial | Type D abstention |
|---|---|---|
| Gemini  | 76.0% → 76.0% | 30.0% |
| Mistral | 70.0% → 70.0% | 50.0% |
| Llama 3 | 74.0% → 72.0% | 50.0% |

CCR is essentially unchanged. The loop strips redundant citations **without** changing
which company is cited as the answer. Faithfulness improves at no cost to correctness.

Type D abstention — correctly citing nothing when no answer exists — is 30% for Gemini
versus 50% for both local models, consistent with Gemini's high Type D PRR.

---

## Finding 6 — Type D resists correction structurally

PRR delta by type (representative conditions):

| Type | Gemini (C2) | Mistral (C4) | Llama 3 (C8) |
|------|------------:|-------------:|-------------:|
| A Answerable | −1.7 | **−20.0** | −6.7 |
| B Ambiguous | +2.3 | −12.2 | −5.6 |
| C Hard | +0.8 | −5.0 | −10.0 |
| **D Unanswerable** | **+0.0** | −8.0 | **+0.0** |

Type A responds most strongly. Type D is flat for Gemini and Llama 3 — when no correct
citation exists there is nothing for the loop to move toward. This is a structural limit
of correction-based approaches, not a tuning problem.

---

## ⚠ Limitation 1 — The effect peaks at the chosen threshold

PRR delta recomputed from stored similarity scores at other thresholds:

| Cond | 0.75 | 0.80 | **0.85** | 0.90 | 0.95 |
|------|-----:|-----:|---------:|-----:|-----:|
| C4/C6/C11 Mistral | −2.2 | −6.2 | **−12.8** | −1.1 | +0.0 |
| C8/C9/C12 Llama 3 | −2.3 | −2.4 | **−6.4** | −1.1 | −0.4 |
| C5 Gemini | −2.4 | −2.5 | **−3.5** | −1.5 | −0.6 |

**Every condition shows its maximum effect at 0.85.** At 0.90 the −12.8pp headline
collapses to −1.1pp; at 0.95 it is zero.

The direction survives, but that is a weak defence when magnitude drops ~90%.
**This is the most likely line of attack in a viva** and needs addressing head-on.

**There is a legitimate explanation.** Baseline PRR by threshold:

| Threshold | PRR before |
|---|---|
| 0.75 | 62–71% |
| 0.85 | 21–26% |
| 0.95 | 1–6% |

At 0.75 nearly everything is flagged — **ceiling effect**, no headroom to improve.
At 0.95 almost nothing is flagged — **floor effect**, nothing to fix. Only mid-range has
dynamic range. The peak is plausibly a measurement property, not a rigged choice.

**Recommendation:** report this table in the thesis with the floor/ceiling explanation
rather than letting an examiner find it. Consider quoting 0.80 (−6.2pp for Mistral) as a
conservative secondary figure.

---

## ⚠ Limitation 2 — Gemini is not deterministic

Temperature 0 fixed the local models completely. It did **not** fix the Gemini API.

C2/C5/C10 share one baseline, so PRR-before must be identical. It is not — 24.2%, 26.0%,
24.9%, with **7/75 queries disagreeing** on byte-identical inputs.

Same prompt, five calls at temperature 0:

| Model | Distinct outputs | Lengths (chars) |
|-------|-----------------:|-----------------|
| Gemini 2.5 Flash | **2** | 1149, 334, 334, 334, 334 |
| Mistral 7B (local) | **1** | 110, 110, 110, 110, 110 |

Greedy decoding is deterministic only if logits are identical every call. On API-served
models they are not: requests batch with other traffic and GPU floating-point addition is
non-associative, so batch composition perturbs low-order bits. Near-tied tokens flip. No
client-side parameter fixes this.

| Conditions | Generator | Determinism |
|---|---|---|
| C3,C4,C6,C7,C8,C9,C11,C12 | Mistral / Llama 3 | **Exact** (0.00pp replicate variance) |
| C1,C2,C5,C10 | Gemini | **±2.0pp** |

Mistral's −12.8pp and Llama 3's −6.4pp are unaffected. Gemini's numbers must be reported
as a null result with a confidence interval, never as point estimates.

---

## Files

| File | Contents |
|------|----------|
| `v7_analysis.json` | All metrics, machine-readable |
| `v7_results.csv` | Per-condition summary |
| `threshold_sensitivity.json` | PRR at 0.75–0.95 |
| `../../logs/C*_38k_v7_*.jsonl` | Raw per-query logs |

```bash
python3 evaluation/analyse_v7.py --tag 38k_v7
python3 evaluation/threshold_sensitivity.py --tag 38k_v7
```

v7 logs carry `query_type`, `ground_truth_company`, `ground_truth_id`, `discriminator` and
`temperature` inline, so every metric comes from the logs alone.

---

## What to claim in the thesis

**Supported:**
1. Chunk-removal correction reduces post-rationalisation for receptive generators —
   Mistral −12.8pp (p=0.031), zero replicate variance.
2. Generator Correction Receptivity is a real, measurable property that ranks models
   (Mistral 59.1% > Llama 3 36.4% > Gemini 14.8%) and predicts PRR reduction.
3. Verbal discrimination has zero causal effect in this architecture — proven across
   three generators, 0/75 outcome differences despite 9–13/75 verdict differences.
4. Correction improves faithfulness without harming citation correctness.
5. Aggregate PRR conceals large model differences; type-stratified reporting is necessary.

**Not supported — do not claim:**
- Any same-model vs cross-model discrimination advantage (the variable is inert).
- Gemini benefits from correction (−1.2pp, 95% CI spans zero).
- Precise effect magnitudes independent of threshold (all peak at 0.85).
- That correction helps on unanswerable queries (flat for 2 of 3 generators).

---

## Outstanding

- [ ] Rebuild presentation from v7 numbers — current deck shows superseded v4 figures
- [ ] Decide how to present the threshold-peak issue
- [ ] Thesis write-up — deadline **2 September 2026**
