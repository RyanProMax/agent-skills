from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
COMMANDS_JSON = SKILL_DIR / "commands.json"
IDEA_EXECUTOR = SKILL_DIR / "commands" / "idea.py"


class IdeaCommandTests(unittest.TestCase):
    def test_commands_manifest_registers_idea_for_im_and_web(self) -> None:
        manifest = json.loads(COMMANDS_JSON.read_text(encoding="utf-8"))

        command = manifest["commands"]["idea"]

        self.assertEqual(command["description"], "挖掘 OPC/solo-founder 产品机会并生成分析报告")
        self.assertEqual(command["entrypoints"], ["im", "web"])
        self.assertEqual(command["executor"], {"command": "python3", "args": ["commands/idea.py"]})

    def test_executor_returns_assistant_prompt_with_cli_run_instructions(self) -> None:
        payload = {
            "version": 1,
            "command": "idea",
            "entrypoint": "im",
            "chatJid": "feishu:chat-1",
            "argsText": "AI agent for local services",
            "args": ["AI", "agent", "for", "local", "services"],
            "workspace": {
                "jid": "web:main",
                "folder": "main",
                "name": "主工作区",
            },
            "issuedAt": "2026-04-30T14:55:45.563Z",
        }

        result = subprocess.run(
            [sys.executable, str(IDEA_EXECUTOR)],
            cwd=SKILL_DIR,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        response = json.loads(result.stdout)
        reply = response["reply"]

        self.assertEqual(reply["type"], "assistant_prompt")
        self.assertIn("OPC/solo-founder", reply["ack"])
        self.assertIn("opc-idea-miner", reply["content"])
        self.assertIn("/idea", reply["content"])
        self.assertIn("主工作区", reply["content"])
        self.assertIn("AI agent for local services", reply["content"])
        self.assertIn("python scripts/opc_idea_miner.py run", reply["content"])
        self.assertIn("--config config.example.yaml", reply["content"])
        self.assertIn("--json-stdout", reply["content"])
        self.assertIn("--no-report", reply["content"])
        self.assertIn("--topic", reply["content"])
        self.assertIn("Top 3", reply["content"])


if __name__ == "__main__":
    unittest.main()

class IdeaCliJsonModeTests(unittest.TestCase):
    def test_cli_outputs_strict_json_without_report_files_and_injects_topic(self) -> None:
        result = subprocess.run(
            [
                str(SKILL_DIR / ".venv" / "bin" / "python"),
                str(SKILL_DIR / "scripts" / "opc_idea_miner.py"),
                "run",
                "--sample",
                "--topic",
                "AI agent for local services",
                "--json-stdout",
                "--no-report",
                "--top",
                "3",
            ],
            cwd=SKILL_DIR,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "opc_idea_miner.v1")
        self.assertEqual(payload["focus"], "AI agent for local services")
        self.assertIn("AI agent for local services", payload["config"]["seed_topics"][:1])
        self.assertLessEqual(len(payload["top_opportunities"]), 3)
        self.assertIn("skipped_sources", payload)
        self.assertIn("summary_contract", payload)
        self.assertFalse((SKILL_DIR / "reports" / "opc_ideas.md").exists())

    def test_idea_executor_uses_channel_reply_json_contract(self) -> None:
        payload = {
            "version": 1,
            "command": "idea",
            "entrypoint": "im",
            "argsText": "AI agent for local services",
            "workspace": {"name": "主工作区", "folder": "main"},
            "issuedAt": "2026-05-02T04:34:45.898Z",
        }

        result = subprocess.run(
            [sys.executable, str(IDEA_EXECUTOR)],
            cwd=SKILL_DIR,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        reply = json.loads(result.stdout)["reply"]

        self.assertIn("--json-stdout", reply["content"])
        self.assertIn("--no-report", reply["content"])
        self.assertIn("--topic", reply["content"])
        self.assertNotIn("--out reports/idea_report.md", reply["content"])
        self.assertIn("💡 机会", reply["content"])
        self.assertIn("🧪 7天验证", reply["content"])
