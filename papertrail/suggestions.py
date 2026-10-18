"""Small, source-derived starter questions without additional model requests."""
import re
from collections import Counter

from papertrail.retrieval import STOP, tokens

SECTION_QUESTIONS = {
    'certifications & education': 'Which certifications and education are listed?',
    'professional experience': 'What roles are listed under Professional Experience?',
    'technical skills': 'What technical skills are listed?',
    'research methods': 'What research methods are described?',
    'evaluation results': 'What evaluation results are reported?',
    'key findings': 'What key findings are reported?',
}


def starter_questions(chunks, limit=8):
    """Prefer recognizable sections, then repeated adjacent terms, balanced by PDF.

    Each starter shares at least two meaningful words with one actual chunk so
    it can satisfy the existing local retrieval check. This is not an answer guarantee.
    """
    by_paper = {}
    for doc in chunks:
        by_paper.setdefault(doc.metadata['paper_id'], []).append(doc)
    groups = []
    for pid, docs in by_paper.items():
        candidates, phrases, counts = [], {}, Counter()
        for topic, question in SECTION_QUESTIONS.items():
            if any(topic in re.sub(r'\s+', ' ', doc.page_content).lower() for doc in docs):
                candidates.append((question, set(tokens(topic))))
        for doc in docs:
            for line in doc.page_content.splitlines():
                if '@' in line or re.search(r'https?://|www\.', line, re.I):
                    continue
                words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", line)
                for left, right in zip(words, words[1:]):
                    pair = (left.lower().strip('.-'), right.lower().strip('.-'))
                    if any(w in STOP or len(w) < 3 for w in pair) or pair[0] == pair[1]:
                        continue
                    topic = f'{left} {right}'.strip('.-')
                    if not 7 <= len(topic) <= 65 or len(set(tokens(topic))) < 2:
                        continue
                    counts[pair] += 1
                    phrases.setdefault(pair, topic)
        for pair, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            topic = phrases[pair]
            candidates.append((f'What does the document say about {topic}?', set(tokens(topic))))
        selected, used_topics = [], []
        for question, terms in candidates:
            if any(terms <= previous or previous <= terms for previous in used_topics):
                continue
            # Verify the whole question against the same lexical floor used by the graph.
            if not any(len(set(tokens(question)) & set(tokens(doc.page_content))) >= 2 for doc in docs):
                continue
            selected.append({'question': question, 'paper_id': pid, 'title': docs[0].metadata.get('title', 'Uploaded PDF')})
            used_topics.append(terms)
            if len(selected) == 4:
                break
        groups.append(selected)
    # Round-robin preserves representation when several PDFs are uploaded together.
    return [group[i] for i in range(4) for group in groups if i < len(group)][:limit]
