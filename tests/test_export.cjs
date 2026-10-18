const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

// Load the actual browser functions without executing the DOM startup handlers.
const script = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
const context = vm.createContext({});
vm.runInContext(script.slice(0, script.indexOf("$$('[data-open]')")), context);

const evidence = [{ id: 'E1', title: 'Education fixture', filename: 'fixture.pdf', page: 2,
  text: 'B.Sc., Physics — Example University, 2010 – 2014' }];

test('rejected answers export retrieved sources, reason, and workflow', () => {
  const output = context.researchTrailMarkdown({ question: 'Which degree?', mode: 'live',
    status: 'unverified', reason: 'audit_rejected', message: 'Answer withheld.', claims: [],
    evidence, trace: ['Retrieved passages', 'Evidence audit rejected answer'] });
  assert.match(output, /Status: unverified/);
  assert.match(output, /Validation result: audit_rejected/);
  assert.match(output, /E1 — Education fixture, PDF page 2/);
  assert.ok(output.includes(evidence[0].text));
  assert.match(output, /not verified answers/);
  assert.match(output, /Evidence audit rejected answer/);
});

test('accepted answers retain their exact supporting quote and source metadata', () => {
  const output = context.researchTrailMarkdown({ question: 'Which degree?', mode: 'live',
    status: 'answered', message: 'Cited answer.', evidence,
    claims: [{ kind: 'Reported finding', text: 'B.Sc. in Physics.', evidence_id: 'E1', quote: evidence[0].text }],
    trace: ['Passed model evidence audit'] });
  assert.ok(output.includes('Supporting quote: ' + evidence[0].text));
  assert.match(output, /Source: Education fixture, PDF page 2 \(fixture.pdf\)/);
});

test('no-evidence refusals export without requiring any claims or passages', () => {
  const output = context.researchTrailMarkdown({ question: 'Outside scope?', mode: 'demo',
    status: 'insufficient', message: 'Outside scope.', scope: 'Selected collection',
    claims: [], evidence: [], trace: ['Checked scope; no model call'] });
  assert.match(output, /Scope: Selected collection/);
  assert.match(output, /Checked scope; no model call/);
});

function composerContext({ status = 'answered', fail = false, nextDraft } = {}) {
  const elements = new Map();
  function element() {
    return { value: '', checked: false, hidden: false, dataset: {}, children: [],
      focus() { this.focused = true; },
      replaceChildren(...children) { this.children = children; },
      append(child) { this.children.push(child); } };
  }
  const get = selector => {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  };
  const box = get('#question'); box.value = 'What technical skills are listed?';
  const selected = [{ value: 'resume' }];
  const sandbox = vm.createContext({
    document: { querySelector: get, createElement: element,
      querySelectorAll: selector => selector === '#paper-list input:checked' ? selected : [] },
    setTimeout: () => 1, clearTimeout: () => {},
    requests: [], answers: [],
    request: async (url, options) => {
      if (nextDraft) box.value = nextDraft;
      if (fail) throw new Error('Temporary connection failure');
      return { status, evidence: [], claims: [], trace: [] };
    },
  });
  vm.runInContext(script.slice(0, script.indexOf("$$('[data-open]')")), sandbox);
  vm.runInContext(`
    collection = { id: 'fixture', questions: [
      { question: 'What technical skills are listed?', paper_id: 'resume', title: 'Resume' },
      { question: 'What research methods are described?', paper_id: 'other', title: 'Other PDF' }
    ] };
    api = async (url, options) => { requests.push(JSON.parse(options.body)); return request(url, options); };
    renderAnswer = (question, result) => answers.push({ question, result });
  `, sandbox);
  return { sandbox, get, box, selected };
}

test('clicking an uploaded suggestion submits once and clears the completed question', async () => {
  const { sandbox, box } = composerContext();
  const button = { dataset: { question: 'What technical skills are listed?', compare: 'false' } };
  await sandbox.runSuggestedQuestion({ target: { closest: () => button } });
  assert.equal(sandbox.requests.length, 1);
  assert.equal(sandbox.requests[0].question, button.dataset.question);
  assert.equal(sandbox.answers[0].question, button.dataset.question);
  assert.equal(box.value, '');
  assert.equal(box.focused, true);
});

test('completed refusals clear the composer but provider and network errors preserve it', async () => {
  for (const status of ['insufficient', 'unverified', 'error']) {
    const { sandbox, box } = composerContext({ status });
    await sandbox.submitQuestion();
    assert.equal(box.value === '', status !== 'error');
  }
  const { sandbox, box } = composerContext({ fail: true });
  await sandbox.submitQuestion();
  assert.equal(box.value, 'What technical skills are listed?');
});

test('a new draft typed during a request is preserved', async () => {
  const { sandbox, box } = composerContext({ nextDraft: 'My next question' });
  await sandbox.submitQuestion();
  assert.equal(box.value, 'My next question');
});

test('suggestions reflect the selected documents and remain after a response', async () => {
  const { sandbox, get, selected } = composerContext();
  sandbox.renderSuggestions();
  assert.equal(get('.suggestions').children.length, 1);
  assert.equal(get('.suggestions').children[0].dataset.question, 'What technical skills are listed?');
  await sandbox.submitQuestion();
  assert.equal(get('#suggestion-panel').hidden, false);
  selected.splice(0);
  sandbox.renderSuggestions();
  assert.equal(get('#suggestion-panel').hidden, true);
});
