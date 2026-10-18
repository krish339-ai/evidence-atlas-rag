# Evidence Atlas RAG demo outline

The default walkthrough uses **CMS Medicare Advantage prior authorization**, covering inpatient and outpatient medical services. This is an educational administrative reading demo. Use public guidance only; do not enter patient details.

1. Click **Explore CMS guidance**. Show the three sources, indexed-page counts, and scope/date notes.
2. Ask “What protection applies after approval during inpatient or outpatient services under the 2026 rule?” Inspect the passage and original PDF page 119, then the inpatient qualification on page 120. In demo mode these are source excerpts, not a generated conclusion.
3. Build the CMS reading matrix. Explain that coverage criteria, review stages, documentation/notices, and timeframes are separate dimensions. Empty cells are allowed.
4. Ask “Give me a universal prior authorization submission checklist for every payer.” Show the insufficient-evidence result.
5. Open Evaluation. Explain the separate CMS actual-source checks and their limits; they are not clinical validation or live-model quality measurements.
6. Switch to the research sample. Show changed starter questions and matrix categories and the cleared citation panel. The research-only walkthrough below remains available.

See [source provenance and more test questions](HEALTHCARE_SAMPLE.md). OpenAI live verification stopped at a HTTP 429 quota error on the first embedding call; run this walkthrough in demo/memory until that is resolved. Pinecone remains optional and inactive.

## Original research-sample walkthrough

Aim for 4 minutes 30 seconds, leaving 30 seconds of margin. This is a recording plan; no video has been recorded.

1. **0:00–0:35 — Problem and scope.** Show the landing page. Explain that AI learners need to compare a small research corpus while keeping every claim close to a paper and page. State the 95% faithfulness / 15-second targets as targets.
2. **0:35–1:10 — Real corpus.** Load RAG, Self-RAG, and CRAG. Show source links, versions, and the 65 pages / 222 chunks. Explain local mode versus live mode before asking a question.
3. **1:10–2:00 — Follow an evidence trail.** Ask “How does Self-RAG use reflection tokens?” Open a citation, inspect its passage, and open the original PDF page. In local mode explicitly say this is excerpt retrieval, not generated synthesis.
4. **2:00–2:40 — Compare with context.** Build the reading matrix. Show the four dimensions and a citation. Explain why different datasets and metrics prevent a simple ranking.
5. **2:40–3:15 — Refuse responsibly.** Ask “Which paper is best?” Show the insufficient-evidence response and request for comparison criteria, then expand the LangGraph workflow trace.
6. **3:15–3:50 — Measure, don't assume.** Show Evaluation: 75% baseline and 80% hybrid recall on the local development set; 3/4 fallback cases. Explain that live faithfulness and latency are still unmeasured until model configuration and human review are complete.
7. **3:50–4:30 — How it was built.** Show the graph and tests in the editor. Explain Codex's role in implementation, debugging dependencies, browser inspection, and tests; explain the project scope and design decisions. End with the next meaningful experiment: a configured live run and held-out evaluation.

Before recording, configure a real model if the demo should demonstrate generated RAG answers rather than local excerpts. Run and review the live evaluation; update this script with the actual results. Do not narrate mock-provider tests as live model success.
