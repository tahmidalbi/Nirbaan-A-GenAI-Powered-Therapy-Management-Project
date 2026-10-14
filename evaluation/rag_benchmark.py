"""Therapist-scoped vs unscoped retrieval on three synthetic therapist workspaces.

Usage: python evaluation/rag_benchmark.py
Steps (each is skipped if its output already exists):
  1. write synthetic handouts for workspaces B and C
  2. ingest all workspaces with the production chunking code
  3. generate one question per sampled chunk (that chunk is the gold answer)
  4. run retrieval with and without the therapist filter and save metrics
"""
import json
import os
import random
import statistics
import time
from types import SimpleNamespace

import common

common.configure()

from openai import OpenAI  # noqa: E402

BOOK_PATH = common.BACKEND / "books" / "ocd_book.pdf"
QUERIES_PER_WORKSPACE = 20
SEED = 42

HANDOUT_TOPICS = {
    "B": [
        "Understanding reassurance seeking in OCD",
        "Building an exposure hierarchy for OCD",
        "Response prevention strategies to use at home",
        "How family accommodation keeps OCD going",
        "Preventing relapse after ERP treatment",
    ],
    "C": [
        "Managing worry in generalized anxiety disorder",
        "Panic attacks and interoceptive exposure",
        "Introduction to cognitive restructuring",
        "Health anxiety and repeated body checking",
        "Sleep problems and anxiety",
    ],
}
RESOURCE_ID_BASE = {"A": 9000, "B": 9100, "C": 9200}

llm = OpenAI()
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.3-chat-latest")


def chat(prompt: str) -> str:
    response = llm.chat.completions.create(
        model=LLM_MODEL, messages=[{"role": "user", "content": prompt}]
    )
    return (response.choices[0].message.content or "").strip()


# ── Step 1: synthetic handouts ────────────────────────────────────────────────

def write_handouts() -> None:
    for key, topics in HANDOUT_TOPICS.items():
        folder = common.DATA_DIR / f"workspace_{key.lower()}"
        folder.mkdir(parents=True, exist_ok=True)
        for i, title in enumerate(topics, start=1):
            path = folder / f"{i:02d}.txt"
            if path.exists():
                continue
            text = chat(
                f"Write a patient education handout titled '{title}' for an outpatient "
                "therapy clinic. About 900 words of plain prose with short headings. "
                "Use conventional, evidence-based clinical guidance. Do not include "
                "references, clinic names, or real people."
            )
            path.write_text(f"{title}\n\n{text}\n", encoding="utf-8")


def workspace_documents() -> dict:
    docs = {"A": [("OCD treatment book", BOOK_PATH, "pdf")]}
    for key in HANDOUT_TOPICS:
        folder = common.DATA_DIR / f"workspace_{key.lower()}"
        docs[key] = [
            (p.read_text(encoding="utf-8").splitlines()[0], p, "txt")
            for p in sorted(folder.glob("*.txt"))
        ]
    return docs


# ── Step 2: ingestion with the production pipeline ───────────────────────────

def ingest(ids: dict) -> dict:
    # Holds raw chunk text (including the copyrighted book), so it stays in a git-ignored cache.
    manifest_path = common.EVAL_DIR / ".cache" / "rag_ingestion.json"
    manifest_path.parent.mkdir(exist_ok=True)
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    from app.resources.tasks import DocumentProcessor, VectorStoreFactory

    processor = DocumentProcessor()
    store = VectorStoreFactory.create()
    manifest = {}

    for key, docs in workspace_documents().items():
        for offset, (title, path, file_type) in enumerate(docs, start=1):
            resource = SimpleNamespace(
                id=RESOURCE_ID_BASE[key] + offset,
                therapist_id=ids[key]["therapist_id"],
                title=title,
                file_type=file_type,
            )
            loaded = processor.load_document(str(path), file_type)
            chunks = processor.chunk_document(loaded)
            documents, doc_ids = processor.to_langchain_documents(resource, chunks)
            for start in range(0, len(documents), 100):
                store.add_documents(documents=documents[start:start + 100], ids=doc_ids[start:start + 100])
            manifest[str(resource.id)] = {
                "workspace": key,
                "title": title,
                "chunks": [c["text"] for c in chunks],
            }
            print(f"ingested workspace {key}: {title} ({len(chunks)} chunks)")

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


# ── Step 3: queries with a known gold chunk ──────────────────────────────────

def build_queries(manifest: dict) -> list:
    queries_path = common.DATA_DIR / "rag_queries.json"
    if queries_path.exists():
        return json.loads(queries_path.read_text(encoding="utf-8"))

    rng = random.Random(SEED)
    queries = []
    for key in common.WORKSPACES:
        candidates = [
            (int(rid), idx, text)
            for rid, res in manifest.items() if res["workspace"] == key
            for idx, text in enumerate(res["chunks"])
            if 400 <= len(text) <= 4000
        ]
        rng.shuffle(candidates)
        accepted = 0
        for rid, idx, text in candidates:
            if accepted == QUERIES_PER_WORKSPACE:
                break
            question = chat(
                "You are building a retrieval test set. Read the passage below. If it "
                "contains substantive clinical or educational content, write ONE natural "
                "question that a therapist or patient might ask and that this passage "
                "answers. Do not copy any phrase longer than three words from the passage. "
                "If the passage is front matter, a table of contents, references, an "
                "index, or too fragmentary, reply exactly SKIP. Reply with the question only."
                f"\n\nPASSAGE:\n{text}"
            )
            if question.strip().upper() == "SKIP":
                continue
            queries.append({"workspace": key, "question": question,
                            "gold_resource_id": rid, "gold_chunk_index": idx})
            accepted += 1

    queries_path.write_text(json.dumps(queries, indent=2), encoding="utf-8")
    return queries


# ── Step 4: scoped vs unscoped retrieval ─────────────────────────────────────

def percentile(values: list, p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]


def evaluate(queries: list, ids: dict) -> dict:
    from app.resources.rag_service import RAG_MMR_FETCH_K, RAG_MMR_LAMBDA, RAG_TOP_K_DEFAULT
    from app.resources.tasks import VectorStoreFactory

    store = VectorStoreFactory.create()
    rows = []
    for q in queries:
        own_therapist = ids[q["workspace"]]["therapist_id"]
        t0 = time.perf_counter()
        embedding = store.embeddings.embed_query(q["question"])
        embed_ms = (time.perf_counter() - t0) * 1000

        for condition, metadata_filter in (
            ("scoped", {"therapist_id": {"$eq": own_therapist}}),
            ("unscoped", None),
        ):
            t0 = time.perf_counter()
            docs = store.max_marginal_relevance_search_by_vector(
                embedding, k=RAG_TOP_K_DEFAULT, fetch_k=RAG_MMR_FETCH_K,
                lambda_mult=RAG_MMR_LAMBDA, filter=metadata_filter,
            )
            search_ms = (time.perf_counter() - t0) * 1000

            rank = next(
                (i for i, d in enumerate(docs, start=1)
                 if d.metadata.get("resource_id") == q["gold_resource_id"]
                 and d.metadata.get("chunk_index") == q["gold_chunk_index"]),
                None,
            )
            own = sum(1 for d in docs if d.metadata.get("therapist_id") == own_therapist)
            rows.append({
                "workspace": q["workspace"], "condition": condition,
                "hit": rank is not None, "reciprocal_rank": 1 / rank if rank else 0.0,
                "own_precision": own / len(docs) if docs else 0.0,
                "leaked": own < len(docs),
                "search_ms": search_ms, "embed_ms": embed_ms,
            })

    def summarise(subset: list) -> dict:
        return {
            "queries": len(subset),
            "hit_at_6": statistics.mean(r["hit"] for r in subset),
            "mrr_at_6": statistics.mean(r["reciprocal_rank"] for r in subset),
            "own_workspace_precision_at_6": statistics.mean(r["own_precision"] for r in subset),
            "queries_with_leakage": statistics.mean(r["leaked"] for r in subset),
            "search_ms_median": statistics.median(r["search_ms"] for r in subset),
            "search_ms_p95": percentile([r["search_ms"] for r in subset], 0.95),
        }

    embed_times = [r["embed_ms"] for r in rows if r["condition"] == "scoped"]
    results = {
        "settings": {"k": RAG_TOP_K_DEFAULT, "fetch_k": RAG_MMR_FETCH_K, "lambda_mult": RAG_MMR_LAMBDA,
                     "embedding_model": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")},
        "query_embedding_ms": {"median": statistics.median(embed_times), "p95": percentile(embed_times, 0.95)},
        "overall": {c: summarise([r for r in rows if r["condition"] == c]) for c in ("scoped", "unscoped")},
        "by_workspace": {
            key: {c: summarise([r for r in rows if r["condition"] == c and r["workspace"] == key])
                  for c in ("scoped", "unscoped")}
            for key in common.WORKSPACES
        },
    }
    (common.RESULTS_DIR / "rag_per_query.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (common.RESULTS_DIR / "rag_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    common.quiet_sql()
    workspace_ids = common.ids_by_workspace()
    write_handouts()
    chunk_manifest = ingest(workspace_ids)
    test_queries = build_queries(chunk_manifest)
    print(json.dumps(evaluate(test_queries, workspace_ids), indent=2))
