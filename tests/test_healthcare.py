import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from papertrail import server
from papertrail.config import Settings
from papertrail.graph import ask
from papertrail.ingest import chunk_pages
from papertrail.retrieval import Index
from papertrail.samples import CMS_SCOPE, DEFAULT_SAMPLE, catalog, sources, verify_source, select_sections
from scripts.evaluate_healthcare import evaluate

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope='module')
def cms_pages():
    # Actual government text, not invented clinical examples. The full-PDF check
    # below and evaluation script compare this fixture with pinned PDF extraction.
    raw = json.loads((ROOT / 'tests/cms-source-excerpts.json').read_text(encoding='utf-8'))
    return [Document(page_content=p['text'], metadata=p['metadata']) for p in raw]


def test_cms_real_source_retrieval_citations_and_refusals(cms_pages):
    cases = evaluate(cms_pages)
    assert all(c['passed'] for c in cases), [c for c in cases if not c['passed']]


def test_default_catalog_and_unrecognized_sample():
    assert DEFAULT_SAMPLE == 'cms-ma' and [s['id'] for s in catalog()] == ['cms-ma', 'rag']
    client = TestClient(server.app)
    assert client.get('/api/status').json()['default_sample'] == 'cms-ma'
    assert client.post('/api/demo?sample_id=unknown').status_code == 400
    assert client.get('/api/evaluation?sample_id=unknown').status_code == 400


def test_snapshot_and_selection_fail_closed(cms_pages):
    with pytest.raises(ValueError, match='snapshot changed'):
        verify_source(b'changed', sources('cms-ma')[0])
    with pytest.raises(ValueError):
        select_sections(cms_pages, {'sections': [{'page': 1, 'start': 'MISSING VERIFIED SECTION'}]})


def test_scope_boundary_prevents_provider_calls(cms_pages, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail('Out-of-scope request called a provider')
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', unexpected)
    index = Index(chunk_pages(cms_pages), Settings(mode='demo', vector_backend='memory'))
    result = ask(index, Settings(mode='live', api_key='test'), 'Will my patient be approved?', [], sample_id='cms-ma')
    assert result['status'] == 'insufficient' and result['scope'] == CMS_SCOPE


def test_cms_matrix_does_not_invent_outpatient_evidence(cms_pages):
    from papertrail.comparison import CMS_DIMENSIONS, matrix_passage
    index = Index(chunk_pages(cms_pages), Settings(mode='demo', vector_backend='memory'))
    pid = next(p.metadata['paper_id'] for p in cms_pages if p.metadata['filename'] == 'CMS-PA-Process-Fact-Sheet.pdf')
    assert matrix_passage(index, pid, 'Outpatient and concurrent review', CMS_DIMENSIONS) is None


@pytest.mark.skipif(not all((ROOT / 'data/papers' / s['file']).exists() for s in sources('cms-ma')), reason='Download pinned CMS PDFs for integration check; CI downloads them explicitly')
def test_default_pdf_integration_and_collection_isolation(cms_pages, monkeypatch):
    from scripts.evaluate_healthcare import load_real_pages
    from tests.test_pipeline import pdf_bytes
    real = load_real_pages()
    assert [(p.page_content, p.metadata) for p in real] == [(p.page_content, p.metadata) for p in cms_pages]
    monkeypatch.setattr(server, 'settings', Settings(mode='demo', vector_backend='memory'))
    server.collections.clear()
    client = TestClient(server.app)
    response = client.post('/api/demo')
    assert response.status_code == 200, response.text
    cms = response.json(); cid = cms['id']
    assert cms['sample']['id'] == 'cms-ma' and cms['pages'] == 11
    raw = pdf_bytes(['Research methods and evaluation datasets. An authored upload fixture for collection isolation. ' * 3])
    upload = client.post('/api/collections', files=[('files', ('upload.pdf', raw, 'application/pdf'))]).json()
    other = upload['papers'][0]['paper_id']
    assert client.post(f'/api/collections/{cid}/ask', json={'question': 'inpatient approval', 'paper_ids': [other]}).status_code == 400
    assert client.get(f'/api/collections/{cid}/papers/{other}').status_code == 404
    assert client.get(f"/api/collections/{upload['id']}/papers/{cms['papers'][0]['paper_id']}").status_code == 404
    paper = next(p for p in cms['papers'] if p['filename'] == 'CMS-CY2026-Final-Rule.pdf')
    original = client.get(f"/api/collections/{cid}/papers/{paper['paper_id']}")
    assert original.content == (ROOT / 'data/papers' / paper['filename']).read_bytes()
    matrix = client.post(f'/api/collections/{cid}/compare', json={'question': 'compare'}).json()
    assert matrix['rows'][1]['dimension'] == 'Outpatient and concurrent review'
    client.delete(f'/api/collections/{cid}')
    assert client.get(f"/api/collections/{upload['id']}/papers/{other}").status_code == 200
    client.delete(f"/api/collections/{upload['id']}")
