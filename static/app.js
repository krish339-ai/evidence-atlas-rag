'use strict';
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let collection = null;
let evidence = [];
let currentAnswer = null;
let matrixEvidence = [];
let working = false;
let status = null;
let toastTimer;

function node(tag, cls, text) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (text !== undefined) element.textContent = text;
  return element;
}
function toast(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 7500);
}
async function api(path, options = {}) {
  const response = await fetch(path, options);
  let body;
  try { body = await response.json(); } catch { throw new Error('The server returned an unexpected response.'); }
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'This request could not be completed. Check your inputs and try again.');
  return body;
}
async function task(message, action) {
  if (working) return;
  working = true;
  $('#busy-message').textContent = message;
  $('#busy').hidden = false;
  $$('button, #sample-select').forEach(b => { b.disabled = true; });
  $('#file-input').disabled = true;
  try { await action(); } catch (error) { toast(error.message || 'Something went wrong. Please try again.'); }
  finally {
    working = false;
    $('#busy').hidden = true;
    $$('button, #sample-select').forEach(b => { b.disabled = false; });
    $('#file-input').disabled = false;
  }
}
function openWorkspace() {
  $('#landing').hidden = true;
  $('#workspace').hidden = false;
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function openHome() {
  $('#landing').hidden = false;
  $('#workspace').hidden = true;
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function tab(name) {
  ['ask', 'compare', 'eval'].forEach(n => { $(`#${n}-view`).hidden = n !== name; });
  $$('[data-tab]').forEach(b => { b.classList.toggle('active', b.dataset.tab === name); b.setAttribute('aria-selected', String(b.dataset.tab === name)); });
  if (name === 'eval') loadEvaluation();
  evidence = name === 'compare' ? matrixEvidence : (name === 'ask' ? (currentAnswer?.evidence || []) : []);
  renderEvidence();
}
function selected() {
  return $$('#paper-list input:checked').map(input => input.value);
}
function requireCollection(minimum = 1) {
  if (!collection) throw new Error('Add your PDFs or load the sample collection first.');
  if (selected().length < minimum) throw new Error(`Select at least ${minimum} document${minimum > 1 ? 's' : ''} in your collection.`);
}
function renderCollection() {
  renderSampleContext();
  $('#paper-list').replaceChildren();
  $('#paper-count').textContent = String(collection?.papers.length || 0).padStart(2, '0');
  $('#clear-collection').hidden = !collection;
  if (!collection) {
    $('#library-info').textContent = 'Your collection stays in server memory until you clear it or restart.';
    renderSuggestions();
    return;
  }
  $('#library-info').textContent = `${collection.pages} pages · ${collection.chunks} passages indexed. Select the documents you want to explore.`;
  if (collection.namespace) $('#library-info').append(node('p', '', `Pinecone namespace: ${collection.namespace}. Clearing this collection leaves remote vectors intact.`));
  collection.papers.forEach(paper => {
    const label = node('label', 'paper-item');
    const check = node('input'); check.type = 'checkbox'; check.checked = true; check.value = paper.paper_id;
    const detail = node('div');
    detail.append(node('strong', '', paper.title), node('small', '', `${paper.authors || paper.filename} · ${paper.indexed_pages || paper.page_count} indexed / ${paper.page_count} PDF pages`));
    label.append(check, detail);
    $('#paper-list').append(label);
  });
  renderSuggestions();
}
function resetOutput() {
  $('#question').value = ''; $('#compare-toggle').checked = false;
  $('#answer').replaceChildren();
  $('#welcome').hidden = false;
  $('#matrix').replaceChildren(node('div', 'empty-panel', 'Select at least two documents, then build your reading matrix.'));
  evidence = []; matrixEvidence = []; currentAnswer = null;
  renderEvidence();
}
async function replaceCollection(next) {
  const previous = collection;
  collection = next;
  if (previous) await api(`/api/collections/${previous.id}`, { method: 'DELETE' }).catch(() => {});
  renderCollection(); resetOutput(); tab('ask');
}
function renderSampleContext() {
  const sample = collection?.sample;
  const context = $('#collection-context'); context.replaceChildren();
  if (sample) {
    context.append(node('h3', '', sample.title));
    const details = node('details'); details.append(node('summary', '', 'Scope and source dates'), node('p', '', sample.scope)); context.append(details);
    $('#sample-select').value = sample.id;
  }
  $('#matrix-description').textContent = sample?.id === 'cms-ma' ? 'Inpatient coverage, outpatient review, documentation, and timeframes.' : 'Methods, datasets, findings, and limitations.';
  $('#matrix-warning').textContent = sample?.comparison_note || 'Retrieved excerpts require interpretation and source review.';
}
function renderSuggestions() {
  const ids = selected();
  const starters = collection ? (collection.sample?.questions || collection.questions || [])
    .filter(item => !item.paper_id || ids.includes(item.paper_id))
    : status?.samples?.find(s => s.id === status.default_sample)?.questions || [];
  $('.suggestions').replaceChildren();
  $('#suggestion-panel').hidden = !starters.length;
  starters.forEach(item => {
    const button = node('button', '', item.question + ' ↗');
    button.type = 'button'; button.dataset.question = item.question;
    button.dataset.compare = String(!!item.comparison);
    if (item.title) button.title = 'Suggested from ' + item.title;
    $('.suggestions').append(button);
  });
}
function loadDemo(sampleId = 'cms-ma') {
  openWorkspace();
  return task('Reading sample documents and building your evidence index…', async () => {
    await replaceCollection(await api('/api/demo?sample_id=' + encodeURIComponent(sampleId), { method: 'POST' }));
    toast(collection.sample.title + ' ready. Start with a question or build a reading matrix.');
  });
}
function upload(files) {
  if (!files.length) return;
  openWorkspace();
  task('Reading PDF pages and indexing your collection…', async () => {
    if (files.length > 8) throw new Error('Choose up to 8 documents at a time.');
    if ([...files].some(f => f.size > 20 * 1024 * 1024)) throw new Error('Each PDF must be smaller than 20 MB.');
    const form = new FormData();
    [...files].forEach(f => form.append('files', f));
    await replaceCollection(await api('/api/collections', { method: 'POST', body: form }));
    $('#file-input').value = '';
    toast('Collection ready. Your evidence trail starts here.');
  });
}
function citation(item) {
  const button = node('button', 'citation', `${item.short || item.filename} · p. ${item.page} ↗`);
  button.addEventListener('click', () => focusEvidence(item.id));
  return button;
}
function renderEvidence(activeId) {
  $('#evidence-count').textContent = String(evidence.length).padStart(2, '0');
  const target = $('#evidence-content'); target.replaceChildren();
  if (!evidence.length) {
    const empty = node('div', 'evidence-empty');
    empty.append(node('span', '', '↳'), node('h3', '', 'Every trail starts somewhere.'), node('p', '', 'Select a citation to inspect the passage and open its original PDF page.'));
    target.append(empty); return;
  }
  const sorted = [...evidence].sort((a, b) => (b.id === activeId) - (a.id === activeId));
  sorted.forEach(item => {
    const card = node('article', `evidence-card${item.id === activeId ? ' active' : ''}`);
    card.id = `evidence-${item.id}`;
    card.tabIndex = -1;
    card.append(node('span', 'evidence-label', `${item.id} / PAGE ${item.page}`), node('h3', '', item.title), node('p', '', item.text));
    if (item.published) card.append(node('small', 'source-provenance', `Published ${item.published} · ${item.applicability}`));
    const link = node('a', '', 'Open original PDF page ↗');
    link.href = `/api/collections/${collection.id}/papers/${item.paper_id}#page=${item.page}`;
    link.target = '_blank'; link.rel = 'noopener'; card.append(link);
    target.append(card);
  });
}
function focusEvidence(id) {
  renderEvidence(id);
  const target = $(`#evidence-${id}`);
  target?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' });
  target?.focus({ preventScroll: true });
}
function renderAnswer(question, result) {
  currentAnswer = { question, ...result };
  evidence = result.evidence;
  renderEvidence();
  $('#welcome').hidden = true;
  const target = $('#answer'); target.replaceChildren();
  target.append(node('h2', 'answer-question', question));
  const labels = { excerpts: 'SOURCE EXCERPTS · LOCAL MODE', answered: 'CITED ANSWER', insufficient: 'INSUFFICIENT EVIDENCE', unverified: 'ANSWER NOT VERIFIED', error: 'MODEL UNAVAILABLE' };
  target.append(node('div', `answer-status ${result.status}`, labels[result.status] || result.status), node('p', 'answer-message', result.message));
  if (result.scope) target.append(node('p', 'matrix-warning', result.scope));
  if ($('#compare-toggle').checked) target.append(node('p', 'matrix-warning', $('#matrix-warning').textContent));
  result.claims.forEach(claim => {
    const article = node('article', 'answer-claim');
    article.append(node('span', 'claim-kind', claim.kind), node('p', '', claim.text));
    const item = evidence.find(e => e.id === claim.evidence_id);
    if (item) article.append(citation(item));
    target.append(article);
  });
  const footer = node('div', 'answer-footer');
  const covered = new Set(result.claims.map(c => evidence.find(e => e.id === c.evidence_id)?.paper_id).filter(Boolean)).size;
  footer.append(node('span', '', `${covered}/${selected().length} documents cited · ${(result.elapsed_ms / 1000).toFixed(2)}s`));
  const download = node('button', 'text-button', 'Export trail ↓'); download.addEventListener('click', exportTrail); footer.append(download); target.append(footer);
  const details = node('details', 'graph-trace'); details.append(node('summary', '', 'Inspect the retrieval workflow'));
  const list = node('ol'); result.trace.forEach(step => list.append(node('li', '', step))); details.append(list); target.append(details);
  $('.research-main').scrollTop = 0;
  $('.evidence-panel').scrollTop = 0;
  if (window.innerWidth <= 760) target.scrollIntoView({ block: 'start', behavior: 'instant' });
}
async function submitQuestion(event) {
  event?.preventDefault();
  if (working) return;
  const question = $('#question').value.trim();
  if (!question) return;
  await task('Retrieving evidence and checking the trail…', async () => {
    const comparison = $('#compare-toggle').checked;
    requireCollection(comparison ? 2 : 1);
    const result = await api(`/api/collections/${collection.id}/ask`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, paper_ids: selected(), comparison }),
    });
    renderAnswer(question, result);
    const input = $('#question');
    if (result.status !== 'error' && input.value.trim() === question) input.value = '';
    input.focus({ preventScroll: true });
  });
}
function runSuggestedQuestion(event) {
  const button = event.target.closest('[data-question]');
  if (!button || working) return;
  $('#question').value = button.dataset.question;
  $('#compare-toggle').checked = button.dataset.compare === 'true';
  $('#question').focus();
  if (collection) return submitQuestion();
}
async function buildMatrix() {
  await task('Finding source passages for the selected documents…', async () => {
    requireCollection(2);
    const result = await api(`/api/collections/${collection.id}/compare`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: 'Compare selected papers', paper_ids: selected(), comparison: true }),
    });
    $('#matrix-warning').textContent = result.note;
    matrixEvidence = result.evidence; evidence = matrixEvidence; renderEvidence();
    const scroll = node('div', 'matrix-scroll'); const table = node('table', 'matrix-table');
    const head = node('thead'); const heading = node('tr'); heading.append(node('th', '', 'Dimension'));
    result.paper_ids.forEach(id => { const paper = collection.papers.find(p => p.paper_id === id); heading.append(node('th', '', paper.short || paper.title)); });
    head.append(heading); table.append(head); const body = node('tbody');
    result.rows.forEach(row => {
      const tr = node('tr'); const th = node('th', '', row.dimension); th.scope = 'row'; tr.append(th);
      row.cells.forEach(cell => {
        const td = node('td'); td.append(node('p', '', cell.text));
        const item = evidence.find(e => e.id === cell.evidence_id); if (item) td.append(citation(item));
        tr.append(td);
      }); body.append(tr);
    }); table.append(body); scroll.append(table); $('#matrix').replaceChildren(scroll);
  });
}
async function loadEvaluation() {
  const target = $('#evaluation'); target.replaceChildren(node('p', 'eval-note', 'Loading evaluation results…'));
  try {
    const sampleId = collection?.sample?.id || 'cms-ma';
    const report = await api('/api/evaluation?sample_id=' + sampleId); target.replaceChildren();
    if (report.sample_id === 'cms-ma') {
      target.append(node('h3', '', 'CMS source checks · demo mode'), node('p', 'eval-note', report.description), node('p', 'eval-note', `${report.passed}/${report.total} checks passed · ${report.generated_at}`), node('p', 'eval-note', report.limitations));
      report.cases.forEach(test => { const item = node('div', 'eval-case', test.question); item.append(node('small', '', `${test.passed ? 'PASS' : 'FAIL'} · ${test.kind} · ${test.observation}`)); target.append(item); });
      return;
    }
    target.append(node('h3', '', 'RAG / Self-RAG / CRAG evaluation only'));
    target.append(node('p', 'eval-note', report.description));
    const cards = node('div', 'eval-cards');
    for (const [key, label] of [['baseline', 'Dense baseline · evidence recall@6'], ['hybrid', 'Hybrid + paper coverage · evidence recall@6']]) {
      const card = node('div', 'eval-stat'); card.append(node('strong', '', `${(report.summary[key].recall * 100).toFixed(1)}%`), node('span', '', label)); cards.append(card);
    } target.append(cards);
    target.append(node('p', 'eval-note', report.limitations));
    target.append(node('p', 'eval-note', `Generated ${report.generated_at}. ${report.cases.length} questions. Answer faithfulness: not measured without live model + human review.`));
    report.cases.forEach(test => {
      const item = node('div', 'eval-case', test.question);
      item.append(node('small', '', `${test.kind} · actual: ${test.actual_route}${test.expected_route ? ' (expected: ' + test.expected_route + ')' : ''} · baseline recall ${test.baseline.recall === null ? 'n/a' : Math.round(test.baseline.recall * 100) + '%'} · hybrid recall ${test.hybrid.recall === null ? 'n/a' : Math.round(test.hybrid.recall * 100) + '%'}`));
      if (test.observation) item.append(node('small', '', test.observation)); target.append(item);
    });
  } catch (error) { target.replaceChildren(node('p', 'eval-note', error.message)); }
}
function researchTrailMarkdown(a) {
  let text = `# Evidence Atlas RAG research trail\n\nQuestion: ${a.question}\n\nMode: ${a.mode} | Status: ${a.status}\n\n${a.message}\n\n`;
  if (a.scope) text += `Scope: ${a.scope}\n\n`;
  if (a.reason) text += `Validation result: ${a.reason}\n\n`;
  a.claims.forEach(claim => {
    const e = a.evidence.find(item => item.id === claim.evidence_id);
    text += `## ${claim.kind}\n\n${claim.text}\n\nSource: ${e.title}, PDF page ${e.page} (${e.filename}).\n\n`;
    if (claim.kind !== 'Source excerpt') text += `Supporting quote: ${claim.quote}\n\n`;
    if (e.url) text += `${e.url}\n\n`;
  });
  text += '## Retrieved passages\n\nThese are retrieval candidates, not verified answers.\n\n';
  a.evidence.forEach(e => {
    text += `### ${e.id} — ${e.title}, PDF page ${e.page}\n\nFile: ${e.filename}\n\n${e.text}\n\n`;
    if (e.url) text += `${e.url}\n\n`;
  });
  text += '## Retrieval workflow\n\n';
  (a.trace || []).forEach(step => { text += `- ${step}\n`; });
  return text + '\nRetrieved excerpts require interpretation and source review.\n';
}
function exportTrail() {
  if (!currentAnswer) return;
  const text = researchTrailMarkdown(currentAnswer);
  const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
  const link = node('a'); link.href = url; link.download = 'evidence-atlas-rag-research-trail.md'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$$('[data-open]').forEach(button => button.addEventListener('click', openWorkspace));
$$('[data-demo]').forEach(button => button.addEventListener('click', () => loadDemo(button.dataset.demo || 'cms-ma')));
$$('[data-art]').forEach(button => button.addEventListener('click', () => loadDemo(button.dataset.demo || 'cms-ma')));
$('#go-home').addEventListener('click', openHome);
$$('.wordmark').forEach(link => link.addEventListener('click', openHome));
$$('.site-header nav a').forEach(link => link.addEventListener('click', openHome));
$$('[data-tab]').forEach(button => button.addEventListener('click', () => tab(button.dataset.tab)));
$('#nav-eval').addEventListener('click', () => { openWorkspace(); tab('eval'); });
$('#refresh-eval').addEventListener('click', loadEvaluation);
$('#file-input').addEventListener('change', event => upload(event.target.files));
$('#question-form').addEventListener('submit', submitQuestion);
$('#question').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submitQuestion(); } });
$('#build-matrix').addEventListener('click', buildMatrix);
$('.suggestions').addEventListener('click', runSuggestedQuestion);
$('#paper-list').addEventListener('change', renderSuggestions);
$('#load-selected-sample').addEventListener('click', () => loadDemo($('#sample-select').value));
$('#clear-collection').addEventListener('click', () => task('Clearing your collection…', async () => {
  const remoteNamespace = collection?.namespace;
  if (collection) await api(`/api/collections/${collection.id}`, { method: 'DELETE' });
  collection = null; renderCollection(); resetOutput();
  if (remoteNamespace) toast(`Local collection cleared. Pinecone vectors remain in ${remoteNamespace}.`);
}));
const zone = $('#dropzone');
zone.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('dragover'); });
zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
zone.addEventListener('drop', event => { event.preventDefault(); zone.classList.remove('dragover'); if (!working) upload(event.dataTransfer.files); });
api('/api/status').then(result => {
  status = result; renderSampleContext(); renderSuggestions();
  $('#mode-badge').textContent = status.mode === 'live' ? `LIVE MODE · ${status.vector_backend.toUpperCase()}` : 'LOCAL EXCERPT MODE';
  $('#privacy-note').textContent = status.mode === 'live' ? 'Live mode: document text is sent to your configured embedding provider. Questions and retrieved passages are sent to your model provider. Collections are not saved to disk.' : 'Local mode: no model calls and no document text leaves this server. Answers are verbatim excerpts, using lexical retrieval. Enable live mode for semantic search and synthesis.';
  if (status.vector_backend === 'pinecone') $('#privacy-note').append(node('p', '', 'Pinecone stores vectors and passage text remotely in an isolated namespace. PDFs and session state remain local; remote vectors alone do not restore a collection after restart.'));
  if (!status.configured) toast(status.configuration_message || 'Check your local .env configuration.');
}).catch(() => { $('#mode-badge').textContent = 'SERVER UNAVAILABLE'; toast('Cannot reach Evidence Atlas RAG. Start the Python server and reload.'); });
