#!/usr/bin/env python3
"""Regenerate an unsigned current-source checksum inventory; no evidence signing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--include', action='append', default=[], help='New repository file not yet tracked by Git')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
paths = sorted(set(filter(None, tracked + args.include)) - {'hash_manifest.json'})
files = {}
for relative in paths:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise SystemExit('Invalid or unavailable repository file: ' + relative)
    content = path.read_bytes()
    files[relative] = {'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content)}
manifest = {
    'schema_version': '2.0',
    'updated_on': '2026-11-02',
    'algorithm': 'SHA-256',
    'scope': 'Unsigned checksum inventory of the listed current repository files; not origin, signature, anchor, conformance or production verification.',
    'historical_manifest': 'archive/hash_manifest.pre-2026-11-02.json',
    'file_count': len(files),
    'files': files,
    'excluded_from_manifest': ['hash_manifest.json (this file)'],
}
(root / 'hash_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print('Recorded', len(files), 'files; no evidence content was regenerated.')
