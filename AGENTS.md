# agent-skills

This repository stores reusable agent skills. Each top-level directory should be a self-contained skill package with a `SKILL.md` entry point and only the resources needed for that skill to work.

## Current Skills

- `opc-idea-miner/`: Python CLI skill for mining public product/startup idea signals and generating OPC/solo-founder opportunity reports.

## Skill Authoring Rules

- Keep every skill self-contained in its own top-level directory.
- Put the skill trigger, workflow, and concise operating notes in `SKILL.md`.
- Put executable helpers in `scripts/`, templates in `templates/`, reusable non-context assets in `assets/`, and longer optional references in `references/`.
- Avoid committing generated runtime output unless it is an intentional sample fixture.
- Do not store secrets, API tokens, private configs, or local environment files in the repo.
- Prefer example config files such as `config.example.yaml`; local configs should be ignored.

## `opc-idea-miner` Notes

- Main entry: `opc-idea-miner/scripts/opc_idea_miner.py`.
- Example config: `opc-idea-miner/config.example.yaml`.
- Report template: `opc-idea-miner/templates/report.md.j2`.
- Intentional sample outputs may live in `opc-idea-miner/reports/sample_report.*`; other generated report files should stay untracked.

## Validation

- For CLI changes, run the no-network smoke test from `opc-idea-miner/`:
  `python scripts/opc_idea_miner.py run --sample --out reports/sample_report.md --json-out reports/sample_report.json`
- If dependencies are missing, create a local virtualenv and install `requirements.txt`; do not commit `.venv/`.

