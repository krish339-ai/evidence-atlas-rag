"""Dense baseline plus reciprocal-rank fusion and optional paper balancing."""
import hashlib
import math
import re
from collections import Counter

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from papertrail.config import Settings

STOP = set('a an the is are was were what which how why who when where of in on to for and or with from by as do does did this that these those paper papers study studies compare comparison across between their they it its can could would should me tell about please reported report results using use used'.split())


def tokens(text):
    return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if len(w) > 1 and w not in STOP]


class LocalHashEmbeddings(Embeddings):
    """Deterministic lexical vectors for offline testing, NOT semantic embeddings."""
    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text):
        vector = [0.0] * 2048
        for word, count in Counter(tokens(text)).items():
            index = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], 'big') % len(vector)
            vector[index] += 1 + math.log(count)
        norm = math.sqrt(sum(x*x for x in vector)) or 1
        return [x / norm for x in vector]


class Index:
    def __init__(self, chunks, config: Settings):
        config.validate()
        embedding = LocalHashEmbeddings() if config.mode == 'demo' else OpenAIEmbeddings(
            model=config.embedding_model, api_key=config.embedding_key or config.api_key,
            base_url=config.embedding_url or config.base_url, request_timeout=30, max_retries=0,
            check_embedding_ctx_length=False,
        )
        self.chunks = chunks
        self.backend = config.vector_backend
        self.namespace = None
        if self.backend == 'pinecone':
            from papertrail.pinecone_backend import build_pinecone_store
            self.store, self.namespace = build_pinecone_store(chunks, embedding, config)
        else:
            self.store = InMemoryVectorStore(embedding)
            self.store.add_documents(chunks)
        self.terms = [Counter(tokens(d.page_content)) for d in chunks]
        self.lengths = [sum(t.values()) for t in self.terms]
        self.average = sum(self.lengths) / max(1, len(chunks))
        self.df = Counter(w for terms in self.terms for w in terms)

    def sparse(self, question):
        scores = []
        for i, terms in enumerate(self.terms):
            score = 0
            for word in set(tokens(question)):
                freq = terms.get(word, 0)
                idf = math.log(1 + (len(self.chunks) - self.df[word] + .5) / (self.df[word] + .5))
                score += idf * freq * 2.5 / (freq + 1.5 * (.25 + .75 * self.lengths[i] / (self.average or 1)))
            scores.append(score)
        return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True), scores

    def retrieve(self, question, strategy='hybrid', k=6, paper_ids=None, balanced=False):
        allowed = set(paper_ids or [d.metadata['paper_id'] for d in self.chunks])
        # Cap remote query payloads. Namespace isolation is enforced by the store instance.
        raw_dense = self.store.similarity_search(question, k=min(len(self.chunks), 1000))
        local = {d.metadata['chunk_id']: d for d in self.chunks}
        dense = [local[d.metadata['chunk_id']] for d in raw_dense if d.metadata.get('chunk_id') in local]
        if strategy == 'baseline':
            return [d for d in dense if d.metadata['paper_id'] in allowed][:k]
        ranks, scores = self.sparse(question)
        fusion = {key: 0.0 for key in local}
        fusion.update({d.metadata['chunk_id']: 1/(60+i+1) for i, d in enumerate(dense)})
        for rank, idx in enumerate(ranks):
            key = self.chunks[idx].metadata['chunk_id']
            fusion[key] += 1/(60+rank+1) if scores[idx] > 0 else 0
        candidates = sorted((d for d in self.chunks if d.metadata['paper_id'] in allowed),
                            key=lambda d: fusion[d.metadata['chunk_id']], reverse=True)
        chosen = []
        if balanced:
            # First cover each selected paper, then spend remaining budget on relevance.
            for pid in sorted(allowed):
                match = next((d for d in candidates if d.metadata['paper_id'] == pid), None)
                if match is not None:
                    chosen.append(match)
        for doc in candidates:
            if doc not in chosen:
                chosen.append(doc)
        return chosen[:k]
