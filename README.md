# Evidence Atlas RAG

The product and repository share the Evidence Atlas RAG name. The internal Python package retains its existing import path; see [compatibility notes](docs/COMPATIBILITY.md) for the supported legacy configuration identifiers.

A local research-paper comparison workspace built with LangChain and LangGraph. It includes a responsive editorial landing page, PDF uploads, cited research questions, a source-excerpt reading matrix, inspectable PDF evidence, research-trail export, and a reproducible evaluation.

**Scope:** My RAG app helps AI learners answer research questions from the RAG, Self-RAG, and CRAG papers in a web app, targeting 95% faithfulness and responses within 15 seconds.

Those are targets, not verified achievements. This first version works without credentials in **local excerpt mode**. Live semantic embeddings and generated answers need model configuration and have not been tested against a real provider.

## Run the existing workspace

From this project directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn papertrail.server:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Click **Explore the sample collection**, then ask a question or build a reading matrix. Stop with Ctrl+C. Complete the fresh setup below first to install dependencies and download the three PDFs. `run.cmd` also starts the server from this folder.

The self-contained [project brief](docs/project-brief.html) opens directly in a browser without starting the app. It records the primer, six-field framework, retrieval design notes, and implementation status.

## Fresh setup

Use Python 3.11+ (tested on Python 3.12, Windows). No Node build or database service is required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/download_papers.py
.\.venv\Scripts\python.exe -m uvicorn papertrail.server:app --host 127.0.0.1 --port 8000
```

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` instead. The lock file records the tested environment; `requirements.txt` and `requirements-dev.txt` specify compatible ranges. If `py` is unavailable, substitute the full path to your Python executable.

## Two honest operating modes

| Mode | Retrieval | Output | Network use |
|---|---|---|---|
| `demo` (default) | Deterministic hashed word vectors + BM25 + rank fusion | Verbatim source excerpts, explicitly labeled | No model calls; sample download is a separate explicit step |
| `live` | Configured semantic embeddings + BM25 + rank fusion | Structured cited claims, quote checks, model evidence audit | Paper text to embedding provider; questions and retrieved text to model provider |

Copy `.env.example` to `.env`, set `EVIDENCE_ATLAS_MODE=live`, and supply `MODEL_API_KEY`. The initial defaults are `gpt-4.1-mini` and `text-embedding-3-small`. These are configuration defaults, not a promise that a particular account has access. Set separate embedding credentials/base URL if needed. Restart after changes.

An OpenAI-compatible provider, including a suitably configured Nebius account, needs compatible chat, embedding, and JSON-schema structured-output endpoints. No Nebius model IDs, credits, account access, or compatibility have been verified. Failed requests display a configuration error and never fabricate a successful answer. Never put keys in frontend code or commit `.env`.

The app is intended for a **single user on loopback**. Collections and PDF bytes stay in process memory; a restart clears them. Browser refresh currently requires reloading the collection. Clear the current collection in the sidebar; restart to clear any orphaned collections. There is no authentication or durable collection catalog. Pinecone can persist vectors and passage text remotely when explicitly configured; see below. Do not expose this development server publicly.

## Optional Pinecone backend

In-memory vectors are the active local backend. Pinecone is optional; live generation can also use in-memory vectors. See [the credential and index checklist](docs/PINECONE.md). Copy `.env.example` to `.env` and enter credentials locally, never in chat or frontend code.

Set `EVIDENCE_ATLAS_MODE=live`, `VECTOR_BACKEND=pinecone`, `MODEL_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_INDEX_NAME`. Confirm model names/base URLs and `EMBEDDING_DIMENSIONS` (1536 for the initial default). The adapter requires an existing, ready, externally embedded dense cosine index; it validates dimensions and metric before writing. It never creates/reconfigures an index and always allocates a fresh `evidence-atlas-...` namespace per collection.

Pinecone retains vectors and passage text; PDFs, BM25 input, and the collection catalog remain process-local. **Clear collection clears local state only and does not delete remote vectors.** Reindexing creates a new namespace. Live Pinecone access is not verified; all adapter test results use mocks. No LangSmith account or remote tracing has been configured.

## Corpus and ingestion

Three real English arXiv PDFs are recorded in [data/sources.json](data/sources.json):

- [RAG — Lewis et al., 2005.11401v4](https://arxiv.org/abs/2005.11401v4).
- [Self-RAG — Asai et al., 2310.11511v1](https://arxiv.org/abs/2310.11511v1).
- [CRAG — Yan et al., 2401.15884v3](https://arxiv.org/abs/2401.15884v3).

The current snapshot contains 65 PDF pages and 222 chunks. `scripts/download_papers.py` downloads pinned versions and records SHA-256 hashes in `data/download-record.json`. PDFs are ignored by Git; review source licenses before redistribution. Authored synthetic fixtures exist only inside tests and are never attributed to real authors.

Uploads accept 1–8 text-based PDFs, up to 20 MB and 200 pages each. The LangChain `BaseLoader` implementation uses pypdf, normalizes whitespace and line hyphenation, removes short repeated boilerplate where detected, and retains one-based physical PDF page numbers. It preserves filenames, content-derived paper IDs, source versions, and chunk offsets. Scans need OCR before upload. Complex tables, figures, equations, and multi-column layouts may extract poorly: inspect the original page.

The recursive splitter uses **1,400 characters / 200 characters overlap**, within each page. These are character counts, not token counts, and are an initial choice to evaluate jointly with the embedding model.

## Retrieval and graph

```text
PDF -> page documents -> recursive chunks -> embeddings -> in-memory store
                                                      + BM25
Question -> dense + sparse ranks -> reciprocal rank fusion (top 6)
         -> lexical evidence/selected-paper coverage heuristic
              | adequate -> excerpts (demo)
              |          -> draft -> citation/quote validation -> model audit (live)
              | weak -> expand once to 12 -> recheck -> answer or insufficient evidence
```

Comparisons reserve coverage for selected papers. If more than six papers are selected, the first pass may need expansion to cover them. Quote validation checks that the evidence ID resolves and the quote exists in that passage; a second model call checks whether the whole claim is supported. This is a useful defense, not a proof of semantic correctness. Every accepted generated claim is labeled `Reported finding` or `Interpretation`; uncited model explanations are never surfaced.

The reading matrix is **retrieved excerpts**, not a generated comparative conclusion. Its four dimensions are methods, datasets, findings, and limitations. Missing matches are explicit. Neither it nor the question view claims that differing experiments are directly comparable.

The reading matrix also prefers relevant section headings within its retrieved candidate set; that is a deterministic heuristic, not a model reranker.

The displayed workflow trace is local application data. LangSmith remote tracing/evaluation is not configured. No parent-document retriever, self-query retriever, multi-query retriever, agentic multi-hop planner, or separate model reranker is implemented. The graph directly invokes LangChain components; there is no explicit LCEL pipe composition.

## Tests and measured evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate
```

The latest run passed **32 tests**: PDF parsing and page boundaries, invalid/scanned files, retrieval filtering and paper coverage, exact local excerpts, bounded refusal, forged citation rejection, rejected-output containment, mocked live generation/audit success and failure, provider failure, an upload/ask/PDF/delete API round trip, section-aware matrix selection with absent limitations, and the optional Pinecone adapter using mocks. Mocked live tests are not real provider validation.

The [evaluation report](evaluation/REPORT.md) and [raw results](evaluation/results.json) record 14 questions, including 10 evidence-annotated direct/cross-paper questions and 4 fallback/ambiguous/adversarial cases:

- Mean gold-evidence recall@6: **75% baseline → 80% hybrid**, +5 percentage points.
- Fallback routing: **3/4** cases. The adversarial question returned labeled source excerpts; this remains a documented local-mode limitation.
- Local graph query p95: **193 ms** in this run, excluding ingestion. This is not live latency or a browser-to-browser measurement.
- **Live faithfulness and live latency are not measured.** Neither the 95% nor 15-second target is established.

Both retrieval strategies use lexical hash embeddings in this evaluation. This measures a local retrieval improvement, not the quality of live semantic embeddings. The tiny authored development set is not held out. Exact-term queries can retrieve related-work/references; cross-paper coverage can displace useful passages. Gold anchors are verified against the actual PDF text before scoring.

For live review, use the same questions, inspect every claim against its full source, and record outcomes in [evaluation/human-review.csv](evaluation/human-review.csv). Faithfulness = supported factual claims / evaluated factual claims; refusals are excluded and answer coverage is reported separately. Score relevance 0–2, citation validity, correct and false refusals, p50/p95 query latency, and misses over 15 seconds. Request timeouts (18 seconds per model call and 30 seconds per embedding call) are failure limits, not an enforced 15-second total deadline.

## Interface verification

The landing page was inspected in the in-app browser at desktop and 390px mobile width. Local screenshots are in `docs/screenshots/` and are excluded from public Git content. Browser QA covers sample loading, question retrieval, citation inspection, reading matrix, evaluation display, and ambiguity handling; see `docs/VERIFICATION.md` for the completed checklist and limits. Reduced-motion styles suppress animation. The saved HTML project brief has no external dependencies; the app's typography loads Google Fonts with system fallbacks.

## Project documentation

The [project documentation](docs/PROJECT_DOCUMENTATION.md) is the detailed record of the overview, datasets, prompts, iterations, and observations. The [project brief](docs/project-brief.html), [development notes](docs/DEVELOPMENT.md), and [demo outline](docs/DEMO.md) provide shorter references. Publication details are in [docs/PUBLICATION.md](docs/PUBLICATION.md). The app remains a local prototype, not a production service.

## Implementation references

The implementation was checked against the official [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and [LangChain in-memory vector store API](https://reference.langchain.com/python/langchain-core/vectorstores/in_memory/InMemoryVectorStore). These informed the StateGraph and store implementation.
