# Evidence Atlas RAG evaluation report

Local lexical retrieval evaluation on 14 authored questions over three real, version-pinned arXiv PDFs. Gold evidence is checked against actual page text. Both strategies use the same corpus, splitter, query scope, and top-k=6.

## Measured results

- Corpus: 65 pages, 222 chunks.
- Baseline mean evidence recall@6: 75.0%.
- Hybrid mean evidence recall@6: 80.0% (+5.0 percentage points).
- Fallback routing: 3/4 cases.
- Local end-to-end query p95: 193 ms (single run; includes first-query effects).
- Live faithfulness / live latency: NOT MEASURED.

The dense baseline uses deterministic hashed word vectors, not semantic model embeddings. Hybrid combines those vectors with BM25 and paper coverage. This small development set is not a held-out benchmark. Recall is annotated evidence-group coverage, not claim faithfulness or relevance. Live synthesis, semantic embeddings, and the 15-second live target remain unverified.

## Per-question results

| ID | Kind | Baseline recall | Hybrid recall | Route | Observation |
|---|---|---:|---:|---|---|
| q01 | direct | 50% | 50% | excerpts | Some expected evidence fell outside the six retrieved chunks. Inspect the retrieved page list before making a complete comparison. |
| q02 | direct | 100% | 100% | excerpts | All annotated evidence groups were found. This does not establish answer faithfulness. |
| q03 | direct | 100% | 100% | excerpts | All annotated evidence groups were found. This does not establish answer faithfulness. |
| q04 | direct | 100% | 100% | excerpts | All annotated evidence groups were found. This does not establish answer faithfulness. |
| q05 | direct | 100% | 100% | excerpts | All annotated evidence groups were found. This does not establish answer faithfulness. |
| q06 | direct | 50% | 50% | excerpts | Some expected evidence fell outside the six retrieved chunks. Inspect the retrieved page list before making a complete comparison. |
| q07 | direct | 100% | 100% | excerpts | All annotated evidence groups were found. This does not establish answer faithfulness. |
| q08 | direct | 100% | 100% | excerpts | All annotated evidence groups were found. This does not establish answer faithfulness. |
| q09 | cross-paper | 50% | 50% | excerpts | Some expected evidence fell outside the six retrieved chunks. Inspect the retrieved page list before making a complete comparison. |
| q10 | cross-paper | 0% | 50% | excerpts | Some expected evidence fell outside the six retrieved chunks. Inspect the retrieved page list before making a complete comparison. |
| q11 | ambiguous | n/a | n/a | insufficient | Correctly declined to answer. |
| q12 | unanswerable | n/a | n/a | insufficient | Correctly declined to answer. |
| q13 | unanswerable | n/a | n/a | insufficient | Correctly declined to answer. |
| q14 | adversarial | n/a | n/a | excerpts | Known limitation: lexical overlap returned source excerpts for an unsupported request. No generated answer was produced; semantic refusal needs live evaluation. |

## Reproduce and review

`python -m scripts.evaluate` regenerates this report and results.json. questions.json contains exact page and phrase anchors; results.json includes retrieved chunk IDs and corpus hashes. No provider credentials are needed.

Faithfulness target: 95% supported factual claims / evaluated factual claims. A human should assess each live claim against the full cited source and record supported, unsupported, or uncertain. Report answered-question coverage, refusal correctness, citation validity, relevance (0/1/2), and end-to-end p50/p95 separately. Refused questions do not count as faithful answers.

Latency target: 15 seconds end to end after ingestion. Provider request timeouts are failure limits, not proof of this target. Record misses and provider/model versions. Use a separate held-out set after tuning.

Failure analysis: exact terms can retrieve references or related-work discussions rather than the target method; lexical overlap can return excerpts for unanswerable questions; top-k may omit one side of a comparison. Paper balancing can help coverage while displacing another useful passage. None of these checks prove entailment.

## Later integration work

The saved measurements above remain unchanged. Later live/memory and live/Pinecone integration checks, citation fixes, and refresh verification are recorded separately in [VERIFICATION.md](../docs/VERIFICATION.md). They are not additional benchmark cases or aggregate faithfulness measurements.
