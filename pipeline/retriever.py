import chromadb
from config import CHROMA_DIR, COLLECTION_NAME, TOP_K
from models.gemini_client import embed

_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _client.get_collection(COLLECTION_NAME)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    query_embedding = embed(query)
    results = _collection.query(query_embeddings=[query_embedding], n_results=k)
    chunks = []
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        chunks.append({
            "index":    i + 1,
            "text":     doc,
            "name":     meta.get("name", ""),
            "country":  meta.get("country", ""),
            "tags":     meta.get("tags", ""),
        })
    return chunks
