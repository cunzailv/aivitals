"""声明对正：四态判定回归。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aivitals import claims, profile as prof  # noqa: E402

DEMO = ROOT / "fixtures" / "claims-demo"
PREDICATES = ROOT / "aivitals" / "data" / "claims" / "predicates.yaml"


class ClaimsTest(unittest.TestCase):
    def setUp(self):
        self.preds, self.errors = claims.load_predicates(PREDICATES)
        self.assertEqual(self.errors, [])
        self.profile, self.files = prof.build(DEMO)
        self.results = claims.run(DEMO, DEMO / "README.md", self.files, self.profile, self.preds)

    def test_all_four_verdicts_present(self):
        verdicts = {r.verdict for r in self.results}
        self.assertEqual(verdicts, set(claims.VERDICTS))

    def test_contradicted_has_evidence(self):
        for r in self.results:
            if r.verdict == "contradicted":
                self.assertTrue(r.evidence, r.claim.text)

    def test_unsupported_is_not_a_negative_finding(self):
        # 未找到证据不等于没有实现：必须带免责口径
        body = claims.to_markdown(self.results, DEMO / "README.md")
        self.assertIn("未找到证据", body)


if __name__ == "__main__":
    unittest.main()
