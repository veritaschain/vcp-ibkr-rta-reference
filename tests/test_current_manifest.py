"""Current checksums must match, while archived evidence remains byte-identical."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CurrentManifestTests(unittest.TestCase):
    def test_listed_file_digests_and_sizes_match_current_tree(self):
        manifest = json.loads((ROOT / 'hash_manifest.json').read_text())
        self.assertEqual(manifest['file_count'], len(manifest['files']))
        for name, expected in manifest['files'].items():
            with self.subTest(file=name):
                content = (ROOT / name).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected['sha256'])
                self.assertEqual(len(content), expected['size_bytes'])

    def test_original_manifest_and_evidence_bytes_are_preserved(self):
        historical = ROOT / 'archive/hash_manifest.pre-2026-11-02.json'
        self.assertEqual(hashlib.sha256(historical.read_bytes()).hexdigest(), '853b63d298a117538cbb619ec349acb42f3df75020d011ef3afd2067c455630a')
        original = json.loads(historical.read_text())
        corrected = {'README.md', 'verify.py', 'CHANGELOG.md'}
        redirects = {'datasets/metadata.json': 'archive/metadata.pre-2026-11-02.json', 'keys/key_manifest.json': 'archive/key_manifest.pre-2026-11-02.json'}
        for name, entry in original['files'].items():
            if name in corrected:
                continue
            expected = entry['sha256'] if isinstance(entry, dict) else entry
            path = ROOT / redirects.get(name, name)
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

if __name__ == '__main__':
    unittest.main()
