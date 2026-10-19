from dataclasses import replace
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from papertrail.config import Settings
from papertrail.pinecone_backend import build_pinecone_store, validate_description


def test_legacy_mode_and_current_precedence(monkeypatch):
    monkeypatch.delenv('EVIDENCE_ATLAS_MODE', raising=False)
    monkeypatch.setenv('PAPERTRAIL_MODE', 'live')
    assert Settings().mode == 'live'
    monkeypatch.setenv('EVIDENCE_ATLAS_MODE', 'demo')
    assert Settings().mode == 'demo'


@pytest.mark.parametrize('prefix', ['papertrail', 'papertrail-existing'])
def test_legacy_namespace_configuration_remains_valid(prefix):
    settings = config(namespace_prefix=prefix)
    settings.validate()
    assert settings.namespace_prefix == prefix


def config(**kwargs):
    base = Settings(mode='live', api_key='test-model-key', vector_backend='pinecone',
                    pinecone_api_key='test-pinecone-key', pinecone_index='test-existing', embedding_dimensions=3)
    return replace(base, **kwargs)


def description(**kwargs):
    return dict(dimension=3, metric='cosine', status={'ready': True}, host='test.invalid', vector_type='dense', **kwargs)


@pytest.mark.parametrize('field,value,message', [
    ('dimension', 4, 'dimension'), ('metric', 'dotproduct', 'cosine'),
    ('status', {'ready': False}, 'not ready'), ('vector_type', 'sparse', 'dense'),
    ('embed', {'model': 'integrated'}, 'externally generated'),
])
def test_rejects_incompatible_index(field, value, message):
    desc = description(); desc[field] = value
    with pytest.raises(ValueError, match=message):
        validate_description(desc, 3)


@pytest.mark.parametrize('changes,message', [
    ({'mode': 'demo'}, 'requires live'), ({'pinecone_api_key': ''}, 'PINECONE_API_KEY'),
    ({'pinecone_index': ''}, 'PINECONE_INDEX_NAME'), ({'namespace_prefix': 'unrelated'}, 'PREFIX'),
])
def test_pinecone_configuration(changes, message):
    with pytest.raises(ValueError, match=message):
        config(**changes).validate()


def test_isolated_namespaces_and_existing_index_only():
    calls, stats = [], {}

    class Embedding:
        def embed_query(self, text):
            assert text == 'Evidence Atlas RAG embedding dimension compatibility check'
            return [1, 0, 0]

    class Remote:
        def describe_index_stats(self): return {'namespaces': stats}

    class Client:
        def __init__(self, **kwargs): assert kwargs['api_key'] == 'test-pinecone-key'
        def describe_index(self, name):
            assert name == 'test-existing'; return SimpleNamespace(**description())
        def Index(self, host):
            assert host == 'test.invalid'; return Remote()

    class Store:
        def __init__(self, **kwargs): self.namespace = kwargs['namespace']
        def add_documents(self, docs, ids):
            # Mirror the real adapter's mutation rather than a read-only fake.
            for doc in docs:
                doc.metadata['text'] = doc.page_content
            calls.append((self.namespace, ids))
            stats[self.namespace] = {'vector_count': len(docs)}

    docs = [Document(page_content='Authored fixture', metadata={'chunk_id': 'fixture:1:0'})]
    first, one = build_pinecone_store(docs, Embedding(), config(), Client, Store)
    second, two = build_pinecone_store(docs, Embedding(), config(), Client, Store)
    assert one != two and one.startswith('evidence-atlas-') and two.startswith('evidence-atlas-')
    assert all(ids == ['fixture:1:0'] for namespace, ids in calls)
    assert len(calls) == 2
    assert docs[0].metadata == {'chunk_id': 'fixture:1:0'}


def test_dimension_probe_blocks_all_pinecone_operations():
    embedding = SimpleNamespace(embed_query=lambda text: [1, 0])
    def forbidden(**kwargs): pytest.fail('No Pinecone client should be opened for incompatible embeddings')
    with pytest.raises(ValueError, match='model output'):
        build_pinecone_store([], embedding, config(), forbidden, forbidden)


def test_partial_write_error_is_redacted_and_no_remote_delete():
    class Embedding:
        def embed_query(self, text): return [1, 0, 0]
    class Client:
        def __init__(self, **kwargs): pass
        def describe_index(self, name): return description()
        def Index(self, host): return object()
    class Store:
        def __init__(self, **kwargs): pass
        def add_documents(self, docs, ids): raise RuntimeError('private-key-must-not-leak')
    with pytest.raises(ValueError) as caught:
        build_pinecone_store([], Embedding(), config(), Client, Store)
    assert 'private-key-must-not-leak' not in str(caught.value)
    assert 'evidence-atlas-' in str(caught.value) and 'no remote cleanup' in str(caught.value)


def test_credentials_are_omitted_from_configuration_repr():
    text = repr(config())
    assert 'test-model-key' not in text and 'test-pinecone-key' not in text


def test_provider_probe_error_is_redacted():
    class BrokenEmbedding:
        def embed_query(self, text): raise ValueError('provider-secret-value')
    with pytest.raises(ValueError, match='compatibility probe') as caught:
        build_pinecone_store([], BrokenEmbedding(), config(), object, object)
    assert 'provider-secret-value' not in str(caught.value)
