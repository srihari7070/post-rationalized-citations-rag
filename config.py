import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")
GEMINI_EMBED_MODEL  = "models/gemini-embedding-001"
GEMINI_GEN_MODEL    = "models/gemini-2.5-flash"

# Local models served by Ollama. OLLAMA_MODEL is the legacy default (Mistral).
OLLAMA_MODEL        = "mistral"
OLLAMA_MODELS       = {"mistral": "mistral", "llama3": "llama3"}

CHROMA_DIR          = "data/chroma_db_38k"
COLLECTION_NAME     = "startup_corpus"
CORPUS_JSONL        = "data/corpus_38k.jsonl"

TOP_K               = 5
SIMILARITY_THRESHOLD = 0.85  # methodological parameter; sensitivity reported at 0.80/0.90

# Sampling temperature for ALL generation, including audit regeneration.
#
# 0 = greedy decoding: the same prompt returns character-identical output every
# time, so the chunk removal audit is exactly reproducible. This is not a tuning
# preference — it is a correctness requirement. Prior runs used library defaults
# (Gemini 1.0, Ollama 0.8), which let sampling noise decide roughly half of all
# audit verdicts near the 0.85 threshold. See MEETING_NOTES.md, "Audit Determinism".
GEN_TEMPERATURE     = 0.0
