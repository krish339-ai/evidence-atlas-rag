"""Offline launcher preflight. Never connect to providers or print settings values."""
from importlib.util import find_spec


def main():
    try:
        from papertrail.config import settings

        required = ['MODEL_API_KEY'] if settings.mode == 'live' else []
        if settings.vector_backend == 'pinecone':
            required += ['PINECONE_API_KEY', 'PINECONE_INDEX_NAME']
        import os
        missing = [name for name in required if not os.getenv(name, '').strip()]
        if missing:
            print('Missing configuration: ' + ', '.join(missing) + '. Set these in the project .env or process environment. Separate test .env files are not loaded.')
            return 1
        settings.validate()
        if settings.vector_backend == 'pinecone' and any(
            find_spec(name) is None for name in ('pinecone', 'langchain_pinecone')
        ):
            print('Install the optional backend with the project Python: python -m pip install -r requirements-pinecone.txt')
            return 1
    except ValueError as exc:
        # Settings.validate emits fixed instructions, not configuration values.
        print(str(exc))
        return 1
    except Exception:
        print('Local configuration check could not run. Follow README.md > Fresh setup to install the project dependencies.')
        return 1
    print('Local configuration is present. No provider connection or index check was performed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
