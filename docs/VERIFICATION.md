# Verification record

## Latest verification — October 18, 2026

- **63 Python tests and 12 browser-function tests passed.** Tests force dummy credentials and demo/memory. New regressions cover Pinecone metadata isolation, request-specific citation IDs, explicit payer exceptions, per-claim literal details, collection restoration, selection preservation, and stale-restore races.
- Main live/memory and isolated live/Pinecone sessions were exercised separately. Launchers still default to demo/memory; `restart-live.bat` explicitly chooses live/memory. Pinecone setup is described in [PINECONE.md](PINECONE.md).
- The existing Pinecone index was ready: externally embedded dense vectors, 1536 dimensions, cosine, serverless AWS us-east-1. A public four-page PDF yielded twelve chunks; upsert, namespace visibility, dense retrieval and a cited answer were observed. This was an integration check, not a benchmark.
- Human review caught an omitted payer exception despite audit approval. The captured overbroad claim now fails the local guard. A public replay included the QHP issuer exception, used one query embedding and two model requests, and passed the audit; no corpus reindexing occurred.
- A library metadata mutation caused a post-upload failure. Independent document copies and authoritative evidence fields fixed it; subsequent live submission succeeded.
- The user reported two answered and two unanswered questions on a nine-passage upload. The latter statuses were unknown citation and audit rejection. Both bounded replays returned answers after citation-schema changes, but human review found multi-passage lists assigned to one citation. The final literal-detail guard rejects those captured drafts offline. Synthetic role and skill lists with separate citations passed live checks; the final bounded replay of both original questions returned separately cited claims and passed the audit. Individual claim citations were reviewed; these checks do not establish exhaustive list coverage. A rejection is not automatically a bug.
- Same-tab refresh on both the root route and private test wrapper restored the existing nine-passage collection, selection, and namespace without re-embedding or upserting. Automated checks also cover unchecked selection and failed restoration. Original running instances and remote vectors were preserved.
- Refresh restoration is **not server-restart durability**. PDF bytes, BM25 and collection catalog remain local process state. Chat history is not restored. Remote vectors alone cannot rebuild the workspace.
- The 95% faithfulness goal and fifteen-second live latency target remain unmeasured. Saved research and CMS evaluation results are unchanged and separately scoped. No production-readiness claim is made.

The records below describe earlier builds and keep their historical counts and limitations; this section supersedes their current-status statements.

## CMS sample update — October 18, 2026

- The default CMS Medicare Advantage sample uses verified government PDF sections for inpatient and outpatient medical services. The current corpus contains 13 selected spans on 11 physical pages and 20 chunks; original PDF bytes and original citation pages are preserved.
- The expanded automated suite passes 38 tests. The separate CMS source report passes 18/18 checks against downloaded originals, including source hashes, fixture equality, page/phrase retrieval anchors, scope refusals, and applicability dates. API tests verify default selection, collection isolation, PDF serving, and absent matrix evidence. CI downloads the pinned originals explicitly.
- Browser verification exercised the default CMS CTA, an inpatient/outpatient protection question, a page-119 citation, a universal-checklist refusal, research-sample switching with cleared question/answer/evidence, the research reading matrix, and its separately labeled evaluation. The CMS landing page and workspace were also inspected at 390-pixel width with no horizontal overflow. Screenshots are excluded from publication.
- Live results and the faithfulness goal remain unverified. The preview remains demo/memory, and Pinecone is inactive.

The following original-build record is retained for historical context. Its research metrics and screenshots do not establish healthcare quality.

Verified locally on Windows with Python 3.12. Live model/Pinecone calls are not included in these results.

## Automated checks

- Pipeline tests cover PDF extraction, source/page metadata, chunk boundaries, rejection of invalid/scanned PDFs, filtered and balanced retrieval, exact excerpt output, bounded refusal, citation and quote validation, rejected model explanation containment, mocked model audit outcomes, provider failure, and an upload/ask/PDF/delete API round trip.
- Comparison tests cover the singular word “limitation” and absence of matching limitations evidence.
- Pinecone adapter tests use mocks and cover dimensions, metric, vector type, ready status, missing settings, namespace isolation, no index creation/deletion, and sanitized partial-write errors.
- Tests force local/test-only configuration before loading application modules, so entering real credentials in `.env` cannot make the test suite call providers.
- JavaScript syntax checked with `node --check static/app.js`; dependency consistency checked with `python -m pip check`.
- The 14-question retrieval evaluation uses the real pinned PDFs, verifies every expected evidence anchor against the extracted page, and saves actual retrieved chunk IDs and corpus hashes. See `evaluation/REPORT.md` for measured values and failure analysis.

## Browser checks completed

- Desktop landing page inspected visually; original paper-stack graphics and all major sections rendered.
- Landing page inspected at 390 × 844 viewport width; no horizontal document overflow observed. Temporary viewport override was reset.
- Real sample collection loaded: 3 papers, 65 pages, 222 chunks.
- A Self-RAG reflection-token question returned labeled source excerpts with paper/page citation buttons.
- Reading matrix rendered all four dimensions across three papers. Section-aware passage selection changed methods to relevant model sections and found CRAG's explicit limitation on PDF page 10.
- “Which paper is best?” produced an explicit insufficient-evidence message requesting dataset, metric, and conditions, with 0/3 papers cited.
- Evaluation view displayed 75% baseline and 80% hybrid evidence recall and the documented fallback failure.
- Project-brief route served the self-contained HTML and was inspected visually.
- No browser console errors were observed in the checked interaction sequence.

Local screenshots are stored in `docs/screenshots/` and excluded from Git publication. API tests verify PDF delivery; browser PDF-viewer behavior can vary. Local-source excerpts are not a completed live-model demo. Browser keyboard, screen-reader, and mobile coverage are limited spot checks, not a full accessibility audit.

## Remaining checks

Configure the chosen model locally with the in-memory backend, then verify actual authentication, embedding dimensions, retrieval, structured answers, and provider latency. If optional Pinecone storage is enabled later, verify its existing index and ingestion/read visibility separately. Human-review live claims and collect a held-out evaluation. No live service success, 95% faithfulness achievement, or 15-second live target achievement is claimed.

## Product name update

The renamed build passed 32 offline tests, including precedence of the current mode variable over its legacy alias and acceptance of existing namespace prefixes. Dotenv file loading is disabled in the test suite. JavaScript syntax passed; the renamed interface was visually checked at desktop and 390-pixel width, with no horizontal document overflow observed. Existing backend processes and in-memory collections were left running. Compatibility identifiers are documented in COMPATIBILITY.md.
