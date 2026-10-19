"""Launcher preflight against disposable configuration, with no provider calls."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('file_config,overrides,success,message', [
    ('MODEL_API_KEY=dummy-model\nPINECONE_API_KEY=dummy-pinecone\nPINECONE_INDEX_NAME=test-index\nVECTOR_BACKEND=memory\n',
     {'VECTOR_BACKEND': 'pinecone'}, True, 'No provider connection'),
    ('MODEL_API_KEY=dummy-model\nPINECONE_API_KEY=dummy-pinecone\n',
     {'VECTOR_BACKEND': 'pinecone'}, False, 'PINECONE_INDEX_NAME'),
    ('MODEL_API_KEY=dummy-model\nVECTOR_BACKEND=pinecone\n',
     {'VECTOR_BACKEND': 'memory'}, True, 'No provider connection'),
    ('MODEL_API_KEY=dummy-model\nPINECONE_API_KEY="  "\nPINECONE_INDEX_NAME=test-index\n',
     {'VECTOR_BACKEND': 'pinecone'}, False, 'PINECONE_API_KEY'),
    ('MODEL_API_KEY=dummy-model\nPINECONE_API_KEY=dummy-pinecone\nPINECONE_INDEX_NAME=test-index\nEMBEDDING_DIMENSIONS=bad-value\n',
     {'VECTOR_BACKEND': 'pinecone'}, False, 'positive integer'),
])
def test_preflight_configuration(tmp_path, file_config, overrides, success, message):
    for package, filename in [('papertrail', 'config.py'), ('scripts', 'check_local_config.py')]:
        folder = tmp_path / package
        folder.mkdir()
        (folder / '__init__.py').write_text('')
        shutil.copyfile(ROOT / package / filename, folder / filename)
    config = tmp_path / '.env'
    config.write_text(file_config)
    # A private test configuration must not fill gaps in the standard .env.
    (tmp_path / '.env.pinecone-test.local').write_text('PINECONE_INDEX_NAME=do-not-load\n')
    # Prevent any optional SDK import or network use; preflight checks presence only.
    for name in ('pinecone', 'langchain_pinecone'):
        (tmp_path / (name + '.py')).write_text('raise AssertionError("SDK must not be imported")\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith((
        'MODEL_', 'EMBEDDING_', 'PINECONE_', 'PAPERTRAIL_', 'EVIDENCE_ATLAS_',
        'VECTOR_BACKEND', 'PYTHON_DOTENV_', 'PYTHONPATH',
    ))}
    env.update(EVIDENCE_ATLAS_MODE='live', **overrides)
    result = subprocess.run([sys.executable, '-m', 'scripts.check_local_config'],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    assert (result.returncode == 0) is success, result.stdout + result.stderr
    assert message in result.stdout
    assert not result.stderr
    assert all(value not in result.stdout for value in ('dummy-model', 'dummy-pinecone', 'test-index', 'bad-value'))
    assert config.read_text() == file_config


def test_missing_optional_adapter(monkeypatch, capsys):
    from scripts import check_local_config
    from papertrail import config
    monkeypatch.setattr(config, 'settings', config.Settings(
        mode='live', vector_backend='pinecone', api_key='dummy-model',
        pinecone_api_key='dummy-pinecone', pinecone_index='test-index'))
    monkeypatch.setenv('PINECONE_INDEX_NAME', 'test-index')
    monkeypatch.setattr(check_local_config, 'find_spec', lambda name: None)
    assert check_local_config.main() == 1
    assert 'requirements-pinecone.txt' in capsys.readouterr().out
