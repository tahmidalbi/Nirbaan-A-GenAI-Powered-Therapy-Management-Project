# Nirbaan evaluation

This folder holds everything behind Section 4 (Evaluation) of the Nirbaan paper:
the scripts, the test data, the raw results, and the details that did not fit in the paper.
All data here is synthetic. No real patient data was used.

## Contents

| Path | What it is |
|---|---|
| `setup_eval_db.py` | Creates a separate evaluation database, all tables, and three test therapists and patients |
| `rag_benchmark.py` | Therapist-scoped vs. unscoped retrieval (paper Table 3) |
| `latency_benchmark.py` | Response time and routing of the patient assistant (paper Table 4) |
| `common.py` | Shared setup: points the backend at the evaluation database |
| `data/workspace_b/`, `data/workspace_c/` | The 10 synthetic patient handouts (written with a language model) |
| `data/rag_queries.json` | The 60 test questions and the passage each one should find |
| `data/latency_messages.json` | The 60 test messages (20 per path) |
| `results/rag_results.json`, `results/rag_per_query.json` | Retrieval results: summary and per question |
| `results/latency_results.json`, `results/latency_runs.json` | Full 60-message run (summary and every step of every message) |
| `results/latency_results_human_escalation.json`, `results/latency_runs_human_escalation.json` | Re-run of the 20 escalation messages with the current escalation rules |
| `results/federated_results.json` | Full federated QLoRA configuration, per-round losses, and communication size |
| `../backend/tests/` | Automated access-control and escalation-rule tests |

## How to re-run

1. Start a disposable pgvector database:
   `docker run -d --name nirbaan-eval-db -e POSTGRES_PASSWORD=2021 -e POSTGRES_DB=nirbaan_eval -p 5433:5432 pgvector/pgvector:pg16`
2. Put `OPENAI_API_KEY` (and optionally `TAVILY_API_KEY`) in `backend/.env`, and install `backend/requirements.txt`.
3. Run, from the repository root:
   - `python evaluation/setup_eval_db.py`
   - `python evaluation/rag_benchmark.py`
   - `python evaluation/latency_benchmark.py` (or `python evaluation/latency_benchmark.py human_escalation` for one path)
4. Run the tests from `backend/`: `pip install pytest httpx`, then `python -m pytest tests`.

The paper used `gpt-5.4-2026-03-05` for all language model calls and `text-embedding-3-large` for embeddings.
Workspace A used a published OCD self-help book (186 pages). The book is not included here for copyright reasons,
so to re-run, place any PDF at `backend/books/ocd_book.pdf`. Results with a different book will differ.

## Details not shown in the paper

### Therapist-scoped retrieval (paper Section 4.2)

- **Workspaces:** A = the book (279 chunks); B = 5 handouts on OCD and ERP (48 chunks);
  C = 5 handouts on general anxiety that partly overlap with OCD (51 chunks). All three share one pgvector collection.
- **How the questions were made:** for each workspace, passages of 400–4,000 characters were shuffled (seed 42).
  A language model read each passage and wrote one question that the passage answers, without copying long phrases,
  or replied "SKIP" for front matter, references, or fragments. The first 20 accepted passages per workspace were kept.
  Each question has exactly one correct passage.
- **Retrieval settings:** the same as Nirbaan: MMR search, top 6 results, 20 candidates, lambda 0.5.
  Each question was run once with the therapist filter and once without.

| Workspace | Correct passage in top 6 (filter / no filter) | Questions that got another therapist's material (filter / no filter) |
|---|---|---|
| A (book) | 75% / 75% | 0% / 40% |
| B (OCD handouts) | 90% / 95% | 0% / 100% |
| C (anxiety handouts) | 100% / 100% | 0% / 90% |

Embedding each question took 412 ms (median), on top of the search time in the paper.

### Response time and routing (paper Section 4.3)

- **Which run each number comes from:** the psychoeducation and general-support rows of paper Table 4 come from the full
  60-message run (`latency_results.json`). The escalation row comes from the re-run of the 20 escalation messages
  (`latency_results_human_escalation.json`), made after the escalation rules described below were added.
  The full run's escalation numbers reflect the earlier escalation code and are not used in the paper.
- **Median time per step:** routing 1.3 s; knowledge base retrieval (including embedding the query) 2.9 s;
  checking whether the retrieved material is enough 3.7 s; web search 8.5 s;
  writing the answer 12.6 s (psychoeducation) or 8.8 s (support); writing the alert for responders 5.1 s;
  each database step under 30 ms.
- **Machine:** the database ran locally in Docker on a Windows 10 laptop with a 6th-generation Intel Core processor;
  all language model calls went to the OpenAI API.
- **Throughput:** 3.2 messages per minute when messages are processed one at a time. No test with many users at once was run.
- **Web fallback:** 14 of the 20 psychoeducation questions fell back to web search
  (see `latency_runs.json` for which ones).
- **Escalation rules:** an explicit request for a person or for emergency help, or clear crisis wording,
  alerts emergency personnel by fixed rules (`backend/app/NirbaanAIPatient/HumanEscalationAgent/Nodes/verifier.py`).
  Other messages go to a language model check. The rules were developed using the 20 test messages, so
  `backend/tests/test_escalation_rule.py` also checks 10 requests worded differently (all escalated)
  and 8 typical OCD messages such as "What if I hurt my baby? I would never want to." (all left to the language model).

### Federated QLoRA (paper Section 4.4)

Full numbers are in `results/federated_results.json`. In short:

- **Model:** `mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated`, revision `368c8ed94ce4c986e7b9ca5c159651ef753908ce`, loaded in 4-bit.
- **Clients:** 223, 211, 216 and 147 training examples. Clients 0–2 each hold most of one OCD subtype
  (harm, contamination, checking), so the clients' data differ.
- **Training:** Flower 1.27, FedAvg, 5 rounds, 1 local epoch per round, LoRA rank 16 on all attention and MLP layers,
  one NVIDIA A100 (80 GB), 1,946 seconds in total.

| Round | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Held-out loss | 1.975 | 1.098 | 0.979 | 0.900 | 0.860 | 0.843 |
| Average client training loss | – | 1.332 | 1.024 | 0.920 | 0.846 | 0.799 |

- **Communication:** the adapters are 448 tensors with 41,943,040 parameters (about 0.5% of the base model),
  sent as 32-bit numbers: 167.8 MB per client in each direction per round. With four clients that is about
  1.34 GB per round and 6.7 GB for the whole run (calculated from the measured size; Flower overhead not included).
- **Privacy threat model:** we assume the server follows the protocol but may try to learn from the updates it receives,
  and that clients do not work together against the others. Raw training text never leaves a client. The pipeline does
  not use secure aggregation or differential privacy, so the shared updates could still reveal some information about a
  client's data (for example through membership-inference attacks). It gives no formal privacy guarantee.

### Automated tests (paper Section 4)

- `backend/tests/test_imaginal_access.py` (13 tests): requests without a login are rejected; the treating therapist and the
  patient can play the patient's approved script audio, other patients and therapists cannot; a patient cannot approve a
  script; a therapist cannot start or approve a script for another therapist's patient; the AI rewrite limit is enforced.
- `backend/tests/test_escalation_rule.py` (19 tests): the escalation rules described above.
