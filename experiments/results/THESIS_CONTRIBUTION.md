# Thesis Contribution — Why This Is Not a Copy
> Written: 2026-07-26. Clarifies what already exists in the literature vs what this thesis adds.
> Use this before supervisor meetings or when writing the introduction/contribution section.

---

## What Already Exists

**Chunk removal as a faithfulness evaluation metric** is not new. Papers like RAGAS, FaithScore,
and similar RAG evaluation frameworks use "remove the source and see if the answer changes" as
a way to *score* whether a RAG system is faithful after the fact. You run the query, get an
answer, then evaluate how faithful the citations are. It produces a number. You report it.
That is all it does — measure and report.

---

## What This Thesis Adds

### Contribution 1 — Chunk removal as a real-time correction signal, not just an evaluation metric

The key difference: you wired the chunk removal result directly into a feedback loop that
changes the model's behaviour during inference. The audit runs, finds a fake citation, and
immediately triggers a re-prompt that asks the generator to revise. The generator produces a
new answer. The audit runs again on the revised answer. PRR is measured before and after.

Evaluation tools don't do this. They score and stop. Your system scores and corrects.

This is the architectural contribution: **chunk removal as a reward signal inside an
adversarial feedback loop**, not merely as an offline evaluation tool.

### Contribution 2 — Generator revision responsiveness as a new empirical finding

This finding only exists because you built the feedback loop. Nobody has characterised this
before because nobody has sent causal audit feedback to generators and measured whether they
accept it.

**Gemini as a generator resists correction.** When the audit finds a fake citation and the
re-prompt is sent — "chunk removal showed this citation was not needed, please revise" —
Gemini reproduces its original answer approximately 80% of the time. It is an immovable
object in the face of evidence-based correction.

**Mistral as a generator accepts correction.** The same re-prompt leads Mistral to genuinely
revise its citations approximately 66% of the time.

This is not about self-awareness or model identity — the discriminator and re-prompt contain
no information about which model generated the original answer. It is a behavioural property
of each model in the revision context: Mistral is instruction-compliant when corrected,
Gemini is instruction-resistant.

This is not a failure of the system. It is a discovery. The practical implication is direct:
in a production RAG system where citation faithfulness matters, model selection should account
for revision responsiveness, not just generation quality. Gemini may produce better initial
answers but is harder to correct. Mistral may be more correctable even if its initial PRR
is also lower.

### Contribution 3 — The discriminator as a measurement instrument, not a control mechanism

The original GAN analogy suggested the discriminator would actively detect and flag fake
citations. The cross-modal trust analysis showed that LLMs cannot reliably detect
post-rationalised citations by reading text alone — all models default to "genuine" regardless
of whether they are judging themselves or another model.

This is itself a finding: **verbal/semantic discrimination is insufficient for detecting
post-rationalisation**. The causal test (chunk removal) is the only reliable detection method.
This validates the architecture — the discriminator alone would not work; the audit is essential.

---

## How to Frame This in the Thesis

**Introduction:** "Chunk removal has been used as a faithfulness evaluation metric in prior
work. This thesis extends that idea from evaluation to correction — using chunk removal as a
real-time reward signal inside an adversarial feedback loop."

**Contribution statement:**
1. A feedback loop architecture where chunk removal audit results trigger generator re-prompting
   and revision, reducing post-rationalisation during inference.
2. The empirical finding that generator revision responsiveness is the primary determinant of
   PRR reduction, with Mistral showing 3× greater responsiveness than Gemini to causal feedback.
3. The finding that verbal LLM discrimination (without chunk removal) cannot reliably detect
   post-rationalised citations, validating the necessity of the causal test.

**What to avoid saying:** "We built a GAN for RAG." The GAN framing is a loose inspiration.
The system is better described as an audit-triggered correction loop with a measurement
discriminator.
