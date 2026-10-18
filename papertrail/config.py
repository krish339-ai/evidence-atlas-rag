from dataclasses import dataclass, field
import os
import re

from dotenv import load_dotenv

load_dotenv()


def configured_dimension():
    try:
        return int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))
    except ValueError:
        return 0  # validate() returns an actionable error without echoing the value.


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv('PAPERTRAIL_MODE', 'demo')
    api_key: str = field(default=os.getenv('MODEL_API_KEY', ''), repr=False)
    base_url: str = os.getenv('MODEL_BASE_URL', 'https://api.openai.com/v1')
    chat_model: str = os.getenv('CHAT_MODEL', 'gpt-4.1-mini')
    embedding_model: str = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    embedding_key: str = field(default=os.getenv('EMBEDDING_API_KEY', ''), repr=False)
    embedding_url: str = os.getenv('EMBEDDING_BASE_URL', '')
    vector_backend: str = os.getenv('VECTOR_BACKEND', 'memory')
    pinecone_api_key: str = field(default=os.getenv('PINECONE_API_KEY', ''), repr=False)
    pinecone_index: str = os.getenv('PINECONE_INDEX_NAME', '')
    namespace_prefix: str = os.getenv('PINECONE_NAMESPACE_PREFIX', 'papertrail')
    embedding_dimensions: int = configured_dimension()

    def validate(self):
        if self.mode not in {'demo', 'live'}:
            raise ValueError('PAPERTRAIL_MODE must be demo or live.')
        if self.mode == 'live' and not self.api_key:
            raise ValueError('Live mode requires MODEL_API_KEY in .env. Demo mode needs no key.')
        if self.vector_backend not in {'memory', 'pinecone'}:
            raise ValueError('VECTOR_BACKEND must be memory or pinecone.')
        if self.vector_backend == 'pinecone':
            if self.mode != 'live':
                raise ValueError('Pinecone requires live semantic embeddings. Use VECTOR_BACKEND=memory for the local demo.')
            if not self.pinecone_api_key or not self.pinecone_index:
                raise ValueError('Set PINECONE_API_KEY and PINECONE_INDEX_NAME locally in .env.')
            if not re.fullmatch(r'papertrail(?:-[a-z0-9-]{1,35})?', self.namespace_prefix):
                raise ValueError('PINECONE_NAMESPACE_PREFIX must be papertrail or papertrail- followed by lowercase letters, digits, or hyphens.')
            if self.embedding_dimensions < 1:
                raise ValueError('EMBEDDING_DIMENSIONS must be a positive integer matching the model and index.')


settings = Settings()
