# Evidence Atlas RAG compatibility notes

Evidence Atlas RAG is the product name in the interface, documentation, prompts, API metadata, evaluation report, and exported research trails. The repository remains `krish339-ai/evidence-atlas-rag`.

Three legacy identifiers are intentionally retained:

| Identifier | Where it remains | Reason |
|---|---|---|
| `papertrail` Python package and `papertrail.*` imports | Package directory, Python imports and mock targets, `run.cmd`, publication allowlist, source links, and documented server commands | Preserves existing import paths, launch commands, and external integrations. It is an implementation identifier, not the product name. |
| `PAPERTRAIL_MODE` | Configuration fallback and its compatibility test | Existing local settings remain valid. `EVIDENCE_ATLAS_MODE` takes precedence when both are present. New setup instructions use the current variable. |
| `papertrail` and `papertrail-*` Pinecone namespace prefixes | Namespace validation and compatibility tests | Existing configured prefixes remain valid. No stored records or namespaces are renamed, moved, or deleted. New configurations default to `evidence-atlas`; each new collection still receives a unique suffix. |

This document names those identifiers to explain compatibility. Earlier commits may contain the former branding; the rename is a normal forward commit and does not rewrite published history.

No local credential file is needed for the rename or its tests. The tests disable dotenv file loading and use offline/mocked settings. Existing running processes retain their loaded backend metadata until restarted; refreshing the page loads the updated static interface. Finish any in-memory research session before restarting, because the application's existing process-memory storage is unchanged.
