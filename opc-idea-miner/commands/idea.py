#!/usr/bin/env python3
"""Skill command executor for /idea."""

from __future__ import annotations

import json
import os
import shlex
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def resolve_skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def venv_dir() -> Path:
    override = os.environ.get("OPC_IDEA_MINER_VENV")
    if override:
        return Path(override).expanduser()
    return Path(tempfile.gettempdir()) / "cli-claw-opc-idea-miner-venv"


def venv_python() -> Path:
    root = venv_dir()
    if sys.platform == "win32":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def venv_pip() -> Path:
    root = venv_dir()
    if sys.platform == "win32":
        return root / "Scripts" / "pip.exe"
    return root / "bin" / "pip"


def bootstrap_command(skill_dir: Path) -> str:
    return (
        f"cd {shlex.quote(str(skill_dir))} && "
        f"python -m venv {shlex.quote(str(venv_dir()))} && "
        f"{shlex.quote(str(venv_pip()))} install -r requirements.txt"
    )


def shell_command(skill_dir: Path, topic: str) -> str:
    python_path = venv_python()
    topic_args = f" --topic {shlex.quote(topic)}" if topic else ""
    return (
        f"cd {shlex.quote(str(skill_dir))} && "
        f"{shlex.quote(str(python_path))} scripts/opc_idea_miner.py run "
        "--config config.example.yaml --json-stdout --no-report --top 3"
        f"{topic_args}"
    )


def build_prompt(payload: dict[str, Any]) -> str:
    skill_dir = resolve_skill_dir()
    workspace = payload.get("workspace") if isinstance(payload, dict) else {}
    if not isinstance(workspace, dict):
        workspace = {}
    workspace_name = workspace.get("name") or workspace.get("folder") or "当前工作区"
    args_text = str(payload.get("argsText") or "").strip()
    issued_at = str(payload.get("issuedAt") or datetime.now(timezone.utc).isoformat())
    focus_line = (
        f"- 用户给定关注方向：{args_text}。必须通过 CLI 的 `--topic` 注入采集配置。"
        if args_text
        else "- 用户未指定细分方向；按 OPC/solo-founder 友好度自动发现 broad opportunity pool。"
    )

    return f"""这是由 opc-idea-miner skill 的 /idea 触发的 OPC/solo-founder 产品机会挖掘任务，当前工作区为：{workspace_name}。

触发信息
- 命令：/idea
- 触发时间：{issued_at}
{focus_line}

执行要求
- 只做 channel 回复，不输出或引用本地报告文件路径。
- 必须使用 opc-idea-miner skill 目录内的 CLI，不要把采集/评分逻辑重写到当前工作区。
- 依赖预检：如果缓存 venv Python 不存在或缺依赖，先运行：`{bootstrap_command(skill_dir)}`。
- 然后运行并读取 stdout JSON：`{shell_command(skill_dir, args_text)}`。
- CLI stdout 必须是 `schema=opc_idea_miner.v1` 的强约束 JSON；最终回复只能基于 JSON 的 `top_opportunities`、`evidence`、`skipped_sources` 和 `summary_contract`。
- 如果 `PRODUCTHUNT_TOKEN` 或 `GITHUB_TOKEN` 不存在，继续使用其他公开来源，并按 JSON 的 `skipped_sources` 简短说明降级。
- 不要给投资建议或确定性成功判断；评分只表达启发式优先级。

固定输出模板
**OPC 产品机会｜{args_text or "自动发现"}**
----
**💡 关键结论**
- 用 1-2 条 bullet 总结最值得做的方向和最大约束。

**📌 Top 3**
**1｜机会名｜评分**
💡 机会：一句话说明产品切口
👤 用户/痛点：目标用户 + 高频痛点
🔥 信号/为什么现在：证据来源混合 + why_now
🧪 7天验证：mvp_7d 或 validation_plan 的最短动作
⚠️ 风险：最大风险

**数据降级**
- 仅当 skipped_sources 非空时输出一行。
"""


def main() -> None:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        payload = {}
    emit(
        {
            "reply": {
                "type": "assistant_prompt",
                "content": build_prompt(payload),
                "ack": "已开始挖掘 OPC/solo-founder 产品机会，完成后直接在当前 channel 返回 Top 3。",
            }
        }
    )


if __name__ == "__main__":
    main()
