"""Optional Pinecone storage: existing cosine index, unique collection namespace."""
import time
import uuid


def _field(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def validate_description(description, expected_dimension):
    if _field(description, 'dimension') != expected_dimension:
        raise ValueError('Pinecone index dimension does not match EMBEDDING_DIMENSIONS. Choose a compatible existing dense index; this app will not reconfigure it.')
    if _field(description, 'metric') != 'cosine':
        raise ValueError('Evidence Atlas RAG requires a cosine Pinecone index. This app will not change the existing index metric.')
    if _field(description, 'vector_type', 'dense') != 'dense':
        raise ValueError('Evidence Atlas RAG requires a dense vector index, not a sparse or integrated-embedding index.')
    if _field(description, 'embed'):
        raise ValueError('Use an index for externally generated dense vectors, not a Pinecone integrated-embedding index.')
    if not _field(_field(description, 'status', {}), 'ready', False):
        raise ValueError('The Pinecone index is not ready. Retry when the existing index is ready.')


def build_pinecone_store(chunks, embedding, config, client_factory=None, store_factory=None):
    config.validate()
    if client_factory is None or store_factory is None:
        try:
            from pinecone import Pinecone
            from langchain_pinecone import PineconeVectorStore
        except ImportError as exc:
            raise ValueError('Install the optional backend: python -m pip install -r requirements-pinecone.txt') from exc
        client_factory = client_factory or Pinecone
        store_factory = store_factory or PineconeVectorStore
    # Probe only a fixed non-document string before sending the corpus anywhere.
    try:
        dimension = len(embedding.embed_query('Evidence Atlas RAG embedding dimension compatibility check'))
    except Exception as exc:
        raise ValueError('Embedding compatibility probe failed. Check the embedding credentials, model name, and endpoint in .env.') from exc
    if dimension != config.embedding_dimensions:
        raise ValueError('The embedding model output does not match EMBEDDING_DIMENSIONS. Check your model configuration before indexing.')
    try:
        client = client_factory(api_key=config.pinecone_api_key)
        description = client.describe_index(config.pinecone_index)
    except Exception as exc:
        raise ValueError('Could not describe the existing Pinecone index. Check the local key, index name, permissions, and connection.') from exc
    validate_description(description, dimension)
    namespace = f'{config.namespace_prefix}-{uuid.uuid4().hex}'
    remote = client.Index(host=_field(description, 'host'))
    store = store_factory(index=remote, embedding=embedding, namespace=namespace)
    ids = [d.metadata['chunk_id'] for d in chunks]
    try:
        # PineconeVectorStore inserts its text field into each metadata dict.
        # Keep those transport mutations out of the local citation corpus.
        store.add_documents([doc.model_copy(deep=True) for doc in chunks], ids=ids)
        # Pinecone is eventually consistent. Bound the readiness wait at ingestion.
        deadline = time.monotonic() + 12
        while True:
            stats = remote.describe_index_stats()
            count = _field(_field(stats, 'namespaces', {}).get(namespace, {}), 'vector_count', 0)
            if count >= len(chunks):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('Namespace visibility timeout')
            time.sleep(.4)
    except Exception as exc:
        # Never auto-delete remotely, even on a partial write. Expose only safe recovery context.
        raise ValueError(f'Pinecone indexing did not finish. Partial vectors may remain in namespace {namespace}. Check this namespace in your console; no remote cleanup was performed.') from exc
    return store, namespace
