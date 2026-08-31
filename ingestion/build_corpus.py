"""
Build the full 38K RAG corpus.

Selects ALL active DACH companies whose source_text (the text that was
actually embedded) contains at least 30 words. This is the complete eligible
population — not a sample.

Why 30 words: below this, the profile contains only name and city, which is
not enough to support a verifiable citation. At 30+ words the profile includes
founding year, company size, sector tags, and a description sentence.

Why source_text (not companyboard_description): the embedding vector was
generated from source_text. Using source_text ensures the RAG chunk text and
the vector are always the same document.

Why no LIMIT: corpus size does not affect experiment runtime. The experiment
always runs the same 50 queries and retrieves top-5 chunks. Using all eligible
companies maximises retrieval diversity across sectors and geographies.
"""

import json
import psycopg2
from pathlib import Path
import chromadb

MIN_SOURCE_WORDS = 30   # minimum words in source_text to be a citable chunk
DB_NAME          = "thesis_startup"
OUTPUT_JSONL     = Path("data/corpus_38k.jsonl")
CHROMA_DIR       = Path("data/chroma_db_38k")
COLLECTION_NAME  = "startup_corpus"

QUERY = """
WITH company_pool AS (
    SELECT DISTINCT ON (c.id)
        c.id::text                AS id,
        c.name,
        co.iso_code               AS country,
        e.source_text,
        e.vector::text            AS vector_text,
        array_length(regexp_split_to_array(trim(e.source_text), E'\\s+'), 1) AS source_words,
        CASE WHEN EXISTS (
            SELECT 1 FROM companyboard_companytag ct WHERE ct.company_id = c.id
        ) THEN 1 ELSE 0 END       AS has_tags,
        CASE WHEN EXISTS (
            SELECT 1 FROM companyboard_equityfundingdata ef WHERE ef.company_id = c.id
        ) THEN 1 ELSE 0 END       AS has_funding
    FROM companyboard_company c
    JOIN companyboard_companyembedding e  ON e.company_id  = c.id
    JOIN companyboard_address a          ON a.company_id  = c.id
    JOIN companyboard_city ci            ON ci.id         = a.city_id
    JOIN companyboard_country co         ON co.id         = ci.country_id
    WHERE co.iso_code IN ('DE', 'AT', 'CH')
      AND c.is_active = TRUE
      AND array_length(regexp_split_to_array(trim(e.source_text), E'\\s+'), 1) >= %(min_words)s
    ORDER BY c.id,
             array_length(regexp_split_to_array(trim(e.source_text), E'\\s+'), 1) DESC
)
SELECT
    id,
    name,
    country,
    source_text,
    vector_text,
    source_words,
    has_tags,
    has_funding,
    source_words + has_tags * 100 + has_funding * 50  AS enrichment_score
FROM company_pool
ORDER BY enrichment_score DESC
"""


def fetch_companies():
    conn = psycopg2.connect(dbname=DB_NAME, host="localhost")
    cur  = conn.cursor()
    cur.execute(QUERY, {"min_words": MIN_SOURCE_WORDS})
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]


def fetch_tags(company_ids: list[str]) -> dict:
    conn = psycopg2.connect(dbname=DB_NAME, host="localhost")
    cur  = conn.cursor()
    cur.execute("""
        SELECT ct.company_id::text, array_agg(t.name) AS tags
        FROM companyboard_companytag ct
        JOIN companyboard_tag t ON t.id = ct.tag_id
        WHERE ct.company_id = ANY(%s::bigint[])
        GROUP BY ct.company_id
    """, (company_ids,))
    result = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return result


def save_jsonl(records: list[dict]):
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  Saved {len(records)} records → {OUTPUT_JSONL}")


def load_into_chroma(records: list[dict]):
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        collection.add(
            ids        = [r["id"] for r in batch],
            embeddings = [json.loads(r["vector_text"]) for r in batch],
            documents  = [r["source_text"] for r in batch],
            metadatas  = [{
                "company_id":       r["id"],
                "name":             r["name"] or "",
                "country":          r["country"],
                "tags":             ", ".join(r["tags"]) if r["tags"] else "",
                "source_words":     r["source_words"],
                "has_funding":      r["has_funding"],
                "enrichment_score": r["enrichment_score"],
            } for r in batch],
        )
        print(f"  Loaded batch {i // batch_size + 1} ({len(batch)} docs)")

    return collection


def print_summary(records: list[dict]):
    from collections import Counter
    countries   = Counter(r["country"] for r in records)
    with_tags   = sum(r["has_tags"] for r in records)
    with_funding = sum(r["has_funding"] for r in records)
    scores      = [r["enrichment_score"] for r in records]
    print(f"\n  Country breakdown:  DE={countries['DE']}  CH={countries['CH']}  AT={countries['AT']}")
    print(f"  Has tags:           {with_tags} / {len(records)} ({with_tags/len(records):.0%})")
    print(f"  Has funding data:   {with_funding} / {len(records)} ({with_funding/len(records):.0%})")
    print(f"  Enrichment score:   min={min(scores)}  median={sorted(scores)[len(scores)//2]}  max={max(scores)}")


def main():
    print("=== Building corpus (top enriched DACH companies) ===\n")

    print("1. Querying PostgreSQL...")
    rows = fetch_companies()
    print(f"   Fetched: {len(rows)} companies")

    print("\n2. Fetching tags...")
    ids      = [r["id"] for r in rows]
    tags_map = fetch_tags(ids)
    for r in rows:
        r["tags"] = tags_map.get(r["id"], [])

    print("\n3. Corpus summary:")
    print_summary(rows)

    print("\n4. Saving JSONL...")
    # Strip vector from JSONL (keep source_text only — vectors live in Chroma)
    jsonl_records = [{k: v for k, v in r.items() if k != "vector_text"} for r in rows]
    save_jsonl(jsonl_records)

    print("\n5. Loading into Chroma...")
    collection = load_into_chroma(rows)

    print(f"\n=== Done. Corpus: {collection.count()} documents ===")


if __name__ == "__main__":
    main()
