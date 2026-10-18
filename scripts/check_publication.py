"""Review an explicit public-file allowlist without reading local credentials."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET = re.compile(r'(?:sk-[A-Za-z0-9_-]{24,}|pcsk_[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
USER_PATH = re.compile(r'[A-Z]:[\\/](?:Users|D_Drive)[\\/]', re.I)


def main():
    files = [line.strip() for line in (ROOT/'PUBLIC_FILES.txt').read_text().splitlines() if line.strip()]
    assert len(files) == len(set(files)), 'Duplicate allowlist entry'
    reviewed = []
    for name in files:
        path = (ROOT/name).resolve()
        assert path.is_relative_to(ROOT), 'Allowlist path escapes project'
        assert path.is_file(), f'Missing publication file: {name}'
        assert path.suffix.lower() not in {'.pdf', '.docx', '.jpg', '.png', '.zip', '.key', '.pem'}, f'Unexpected binary/private file: {name}'
        content = path.read_text(encoding='utf-8-sig')
        assert not SECRET.search(content), f'Potential credential pattern in {name}; contents withheld'
        assert not USER_PATH.search(content), f'Private absolute path in {name}; contents withheld'
        reviewed.append({'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
    template = (ROOT/'.env.example').read_text()
    for key in ['MODEL_API_KEY', 'EMBEDDING_API_KEY', 'PINECONE_API_KEY']:
        assert re.search(rf'^{key}=\s*$', template, re.M), f'{key} example must stay blank'
    # Check staged/tracked paths when a repository is present; do not stage anything here.
    git = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True)
    if git.returncode == 0:
        unexpected = set(git.stdout.splitlines()) - set(files)
        assert not unexpected, f'Tracked files outside publication allowlist: {sorted(unexpected)}'
    report = {'files': reviewed, 'count': len(files), 'checks': 'Explicit paths, text-only, no known credential signatures, no private absolute paths, blank credential placeholders, tracked-file allowlist.'}
    (ROOT/'PUBLICATION-REVIEW.local.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Publication checks passed for {len(files)} explicitly listed text files. No credential values were read or printed.')


if __name__ == '__main__':
    main()
