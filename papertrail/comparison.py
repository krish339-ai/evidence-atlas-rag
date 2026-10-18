"""Section-aware excerpt selection for the reading matrix; not a semantic reranker."""
import re

from papertrail.retrieval import tokens

DIMENSIONS = {
    'Methods': ('retriever generator model inference proposed method', r'(?:^|\n)(?:[0-9.]+\s+)?(?:models\b|retriever\b|generator\b|inference overview\b|overview of model\b|methodology\b)'),
    'Datasets': ('evaluation tasks datasets metrics experiments', r'(?:^|\n)(?:[0-9.]+\s+)?(?:tasks[, ]|experiments\b|datasets\b|open-domain question answering\b)'),
    'Findings': ('experimental results performance findings', r'(?:main results|experimental results|comparison against baselines|results and discussion|we find that|we observe that)'),
    'Limitations': ('limitation limitations future work', r'\blimitations?\b|\bfuture work\b'),
}


CMS_DIMENSIONS = {
    'Inpatient coverage': ('inpatient admission medical record benchmark', r'\binpatient\b'),
    'Outpatient and concurrent review': ('outpatient concurrent determination approval', r'\b(outpatient|concurrent)\b'),
    'Documentation and notices': ('documentation clinical notes notice denial reason', r'\b(documentation|clinical notes|notice|denial)\b'),
    'Timeframes and applicability': ('2026 2027 calendar days hours prior authorization', r'\b(2026|2027|hours|calendar days)\b'),
}


def matrix_passage(index, paper_id, dimension, dimensions=None):
    query, pattern = (dimensions or DIMENSIONS)[dimension]
    candidates = index.retrieve(query, paper_ids=[paper_id], k=12)
    relevant = [doc for doc in candidates if set(tokens(query)) & set(tokens(doc.page_content))]
    if not relevant:
        return None
    # Prefer explicit sections within the retrieved set; preserve retrieval order otherwise.
    section_matches = [doc for doc in relevant if re.search(pattern, doc.page_content, re.I)]
    if dimension == 'Limitations' or dimensions is CMS_DIMENSIONS:
        return section_matches[0] if section_matches else None
    return (section_matches or relevant)[0]
