# Cross-Modal Trust Analysis
> Created: 2026-07-26. Analysis of discriminator behaviour and generator responsiveness
> across all 4 adversarial conditions (C2, C4, C5, C6).

---

## What This Folder Contains

| File | Description |
|---|---|
| README.md | This analysis document |
| summary_stats.json | Full per-condition statistics |
| raw_per_query.json | Per-query discriminator vs audit verdicts for all 4 conditions |

Log files used (copies from v3 folder):
- C2_38k_v2_20260725_125950.jsonl — Gemini generator, Mistral discriminator (cross)
- C4_38k_v2_20260725_132043.jsonl — Mistral generator, Gemini discriminator (cross)
- C5_38k_v2_20260725_175809.jsonl — Gemini generator, Gemini discriminator (same)
- C6_38k_v2_20260725_181809.jsonl — Mistral generator, Mistral discriminator (same)

---

## A Critical Architecture Clarification

Before reading results, this is essential to understand.

**The discriminator does NOT control re-prompting.**

Looking at the loop code (`adversarial/loop.py`):
```python
# pr_indices comes from the AUDIT, not the discriminator
pr_indices = [r["cited_index"] for r in audit["results"] if r["verdict"] == "post_rationalised"]

if pr_indices:                          # <-- triggered by audit
    revised_answer = generate_fn(...)   # re-prompt always uses audit findings
```

The discriminator runs in parallel, its verdict is logged, but whether re-prompting happens
is decided entirely by the chunk removal audit. If the audit finds fake citations, re-prompting
always happens — regardless of what the discriminator said. If the audit finds nothing, no
re-prompting — regardless of what the discriminator said.

**This means:** PRR reduction in all conditions comes from audit-triggered re-prompting,
not from the discriminator catching fake citations.

---

## Core Results

| Condition | Generator | Discriminator | Type | Disc flagged PR | Disc TPR | Generator fix rate | PRR delta |
|---|---|---|---|---|---|---|---|
| C2 | Gemini | Mistral | cross | 0 / 21 PR found | **0%** | 23% (3/13) | -5pp |
| C4 | Mistral | Gemini | cross | 7 / 12 PR found | **8%** | 75% (6/8) | -12pp |
| C5 | Gemini | Gemini | same | 0 / 18 PR found | **0%** | 18% (2/11) | -2.6pp |
| C6 | Mistral | Mistral | same | 0 / 11 PR found | **0%** | 57% (4/7) | -8pp |

**Disc TPR** = discriminator true-positive rate: % of audit-confirmed fake citations that the
discriminator also flagged. **Generator fix rate** = % of re-prompted queries where PRR actually
decreased after revision.

---

## Finding 1 — Discriminators Cannot Detect Fake Citations Without Chunk Removal

Every discriminator (cross-model AND same-model) defaults to labelling citations as genuine.

| Condition | Disc flagged PR | Out of audit-confirmed PR | Miss rate |
|---|---|---|---|
| C2 (Mistral disc) | 0 | 21 | **100%** |
| C4 (Gemini disc) | 7 | 12 | **92%** |
| C5 (Gemini disc) | 0 | 18 | **100%** |
| C6 (Mistral disc) | 0 | 11 | **100%** |

C4 is the only condition where the discriminator fires at all — and even then it catches
only 1 out of 12 fake citations correctly (TPR = 8%). The other 6 times it fires are false
positives (flagging genuine citations as fake).

**What this means:** When you ask an LLM "is this citation genuine?" without giving it the
causal test (chunk removal), it almost always says yes. It cannot tell, purely from reading
the answer and the cited text, whether the citation was actually needed. This is a strong
argument for why chunk removal is essential — verbal/semantic discrimination alone is
insufficient for detecting post-rationalisation.

---

## Finding 2 — The Central New Insight: Gemini Resists Revision. Mistral Does Not.

This is the most important finding from this analysis. It is not about the discriminator.
The discriminator's output is not useless — the problem is that Gemini as a generator is an
immovable object. It receives the re-prompt with causal evidence from the audit and mostly
reproduces its original answer unchanged.

Important clarification: **the discriminator has no idea which model produced the answer.**
There is no model label or signature in the prompt — just text. So Gemini is not "protecting
its own output" in any self-aware sense. It is simply resistant to correction instructions
as a behavioural property, regardless of what evidence is presented or who is asking.

| Generator | Condition | Queries re-prompted | Fixed PRR | Failed | Fix rate |
|---|---|---|---|---|---|
| Gemini | C2 (cross disc) | 13 | 3 | 10 | **23%** |
| Gemini | C5 (same disc) | 11 | 2 | 9 | **18%** |
| Mistral | C4 (cross disc) | 8 | 6 | 2 | **75%** |
| Mistral | C6 (same disc) | 7 | 4 | 3 | **57%** |

**Gemini ignores correction 80% of the time.** Across both C2 and C5 — regardless of whether
the discriminator is Mistral or Gemini itself — Gemini receives the audit-based re-prompt and
reproduces its original answer. The discriminator identity makes almost no difference (23% vs
18%). The generator is the bottleneck, not the discriminator.

**Mistral accepts correction 66% of the time.** Across C4 and C6, Mistral consistently revises
when told a citation failed the causal test. The discriminator identity again makes little
difference (75% vs 57% — within expected variance for 7–8 re-prompted queries).

The dominant signal is generator identity, not discriminator identity:
- Which model is judging citations? — Does not meaningfully affect outcomes.
- Which model is being asked to revise? — Determines almost everything.

---

## Finding 3 — Cross-Modal Trust Reframed

The original hypothesis was: "a different-model discriminator would be a harsher judge than
a same-model discriminator, leading to more aggressive re-prompting and greater PRR reduction."

The data shows this hypothesis is wrong in its mechanism but points to something more interesting:

**Discriminator harshness doesn't matter** — because the discriminator doesn't control
re-prompting. Both cross-model and same-model discriminators say "genuine" for everything.

**What actually varies** is generator willingness to revise:

| Generator | Re-prompt fix rate (all conditions) |
|---|---|
| Gemini | ~20% |
| Mistral | ~66% |

Gemini is not "trusting its same-model discriminator" — it's **trusting its own original answer**
and resisting the audit's evidence. It receives the re-prompt ("testing showed this citation
wasn't needed — please revise") and mostly reproduces the same answer anyway.

Mistral, by contrast, is highly responsive to evidence-based feedback. When told a citation
failed the causal test, it revises.

**Revised thesis framing:** "Intra-generator conservatism" — Gemini resists revising its own
citations even when presented with causal evidence (chunk removal audit) that they are fake.
Mistral accepts this evidence and revises. This is independent of which model is the
discriminator.

---

## Per-Query Breakdown — Queries Where Audit Found Fake Citations

| Query | C2 PRR (b→a) | C4 PRR (b→a) | C5 PRR (b→a) | C6 PRR (b→a) | Disc fired |
|---|---|---|---|---|---|
| Q07 | 50%→50% | 0%→0% | 50%→50% | 0%→0% | none |
| Q08 | 50%→50% | 100%→0% ✅ | 50%→50% | 100%→0% ✅ | none |
| Q12 | 80%→80% | 0%→0% | 80%→0% ✅ | 0%→0% | C4 |
| Q14 | 100%→0% ✅ | 0%→0% | 0%→0% | 0%→0% | C4 |
| Q15 | 100%→100% ❌ | 0%→0% | 100%→100% ❌ | 0%→0% | C4 |
| Q19 | 50%→50% | 0%→0% | 50%→50% | 0%→0% | none |
| Q20 | 0%→0% | 100%→0% ✅ | 0%→0% | 100%→100% ❌ | none |
| Q22 | 80%→80% | 0%→0% | 60%→60% | 0%→0% | C4 |
| Q27 | 100%→100% ❌ | 0%→0% | 0%→0% | 0%→0% | none |
| Q29 | 0%→0% | 0%→0% | 0%→0% | 100%→0% ✅ | none |
| Q33 | 100%→0% ✅ | 80%→80% ❌ | 100%→100% ❌ | 80%→80% ❌ | none |
| Q36 | 0%→0% | 100%→0% ✅ | 0%→0% | 0%→0% | none |
| Q37 | 50%→50% | 0%→0% | 50%→0% ✅ | 0%→0% | none |
| Q38 | 100%→100% ❌ | 0%→0% | 100%→100% ❌ | 0%→0% | C4 |
| Q40 | 0%→0% | 100%→0% ✅ | 0%→0% | 100%→0% ✅ | none |
| Q42 | 100%→50% | 0%→0% | 100%→100% ❌ | 0%→0% | none |
| Q43 | 0%→0% | 100%→0% ✅ | 0%→0% | 100%→0% ✅ | C4 |
| Q45 | 100%→100% ❌ | 100%→100% ❌ | 100%→100% ❌ | 100%→100% ❌ | none |
| Q46 | 0%→0% | 100%→0% ✅ | 0%→0% | 0%→0% | none |

✅ = re-prompt reduced PRR. ❌ = re-prompt failed. "Disc fired" = only C4's Gemini discriminator
fired (and only for 6 of these queries).

**Q45 is the hardest query** — fake citations survive across all 4 conditions, all re-prompts.
The model cannot be persuaded to drop that citation regardless of model, discriminator, or evidence.

---

## Summary of Thesis Insights

### Insight 1 — Verbal discrimination is insufficient
LLMs cannot reliably detect post-rationalised citations by reading text alone. All models
default to "genuine." The chunk removal causal test is the only reliable detection method.

### Insight 2 — Generator responsiveness is the key variable
The ability to reduce PRR depends primarily on whether the generator accepts audit evidence
and revises. Mistral accepts it (~66% fix rate). Gemini largely ignores it (~20% fix rate).

### Insight 3 — Cross-model vs same-model discrimination is a weaker effect than expected
The discriminator's model identity has no meaningful effect on outcomes because the
discriminator doesn't control re-prompting. The originally observed differences between
C2/C5 and C4/C6 reflect audit variance (non-deterministic regeneration) and generator
identity, not discriminator behaviour.

### Insight 4 — Intra-generator conservatism
Gemini resists revising its own citations even when the chunk removal audit provides causal
evidence they are fake. This is not about trusting its own discriminator — it's about
trusting its original answer. A direction for future work: a stronger re-prompt that includes
the explicit similarity score ("your answer remained 0.92 similar after removing this chunk —
it was not needed") may reduce this resistance.

---

## What This Means for the Thesis Design

**What worked:** The audit-triggered re-prompting pipeline works well for Mistral. C4 achieves
-12pp and C6 achieves -8pp PRR reduction. These are strong, meaningful results.

**What needs redesign for Gemini:** The re-prompt text currently says "testing showed this
citation wasn't needed." Gemini doesn't seem to accept this at face value. A stronger version
could include: the actual similarity score, the regenerated answer text, and a more directive
instruction. This is a design improvement worth implementing for v5/v6 experiments.

**Discriminator role:** In the current architecture, the discriminator is a passive measurement
instrument, not an active participant. If you want the discriminator to actually influence
outcomes, its verdict needs to be incorporated into the re-prompt (e.g., "both chunk removal
testing AND an independent model flagged citation [2] as unnecessary"). This is a meaningful
architectural change worth testing.
