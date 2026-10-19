import io
import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from papertrail.config import Settings
from papertrail.comparison import matrix_passage
from papertrail.graph import Audit, Claim, Draft, SourceClaim, SourceDraft, ask, validate_claims, evidence_items
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


def test_transport_metadata_cannot_replace_evidence_text_or_id():
    doc = Document(page_content='The actual source passage.', metadata={
        'text': 'Transport copy', 'id': 'forged', 'paper_id': 'fixture', 'page': 3})
    result = evidence_items([doc])
    assert result == [{'text': doc.page_content, 'id': 'E1', 'paper_id': 'fixture', 'page': 3}]


@pytest.mark.parametrize('text, accepted', [
    ('Impacted payers must send decisions within 72 hours for expedited requests and seven calendar days for standard requests.', False),
    ('Impacted payers, excluding QHP issuers on the FFEs, must send decisions within 72 hours for expedited requests and seven calendar days for standard requests.', True),
    ('Impacted payers must send decisions within 72 hours for expedited requests and seven calendar days for standard requests, except for QHP issuers on the FFEs.', True),
    ('Impacted payers, excluding other groups, must send decisions within 72 hours for expedited requests and seven calendar days for standard requests.', False),
    ('Impacted payers must send decisions within 72 hours for expedited requests and seven calendar days for standard requests. QHP issuers on the FFEs are discussed in the source.', False),
    ('Medicare Advantage plans must send decisions within 72 hours for expedited requests and seven calendar days for standard requests.', True),
    ('Impacted payers must provide a specific reason for denied prior authorization decisions beginning in 2026.', True),
])
def test_material_exception_cannot_be_waived_by_optimistic_audit(monkeypatch, text, accepted):
    # Public source wording, with a neighboring rule to exercise relevance.
    source = ('Prior Authorization Decision Timeframes: We are requiring impacted payers '
              '(excluding QHP issuers on the FFEs) to send prior authorization decisions '
              'within 72 hours for expedited requests and seven calendar days for standard requests. '
              'Provider Notice: Beginning in 2026, impacted payers must provide a specific reason '
              'for denied prior authorization decisions.')
    doc = Document(page_content=source, metadata={'paper_id': 'public', 'chunk_id': 'public:3', 'page': 3})
    index = Index([doc], Settings(mode='demo'))
    calls = []
    class Model:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            self.schema = SourceDraft if issubclass(schema, SourceDraft) else schema
            return self
        def invoke(self, messages):
            calls.append(self.schema)
            if self.schema is Audit:
                return Audit(reason='Optimistic model approval must not waive local checks.', supported=True)
            return SourceDraft(sufficient=True, claims=[SourceClaim(text=text, evidence_id='E1')])
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', Model)
    result = ask(index, Settings(mode='live', api_key='fake'), 'What prior authorization decisions are required?', ['public'])
    if accepted:
        assert result['status'] == 'answered'
        assert calls == [SourceDraft, Audit]
    else:
        assert result['status'] == 'unverified' and result['reason'] == 'omitted_exception'
        assert result['claims'] == [] and result['evidence'][0]['text'] == source
        assert calls == [SourceDraft]  # No extra paid audit for a known omission.


def test_audit_schema_assesses_evidence_before_final_verdict():
    # A real provider produced supported=false before a reason concluding true.
    # Keep the reason first in the provider's structured-output schema.
    from langchain_core.utils.function_calling import convert_to_openai_function
    schema = convert_to_openai_function(Audit)['parameters']
    assert list(schema['properties']) == ['reason', 'supported']
    assert set(schema['required']) == {'reason', 'supported'}


def test_generation_schema_allows_only_this_requests_retrieved_ids():
    from pydantic import ValidationError
    from papertrail.graph import source_draft_schema
    schema = source_draft_schema([{'id': 'E1'}, {'id': 'E2'}])
    payload = {'sufficient': True, 'claims': [{'text': 'Supported fact.', 'evidence_id': 'E2'}]}
    assert schema.model_validate(payload).claims[0].evidence_id == 'E2'
    assert schema.model_json_schema()['$defs']['RetrievedSourceClaim']['properties']['evidence_id']['enum'] == ['E1', 'E2']
    for wrong in ['E99', 'chunk-1', '[E1]', 'e1']:
        payload['claims'][0]['evidence_id'] = wrong
        with pytest.raises(ValidationError):
            schema.model_validate(payload)
    # No citation choices from a previous request are cached or reused.
    second = source_draft_schema([{'id': 'E3'}])
    payload['claims'][0]['evidence_id'] = 'E2'
    with pytest.raises(ValidationError):
        second.model_validate(payload)


@pytest.mark.parametrize('split, accepted', [(False, False), (True, True)])
def test_list_details_must_be_in_each_claims_own_quote(monkeypatch, split, accepted):
    docs = [Document(page_content=text, metadata={'paper_id': 'fixture', 'chunk_id': str(i), 'page': i+1})
            for i, text in enumerate(['Technical skills include SQL and Python. Experience: Architect, 2022 to 2026.',
                                      'Technical skills include GraphTool and XML. Experience: Analyst, 2018 to 2021.'])]
    idx = Index(docs, Settings(mode='demo'))
    calls = []
    class Model:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            self.schema = schema
            return self
        def invoke(self, messages):
            calls.append(self.schema)
            if self.schema is Audit:
                return Audit(reason='Optimistic audit does not waive local checks.', supported=True)
            passages = json.loads(messages[-1][1])['passages']
            first = next(p for p in passages if 'SQL' in p['text'])
            second = next(p for p in passages if 'GraphTool' in p['text'])
            claims = ([SourceClaim(text='Technical skills include SQL and Python.', evidence_id=first['id']),
                       SourceClaim(text='Technical skills include GraphTool and XML.', evidence_id=second['id'])] if split else
                      [SourceClaim(text='Technical skills include SQL, Python, GraphTool and XML. Roles span 2018 to 2026.', evidence_id=first['id'])])
            return SourceDraft(sufficient=True, claims=claims)
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', Model)
    result = ask(idx, Settings(mode='live', api_key='fake'), 'What technical skills are listed?', ['fixture'])
    assert result['status'] == ('answered' if accepted else 'unverified')
    if not accepted:
        assert result['reason'] == 'unsupported_details' and not result['claims']
        assert len(calls) == 1


def test_literal_guard_normalizes_common_number_words_and_grouping():
    from papertrail.graph import unsupported_literal_details
    draft = Draft(sufficient=True, explanation='', claims=[Claim(text='SQL jobs use 7 days and 1,000 records.', evidence_id='E1', quote='SQL jobs use seven days and 1000 records.')])
    assert not unsupported_literal_details(draft)


def test_rejected_model_explanation_never_leaks(index, monkeypatch):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs): return self
        def invoke(self, messages):
            return SourceDraft(sufficient=False, claims=[], explanation='UNSUPPORTED SECRET CLAIM')
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'method retrieval', ['alpha'])
    assert result['status'] == 'insufficient'
    assert 'UNSUPPORTED SECRET CLAIM' not in str(result)


@pytest.mark.parametrize('audit_supported', [True, False])
def test_live_branch_with_mock_provider(index, monkeypatch, audit_supported):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            self.schema = SourceDraft if issubclass(schema, SourceDraft) else schema; return self
        def invoke(self, messages):
            if self.schema is Audit:
                return Audit(supported=audit_supported, reason='mock check')
            return SourceDraft(sufficient=True, claims=[SourceClaim(text='Alpha uses sparse retrieval.', evidence_id='E1')])
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'Alpha sparse retrieval', ['alpha'])
    assert result['status'] == ('answered' if audit_supported else 'unverified')
    assert 'UNVALIDATED TEXT' not in str(result)


@pytest.mark.parametrize('audit_supported', [True, False])
def test_live_quotes_are_copied_from_source_and_still_audited(monkeypatch, audit_supported):
    # Synthetic fixture: no private resume content belongs in regression tests.
    source = 'B.Sc., Physics — Example University, 2010 – 2014\nResearch: “Optics” • laboratory work.'
    doc = Document(page_content=source, metadata={'paper_id': 'education', 'chunk_id': 'education:1', 'page': 1})
    index = Index([doc], Settings(mode='demo'))
    calls = []

    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            self.schema = SourceDraft if issubclass(schema, SourceDraft) else schema; return self
        def invoke(self, messages):
            calls.append(self.schema)
            payload = json.loads(messages[1][1])
            assert '—' in messages[1][1] and '\\u2014' not in messages[1][1]
            if self.schema is Audit:
                assert payload['answer']['claims'][0]['quote'] == source
                return Audit(supported=audit_supported, reason='UNVALIDATED AUDIT TEXT')
            assert self.schema is SourceDraft
            assert 'quote' not in SourceClaim.model_fields
            assert payload['passages'][0]['text'] == source
            return SourceDraft(sufficient=True, claims=[SourceClaim(
                text='The degree is B.Sc. in Physics.' if audit_supported else 'The degree is a Ph.D. in Biology.',
                evidence_id='E1')])

    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'What degree is listed for Example University?', ['education'])
    assert calls == [SourceDraft, Audit]
    assert result['status'] == ('answered' if audit_supported else 'unverified')
    assert 'UNVALIDATED AUDIT TEXT' not in str(result)
    if audit_supported:
        assert result['claims'][0]['quote'] == source
    else:
        assert not result['claims']
        assert result['reason'] == 'audit_rejected'


@pytest.mark.parametrize('draft, reason, status', [
    (SourceDraft(sufficient=False, claims=[]), 'model_insufficient', 'insufficient'),
    (SourceDraft(sufficient=True, claims=[]), 'empty_answer', 'unverified'),
    (SourceDraft(sufficient=True, claims=[SourceClaim(text='Unverified claim.', evidence_id='E99')]), 'unknown_citation', 'unverified'),
    (SourceDraft(sufficient=True, claims=[SourceClaim(text='   ', evidence_id='E1')]), 'empty_answer', 'unverified'),
])
def test_live_rejections_explain_failure_without_exposing_draft(index, monkeypatch, draft, reason, status):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            assert issubclass(schema, SourceDraft)  # Invalid drafts must not reach the audit.
            return self
        def invoke(self, messages): return draft
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'Alpha sparse retrieval', ['alpha'])
    assert result['status'] == status and result['reason'] == reason
    assert result['evidence'] and not result['claims']
    assert 'Unverified claim.' not in str(result)


def test_live_comparison_requires_citations_for_every_selected_document(index, monkeypatch):
    class FakeModel:
        def __init__(self, **kwargs): pass
        def with_structured_output(self, schema, **kwargs):
            assert issubclass(schema, SourceDraft)
            return self
        def invoke(self, messages):
            return SourceDraft(sufficient=True, claims=[SourceClaim(text='Alpha uses sparse retrieval.', evidence_id='E1')])
    monkeypatch.setattr('papertrail.graph.ChatOpenAI', FakeModel)
    result = ask(index, Settings(mode='live', api_key='fake'), 'Compare method retrieval', ['alpha', 'beta'], True)
    assert result['status'] == 'unverified' and result['reason'] == 'incomplete_coverage'
    assert not result['claims']


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
    assert data['questions'] and all(q['paper_id'] == pid for q in data['questions'])
    # A page refresh reads the existing collection without constructing an index.
    def no_reindex(*args, **kwargs):
        raise AssertionError('Restoration must not embed or upsert documents')
    monkeypatch.setattr(server, 'Index', no_reindex)
    restored = client.get(f'/api/collections/{cid}')
    assert restored.status_code == 200 and restored.json() == data
    assert restored.headers['cache-control'] == 'no-store'
    answer = client.post(f'/api/collections/{cid}/ask', json={'question': 'What method uses sparse retrieval?'}).json()
    assert answer['status'] == 'excerpts'
    assert client.get(f'/api/collections/{cid}/papers/{pid}').content == raw
    assert client.post(f'/api/collections/{cid}/ask', json={'question': 'test', 'paper_ids': ['unknown']}).status_code == 400
    assert client.post(f'/api/collections/{cid}/compare', json={'question': 'compare'}).status_code == 400
    assert client.delete(f'/api/collections/{cid}').status_code == 200
    assert client.get(f'/api/collections/{cid}').status_code == 404
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


def test_matrix_transport_metadata_cannot_override_evidence(index, monkeypatch):
    for doc in index.chunks:
        doc.metadata.update(text='transport copy', id='transport-id')
    monkeypatch.setattr(server, 'collections', {'fixture': {
        'index': index, 'papers': [{'paper_id': 'alpha'}, {'paper_id': 'beta'}], 'sample_id': None}})
    result = server.compare('fixture', server.Question(question='compare', paper_ids=['alpha', 'beta']))
    assert result['evidence']
    assert all(e['id'].startswith('M') and e['text'] != 'transport copy' for e in result['evidence'])
