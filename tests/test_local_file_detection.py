"""Run local-file regression tests in an isolated interpreter."""
import os
import subprocess
import sys
import unittest
from pathlib import Path


class LocalFileDetectionRegressionTests(unittest.TestCase):
    def test_local_playlist_tracks_skip_metadata_and_output_expansion(self):
        repo_root = Path(__file__).resolve().parents[1]
        harness = Path(__file__).with_name("local_file_detection_harness.py")
        environment = os.environ.copy()
        environment["ZOTIFY_SRC_PATH"] = str(repo_root)
        result = subprocess.run(
            [sys.executable, str(harness)],
            cwd=repo_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
