# Public source distribution

The CMS sample update adds government-source manifests, page-preserving section selection, default/secondary sample controls, healthcare source fixtures and evaluation, and scope documentation. The publication allowlist now contains 52 text files. The current local suite passes 38 tests; the CMS actual-source report passes 18/18 checks. Original research metrics remain separately labeled. CI also downloads and verifies the pinned government PDFs. Live results, the faithfulness goal, and Pinecone access remain unverified.

Repository: https://github.com/krish339-ai/evidence-atlas-rag

Evidence Atlas RAG is the product name; evidence-atlas-rag is the repository slug. The repository contains source, tests, configuration placeholders, documentation, paper metadata, and measured evaluation artifacts. Source publication does not provide a hosted application.

`PUBLIC_FILES.txt` is the explicit publication allowlist. `scripts/check_publication.py` checks those paths for known credential patterns, private absolute paths, blank credential placeholders, and unexpected tracked files. It never reads the local `.env`.

Private documents, downloaded and uploaded PDFs, credentials, session state, screenshots, logs, caches, virtual environments, and local review output are excluded. Public data includes source links, version metadata, PDF hashes, authored evaluation questions, and measured results. Paper citations and dependency metadata are retained.

The repository was created with a generated README before application publication. The first application commit is [`325f9eb8c3beb04885d713e7ff2f1f976a9d47c1`](https://github.com/krish339-ai/evidence-atlas-rag/commit/325f9eb8c3beb04885d713e7ff2f1f976a9d47c1). Its 42 remote file paths and Git blob hashes were verified against the reviewed local index. The original README-only commit is retained; no remote history rewrite was needed.

The recorded local suite passed 29 tests. GitHub Actions runs the offline tests and publication checker on pushes and pull requests; consult the repository's Actions tab for the status of a particular commit. Live model and Pinecone validation remain separate, uncompleted checks.
