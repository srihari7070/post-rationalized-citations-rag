import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from models.gemini_client import generate as gemini_generate, embed as gemini_embed
from pipeline.baseline import run_baseline
from adversarial.loop import run_adversarial_cycle

st.set_page_config(page_title="RAG Citation Faithfulness", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Experiment Setup")

    model_choice = st.radio("Generator model", ["Gemini", "Mistral 7B"])
    mode = st.radio("Pipeline mode", ["Baseline", "Adversarial"])
    threshold = st.slider("Similarity threshold", 0.5, 1.0, 0.85, 0.01,
                          help="Above this = answer didn't change = post-rationalised")
    query = st.text_area("Query", height=100,
                         placeholder="e.g. Which Berlin fintech startups focus on payments?")
    run = st.button("Run Experiment", type="primary", use_container_width=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("RAG Citation Faithfulness")
st.caption("Chunk-Removal Adversarial Loop — Master's Thesis, Srihari Ananthan, SRH Berlin 2026")
st.divider()

if not run or not query.strip():
    st.info("Enter a query in the sidebar and click **Run Experiment** to start.")
    st.stop()

# ── Model setup ───────────────────────────────────────────────────────────────
def get_generate_fn(name: str):
    if name == "Gemini":
        return gemini_generate
    else:
        from models.ollama_client import generate as ollama_generate
        return ollama_generate

generate_fn    = get_generate_fn(model_choice)
discriminator_fn = get_generate_fn("Mistral 7B" if model_choice == "Gemini" else "Gemini")

# ── Run ───────────────────────────────────────────────────────────────────────
with st.spinner("Retrieving chunks and generating answer..."):
    baseline = run_baseline(query, generate_fn)

chunks = baseline["chunks"]
answer = baseline["answer"]

# ── Retrieved Chunks ──────────────────────────────────────────────────────────
st.subheader("Retrieved Chunks")
cols = st.columns(len(chunks))
for i, (col, chunk) in enumerate(zip(cols, chunks)):
    with col:
        st.markdown(f"**[{chunk['index']}] {chunk['name']}** `{chunk['country']}`")
        st.caption(chunk["tags"][:80] if chunk["tags"] else "")
        st.text(chunk["text"][:200] + "...")

st.divider()

# ── Baseline Answer ───────────────────────────────────────────────────────────
st.subheader(f"Answer — {model_choice} · Baseline")
st.markdown(answer)
st.divider()

if mode == "Baseline":
    st.info("Switch to **Adversarial** mode to run the chunk-removal audit and adversarial loop.")
    st.stop()

# ── Adversarial cycle ─────────────────────────────────────────────────────────
with st.spinner("Running chunk-removal audit and adversarial loop..."):
    from config import SIMILARITY_THRESHOLD
    result = run_adversarial_cycle(
        query=query,
        chunks=chunks,
        answer=answer,
        generate_fn=generate_fn,
        discriminator_fn=discriminator_fn,
        embed_fn=gemini_embed,
        threshold=threshold,
    )

# ── Citation Audit ────────────────────────────────────────────────────────────
st.subheader("Citation Audit — Chunk Removal Results")

audit = result["audit_before"]
if not audit["cited"]:
    st.warning("No citations found in the answer. Check the model is citing with [1], [2] format.")
else:
    for r in audit["results"]:
        verdict = r["verdict"]
        icon = "🔴" if verdict == "post_rationalised" else "🟢"
        label = "Post-Rationalised" if verdict == "post_rationalised" else "Genuine"
        chunk = next((c for c in chunks if c["index"] == r["cited_index"]), {})
        with st.expander(f"{icon} [{r['cited_index']}] {chunk.get('name', '')} — {label}  |  similarity: {r['similarity']}"):
            st.markdown(f"**Removal test:** removing this chunk gave similarity `{r['similarity']}` to original answer")
            st.markdown(f"**Threshold:** `{threshold}` — {'above' if verdict == 'post_rationalised' else 'below'} → {label}")
            st.text_area("Answer without this chunk:", r["new_answer"], height=120, key=f"rem_{r['cited_index']}")

# ── Discriminator ─────────────────────────────────────────────────────────────
st.subheader("Discriminator Cross-Validation")
disc_model = "Mistral 7B" if model_choice == "Gemini" else "Gemini"
st.caption(f"Discriminator: {disc_model} independently judged each citation")

if result["discriminator_verdicts"]:
    disc_acc = result["discriminator_accuracy"]
    st.metric("Discriminator Accuracy", f"{disc_acc:.0%}",
              help="% of discriminator verdicts confirmed by chunk-removal ground truth")
    for v in result["discriminator_verdicts"]:
        correct = "✅" if v["discriminator_correct"] else "❌"
        st.write(f"{correct} **[{v['cited_index']}]** — Discriminator: `{v['discriminator']}` | Removal test: `{v['removal_test']}`")

st.divider()

# ── PRR + Revised Answer ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)
col1.metric("PRR Before", f"{result['prr_before']:.0%}",
            help="Post-Rationalisation Rate before adversarial feedback")
col2.metric("PRR After", f"{result['prr_after']:.0%}",
            delta=f"{result['prr_after'] - result['prr_before']:.0%}",
            delta_color="inverse",
            help="Post-Rationalisation Rate after one adversarial cycle")

if result["revised_answer"] != answer:
    st.subheader("Revised Answer (after adversarial feedback)")
    st.markdown(result["revised_answer"])
else:
    st.info("No citations were flagged as post-rationalised — no revision needed.")
