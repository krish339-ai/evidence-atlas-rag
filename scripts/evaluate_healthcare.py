"""Offline CMS checks against downloaded, hash-pinned PDFs; never reads .env."""
import os
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['EVIDENCE_ATLAS_MODE'] = 'demo'
os.environ['VECTOR_BACKEND'] = 'memory'

import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document
from papertrail.config import Settings
from papertrail.graph import ask
from papertrail.ingest import ResearchPDFLoader, chunk_pages
from papertrail.retrieval import Index
from papertrail.samples import sources, select_sections, verify_source

ROOT = Path(__file__).resolve().parent.parent


def load_real_pages():
    pages = []
    for source in sources('cms-ma'):
        data = (ROOT / 'data/papers' / source['file']).read_bytes()
        verify_source(data, source)
        selected = select_sections(ResearchPDFLoader(data, source['file']).load(), source)
        for page in selected:
            page.metadata.update({k: v for k, v in source.items() if k != 'sections'})
        pages.extend(selected)
    return pages


def evaluate(pages):
    config = Settings(mode='demo', vector_backend='memory')
    index = Index(chunk_pages(pages), config)
    ids = {p.metadata['filename']: p.metadata['paper_id'] for p in pages}
    cases = []
    for case in json.loads((ROOT / 'evaluation/healthcare-questions.json').read_text()):
        chosen = [ids[f] for f in case.get('files', ids)]
        for gold in case.get('gold', []):
            assert any(p.metadata['filename'] == gold['file'] and p.metadata['page'] == gold['page'] and gold['anchor'] in p.page_content for p in pages), f"Invalid gold anchor: {case['id']}"
        result = ask(index, config, case['question'], chosen, case.get('comparison', False), 'cms-ma')
        if case.get('gold'):
            hits = [any(e['filename'] == g['file'] and e['page'] == g['page'] and g['anchor'] in e['text'] for e in result['evidence']) for g in case['gold']]
            passed = all(hits) and result['status'] == 'excerpts'
            observation = f"{sum(hits)}/{len(hits)} annotated page/phrase anchors retrieved; route {result['status']}"
        else:
            passed = result['status'] == case['expected_route'] and not result['claims']
            observation = f"Expected {case['expected_route']}; actual {result['status']}"
        assert all(e['paper_id'] in chosen for e in result['evidence'])
        lookup = {e['id']: e for e in result['evidence']}
        assert all(c['quote'] == lookup[c['evidence_id']]['text'] for c in result['claims'])
        cases.append(dict(id=case['id'], kind=case['kind'], question=case['question'], passed=passed, observation=observation))
    return cases


def main():
    pages = load_real_pages()
    fixture = json.loads((ROOT / 'tests/cms-source-excerpts.json').read_text(encoding='utf-8'))
    assert [(p.page_content, p.metadata) for p in pages] == [(p['text'], p['metadata']) for p in fixture], 'Offline excerpts differ from original source extraction'
    cases = evaluate(pages)
    cases.append(dict(id='source-integrity', kind='provenance', question='Do offline fixtures exactly match the selected original PDF sections?', passed=True, observation='All three original PDF SHA-256 hashes, section anchors, physical pages, and committed fixture texts verified.'))
    report = dict(sample_id='cms-ma', generated_at=datetime.now(timezone.utc).isoformat(),
                  description='CMS Medicare Advantage sample checks using the three downloaded government PDFs, pinned hashes, original physical pages, and selected text sections. Demo/memory only.',
                  limitations='Small authored development set, not held out. Checks source retrieval, exact excerpt citations, scope routing, and source integrity. Does not measure legal completeness, clinical accuracy, live model faithfulness, or authorization outcomes. Separate from the RAG-paper evaluation.',
                  passed=sum(c['passed'] for c in cases), total=len(cases), cases=cases)
    (ROOT / 'evaluation/healthcare-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    text = '# CMS Medicare Advantage source checks\n\n' + report['description'] + '\n\n' + f"{report['passed']}/{report['total']} checks passed. Generated {report['generated_at']}.\n\n" + report['limitations'] + '\n\n| Check | Result | Observation |\n|---|---|---|\n'
    text += ''.join(f"| {c['id']} — {c['kind']} | {'PASS' if c['passed'] else 'FAIL'} | {c['observation']} |\n" for c in cases)
    (ROOT / 'evaluation/HEALTHCARE_REPORT.md').write_text(text, encoding='utf-8')
    print(f"CMS checks: {report['passed']}/{report['total']}; {len(chunk_pages(pages))} chunks; original PDF and offline fixture integrity verified.")
    if report['passed'] != report['total']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
