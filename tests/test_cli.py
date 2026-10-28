from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


class CLITests(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, "-m", "cohortframe", *map(str, args)],
                              text=True, capture_output=True, timeout=20)

    def test_capabilities_are_machine_readable_and_honest(self):
        result = self.call("capabilities")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["providers"], [])
        self.assertFalse(data["result"]["security"]["os_sandbox"])

    def test_invalid_cli_is_structured(self):
        result = self.call("job", "submit", "missing")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["ok"])

    def test_duplicate_json_is_rejected_before_project_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            brief = Path(folder) / "brief.json"
            brief.write_text('{"version":1,"version":2}')
            result = self.call("--home", Path(folder) / "state", "project", "create", brief)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)["ok"])

    def test_project_survives_separate_cli_process(self):
        with tempfile.TemporaryDirectory() as folder:
            brief = Path(folder) / "brief.json"
            brief.write_text(json.dumps({"version":1,"name":"CLI persistence","width":320,
                "height":180,"fps":12,"scenes":[{"id":"a","title":"HELLO","duration":1}]}))
            home = Path(folder) / "state"
            created = self.call("--home", home, "project", "create", brief)
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            project = json.loads(created.stdout)["result"]
            shown = self.call("--home", home, "project", "show", project["id"])
            self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)
            self.assertEqual(json.loads(shown.stdout)["result"]["manifest"]["name"], "CLI persistence")

    @unittest.skipUnless(Path('/dev/zero').exists(), 'requires a POSIX character device')
    def test_device_is_rejected_without_unbounded_read(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.call('--home', folder, 'project', 'create', '/dev/zero')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)['ok'])

    def test_corrupt_state_is_a_json_error(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'cohortframe.sqlite3').write_bytes(b'not a database')
            result = self.call('--home', folder, 'job', 'list')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(json.loads(result.stdout)['ok'])
            self.assertNotIn('Traceback', result.stderr)


if __name__ == "__main__":
    unittest.main()
