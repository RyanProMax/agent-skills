#!/usr/bin/env python3
"""Skill command executor for /idea."""

from __future__ import annotations

import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_MD = "reports/idea_report.md"
REPORT_JSON = "reports/idea_report.json"


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def resolve_skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def shell_command(skill_dir: Path) -> str:
    return (
        f"cd {shlex.quote(str(skill_dir))} && "
        "python scripts/opc_idea_miner.py run "
        f"--config config.example.yaml --out {REPORT_MD} --json-out {REPORT_JSON}"
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
        f"- 用户给定关注方向：{args_text}。请用它校准机会筛选、排序和最终 top 3。"
        if args_text
        else "- 用户未指定细分方向；请按 OPC/solo-founder 友好度自动发现 broad opportunity pool。"
    )

    return f"""这是由 opc-idea-miner skill 的 /idea 触发的 OPC/solo-founder 产品机会挖掘任务，当前工作区为：{workspace_name}。

触发信息
- 命令：/idea
- 触发时间：{issued_at}
{focus_line}

执行要求
- 必须使用 opc-idea-miner skill 目录内的 CLI，不要把逻辑重写到当前工作区。
- 先进入 skill 目录，再运行：`{shell_command(skill_dir)}`。
- 如果缺少 Python 依赖，先在 skill 目录创建 `.venv` 并安装 `requirements.txt`，然后用同一命令重试；不要提交 `.venv`。
- 如果 `PRODUCTHUNT_TOKEN` 或 `GITHUB_TOKEN` 不存在，继续使用其他公开来源，并在结果中简短说明跳过或降级的数据源。
- 如果用户给了关注方向，CLI 仍可先跑默认配置；最终报告必须把关注方向作为排序和取舍依据。
- 输出必须基于生成的 Markdown 和 JSON evidence，不要凭空发散。

输出格式
- 先给一句总览：报告已生成到 `{REPORT_MD}`，证据 JSON 在 `{REPORT_JSON}`。
- 然后列 top 3 ideas，每个 idea 最多 4 行：机会名、目标用户/痛点、为什么现在、MVP/验证动作。
- 最后列 skipped/degraded sources（如有），保持简短。
- 不要给投资建议或确定性成功判断；把评分表述为启发式优先级。
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
                "ack": "已开始挖掘 OPC/solo-founder 产品机会，完成后返回报告路径和 top 3 ideas。",
            }
        }
    )


if __name__ == "__main__":
    main()
