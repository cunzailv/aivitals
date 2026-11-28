"""工作流：把 CLI 动作按顺序编排成一条可复跑的命令。

工作流不是新的执行引擎，它只是把 `scan` / `claims` 这些已验证的动作串起来，
所以每条步骤都能单独复现、退出码也照旧。真正需要判断的部分（改代码、取舍）
仍然交给智能体（agents/）和用户。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml


def load_all(directory: Path) -> list[dict]:
    out: list[dict] = []
    for p in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and data.get("steps"):
            data["_path"] = str(p)
            data.setdefault("name", p.stem)
            out.append(data)
    return out


def find(directory: Path, name: str) -> dict | None:
    for wf in load_all(directory):
        if wf.get("name") == name or Path(wf["_path"]).stem == name:
            return wf
    return None


def build_command(step: dict, checks: Path | None) -> list[str]:
    action = step.get("run", "scan")
    cmd = [sys.executable, "-m", "aivitals.cli", action]
    opts = dict(step.get("with") or {})
    target = opts.pop("target", None)
    if target is not None:
        cmd.append(str(target))
    for key, value in opts.items():
        flag = "--" + key.replace("_", "-")
        if value is True:
            cmd.append(flag)
        elif value is False or value is None:
            continue
        else:
            cmd += [flag, str(value)]
    if checks and action == "scan":
        cmd += ["--checks", str(checks)]
    return cmd


def run(wf: dict, root: Path, checks: Path | None = None, echo=print) -> int:
    steps = wf.get("steps") or []
    echo(f"工作流 {wf.get('name')} · {len(steps)} 步 · {wf.get('description', '')}")
    last_code = 0
    for i, step in enumerate(steps, 1):
        cmd = build_command(step, checks)
        echo(f"▶ [{i}/{len(steps)}] {step.get('id', '-')} · {' '.join(cmd[3:])}")
        env = dict(os.environ)
        pkg_root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = pkg_root + ((":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
        proc = subprocess.run(cmd, cwd=str(root), env=env)
        last_code = proc.returncode
        if proc.returncode != 0:
            if step.get("continue_on_error"):
                echo(f"  ↳ 退出码 {proc.returncode}，按配置继续")
                continue
            echo(f"  ↳ 退出码 {proc.returncode}，工作流中止")
            return proc.returncode
    echo(f"工作流 {wf.get('name')} 结束，退出码 {last_code}")
    return last_code
