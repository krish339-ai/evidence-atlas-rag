# Evidence Atlas RAG development notes

Design rationale, implementation history, and remaining validation work.

## Overview

Evidence Atlas RAG helps AI learners compare research papers through questions, source excerpts, page citations, and a reading matrix. It uses LangChain and LangGraph with a custom web interface.

Use the exact primer and six-field framework from `project-brief.html`. The 95% faithfulness and 15-second response figures are proposed targets, not verified results.

## Datasets

The default sample uses selected CMS Medicare Advantage guidance. The secondary research corpus consists of version-pinned RAG, Self-RAG, and CRAG PDFs from arXiv. See `data/sources.json` for authors and URLs and `data/download-record.json` for byte hashes. User uploads are optional. Synthetic fixtures are authored solely for deterministic testing and are not research evidence.

## Prompts and agent instructions

`papertrail/graph.py` contains the actual answer system prompt and evidence-audit prompt. The answer prompt treats passages as untrusted data, requires an evidence ID per claim, separates reported findings from interpretation, rejects unsupported conclusions, and warns against comparing incompatible experiments. The model returns a structured schema of claims and source IDs. The application copies each cited passage verbatim into its claim's quote before citation validation and the separate evidence audit; the model does not transcribe source punctuation. The audit schema places its evidence assessment before its final decision, and the prompt recognizes facts directly established by headings and list entries. Unverified drafts are withheld and receive a specific rejection reason. The application never displays uncited explanation text.

Codex assisted with implementation, dependency debugging, browser inspection, and tests. The development process used official API references and checked the research workspace with deterministic tests and visual inspection.

## Iterations actually tried

1. Implemented page-preserving ingestion and a deterministic vector retrieval baseline.
2. Added BM25, reciprocal rank fusion, and selected-paper coverage. The first local comparison improved mean gold-evidence recall@6 from 75% to 80% on the same 10 answerable questions.
3. Added one bounded retrieval expansion and an insufficient-evidence route. Three of four fallback cases passed; adversarial wording still retrieves local excerpts. This is documented rather than hidden.
4. Closed a grounding gap: uncited model explanations could bypass claim checks. The application now uses fixed status text and tests that rejected explanation text never reaches the output.
5. Verified browser rendering and adjusted long-answer/evidence scrolling, citation context when switching tabs, and mobile layout.

## Learnings and limitations

Preserving page boundaries makes citations inspectable but may split an argument across pages. Hybrid retrieval helps some exact terms and cross-paper coverage but can displace other relevant chunks. Quote existence is not entailment; the live path also audits support, and human review remains necessary. The local embedding mode is lexical, not semantic. Multi-column PDFs can extract awkwardly and references can outrank substantive content.

No live provider was configured during the first build. Mocked model tests check routing and containment only. Later live/memory and live/Pinecone checks succeeded; see VERIFICATION.md. Aggregate faithfulness and response latency remain unmeasured.

## Next validation steps

- Extend live source review to held-out questions and resolve unexplained support rejections without weakening the audit.
- Measure faithfulness, answer coverage, false refusals, and end-to-end latency.
- Expand to held-out questions and additional papers.
- Record the demo after updating its narrative with actual measured results.

## Latest reliability changes

- Pinecone receives independent document copies so transport metadata cannot alter local evidence. Evidence IDs and text are assigned authoritatively by the application.
- Generation is constrained to the retrieved citation IDs. Quotes are copied locally; omitted explicit source exceptions are rejected before semantic auditing.
- Browser refresh restores the active collection and selection through a read-only endpoint, with no embedding or upsert. Server restart still clears the local catalog and PDF bytes.
- Regression checks passed: 63 Python tests and 12 browser-function tests. The original omitted-exception answer is rejected offline; a bounded public-source live replay includes the exception. Broader quality targets remain unmeasured.
