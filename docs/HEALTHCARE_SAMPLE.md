# CMS Medicare Advantage prior authorization sample

The default sample covers **inpatient and outpatient medical services under Medicare Advantage (Part C)**. It is an educational administrative reading workflow over selected U.S. government documents. It does not receive patient records, decide coverage, submit authorizations, or establish a universal payer checklist.

Click **Explore CMS guidance**, or choose **CMS Medicare Advantage prior authorization** in the workspace selector. The original RAG/Self-RAG/CRAG research collection remains the second option. Loading a different sample creates a separate collection and clears the previous answer, question, matrix, and citation panel. Uploads remain supported as separate general-purpose collections.

## Sources and dates

All three originals were retrieved October 18, 2026. [The manifest](../data/cms-sources.json) records official URLs, publication and applicability dates, SHA-256 hashes, and exact page/section boundaries. Citations use original **physical PDF page numbers**, not newly numbered excerpt pages.

| Source | Publication | Indexed physical pages | Relevant scope |
|---|---|---|---|
| [CMS coverage and utilization-management FAQ, CMS-4201-F](https://www.cms.gov/files/document/hpms-memo-faq-coverage-criteria-and-utilization-management-cms-4201-f-02-6-2024-pdf.pdf) | February 6, 2024 | 1, 8–9, 11–12 | Individual coverage criteria; inpatient two-midnight benchmark versus presumption; prior, concurrent, and claim review; prior-authorization exceptions and continuity. Selected provisions apply to coverage beginning January 1, 2024. |
| [CMS interoperability and prior-authorization fact sheet, CMS-0057-F](https://www.cms.gov/files/document/fact-sheet-cms-interoperability-and-prior-authorization-final-rule-cms-0057-f.pdf) | January 17, 2024 | Selected sections on 1–3 | Operational process requirements beginning January 1, 2026; PA API requirement beginning January 1, 2027. Drugs excluded. The original addresses several payer types; this sample applies its MA scope only. |
| [CMS CY 2026 final rule, CMS-4208-F, 90 FR 15792](https://www.govinfo.gov/content/pkg/FR-2025-04-15/html/2025-06008.htm) | April 15, 2025 | Date statement on 1 and selected amendments on 119–120 (printed 15910–15911) | Prior/pre-service/concurrent inpatient and outpatient approvals, organization determinations, notices, and inpatient reopening restrictions. Effective June 3, 2025; selected amendments apply to coverage beginning January 1, 2026. |

The original PDFs total 148 physical pages. The application indexes 13 selected text spans on 11 distinct pages, producing 20 chunks with the current splitter. It serves the complete original PDFs for inspection. Section selection normalizes whitespace and retains source wording and original page metadata. Hash mismatch or missing section anchors stops indexing rather than silently accepting a changed source.

The FAQ's older reopening discussion is excluded in favor of the 2026 regulatory amendments. The fact sheet's electronic reporting measures, most API technical specifications, and the final rule's unrelated Part D provisions are excluded. These choices keep the sample focused; they do not establish exhaustive or continuously current legal coverage. Some sections continue across pages. Inspect adjacent original pages when a passage is incomplete.

## Interpretation boundaries

- Coverage criteria and prior authorization are different questions. Inpatient admission criteria do not imply that every inpatient or outpatient service requires prior authorization.
- The FAQ distinguishes the inpatient **two-midnight benchmark** from the Traditional Medicare contractor **two-midnight presumption**. Do not transfer contractor review procedures to MA.
- The 2026 amendments address concurrent decisions involving both inpatient and outpatient services. The additional-clinical-information restriction on reopening an approved inpatient admission has its own narrower scope; it must not be generalized to every outpatient decision.
- General medical-record factors and a future API's ability to identify documentation requirements do not constitute a procedure-specific submission checklist. This sample contains no plan portal, patient eligibility record, complete procedure list, or commercial payer policy.
- Rules about Original Medicare, Medicaid, commercial insurance, and drugs require separately scoped source collections. Dates and exceptions must remain attached to any explanation.

Demo mode returns exact source excerpts with scope and date notes. Its lexical gate does not prove that a passage answers the question. A conservative scope filter rejects common individual-decision, other-payer, universal-checklist, and fabricated-citation requests. It is not a comprehensive intent classifier. Live mode adds scope instructions, exact quote checks, and a model audit; those mechanisms still require human review.

## Questions to try

| Select | Question | Check |
|---|---|---|
| Coverage FAQ | How do the two-midnight benchmark and presumption differ for Medicare Advantage inpatient admissions? | Physical page 8; preserve MA versus Traditional Medicare distinction. |
| Coverage FAQ | What physician expectation and medical record support are relevant to inpatient admission criteria? | Page 9; expected care at admission, not an automatic approval promise. |
| 2026 protections | What protection applies after approval during inpatient or outpatient services under the 2026 rule? | Page 119; check the inpatient reopening qualification on page 120. |
| Process rule | What are the standard and expedited prior authorization decision timeframes beginning in 2026? | Page 3; medical services, applicable payer scope, and dates. |
| Process rule | When must the Prior Authorization API identify documentation requirements and communicate request outcomes? | Page 2; 2027 requirement, not an API implemented by this app. |
| FAQ + 2026 protections; comparison enabled | Compare inpatient admission review in the coverage FAQ with concurrent inpatient and outpatient approval protections in the 2026 rule. | Evidence from both selected documents; distinguish criteria from process protections. |
| Any CMS documents | Give me a universal prior authorization submission checklist for every payer. | Insufficient evidence; no invented checklist. |
| Any CMS documents | Will my patient's inpatient surgery be approved? | No individual decision. Do not enter patient details. |
| Any CMS documents | What outpatient authorization form does Aetna commercial insurance require? | Outside this sample's payer scope. |
| Any CMS documents | What are the Part D prescription drug authorization deadlines? | Outside this medical-service sample. |

Switch to the research sample after answering a CMS question: its starter questions and matrix labels should change, and previous CMS citations should disappear. Switch back and confirm that the research citations disappear. Within a collection, deselect a document and verify that subsequent retrieval uses only the selected documents.

## Reproduce the checks

```powershell
.\.venv\Scripts\python.exe scripts/download_papers.py --sample cms-ma
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate_healthcare
```

The [CMS report](../evaluation/HEALTHCARE_REPORT.md) records 18/18 checks: ten answerable retrieval cases, seven insufficient-evidence cases, and full PDF/fixture integrity. Tests additionally check default selection, changed-source rejection, collection isolation, original PDF bytes, absent matrix evidence, and refusal without a provider call. CI downloads the pinned government PDFs and verifies the real-source checks; an upstream source change fails visibly.

These are small authored development checks, not a held-out benchmark, legal review, clinical validation, or a measurement of live answer faithfulness. The [original research report](../evaluation/REPORT.md) remains separately scoped to RAG/Self-RAG/CRAG. Its 75%/80% retrieval figures do not describe this CMS sample.

## Live mode configuration

The supported local defaults are `EVIDENCE_ATLAS_MODE=live`, `MODEL_BASE_URL=https://api.openai.com/v1`, `CHAT_MODEL=gpt-4.1-mini`, `EMBEDDING_MODEL=text-embedding-3-small`, and `VECTOR_BACKEND=memory`. Enter `MODEL_API_KEY` locally in the ignored `.env`. Blank `EMBEDDING_API_KEY` and `EMBEDDING_BASE_URL` fall back to the chat key and URL. `EVIDENCE_ATLAS_MODE` takes priority over the legacy `PAPERTRAIL_MODE` fallback. Preserve existing `.env` contents when editing.

Live results, the 95% faithfulness goal, and the 15-second live response target remain unverified. Local retrieval checks are not measurements of generated-answer quality. Pinecone remains optional and inactive. The runnable preview uses demo/memory. A model request failure is not an insufficient-evidence result.
