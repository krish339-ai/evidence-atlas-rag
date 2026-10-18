import json
import secrets
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from papertrail.config import settings
from papertrail.comparison import DIMENSIONS, matrix_passage
from papertrail.graph import ask
from papertrail.ingest import MAX_BYTES, ResearchPDFLoader, chunk_pages
from papertrail.retrieval import Index, tokens
from papertrail.samples import DEFAULT_SAMPLE, catalog, sample_info, sources, select_sections, verify_source
from papertrail.suggestions import starter_questions

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title='Evidence Atlas RAG', version='0.1.0')
collections = {}
collection_lock = threading.Lock()
SOURCES = json.loads((ROOT / 'data/sources.json').read_text(encoding='utf-8'))


@app.get('/api/status')
def status():
    try:
        settings.validate()
        configured = True
        configuration_message = None
    except ValueError as exc:
        configured = False
        configuration_message = str(exc)
    return {'mode': settings.mode, 'configured': configured, 'configuration_message': configuration_message,
            'vector_backend': settings.vector_backend,
            'demo_available': catalog()[0]['available'], 'default_sample': DEFAULT_SAMPLE,
            'samples': catalog(), 'sources': sources(DEFAULT_SAMPLE)}


def create_collection(files, source_metadata=None, sample_id=None):
    settings.validate()
    pages, raw, papers = [], {}, []
    for filename, data in files:
        extra = (source_metadata or {}).get(filename, {})
        verify_source(data, extra)
        loaded = ResearchPDFLoader(data, filename).load()
        pid = loaded[0].metadata['paper_id']
        if pid in raw:
            continue
        loaded = select_sections(loaded, extra)
        for d in loaded:
            d.metadata.update({k: v for k, v in extra.items() if k != 'sections'})
        raw[pid] = data
        pages.extend(loaded)
        papers.append(dict(loaded[0].metadata, indexed_pages=len({d.metadata['page'] for d in loaded}), characters=sum(len(d.page_content) for d in loaded)))
    chunks = chunk_pages(pages)
    index = Index(chunks, settings)
    cid = secrets.token_urlsafe(24)
    with collection_lock:
        if len(collections) >= 8:
            raise ValueError('The local server has 8 collections. Clear an existing collection or restart the server.')
        collections[cid] = dict(index=index, papers=papers, raw=raw, pages=pages, sample_id=sample_id)
    return {'id': cid, 'papers': papers, 'chunks': len(chunks), 'pages': len({(d.metadata['paper_id'], d.metadata['page']) for d in pages}), 'mode': settings.mode,
            'sample': sample_info(sample_id) if sample_id else None,
            'questions': starter_questions(chunks) if not sample_id else [],
            'vector_backend': index.backend, 'namespace': index.namespace}


@app.post('/api/demo')
def demo(sample_id: str = DEFAULT_SAMPLE):
    try:
        selected_sources = sources(sample_id)
        if not all((ROOT / 'data/papers' / s['file']).is_file() for s in selected_sources):
            raise HTTPException(409, f'Download this sample first: python scripts/download_papers.py --sample {sample_id}')
        return create_collection([(s['file'], (ROOT / 'data/papers' / s['file']).read_bytes()) for s in selected_sources],
                                 {s['file']: s for s in selected_sources}, sample_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, 'Indexing failed. Check the embedding provider and vector backend configuration and connection.') from exc


@app.post('/api/collections')
async def upload(files: list[UploadFile] = File(...)):
    if not 1 <= len(files) <= 8:
        raise HTTPException(400, 'Choose 1 to 8 PDF files.')
    data = []
    try:
        for f in files:
            content = await f.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError('Each PDF must be smaller than 20 MB.')
            name = (f.filename or 'paper.pdf').replace('\\', '/').split('/')[-1][:180]
            data.append((name, content))
        return await run_in_threadpool(create_collection, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, 'Indexing failed. Check the embedding provider and vector backend configuration and connection.') from exc
    finally:
        for f in files:
            await f.close()


def get_collection(cid):
    if cid not in collections:
        raise HTTPException(404, 'Collection expired. Load your papers again.')
    return collections[cid]


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    paper_ids: list[str] = Field(default_factory=list, max_length=8)
    comparison: bool = False


def selected_ids(collection, requested):
    all_ids = {p['paper_id'] for p in collection['papers']}
    chosen = list(dict.fromkeys(requested)) or sorted(all_ids)
    if not set(chosen) <= all_ids:
        raise HTTPException(400, 'Unknown paper selection.')
    return chosen


@app.post('/api/collections/{cid}/ask')
def question(cid: str, body: Question):
    collection = get_collection(cid)
    ids = selected_ids(collection, body.paper_ids)
    if not body.question.strip():
        raise HTTPException(400, 'Enter a question.')
    if body.comparison and len(ids) < 2:
        raise HTTPException(400, 'Select at least two papers to compare.')
    try:
        return ask(collection['index'], settings, body.question, ids, body.comparison, collection.get('sample_id'))
    except Exception as exc:
        raise HTTPException(502, 'Retrieval failed. Check your embedding provider connection.') from exc


@app.post('/api/collections/{cid}/compare')
def compare(cid: str, body: Question):
    collection = get_collection(cid)
    ids = selected_ids(collection, body.paper_ids)
    if len(ids) < 2:
        raise HTTPException(400, 'Select at least two papers to compare.')
    rows, evidence = [], []
    from papertrail.comparison import CMS_DIMENSIONS
    dimensions = CMS_DIMENSIONS if collection.get('sample_id') == 'cms-ma' else DIMENSIONS
    for label in dimensions:
        cells = []
        for pid in ids:
            doc = matrix_passage(collection['index'], pid, label, dimensions)
            if doc is None:
                cells.append({'paper_id': pid, 'evidence_id': None, 'text': 'No matching passage found.'})
                continue
            item = dict(id=f'M{len(evidence)+1}', text=doc.page_content, **doc.metadata)
            evidence.append(item)
            cells.append({'paper_id': pid, 'evidence_id': item['id'], 'text': doc.page_content})
        rows.append({'dimension': label, 'cells': cells})
    return {'rows': rows, 'evidence': evidence, 'paper_ids': ids,
            'note': sample_info(collection['sample_id'])['comparison_note'] if collection.get('sample_id') else 'A reading matrix of source excerpts, not generated conclusions.'}


@app.get('/api/collections/{cid}/papers/{pid}')
def pdf(cid: str, pid: str):
    collection = get_collection(cid)
    if pid not in collection['raw']:
        raise HTTPException(404, 'Paper not found.')
    return Response(collection['raw'][pid], media_type='application/pdf', headers={'Content-Disposition': 'inline; filename="paper.pdf"', 'Cache-Control': 'no-store'})


@app.delete('/api/collections/{cid}')
def delete(cid: str):
    with collection_lock:
        collections.pop(cid, None)
    return {'deleted': True}


@app.get('/api/evaluation')
def evaluation(sample_id: str = 'rag'):
    if sample_id not in {'cms-ma', 'rag'}:
        raise HTTPException(400, 'Unknown evaluation sample.')
    path = ROOT / 'evaluation' / ('healthcare-results.json' if sample_id == 'cms-ma' else 'results.json')
    if not path.exists():
        raise HTTPException(404, 'Run python -m scripts.evaluate to generate the evaluation report.')
    return json.loads(path.read_text(encoding='utf-8'))


@app.get('/')
def home():
    return FileResponse(ROOT / 'static/index.html')


@app.get('/project-brief')
def project_brief():
    return FileResponse(ROOT / 'docs/project-brief.html')


app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
