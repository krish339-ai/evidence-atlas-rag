"""Pinned sample catalog and auditable, page-preserving government excerpts."""
import hashlib
import json
import re
from pathlib import Path

from langchain_core.documents import Document

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE = 'cms-ma'
CMS_SCOPE = ('CMS Medicare Advantage (Part C), inpatient and outpatient medical services. '
             'Selected government guidance published in 2024–2025; process changes apply in 2026 '
             'and the cited API requirement begins in 2027. This is a dated source snapshot, not a '
             'complete or continuously updated rulebook. Original Medicare review procedures, Medicaid, '
             'commercial plans, and drugs are outside this sample’s application scope. '
             'Educational administrative use only: no patient records, individual approval decisions, '
             'universal submission checklist, or authorization submission.')
SAMPLES = {
    'cms-ma': {
        'id': 'cms-ma', 'title': 'CMS Medicare Advantage prior authorization',
        'description': 'Inpatient and outpatient medical services · selected CMS government guidance',
        'scope': CMS_SCOPE, 'manifest': 'cms-sources.json',
        'comparison_note': 'Compare the service setting, program, publication date, and applicability date. Coverage criteria, prior authorization, concurrent review, and decision notices serve different purposes.',
        'questions': [
            {'question': 'How do the two-midnight benchmark and presumption differ for Medicare Advantage inpatient admissions?'},
            {'question': 'What protection applies after approval during inpatient or outpatient services under the 2026 rule?'},
            {'question': 'What are the standard and expedited prior authorization decision timeframes beginning in 2026?'},
            {'question': 'Compare coverage criteria, prior authorization processes, and concurrent review protections across the three CMS documents.', 'comparison': True},
            {'question': 'Give me a universal prior authorization submission checklist for every payer.'},
        ],
    },
    'rag': {
        'id': 'rag', 'title': 'RAG, Self-RAG, and CRAG research papers',
        'description': 'Three research papers · methods, datasets, findings, and limitations',
        'scope': 'Research-paper sample. Its recorded evaluation measures local retrieval on these three papers only; it does not measure healthcare or live answer quality.',
        'manifest': 'sources.json',
        'comparison_note': 'Different datasets, metrics, and experimental conditions may prevent direct comparison.',
        'questions': [
            {'question': 'How does Self-RAG use reflection tokens?'},
            {'question': 'Compare how these papers handle retrieval quality.', 'comparison': True},
            {'question': 'Which paper is best?', 'comparison': True},
        ],
    },
}


def sources(sample_id):
    if sample_id not in SAMPLES:
        raise ValueError('Unknown sample. Choose cms-ma or rag.')
    return json.loads((ROOT / 'data' / SAMPLES[sample_id]['manifest']).read_text(encoding='utf-8'))


def sample_info(sample_id):
    return {key: value for key, value in SAMPLES[sample_id].items() if key != 'manifest'}


def catalog():
    return [dict(sample_info(key), available=all((ROOT / 'data/papers' / s['file']).is_file() for s in sources(key))) for key in SAMPLES]


def verify_source(data, source):
    expected = source.get('sha256')
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Source snapshot changed: {source['file']}. Review its provenance before indexing.")


def select_sections(pages, source):
    """Keep exact normalized source spans, original IDs and physical page numbers."""
    if 'sections' not in source:
        return pages
    by_page = {page.metadata['page']: page for page in pages}
    selected = []
    for section in source['sections']:
        page = by_page[section['page']]
        text = re.sub(r'\s+', ' ', page.page_content).strip()
        start = text.index(section['start']) if section.get('start') else 0
        end = text.index(section['end'], start) if section.get('end') else len(text)
        if end <= start:
            raise ValueError('Invalid source section boundaries.')
        selected.append(Document(page_content=text[start:end].strip(), metadata=dict(page.metadata, section=section['label'])))
    return selected


def scope_refusal(question):
    """Conservative product boundaries, not a clinical or legal classifier."""
    q = question.lower()
    if re.search(r'\b(invent|fabricate|ignore (?:the |all |previous )?(?:sources|documents|instructions))\b', q):
        return 'Evidence must come from the selected CMS documents; invented facts or citations are not supported.'
    if re.search(r'\b(universal|every payer|all payers|commercial|aetna|cigna|unitedhealth|medicaid|part d|dosage|prescription|cpt|icd-10)\b', q):
        return 'These selected CMS Medicare Advantage medical-service excerpts do not establish that payer, drug, coding, or universal checklist requirement.'
    if re.search(r'\b(my|this|our) (?:patient|claim|surgery|authorization|procedure)\b|\b(guarantee|submit|send)\b|will .{0,50} be approved', q):
        return 'This collection cannot decide an individual case, guarantee coverage, or submit an authorization. It contains general CMS guidance, not patient records or plan-specific requirements.'
    if re.search(r'\b(original|traditional) medicare\b', q) and not re.search(r'\b(advantage|ma|benchmark|presumption)\b', q):
        return 'This sample applies CMS guidance to Medicare Advantage; it is not a complete Original Medicare authorization rulebook.'
    return None
