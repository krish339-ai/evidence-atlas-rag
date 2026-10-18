from langchain_core.documents import Document

from papertrail.config import Settings
from papertrail.graph import ask
from papertrail.retrieval import Index, tokens
from papertrail.suggestions import starter_questions


def document(text, pid='resume'):
    return Document(page_content=text, metadata={'paper_id': pid, 'chunk_id': pid + ':1', 'page': 1, 'title': pid})


def test_uploaded_resume_starters_use_its_sections_and_work_without_a_key():
    docs = [document('CERTIFICATIONS & EDUCATION\nCloud Computing Certificate. B.Sc., Physics — Example University.\n'
                     'PROFESSIONAL EXPERIENCE\nDatabase Engineer at Example Systems.\n'
                     'TECHNICAL SKILLS\nSQL Server, Python scripting and database design. SQL Server administration.')]
    questions = starter_questions(docs)
    assert 3 <= len(questions) <= 4
    assert any('certifications' in q['question'] for q in questions)
    index = Index(docs, Settings(mode='demo'))
    for item in questions:
        assert item['paper_id'] == 'resume'
        result = ask(index, Settings(mode='demo'), item['question'], ['resume'])
        assert result['status'] == 'excerpts'


def test_general_prose_gets_distinct_source_based_questions():
    docs = [document('Solar panels convert sunlight into electrical energy. Solar panels supply clean electricity. '
                     'Battery storage retains electrical energy for later demand.', 'energy')]
    questions = starter_questions(docs)
    assert questions and len({q['question'] for q in questions}) == len(questions)
    for item in questions:
        assert len(set(tokens(item['question'])) & set(tokens(docs[0].page_content))) >= 2


def test_suggestions_cover_multiple_documents_without_stale_topics():
    docs = [document(f'Planetary science and orbital mechanics describe celestial motion for system {i}.', str(i)) for i in range(8)]
    questions = starter_questions(docs)
    assert len(questions) == 8 and {q['paper_id'] for q in questions} == {str(i) for i in range(8)}
    assert starter_questions([]) == []


def test_contact_lines_and_uninformative_content_do_not_become_starters():
    docs = [document('Reach Me contact@example.test\nhttps://private.example.test\nThe and or a an is was.')]
    assert starter_questions(docs) == []
