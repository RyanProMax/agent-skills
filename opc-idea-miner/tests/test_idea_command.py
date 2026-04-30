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
        self.assertIn("--out reports/idea_report.md", reply["content"])
        self.assertIn("--json-out reports/idea_report.json", reply["content"])
        self.assertIn("top 3", reply["content"])


if __name__ == "__main__":
    unittest.main()
