"""检测引擎：用标注样例做召回与误报回归。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aivitals import detect, profile as prof, rules  # noqa: E402

CHECKS = ROOT / "aivitals" / "data" / "checks"


def run(fixture: str):
    checks, _ = rules.load(CHECKS)
    profile, files = prof.build(ROOT / "fixtures" / fixture)
    return detect.run_checks(profile, files, checks, {})


class DetectTest(unittest.TestCase):
    def test_bad_fixture_full_recall(self):
        result = run("bad-sync-long-task")
        got = {f.check_id for f in result.findings}
        self.assertIn("L02-P0-001", got)
        self.assertIn("L10-P0-009", got)
        self.assertGreaterEqual(len(result.findings), 13)
        for f in result.findings:
            self.assertTrue(f.evidence, f.check_id)

    def test_good_fixture_no_false_positive(self):
        result = run("good-production-app")
        self.assertEqual(result.findings, [])

    def test_every_finding_has_file_and_line(self):
        result = run("bad-sync-long-task")
        for f in result.findings:
            ev = f.evidence[0]
            self.assertTrue(ev.file)
            self.assertGreaterEqual(ev.line, 0)  # file_absent 类证据为文件级，行号为 0

    def test_no_evidence_findings_are_dropped(self):
        result = run("bad-sync-long-task")
        for f in result.findings:
            self.assertTrue(f.evidence)


if __name__ == "__main__":
    unittest.main()
