# CMS Medicare Advantage source checks

CMS Medicare Advantage sample checks using the three downloaded government PDFs, pinned hashes, original physical pages, and selected text sections. Demo/memory only.

18/18 checks passed. Generated 2026-10-18T16:25:28.264417+00:00.

Small authored development set, not held out. Checks source retrieval, exact excerpt citations, scope routing, and source integrity. Does not measure legal completeness, clinical accuracy, live model faithfulness, or authorization outcomes. Separate from the RAG-paper evaluation.

| Check | Result | Observation |
|---|---|---|
| cms01 — inpatient | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms02 — documentation | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms03 — outpatient | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms04 — timelines | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms05 — denial-notice | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms06 — future-api | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms07 — inpatient-reopening | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms08 — emergency-exceptions | PASS | 1/1 annotated page/phrase anchors retrieved; route excerpts |
| cms09 — comparison | PASS | 2/2 annotated page/phrase anchors retrieved; route excerpts |
| cms10 — unanswerable-checklist | PASS | Expected insufficient; actual insufficient |
| cms11 — individual-decision | PASS | Expected insufficient; actual insufficient |
| cms12 — other-payer | PASS | Expected insufficient; actual insufficient |
| cms13 — drug-exclusion | PASS | Expected insufficient; actual insufficient |
| cms14 — unrelated | PASS | Expected insufficient; actual insufficient |
| cms15 — adversarial | PASS | Expected insufficient; actual insufficient |
| cms16 — program-scope | PASS | Expected insufficient; actual insufficient |
| cms17 — effective-date | PASS | 2/2 annotated page/phrase anchors retrieved; route excerpts |
| source-integrity — provenance | PASS | All three original PDF SHA-256 hashes, section anchors, physical pages, and committed fixture texts verified. |

## Later integration work

The saved measurements above remain unchanged. Later live/memory and live/Pinecone integration checks, citation fixes, and refresh verification are recorded separately in [VERIFICATION.md](../docs/VERIFICATION.md). They are not additional benchmark cases or aggregate faithfulness measurements.
