import io

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from papertrail.config import Settings
from papertrail.comparison import matrix_passage
from papertrail.graph import Audit, Claim, Draft, ask, validate_claims
from papertrail.ingest import ResearchPDFLoader, chunk_pages
from papertrail.retrieval import Index
from papertrail import server


def pdf_bytes(texts):
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        safe = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream.set_data(f'BT /F1 12 Tf 50 700 Td ({safe}) Tj ET'.encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    result = io.BytesIO(); writer.write(result)
    return result.getvalue()


@pytest.fixture
def index():
    docs = [Document(page_content=text, metadata={'paper_id': pid, 'page': 1, 'filename': pid+'.pdf', 'title': pid, 'chunk_id': pid})
            for pid, text in [('alpha', 'The Alpha method uses sparse retrieval. Its dataset contains 200 questions. The limitation is English only.'),
                              ('beta', 'The Beta method uses dense retrieval. Its dataset contains 300 questions. The limitation is a small corpus.')]]
    return Index(docs, Settings(mode='demo'))


def test_pdf_pages_metadata_and_split_boundaries():
    raw = pdf_bytes(['Research method evidence on the first page. ' * 80, 'Dataset evaluation on the second page. ' * 80])
    pages = ResearchPDFLoader(raw, 'study.pdf').load()
    chunks = chunk_pages(pages)
    assert {d.metadata['page'] for d in chunks} == {1, 2}
    assert all(d.metadata['filename'] == 'study.pdf' for d in chunks)
    assert all(len(d.page_content) <= 1400 for d in chunks)
    assert len({d.metadata['chunk_id'] for d in chunks}) == len(chunks)
    assert not any('first page' in d.page_content and 'second page' in d.page_content for d in chunks)
    assert all('start_index' in d.metadata for d in chunks)


def test_invalid_and_scanned_pdf_rejected():
    with pytest.raises(ValueError, match='PDF'):
        ResearchPDFLoader(b'not a pdf', 'bad.pdf').load()
    with pytest.raises(ValueError, match='No usable text'):
        ResearchPDFLoader(pdf_bytes(['']), 'scan.pdf').load()


def test_balanced_retrieval_and_filtering(index):
    assert {d.metadata['paper_id'] for d in index.retrieve('method retrieval', balanced=True)} == {'alpha', 'beta'}
    assert {d.metadata['paper_id'] for d in index.retrieve('method retrieval', paper_ids=['alpha'])} == {'alpha'}


def test_local_graph_excerpts_are_exact_source_text(index):
    result = ask(index, Settings(mode='demo'), 'Compare method retrieval', ['alpha', 'beta'], True)
    assert result['status'] == 'excerpts'
    assert len(result['claims']) == 2
    lookup = {e['id']: e for e in result['evidence']}
    assert all(c['text'] == lookup[c['evidence_id']]['text'] for c in result['claims'])


@pytest.mark.parametrize('question', ['Which paper is best?', 'Dosage amoxicillin toddler'])
def test_refusal_and_bounded_refinement(index, question):
    result = ask(index, Settings(mode='demo'), question, ['alpha', 'beta'], True)
    assert result['status'] == 'insufficient'
    assert sum('Expanded' in s for s in result['trace']) == 1
    assert not result['claims']


def test_citation_validation_rejects_fabricated_quotes_and_ids():
    evidence = [{'id': 'E1', 'text': 'The method uses sparse retrieval.'}]
    valid = Draft(sufficient=True, explanation='ok', claims=[Claim(text='Uses sparse retrieval.', evidence_id='E1', quote='uses sparse retrieval.')])
    assert validate_claims(valid, evidence)
    valid.claims[0].evidence_id = 'E99'
    assert not validate_claims(valid, evidence)
    valid.claims[0].evidence_id = 'E1'; valid.claims[0].quote = 'uses dense retrieval.'
    assert not validate_claims(valid, evidence)


def test_rejected_model_explanation_never_leaks(index, monkeypatch):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs): return self
        def invoke(self, messages):
            return Draft(sufficient=False, explanation='UNSUPPORTED SECRET CLAIM', claims=[])
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'method retrieval', ['alpha'])
    assert result['status'] == 'insufficient'
    assert 'UNSUPPORTED SECRET CLAIM' not in str(result)


@pytest.mark.parametrize('audit_supported', [True, False])
def test_live_branch_with_mock_provider(index, monkeypatch, audit_supported):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            self.schema = schema; return self
        def invoke(self, messages):
            if self.schema is Audit:
                return Audit(supported=audit_supported, reason='mock check')
            return Draft(sufficient=True, explanation='UNVALIDATED TEXT', claims=[Claim(text='Alpha uses sparse retrieval.', evidence_id='E1', quote='The Alpha method uses sparse retrieval.')])
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'Alpha sparse retrieval', ['alpha'])
    assert result['status'] == ('answered' if audit_supported else 'insufficient')
    assert 'UNVALIDATED TEXT' not in str(result)


def test_provider_failure_returns_no_fabricated_answer(index, monkeypatch):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, *args, **kwargs): raise RuntimeError('secret-provider-error')
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'method retrieval', ['alpha'])
    assert result['status'] == 'error' and not result['claims']
    assert 'secret-provider-error' not in str(result)


def test_api_upload_ask_pdf_and_clear(monkeypatch):
    monkeypatch.setattr(server, 'settings', Settings(mode='demo'))
    server.collections.clear()
    client = TestClient(server.app)
    raw = pdf_bytes(['The sample method uses sparse retrieval. The dataset has 200 questions. This is an authored synthetic fixture, not a real research paper.'])
    response = client.post('/api/collections', files=[('files', ('fixture.pdf', raw, 'application/pdf'))])
    assert response.status_code == 200, response.text
    data = response.json(); cid = data['id']; pid = data['papers'][0]['paper_id']
    answer = client.post(f'/api/collections/{cid}/ask', json={'question': 'What method uses sparse retrieval?'}).json()
    assert answer['status'] == 'excerpts'
    assert client.get(f'/api/collections/{cid}/papers/{pid}').content == raw
    assert client.post(f'/api/collections/{cid}/ask', json={'question': 'test', 'paper_ids': ['unknown']}).status_code == 400
    assert client.post(f'/api/collections/{cid}/compare', json={'question': 'compare'}).status_code == 400
    assert client.delete(f'/api/collections/{cid}').status_code == 200
    assert client.get(f'/api/collections/{cid}/papers/{pid}').status_code == 404


def test_live_mode_requires_configuration():
    with pytest.raises(ValueError, match='MODEL_API_KEY'):
        Settings(mode='live', api_key='').validate()


def test_matrix_finds_singular_limitation_and_preserves_paper(index):
    doc = matrix_passage(index, 'alpha', 'Limitations')
    assert doc is not None and doc.metadata['paper_id'] == 'alpha'
    assert 'limitation is English only' in doc.page_content


def test_matrix_reports_absence_instead_of_mislabeling():
    doc = Document(page_content='Our evaluation results show model accuracy.', metadata={'paper_id': 'x', 'chunk_id': 'x', 'page': 1})
    index = Index([doc], Settings(mode='demo'))
    assert matrix_passage(index, 'x', 'Limitations') is None
