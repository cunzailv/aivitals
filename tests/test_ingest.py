"""资料入账：切节、抽候选、层识别。"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aivitals import ingest  # noqa: E402

SAMPLE = """# 检索层

检索必须按租户过滤，否则会越权拿到别人的文档。

# 成本

没有成本归属，账单无法分摊到具体客户。
"""


class IngestTest(unittest.TestCase):
    def test_split_sections(self):
        sections = ingest.split_sections(SAMPLE)
        self.assertEqual([s["title"] for s in sections], ["检索层", "成本"])

    def test_candidates_have_signal_and_section(self):
        sections = ingest.split_sections(SAMPLE)
        cands = ingest.build_candidates(sections)
        self.assertEqual(len(cands), 2)
        for c in cands:
            self.assertTrue(c["id"].startswith("CAND-"))
            self.assertTrue(c["section"])
            self.assertIn(c["severity_hint"], {"P0", "P1", "P2"})

    def test_layer_hint(self):
        cands = ingest.build_candidates(ingest.split_sections(SAMPLE))
        layers = sorted(c["layer_hint"] for c in cands)
        self.assertEqual(layers, [7, 17])

    def test_dedup(self):
        sections = ingest.split_sections(SAMPLE + "\n\n检索必须按租户过滤，否则会越权拿到别人的文档。\n")
        cands = ingest.build_candidates(sections)
        ids = [c["id"] for c in cands]
        self.assertEqual(len(ids), len(set(ids)))

    def test_ingest_writes_draft_and_private_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "doc.md"
            src.write_text(SAMPLE, encoding="utf-8")
            info = ingest.ingest(src, "t1", root, root / "draft")
            self.assertTrue(Path(info["draft"]).exists())
            manifest = root / "corpus" / "sources" / "t1" / "manifest.json"
            self.assertTrue(manifest.exists())
            self.assertIn(Path(info["draft"]).parent.name, ("draft",))


if __name__ == "__main__":
    unittest.main()
