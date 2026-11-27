"""规则库自检：加载、唯一性、17 层覆盖。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aivitals import rules  # noqa: E402

CHECKS = ROOT / "aivitals" / "data" / "checks"


class RulesTest(unittest.TestCase):
    def setUp(self):
        self.checks, self.errors = rules.load(CHECKS)

    def test_no_errors(self):
        self.assertEqual(self.errors, [])

    def test_unique_ids(self):
        ids = [c.id for c in self.checks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_17_layers_covered(self):
        layers = {c.layer for c in self.checks}
        self.assertEqual(layers, set(range(1, 18)))

    def test_every_rule_has_evidence_channel(self):
        for c in self.checks:
            self.assertTrue(c.detect, c.id)
            self.assertTrue(c.fix, c.id)
            self.assertTrue(c.impact, c.id)
            self.assertTrue(c.derived_from, c.id)

    def test_severity_enum(self):
        for c in self.checks:
            self.assertIn(c.severity, {"P0", "P1", "P2", "P3"}, c.id)


if __name__ == "__main__":
    unittest.main()
