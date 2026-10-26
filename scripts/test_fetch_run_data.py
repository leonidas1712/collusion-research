"""Offline restoration tests; no release or network access required."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('fetch_run_data.py')


class RestoreTests(unittest.TestCase):
    def fixture(self, root, member='runs/example/scores.json'):
        assets = root / 'assets'
        assets.mkdir()
        payload = b'{"score": 0.5}\n'
        archive = assets / 'part.tar.gz'
        with tarfile.open(archive, 'w:gz') as tf:
            info = tarfile.TarInfo(member)
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))
        manifest = {'schema_version': 1, 'assets': [{'name': archive.name,
            'size': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'files': [{'path': member, 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}]}]}
        (assets / 'manifest.json').write_text(json.dumps(manifest))
        return assets, payload

    def run_restore(self, source, dest):
        return subprocess.run([sys.executable, str(SCRIPT), '--source', str(source),
                               '--destination', str(dest)], capture_output=True, text=True)

    def test_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); assets, payload = self.fixture(root); dest = root / 'out'
            self.assertEqual(self.run_restore(assets, dest).returncode, 0)
            self.assertEqual(self.run_restore(assets, dest).returncode, 0)
            target = dest / 'runs/example/scores.json'
            self.assertEqual(target.read_bytes(), payload)
            target.write_text('local changes')
            self.assertNotEqual(self.run_restore(assets, dest).returncode, 0)
            self.assertEqual(target.read_text(), 'local changes')

    def test_corrupt_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); assets, _ = self.fixture(root)
            with (assets / 'part.tar.gz').open('ab') as f:
                f.write(b'corrupt')
            self.assertNotEqual(self.run_restore(assets, root / 'out').returncode, 0)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); assets, _ = self.fixture(root, '../escape')
            self.assertNotEqual(self.run_restore(assets, root / 'out').returncode, 0)
            self.assertFalse((root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
