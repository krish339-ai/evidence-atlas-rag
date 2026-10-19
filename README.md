# Evidence Atlas RAG

The product and repository share the Evidence Atlas RAG name. The internal Python package retains its existing import path; see [compatibility notes](docs/COMPATIBILITY.md) for the supported legacy configuration identifiers.

A local PDF evidence workspace built with LangChain and LangGraph. The default sample is **CMS Medicare Advantage prior authorization for inpatient and outpatient medical services**, using three official U.S. government PDFs. The RAG/Self-RAG/CRAG research sample remains selectable. It includes a responsive editorial landing page, PDF uploads, cited research questions, a source-excerpt reading matrix, inspectable PDF evidence, research-trail export, and a reproducible evaluation.

**Original research-sample scope:** My RAG app helps AI learners answer research questions from the RAG, Self-RAG, and CRAG papers in a web app, targeting 95% faithfulness and responses within 15 seconds.

Those are targets, not verified achievements. This first version works without credentials in **local excerpt mode**. Live semantic embeddings and generated answers need model configuration. Live spot checks have succeeded; aggregate faithfulness and latency remain unmeasured.

## Start, stop, and restart on Windows

Complete **Fresh setup** below once. Then double-click a batch file in the project folder:

| File | Action |
|---|---|
| `start.bat` | Starts the app in the background, checks that it is ready, and prints the local URL. Running it again does not create another server. |
| `stop.bat` | Stops the server started by these batch files for this project. Running it when the server is already stopped is harmless. |
| `restart.bat` | Stops the managed server and starts it again in demo/memory mode. |
| `restart-live.bat` | Stops the managed server and starts it in live/memory mode using your existing provider configuration. Requires `MODEL_API_KEY`; document indexing and questions can incur API charges. |

Open <http://127.0.0.1:8000>. Click **Explore CMS guidance**, then ask a question or build a reading matrix. You can close the launcher window after it reports ready; the app keeps running until you use `stop.bat` or shut down Windows.

`start.bat` and `restart.bat` use **demo/memory mode**, disable remote tracing, and skip loading `.env`. No model credentials or paid API calls are needed for those launchers. `restart-live.bat` explicitly selects **live/memory mode**, allows the app to load its existing `.env`, and keeps remote tracing disabled. None of the launchers edits your saved configuration. Stopping or restarting clears loaded documents, questions, and other in-memory collection state; reload your sample or PDFs afterward.

You can also run them from PowerShell. Add `--no-pause` to skip the final keypress prompt:

```powershell
.\start.bat --no-pause
.\stop.bat --no-pause
.\restart.bat --no-pause
```

To test generated answers, save your provider configuration locally as described under **Two honest operating modes**, then double-click `restart-live.bat` or run:

```powershell
.\restart-live.bat --no-pause
```

Refresh the browser and confirm **LIVE MODE · MEMORY** before loading documents again. Live indexing sends document text to the configured embedding provider; questions and retrieved passages go to the model provider. The launcher checks local configuration and server readiness only; it does not make a paid test request or establish that your account has available API credit. If the key is missing, it stops the newly started server and reports a configuration error. Use `stop.bat` to stop either managed mode, or `restart.bat` to return to demo mode.

The files work from any current directory, including project paths containing spaces. They use the included `scripts/local-server.ps1` helper and Windows PowerShell; no administrator rights are needed. The execution-policy override applies only to that helper process, not your permanent system policy. Organization policies may still prevent scripts from running.

**Troubleshooting:**

- **Missing Python environment or dependencies:** complete Fresh setup below. The scripts do not install packages automatically.
- **Port 8000 already in use:** if you launched the app manually or with `run.cmd`, stop it in its original terminal with Ctrl+C first. The batch files deliberately leave unmanaged servers and unrelated processes alone.
- **Startup fails or times out:** inspect `tmp/local-server/stderr.log` and `tmp/local-server/stdout.log`. These logs are replaced on each start. The ignored `tmp/local-server/server.json` records process identities so stale process IDs cannot target another application; leave it in place while the server runs.
- **App opens but samples do not load:** run the sample download command in Fresh setup. Downloads require an internet connection; asking demo-mode questions does not call a model provider.

For a foreground server that uses your configured environment (including live mode), the existing `run.cmd` remains available. Stop a batch-managed instance first, run `run.cmd`, and use Ctrl+C in its terminal to stop it. See **Two honest operating modes** before enabling live mode.

The self-contained [project brief](docs/project-brief.html) opens directly in a browser without starting the app. It records the primer, six-field framework, retrieval design notes, and implementation status.

## Fresh setup

Use Python 3.11+ (tested on Python 3.12, Windows). No Node build or database service is required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/download_papers.py
.\start.bat
```

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` instead, and start with `.venv/bin/python -m uvicorn papertrail.server:app --host 127.0.0.1 --port 8000` (Ctrl+C stops it). The batch files are Windows-only. The lock file records the tested environment; `requirements.txt` and `requirements-dev.txt` specify compatible ranges. If `py` is unavailable, substitute the full path to your Python executable.

## Two honest operating modes

| Mode | Retrieval | Output | Network use |
|---|---|---|---|
| `demo` (default) | Deterministic hashed word vectors + BM25 + rank fusion | Verbatim source excerpts, explicitly labeled | No model calls; sample download is a separate explicit step |
| `live` | Configured semantic embeddings + BM25 + rank fusion | Structured cited claims, quote checks, model evidence audit | Paper text to embedding provider; questions and retrieved text to model provider |

If `.env` does not exist, copy `.env.example` to it; otherwise edit the existing file locally. Set `EVIDENCE_ATLAS_MODE=live`, and supply `MODEL_API_KEY`. The initial defaults are `gpt-4.1-mini` and `text-embedding-3-small`. These are configuration defaults, not a promise that a particular account has access. Set separate embedding credentials/base URL if needed. Restart after changes.

An OpenAI-compatible provider, including a suitably configured Nebius account, needs compatible chat, embedding, and JSON-schema structured-output endpoints. No Nebius model IDs, credits, account access, or compatibility have been verified. Failed requests display a configuration error and never fabricate a successful answer. Never put keys in frontend code or commit `.env`.

The app is intended for a **single user on loopback**. Collections and PDF bytes stay in process memory; a restart clears them. Browser refresh currently requires reloading the collection. Clear the current collection in the sidebar; restart to clear any orphaned collections. There is no authentication or durable collection catalog. Pinecone can persist vectors and passage text remotely when explicitly configured; see below. Do not expose this development server publicly.

## Optional Pinecone backend

In-memory vectors are the active local backend. Pinecone is optional; live generation can also use in-memory vectors. See [the credential and index checklist](docs/PINECONE.md). Copy `.env.example` to `.env` and enter credentials locally, never in chat or frontend code.

Set `EVIDENCE_ATLAS_MODE=live`, `VECTOR_BACKEND=pinecone`, `MODEL_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_INDEX_NAME`. Confirm model names/base URLs and `EMBEDDING_DIMENSIONS` (1536 for the initial default). The adapter requires an existing, ready, externally embedded dense cosine index; it validates dimensions and metric before writing. It never creates/reconfigures an index and always allocates a fresh `evidence-atlas-...` namespace per collection.

Pinecone retains vectors and passage text; PDFs, BM25 input, and the collection catalog remain process-local. **Clear collection clears local state only and does not delete remote vectors.** Reindexing creates a new namespace. Live Pinecone access is not verified; all adapter test results use mocks. No LangSmith account or remote tracing has been configured.

## Default healthcare sample

The CMS sample indexes selected coverage, prior-authorization process, concurrent-review, and notice provisions. It preserves physical PDF pages and distinguishes 2024 coverage guidance, 2026 process/protection changes, and the cited 2027 API requirement. It is an educational administrative demo, with no patient records, individual approval decisions, or universal payer checklist.

See [healthcare source provenance, boundaries, test questions, and mode configuration](docs/HEALTHCARE_SAMPLE.md). The [CMS manifest](data/cms-sources.json) pins official URLs, hashes, dates, and exact indexed sections. The current selection covers 11 distinct pages and 20 chunks within three complete original PDFs. Hash changes stop indexing for review.

Use the workspace selector to load CMS guidance or the original research sample. Switching creates a separate collection and clears the previous question, answer, matrix, and citations. `POST /api/demo` defaults to `cms-ma`; `POST /api/demo?sample_id=rag` loads the research papers. `scripts/download_papers.py` downloads both; `--sample cms-ma` or `--sample rag` downloads one.

The separate [CMS source check report](evaluation/HEALTHCARE_REPORT.md) records **18/18 checks** using actual PDF sections, page/phrase anchors, refusal cases, and source integrity. These do not measure clinical accuracy, legal completeness, or live-answer faithfulness. The original research metrics below apply only to the three research papers.

## Research corpus and ingestion

Three real English arXiv PDFs are recorded in [data/sources.json](data/sources.json):

- [RAG — Lewis et al., 2005.11401v4](https://arxiv.org/abs/2005.11401v4).
- [Self-RAG — Asai et al., 2310.11511v1](https://arxiv.org/abs/2310.11511v1).
- [CRAG — Yan et al., 2401.15884v3](https://arxiv.org/abs/2401.15884v3).

The current snapshot contains 65 PDF pages and 222 chunks. `scripts/download_papers.py` downloads pinned versions and records SHA-256 hashes in `data/download-record.json`. PDFs are ignored by Git; review source licenses before redistribution. Authored synthetic fixtures exist only inside tests and are never attributed to real authors.

Uploads accept 1–8 text-based PDFs, up to 20 MB and 200 pages each. The LangChain `BaseLoader` implementation uses pypdf, normalizes whitespace and line hyphenation, removes short repeated boilerplate where detected, and retains one-based physical PDF page numbers. It preserves filenames, content-derived paper IDs, source versions, and chunk offsets. Scans need OCR before upload. Complex tables, figures, equations, and multi-column layouts may extract poorly: inspect the original page.

After an upload finishes, **Try a question** shows up to eight starter questions drawn from sections and repeated terms in the uploaded text. Click a question to submit it immediately. Suggestions reflect the selected PDFs and remain available after each response. Creating them requires no extra model request; clicking one follows the normal demo or live answer flow. These are starting points, not guarantees that a complete answer exists. After a completed response, the question box clears for your next question. Connection/provider errors retain the question for retry, and text you type while waiting is preserved.

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

Comparisons reserve coverage for selected papers. If more than six papers are selected, the first pass may need expansion to cover them. In live mode, the model writes claims and selects evidence IDs. The application attaches each cited passage's original text as the supporting quote, avoiding punctuation corruption from model transcription. Citation and quote validation still run, and a second model call checks whether the passage supports the whole claim. This is a useful defense, not a proof of semantic correctness. Every accepted generated claim is labeled `Reported finding` or `Interpretation`; uncited model explanations are never surfaced.

`ANSWER NOT VERIFIED` means a draft failed citation, completeness, or evidence-audit checks; the message identifies the failed check. Generation and auditing explicitly preserve material exceptions, conditions, affected groups, and provision-specific dates. A local guard also withholds broad claims that omit explicit parenthetical exclusions in their matching source sentence, even if a model would approve them. This guard is conservative and limited to recognizable wording; semantic auditing and human source review remain necessary. This differs from retrieval finding insufficient evidence or the model reporting insufficient support. Rejected claims are withheld. **Export trail** includes retrieved passages, page references, the workflow, and the rejection reason even when no answer was accepted. Exports contain source document text; treat them with the same care as the original PDFs. Failed question requests remain visible as **REQUEST FAILED**, with the question preserved for retry.

The reading matrix is **retrieved excerpts**, not a generated comparative conclusion. Its four dimensions are methods, datasets, findings, and limitations. Missing matches are explicit. Neither it nor the question view claims that differing experiments are directly comparable.

The reading matrix also prefers relevant section headings within its retrieved candidate set; that is a deterministic heuristic, not a model reranker.

The displayed workflow trace is local application data. LangSmith remote tracing/evaluation is not configured. No parent-document retriever, self-query retriever, multi-query retriever, agentic multi-hop planner, or separate model reranker is implemented. The graph directly invokes LangChain components; there is no explicit LCEL pipe composition.

## Tests and measured evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m scripts.evaluate
```

With Node.js installed, run `node --test tests/test_export.cjs` for the browser export, suggestion-button, and question-box regression tests. Node.js is not required to run the application.

The latest run passed **63 Python tests and 12 browser-function tests**: PDF parsing and page boundaries, invalid/scanned files, retrieval filtering and paper coverage, exact local excerpts, bounded refusal, forged citation rejection, rejected-output containment, exact Unicode source quotes, specific validation failures, audit assessment before the final decision, omitted-exception rejection despite an optimistic audit, preserved exclusions and narrower claims, mocked live generation/audit success and failure, provider failure, an upload/ask/PDF/delete API round trip, section-aware matrix selection with absent limitations, Pinecone metadata-mutation isolation and reserved evidence fields, source-derived upload suggestions, one-click submission, persistent request errors, question-box clearing and draft preservation, and exports with or without accepted answers. Mocked live tests are not real provider validation.

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

The CMS checks can be regenerated with `python -m scripts.evaluate_healthcare`; the command forces demo/memory and disables dotenv loading. CI also verifies the downloaded CMS PDFs against their pinned hashes and committed source excerpts.

## Current live verification and refresh behavior

The main live/memory app and a separate live/Pinecone instance have passed bounded integration checks. Pinecone was configured for 1536-dimensional external dense vectors, cosine, serverless AWS us-east-1. A four-page public PDF produced twelve chunks; a later public answer retained its payer exception. See [the verification record](docs/VERIFICATION.md) for failures, fixes and limits, and [Pinecone architecture and setup](docs/PINECONE.md) for illustrated details.

The same tab restores its uploaded collection and document selection after refresh while the backend stays running. This reads an existing descriptor and does not re-embed or upsert. Browser storage contains only collection/selection IDs. Server restart still clears the local catalog and PDFs; Pinecone vectors alone do not restore a workspace. Closing the tab ends its saved selection. Old running servers need one restart to load these code changes.

Live generation now constrains citations to retrieved IDs and asks for separately cited list entries. Local guards reject recognizable omitted exceptions and numbers/acronyms/product spellings absent from a claim's own quote. These conservative checks can reject valid paraphrases or new abbreviations; they supplement, rather than prove, semantic support. A model-approved answer still requires source review. Private replay results and synthetic checks are distinguished in the verification record.
