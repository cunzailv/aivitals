"""智能体 / 技能 / 工作流资产：数量、frontmatter、导出、命令构造。"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aivitals import assets, workflow  # noqa: E402
from aivitals.model import CheckDef  # noqa: E402

DATA = ROOT / "aivitals" / "data"


class AssetsTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(assets.items(DATA, "agents")), 3)
        self.assertEqual(len(assets.items(DATA, "skills")), 3)
        self.assertEqual(len(assets.items(DATA, "workflows")), 3)

    def test_frontmatter_name_and_description(self):
        for kind in ("agents", "skills"):
            for item in assets.items(DATA, kind):
                self.assertTrue(item["name"])
                self.assertTrue(item["description"], item["name"])

    def test_show_returns_body(self):
        text = assets.show(DATA, "agents", "aivitals-auditor")
        self.assertIn("file:line", text)
        self.assertIn("禁止", text)

    def test_export_writes_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            total = 0
            for kind in assets.KINDS:
                written = assets.export(DATA, kind, Path(tmp) / kind)
                total += len(written)
                self.assertTrue(all(p.exists() for p in written))
            self.assertEqual(total, 9)

    def test_workflow_target_is_positional(self):
        wf = workflow.find(DATA / "workflows", "audit")
        step = wf["steps"][0]
        cmd = workflow.build_command(step, None)
        self.assertEqual(cmd[3], "scan")
        self.assertEqual(cmd[4], ".")
        self.assertNotIn("--target", cmd)

    def test_workflow_flag_mapping(self):
        cmd = workflow.build_command({"run": "scan", "with": {"update_baseline": True, "fail_on": "P0"}}, None)
        self.assertIn("--update-baseline", cmd)
        self.assertIn("--fail-on", cmd)
        self.assertIn("P0", cmd)


if __name__ == "__main__":
    unittest.main()
