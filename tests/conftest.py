"""Tests must never inherit real provider settings from a developer's .env."""
import os

os.environ['PAPERTRAIL_MODE'] = 'demo'
os.environ['VECTOR_BACKEND'] = 'memory'
os.environ['MODEL_API_KEY'] = 'test-only-model-key'
os.environ['PINECONE_API_KEY'] = 'test-only-pinecone-key'
os.environ['LANGSMITH_TRACING'] = 'false'
