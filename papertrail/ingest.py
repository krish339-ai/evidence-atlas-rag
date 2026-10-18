"""Page-preserving LangChain PDF loader and splitter. No OCR or remote fetches."""
import hashlib
import io
import re
from collections import Counter
from collections.abc import Iterator

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 200


def clean(text: str) -> str:
    text = text.replace('\x00', '').replace('\u00ad', '')
    text = re.sub(r'(?<=\w)-\n(?=[a-z])', '', text)
    return re.sub(r'[ \t]+', ' ', text).strip()


class ResearchPDFLoader(BaseLoader):
    def __init__(self, data: bytes, filename: str):
        self.data, self.filename = data, filename

    def lazy_load(self) -> Iterator[Document]:
        if len(self.data) > MAX_BYTES or not self.data.startswith(b'%PDF-'):
            raise ValueError('Each file must be a PDF smaller than 20 MB.')
        try:
            reader = PdfReader(io.BytesIO(self.data), strict=False)
            if reader.is_encrypted:
                raise ValueError('Password-protected PDFs are not supported.')
            if len(reader.pages) > MAX_PAGES:
                raise ValueError('Each PDF must have at most 200 pages.')
            pages = [clean(p.extract_text() or '') for p in reader.pages]
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('This PDF could not be read. Try a text-based PDF.') from exc
        if sum(len(p) for p in pages) < 100:
            raise ValueError('No usable text found. Scanned PDFs need OCR before upload.')
        paper_id = hashlib.sha256(self.data).hexdigest()[:16]
        title = self.filename.rsplit('.', 1)[0].replace('_', ' ')
        # Remove exact short repeated headers/footers; retain page boundaries.
        counts = Counter(line for page in pages for line in set(page.splitlines()) if 2 < len(line) < 100)
        repeated = {line for line, count in counts.items() if len(pages) >= 4 and count >= max(3, len(pages) * .7)}
        for index, text in enumerate(pages):
            text = '\n'.join(line for line in text.splitlines() if line not in repeated)
            if text.strip():
                yield Document(page_content=text, metadata={
                    'paper_id': paper_id, 'title': title, 'filename': self.filename,
                    'page': index + 1, 'page_count': len(pages), 'source': self.filename,
                })


def chunk_pages(pages: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1400, chunk_overlap=200, add_start_index=True)
    chunks = splitter.split_documents(pages)
    for index, doc in enumerate(chunks):
        doc.metadata['chunk_id'] = f"{doc.metadata['paper_id']}:{doc.metadata['page']}:{index}"
    return chunks
