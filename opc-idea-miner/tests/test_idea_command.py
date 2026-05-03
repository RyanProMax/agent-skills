from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
COMMANDS_JSON = SKILL_DIR / "commands.json"
IDEA_EXECUTOR = SKILL_DIR / "commands" / "idea.py"
TEST_PYTHON = os.environ.get("OPC_IDEA_MINER_TEST_PYTHON", sys.executable)


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

    def test_direct_file_execution_discovers_cli_json_tests(self) -> None:
        if os.environ.get("OPC_IDEA_MINER_DIRECT_RUN_CHECK") == "1":
            return

        env = {**os.environ, "OPC_IDEA_MINER_DIRECT_RUN_CHECK": "1"}
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "-v"],
            cwd=SKILL_DIR,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("test_cli_outputs_strict_json_without_report_files_and_injects_topic", result.stderr)

    def test_executor_uses_requirements_hash_cache_path(self) -> None:
        result = subprocess.run(
            [sys.executable, str(IDEA_EXECUTOR)],
            cwd=SKILL_DIR,
            input=json.dumps({"argsText": "AI agent"}),
            text=True,
            capture_output=True,
            check=True,
        )
        content = json.loads(result.stdout)["reply"]["content"]

        self.assertIn("cli-claw-opc-idea-miner-venv-", content)


class IdeaCliJsonModeTests(unittest.TestCase):
    def test_cli_outputs_strict_json_without_report_files_and_injects_topic(self) -> None:
        result = subprocess.run(
            [
                TEST_PYTHON,
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


    def test_cli_channel_payload_includes_markdown_quality_and_chinese_focus(self) -> None:
        result = subprocess.run(
            [
                TEST_PYTHON,
                str(SKILL_DIR / "scripts" / "opc_idea_miner.py"),
                "run",
                "--sample",
                "--topic",
                "教育 Chrome 插件",
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

        self.assertIn("channel_markdown", payload)
        self.assertIn("**OPC 产品机会｜教育 Chrome 插件**", payload["channel_markdown"])
        self.assertIn("data_quality", payload)
        self.assertIn("overall", payload["data_quality"])
        self.assertIn("data_quality_note", payload)
        self.assertIn("evidence_quality", payload["top_opportunities"][0])
        self.assertIn("evidence_strength", payload["top_opportunities"][0]["evidence"][0])
        self.assertGreater(payload["top_opportunities"][0]["focus_relevance"], 0)
        self.assertTrue(
            any(
                "Chrome" in opportunity["title"] or "插件" in opportunity["title"]
                for opportunity in payload["top_opportunities"]
            )
        )

    def test_cli_respects_global_time_budget_when_sources_are_enabled(self) -> None:
        result = subprocess.run(
            [
                TEST_PYTHON,
                str(SKILL_DIR / "scripts" / "opc_idea_miner.py"),
                "run",
                "--config",
                "config.example.yaml",
                "--topic",
                "developer tools",
                "--json-stdout",
                "--no-report",
                "--top",
                "3",
                "--global-timeout",
                "0.001",
            ],
            cwd=SKILL_DIR,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)

        self.assertIn("time_budget_exceeded", payload["skipped_sources"])
        self.assertIn("data_quality_note", payload)


    def test_quality_fixtures_rank_chinese_focus_topics(self) -> None:
        cases = [
            ("教育 SaaS", "可访问性/学习辅助 Chrome 插件"),
            ("AI 销售 CRM", "垂直工作流 AI Agent"),
            ("出海工具", "开发者效率工具"),
            ("电商导购", "电商售前导购"),
        ]

        for topic, expected_title_part in cases:
            with self.subTest(topic=topic):
                result = subprocess.run(
                    [
                        TEST_PYTHON,
                        str(SKILL_DIR / "scripts" / "opc_idea_miner.py"),
                        "run",
                        "--sample",
                        "--topic",
                        topic,
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

                self.assertIn(expected_title_part, payload["top_opportunities"][0]["title"])
                self.assertGreater(payload["top_opportunities"][0]["focus_relevance"], 0)

    def test_weak_data_does_not_force_three_opportunities(self) -> None:
        result = subprocess.run(
            [
                TEST_PYTHON,
                str(SKILL_DIR / "scripts" / "opc_idea_miner.py"),
                "run",
                "--empty-sample",
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

        self.assertEqual(payload["data_quality"]["overall"], "weak")
        self.assertEqual(payload["top_opportunities"], [])
        self.assertIn("当前数据不足", payload["channel_markdown"])
        self.assertIn("建议放宽方向", payload["channel_markdown"])

    def test_topic_relevance_can_change_top_rank(self) -> None:
        result = subprocess.run(
            [
                TEST_PYTHON,
                str(SKILL_DIR / "scripts" / "opc_idea_miner.py"),
                "run",
                "--sample",
                "--topic",
                "accessibility Chrome extension",
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

        self.assertIn("Chrome", payload["top_opportunities"][0]["title"])


if __name__ == "__main__":
    unittest.main()
