# Verification record

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
