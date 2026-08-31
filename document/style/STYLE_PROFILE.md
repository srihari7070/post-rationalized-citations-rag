# Writing Style Profile

Built from `document/my writing sample.txt`: 2,775 words, 120 sentences, drawn from
recent messages, dictated notes and prompts.

Purpose is not to reproduce the informal register in the thesis. It is to identify which
features are genuinely characteristic, and carry those into formal academic prose while
dropping the ones that only belong in speech.

---

## Measured features

| Feature | Value | Note |
|---|---|---|
| Mean sentence length | 23.2 words | |
| Median | 19 words | mean above median, a long tail |
| Standard deviation | **25.7 words** | very high variance |
| Short sentences under 10 words | 16% | |
| Long sentences over 35 words | 12% | |
| Longest sentence | 263 words | unbroken dictated passage |
| **Em dashes** | **0** | across the whole sample |
| **Semicolons** | **0** | across the whole sample |
| Colons | 13 | used to introduce lists and explanations |
| Contractions | 24.5 per 1,000 words | high |
| "we" vs "I" | 64 vs 62 | roughly equal |
| Questions | 16 of 120 sentences (13%) | |

Discourse markers per 1,000 words:

| Marker | Rate |
|---|---|
| like | 11.5 |
| so | 7.6 |
| we need to | 5.0 |
| and then | 3.6 |
| we can | 3.2 |
| everything | 2.9 |
| maybe | 2.5 |
| yeah | 2.5 |
| basically | 2.2 |
| I think | 1.4 |

Most common sentence openers: **and** (10), we (8), this (8), the (6), let's (5),
what (5), before (4).

---

## What is actually distinctive

Three things stand out as genuinely characteristic rather than merely informal.

**1. Sentence length variance is unusually high.** A standard deviation of 25.7 against a
mean of 23.2 means the rhythm swings hard. Short declarative statements sit next to long
accumulating ones. Most machine-generated prose clusters tightly around 15 to 25 words
with low variance, so this is the single most transferable signature. Preserve it
deliberately.

**2. Zero em dashes, zero semicolons, in 2,775 words.** Not a preference, an absolute.
Clauses get joined with commas, "and", or a full stop instead. Both punctuation marks are
common in generated text, so their complete absence is meaningful.

**3. Claim first, qualification after.** The pattern is to state something plainly, then
soften or extend it. "Slide 3 is completely wrong. This is like I'm trying to tell them
their mistakes." The assertion arrives before the reasoning. That maps cleanly onto good
academic paragraph structure, topic sentence followed by support.

Secondary but real: heavy hedging, a strong preference for concrete named specifics over
abstractions, collaborative "we" even for solo work, and a habit of ending passages with
what should happen next.

---

## Translation table

Informal features on the left, their formal equivalent on the right. The feature carries
over, the wording does not.

| Informal habit | Formal equivalent |
|---|---|
| "maybe", "I think", "kind of" | "appears to", "suggests", "may indicate" |
| "basically" | drop it, or "in effect" if genuinely needed |
| "like 15 to 20" | "approximately 15 to 20" |
| "and yeah", "you know", "okay" | delete entirely |
| "stuff", "everything", "things" | name the specific thing |
| "we need to" | "the next step is", "this requires" |
| Self-correction mid-sentence | a qualifying clause with "though" or "however" |
| Run-on past 45 words | split at the natural clause boundary |
| Rhetorical question to reader | state it as the question the study addresses |
| "amazing", "great", "so much" | quantify it or cut it |

---

## Hard rules

**Never:**
- Em dashes. Not once.
- Semicolons.
- "delve", "leverage" as a verb, "it is worth noting", "furthermore", "moreover",
  "landscape", "realm", "testament to", "underscores"
- Three-item lists as a default rhythm. Use two or four when the content allows.
- Paragraphs that open with "Additionally" or "In conclusion"
- Uniform sentence length across a paragraph

**Always:**
- Vary sentence length deliberately. Put a 7-word sentence next to a 35-word one.
- Keep contractions where the register tolerates them. Academic prose in computer
  science accepts "doesn't" and "can't" more readily than the humanities do.
- Name concrete specifics. Mistral 7B, not "a smaller open model". 38,692, not "a large
  corpus".
- State the claim, then qualify it.
- Hedge real uncertainty rather than overclaiming. This is both characteristic and
  academically correct.
- Use "we" for method and analysis, which is standard in the field anyway.

---

## Register calibration

The sample is spoken and instructional. The thesis is written and expository. Expect the
formal version to be more compressed and better punctuated, and that is correct. What
should survive is the rhythm, the punctuation avoidances, the hedging, the concreteness,
and the claim-first structure.

A useful test while drafting: read a paragraph aloud. If it sounds like something the
author would not say in any register, rewrite it. If it sounds like a transcript, tighten
it.

---

## Known limitation

The sample is 2,775 words of informal instruction. It contains no example of the author
writing formal expository prose. The mapping above is therefore an inference, not an
observation.

The profile would be substantially stronger with any previous academic writing, a course
paper, the thesis exposé, or a technical report written for the company. If such a
document exists it should be added and this profile revised against it.
