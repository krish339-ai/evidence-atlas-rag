"""Download only version-pinned public demo PDFs; never runs on server startup."""
import hashlib
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description='Download pinned public samples; no model calls.')
    parser.add_argument('--sample', choices=['cms-ma', 'rag', 'all'], default='all')
    args = parser.parse_args()
    target = ROOT / 'data/papers'
    target.mkdir(exist_ok=True, parents=True)
    manifest = []
    if args.sample in {'cms-ma', 'all'}:
        manifest.extend(json.loads((ROOT / 'data/cms-sources.json').read_text(encoding='utf-8')))
    if args.sample in {'rag', 'all'}:
        manifest.extend(json.loads((ROOT / 'data/sources.json').read_text(encoding='utf-8')))
    for paper in manifest:
        path = target / paper['file']
        if not path.exists():
            request = Request(paper['pdf'], headers={'User-Agent': 'Evidence Atlas RAG educational local demo'})
            with urlopen(request, timeout=45) as response:
                data = response.read(20 * 1024 * 1024 + 1)
            if not data.startswith(b'%PDF-') or len(data) > 20 * 1024 * 1024:
                raise ValueError(f"Invalid PDF from {paper['pdf']}")
            if paper.get('sha256') and hashlib.sha256(data).hexdigest() != paper['sha256']:
                raise ValueError(f"Source snapshot changed: {paper['file']}. Review provenance before adopting the new PDF.")
            path.write_bytes(data)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if paper.get('sha256') and digest != paper['sha256']:
            raise ValueError(f"Source snapshot changed: {paper['file']}. Review provenance before indexing.")
        paper['sha256'] = digest
        print(f"Ready: {paper['short']} ({paper['version']})")
    if args.sample in {'rag', 'all'}:
        (ROOT / 'data/download-record.json').write_text(json.dumps([p for p in manifest if 'sections' not in p], indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
