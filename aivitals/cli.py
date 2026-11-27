"""命令行入口。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from . import detect, profile as prof, report, rules
from .model import AuditResult

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHECKS = ROOT / "checks"
CORPUS = ROOT / "corpus" / "architecture.json"


def layer_names() -> dict[int, str]:
    try:
        data = json.loads(CORPUS.read_text(encoding="utf-8"))
        return {int(l["id"]): l["name"] for l in data.get("LAYERS", [])}
    except (OSError, ValueError, KeyError):
        return {}


def _ingest(target: str) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    if target.startswith("http://") or target.startswith("https://"):
        tmp = tempfile.TemporaryDirectory(prefix="aivitals-")
        ok = True
        try:
            import subprocess
            subprocess.run(["git", "clone", "--depth", "1", target, f"{tmp.name}/repo"],
                           check=True, capture_output=True, timeout=180)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            ok = False
            raise SystemExit(f"clone 失败：{e}\n提示：可先本地 clone，再用路径扫描。")
        finally:
            if not ok:
                tmp.cleanup()
        return Path(tmp.name) / "repo", tmp
    p = Path(target).expanduser()
    if not p.exists():
        raise SystemExit(f"路径不存在：{p}")
    return p, None


def cmd_scan(args: argparse.Namespace) -> int:
    root, tmp = _ingest(args.target)
    try:
        checks, errs = rules.load(Path(args.checks))
        if errs:
            for e in errs:
                print(f"[rules] {e}", file=sys.stderr)
        if not checks:
            raise SystemExit("没有可用规则")
        profile, files = prof.build(root)
        if args.maturity:
            profile.maturity = args.maturity
        result = detect.run_checks(profile, files, checks, layer_names())

        outdir = Path(args.out).expanduser()
        outdir.mkdir(parents=True, exist_ok=True)
        formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]
        written = []
        if "json" in formats:
            p = outdir / "report.json"
            p.write_text(json.dumps(report.to_json(result), ensure_ascii=False, indent=1), encoding="utf-8")
            written.append(p)
        if "md" in formats or "markdown" in formats:
            p = outdir / "report.md"
            p.write_text(report.to_markdown(result), encoding="utf-8")
            written.append(p)
        if "sarif" in formats:
            p = outdir / "report.sarif"
            p.write_text(json.dumps(report.to_sarif(result), ensure_ascii=False, indent=1), encoding="utf-8")
            written.append(p)
        if "html" in formats:
            p = outdir / "report.html"
            p.write_text(report.to_html(result), encoding="utf-8")
            written.append(p)

        s = report.summary(result)
        print(f"AIVitals · {profile.root}")
        print(f"  类型 {profile.repo_type} / 档位 {profile.maturity} / {profile.file_count} 文件 / {profile.loc} 行")
        print(f"  P0 {s['p0']} · P1 {s['p1']} · 已检查 {s['layers_checked']}/17 层 · 总体 {s['overall']}")
        for f in result.findings[:5]:
            print(f"  [{f.severity}] {f.title}  ({f.check_id})")
        if len(result.findings) > 5:
            print(f"  … 另有 {len(result.findings) - 5} 条")
        print("  输出：" + ", ".join(str(p) for p in written))

        if args.fail_on:
            order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            threshold = order[args.fail_on]
            hits = [f for f in result.findings if order[f.severity] <= threshold]
            return 2 if args.fail_on == "P0" and hits else (1 if hits else 0)
        return 0
    finally:
        if tmp is not None:
            if args.keep_clone:
                print(f"[clone 保留] {root}", file=sys.stderr)
                tmp.cleanup = lambda: None  # type: ignore[method-assign]
            else:
                tmp.cleanup()


def cmd_checks(args: argparse.Namespace) -> int:
    checks, errs = rules.load(Path(args.checks))
    for e in errs:
        print(f"[err] {e}", file=sys.stderr)
    print(f"{len(checks)} 条规则")
    for c in checks:
        print(f"  {c.id:<14} L{c.layer:<2} {c.severity:<2} {c.kind:<16} gate={c.maturity_gate:<11} {c.title}")
    return 1 if errs else 0


def cmd_eval(args: argparse.Namespace) -> int:
    fixtures = Path(args.fixtures)
    cases = sorted(p for p in fixtures.iterdir() if (p / "expected.json").exists())
    if not cases:
        raise SystemExit(f"没有找到带 expected.json 的样例：{fixtures}")
    checks, errs = rules.load(Path(args.checks))
    if errs:
        for e in errs:
            print(f"[rules] {e}", file=sys.stderr)
    rows = []
    total_expect = total_hit = total_forbid = total_fp = 0
    for case in cases:
        exp = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        profile, files = prof.build(case)
        result = detect.run_checks(profile, files, checks, layer_names())
        got = {f.check_id for f in result.findings}
        expect = set(exp.get("expect", []))
        forbid = set(exp.get("forbid", []))
        hit = len(expect & got)
        fp = len(forbid & got)
        total_expect += len(expect)
        total_hit += hit
        total_forbid += len(forbid)
        total_fp += fp
        recall = hit / len(expect) if expect else 1.0
        rows.append((case.name, len(expect), hit, recall, fp, exp.get("maturity"), profile.maturity))
        if args.verbose:
            miss = sorted(expect - got)
            if miss:
                print(f"  {case.name} 漏报: {miss}")
    print(f"{'样例':<28}{'期望':>5}{'命中':>5}{'召回':>8}{'误报':>6}{'档位(期望/实际)':>18}")
    for name, ne, nh, rc, fp, em, am in rows:
        print(f"{name:<28}{ne:>5}{nh:>5}{rc:>8.2f}{fp:>6}{str(em)+'/'+str(am):>18}")
    recall = total_hit / total_expect if total_expect else 1.0
    print(f"\n汇总 recall={recall:.3f}  false_positive={total_fp}（对照 {total_forbid} 条禁止项）")
    ok = recall >= args.min_recall and total_fp == 0
    print("门禁：" + ("PASS" if ok else "FAIL") + f"（recall≥{args.min_recall} 且 误报=0）")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aivitals", description="AI 项目架构体征检查（本地运行，代码不外出）")
    p.add_argument("--version", action="version", version=f"aivitals {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="扫描一个仓库")
    s.add_argument("target", help="本地路径或 GitHub URL")
    s.add_argument("--checks", default=str(DEFAULT_CHECKS), help="规则目录")
    s.add_argument("--maturity", choices=["prototype", "internal", "production", "multi_tenant"], help="覆盖档位判定")
    s.add_argument("--format", default="md,json,sarif", help="md,json,sarif,html")
    s.add_argument("--out", default="./aivitals-report", help="输出目录")
    s.add_argument("--fail-on", choices=["P0", "P1", "P2", "P3"], help="达到该级别返回非零退出码")
    s.add_argument("--keep-clone", action="store_true", help="保留临时 clone（调试用）")
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("checks", help="列出规则")
    c.add_argument("--checks", default=str(DEFAULT_CHECKS))
    c.set_defaults(func=cmd_checks)

    e = sub.add_parser("eval", help="用标注样例评测规则")
    e.add_argument("--fixtures", default=str(ROOT / "fixtures"))
    e.add_argument("--checks", default=str(DEFAULT_CHECKS))
    e.add_argument("--min-recall", type=float, default=0.8)
    e.add_argument("--verbose", action="store_true")
    e.set_defaults(func=cmd_eval)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
