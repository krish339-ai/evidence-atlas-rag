"""Reproducible retrieval evaluation. No model calls; no fabricated faithfulness score."""
import hashlib
import json
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from papertrail.config import Settings
from papertrail.graph import ask
from papertrail.ingest import ResearchPDFLoader, chunk_pages
from papertrail.retrieval import Index

ROOT = Path(__file__).resolve().parent.parent


def norm(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def hit(doc, gold):
    return (doc.metadata['filename'] == gold['file'] and doc.metadata['page'] == gold['page']
            and any(norm(anchor) in norm(doc.page_content) for anchor in gold['anchors']))


def main():
    sources = json.loads((ROOT / 'data/sources.json').read_text(encoding='utf-8'))
    questions = json.loads((ROOT / 'evaluation/questions.json').read_text(encoding='utf-8'))
    pages, hashes = [], {}
    for source in sources:
        data = (ROOT / 'data/papers' / source['file']).read_bytes()
        hashes[source['file']] = hashlib.sha256(data).hexdigest()
        docs = ResearchPDFLoader(data, source['file']).load()
        for doc in docs:
            doc.metadata.update(source)
        pages.extend(docs)
    for question in questions:
        for gold in question['gold']:
            assert any(hit(page, gold) for page in pages), f"Gold anchor missing in corpus: {question['id']} {gold}"
    config = Settings(mode='demo', vector_backend='memory')
    chunks = chunk_pages(pages)
    index = Index(chunks, config)
    ids = {d.metadata['filename']: d.metadata['paper_id'] for d in pages}
    cases = []
    for question in questions:
        case = dict(question)
        paper_ids = [ids[name] for name in question['papers']] or list(ids.values())
        comparison = question['kind'] == 'cross-paper' or not question['papers']
        for strategy in ['baseline', 'hybrid']:
            started = time.perf_counter()
            docs = index.retrieve(question['question'], strategy=strategy, k=6, paper_ids=paper_ids, balanced=comparison)
            found = sum(any(hit(doc, gold) for doc in docs) for gold in question['gold'])
            case[strategy] = {
                'recall': found / len(question['gold']) if question['gold'] else None,
                'latency_ms': round((time.perf_counter()-started)*1000, 2),
                'retrieved': [{'file': d.metadata['filename'], 'page': d.metadata['page'], 'chunk_id': d.metadata['chunk_id']} for d in docs],
            }
        outcome = ask(index, config, question['question'], paper_ids, comparison)
        case['actual_route'] = outcome['status']
        case['query_ms'] = outcome['elapsed_ms']
        if question.get('expected_route'):
            case['route_pass'] = outcome['status'] == question['expected_route']
            case['observation'] = ('Correctly declined to answer.' if case['route_pass'] else
                                   'Known limitation: lexical overlap returned source excerpts for an unsupported request. No generated answer was produced; semantic refusal needs live evaluation.')
        elif case['hybrid']['recall'] < 1:
            case['observation'] = 'Some expected evidence fell outside the six retrieved chunks. Inspect the retrieved page list before making a complete comparison.'
        else:
            case['observation'] = 'All annotated evidence groups were found. This does not establish answer faithfulness.'
        cases.append(case)
    summary = {}
    for strategy in ['baseline', 'hybrid']:
        values = [c[strategy]['recall'] for c in cases if c[strategy]['recall'] is not None]
        times = sorted(c[strategy]['latency_ms'] for c in cases)
        summary[strategy] = {'recall': round(statistics.mean(values), 4), 'p95_retrieval_ms': times[min(len(times)-1, int(len(times)*.95))]}
    fallback = [c for c in cases if 'route_pass' in c]
    summary['fallback_passes'] = sum(c['route_pass'] for c in fallback)
    summary['fallback_cases'] = len(fallback)
    summary['p95_local_query_ms'] = sorted(c['query_ms'] for c in cases)[int(len(cases)*.95)]
    summary['live_faithfulness'] = None
    summary['live_latency'] = None
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'corpus_sha256': hashes,
              'description': 'Local lexical retrieval evaluation on 14 authored questions over three real, version-pinned arXiv PDFs. Gold evidence is checked against actual page text. Both strategies use the same corpus, splitter, query scope, and top-k=6.',
              'limitations': 'The dense baseline uses deterministic hashed word vectors, not semantic model embeddings. Hybrid combines those vectors with BM25 and paper coverage. This small development set is not a held-out benchmark. Recall is annotated evidence-group coverage, not claim faithfulness or relevance. Live synthesis, semantic embeddings, and the 15-second live target remain unverified.',
              'pages': len(pages), 'chunks': len(chunks), 'summary': summary, 'cases': cases}
    (ROOT / 'evaluation/results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    delta = (summary['hybrid']['recall'] - summary['baseline']['recall']) * 100
    lines = ['# Evidence Atlas RAG evaluation report', '', report['description'], '', '## Measured results', '',
             f"- Corpus: {len(pages)} pages, {len(chunks)} chunks.",
             f"- Baseline mean evidence recall@6: {summary['baseline']['recall']:.1%}.",
             f"- Hybrid mean evidence recall@6: {summary['hybrid']['recall']:.1%} ({delta:+.1f} percentage points).",
             f"- Fallback routing: {summary['fallback_passes']}/{len(fallback)} cases.",
             f"- Local end-to-end query p95: {summary['p95_local_query_ms']} ms (single run; includes first-query effects).",
             '- Live faithfulness / live latency: NOT MEASURED.', '', report['limitations'], '', '## Per-question results', '',
             '| ID | Kind | Baseline recall | Hybrid recall | Route | Observation |', '|---|---|---:|---:|---|---|']
    for c in cases:
        fmt = lambda v: 'n/a' if v is None else f'{v:.0%}'
        lines.append(f"| {c['id']} | {c['kind']} | {fmt(c['baseline']['recall'])} | {fmt(c['hybrid']['recall'])} | {c['actual_route']} | {c['observation']} |")
    lines += ['', '## Reproduce and review', '', '`python -m scripts.evaluate` regenerates this report and results.json. questions.json contains exact page and phrase anchors; results.json includes retrieved chunk IDs and corpus hashes. No provider credentials are needed.', '',
              'Faithfulness target: 95% supported factual claims / evaluated factual claims. A human should assess each live claim against the full cited source and record supported, unsupported, or uncertain. Report answered-question coverage, refusal correctness, citation validity, relevance (0/1/2), and end-to-end p50/p95 separately. Refused questions do not count as faithful answers.', '',
              'Latency target: 15 seconds end to end after ingestion. Provider request timeouts are failure limits, not proof of this target. Record misses and provider/model versions. Use a separate held-out set after tuning.', '',
              'Failure analysis: exact terms can retrieve references or related-work discussions rather than the target method; lexical overlap can return excerpts for unanswerable questions; top-k may omit one side of a comparison. Paper balancing can help coverage while displacing another useful passage. None of these checks prove entailment.', '']
    (ROOT / 'evaluation/REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
