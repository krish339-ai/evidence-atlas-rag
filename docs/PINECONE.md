# Configure the live model and Pinecone

The optional adapter is implemented and tested with mocks. A real Pinecone connection and real model calls have **not** been verified. Use an existing compatible index; this app never creates an index, changes its configuration, or deletes remote vectors.

## Enter credentials locally

1. Open `.env` in your local editor. If it does not exist, copy `.env.example` to `.env`. Do not paste keys into chat, the browser UI, GitHub, screenshots, or the project brief.
2. Fill `MODEL_API_KEY` for your chosen model provider. Set `MODEL_BASE_URL`, `CHAT_MODEL`, and `EMBEDDING_MODEL` to models/endpoints your account supports. The default live configuration is `gpt-4.1-mini` plus `text-embedding-3-small` at the OpenAI-compatible base URL in the template.
3. If embeddings use another provider, fill `EMBEDDING_API_KEY` and `EMBEDDING_BASE_URL`. Otherwise leave these blank to reuse the model provider settings.
4. Enter `PINECONE_API_KEY` and the exact existing `PINECONE_INDEX_NAME`. Use a key with access only to the intended project where practical.
5. Confirm the existing index accepts externally generated **dense** vectors with the **cosine** metric. Set `EMBEDDING_DIMENSIONS` to the actual embedding output size and index dimension; the default small embedding model normally uses 1536. Integrated-embedding and sparse indexes are not supported by this adapter.
6. Set `PAPERTRAIL_MODE=live` and `VECTOR_BACKEND=pinecone`. Keep `PINECONE_NAMESPACE_PREFIX=papertrail`, or use a project-specific prefix beginning `papertrail-`. Each collection gets a fresh random suffix, so the app never uses the default or an existing unrelated namespace.
7. Install the adapter if needed: `python -m pip install -r requirements-pinecone.txt`. It is already installed in this workspace and included in the recorded complete lock file.
8. Restart the server and load a small public sample first. The mode badge shows the configured backend, and the library shows the created namespace after indexing succeeds. Configuration presence does not imply a successful connection.

```dotenv
PAPERTRAIL_MODE=live
VECTOR_BACKEND=pinecone
MODEL_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
PINECONE_NAMESPACE_PREFIX=papertrail
```

The blank values above must be filled only in your ignored local `.env`. Do not commit a filled example.

## What the adapter checks

Before sending the corpus, it probes the embedding dimension using a fixed non-document string, reads the named index's description, and verifies dimension, dense-vector type, cosine metric, and ready status. It resolves the host from that description and uses the host for the data client. It then writes only into a new `papertrail-<random collection id>` namespace through `PineconeVectorStore`.

Ingestion waits up to 12 seconds for the namespace's reported vector count because Pinecone is eventually consistent. A failed/partial write reports its namespace with a safe error message. No automatic remote cleanup occurs. A compatible paid model call and Pinecone operations may consume your provider credits; no new paid resource is created by the app.

Hybrid retrieval remains semantic-vector ranks plus local BM25 ranks and reciprocal rank fusion. It is not Pinecone-native sparse hybrid search or a model reranker. Dense candidates are capped at 1,000 per query for payload size; returned chunk IDs are reconciled with the current local collection before citations are displayed.

## Persistence and clearing

Pinecone retains vectors **and passage text/metadata** after the local process stops. Original PDF bytes, the local BM25 corpus, collection IDs, and the UI session remain in memory. Remote vectors alone do not restore a usable collection after restart, and this prototype does not yet implement a persistent collection catalog.

**Clear collection clears local state only.** It deliberately does not delete Pinecone data. Keep the namespace shown by the app if you want to manage those vectors later in your Pinecone console. Reindexing creates another namespace; review unused namespaces yourself. No data in unrelated namespaces is read, overwritten, or deleted by this adapter.

To return to a credential-free local demo, set `PAPERTRAIL_MODE=demo` and `VECTOR_BACKEND=memory`, then restart. Never silently substitute local retrieval after a failed live configuration; the app surfaces the error.

## Verification boundaries

Mock tests cover mismatched dimensions/metrics, non-ready/sparse/integrated indexes, missing credentials, safe namespaces, isolated writes, and redacted partial-write failures. They do not prove your account permissions, network, billing, embedding-model availability, or service latency. The current 75% → 80% retrieval comparison is an offline result, not a Pinecone benchmark.

The implementation uses the official [LangChain PineconeVectorStore API](https://reference.langchain.com/python/langchain-pinecone/vectorstores/PineconeVectorStore), Pinecone's [index-targeting guidance](https://docs.pinecone.io/guides/manage-data/target-an-index), and [data-freshness guidance](https://docs.pinecone.io/guides/index-data/check-data-freshness). Installed adapter versions are recorded in `requirements-lock.txt`.
