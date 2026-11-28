"""提示词模板：可复制、带命令、带版本。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aivitals import prompts  # noqa: E402


class PromptTest(unittest.TestCase):
    def test_all_kinds_render(self):
        for kind in ("audit", "claims", "fix", "ci"):
            text = prompts.render(kind, "zh", "0.2.1")
            self.assertGreater(len(text), 60, kind)

    def test_audit_contains_commands_and_version(self):
        text = prompts.render("audit", "zh", "0.2.1")
        self.assertIn("aivitals scan . --doc README.md", text)
        self.assertIn("aivitals-0.2.1", text)
        self.assertIn("file:line", text)

    def test_claims_keeps_four_states(self):
        text = prompts.render("claims", "zh", "0.2.1")
        for state in ("confirmed", "partial", "contradicted", "unsupported"):
            self.assertIn(state, text)

    def test_fix_forbids_batch_edits(self):
        text = prompts.render("fix", "zh", "0.2.1")
        self.assertIn("一次只处理一条", text)
        self.assertIn("--baseline", text)

    def test_english_fallback(self):
        self.assertIn("AIVitals", prompts.render("audit", "en", "0.2.1"))
        # 未翻译的场景回落到中文而不是报错
        self.assertIn("aivitals", prompts.render("fix", "en", "0.2.1").lower())

    def test_unknown_kind_raises(self):
        with self.assertRaises(KeyError):
            prompts.render("nope", "zh", "0.2.1")


if __name__ == "__main__":
    unittest.main()
