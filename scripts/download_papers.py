"""Download only version-pinned public demo PDFs; never runs on server startup."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    target = ROOT / 'data/papers'
    target.mkdir(exist_ok=True, parents=True)
    manifest = json.loads((ROOT / 'data/sources.json').read_text(encoding='utf-8'))
    for paper in manifest:
        path = target / paper['file']
        if not path.exists():
            request = Request(paper['pdf'], headers={'User-Agent': 'Evidence Atlas RAG educational local demo'})
            with urlopen(request, timeout=45) as response:
                data = response.read(20 * 1024 * 1024 + 1)
            if not data.startswith(b'%PDF-') or len(data) > 20 * 1024 * 1024:
                raise ValueError(f"Invalid PDF from {paper['pdf']}")
            path.write_bytes(data)
        paper['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"Ready: {paper['short']} ({paper['version']})")
    (ROOT / 'data/download-record.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
