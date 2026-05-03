---
name: opc-idea-miner
description: Use this skill when the user wants to discover one-person-company, side-business, solo-founder, or startup product ideas from fresh public signals, generate an OPC opportunity report, or invoke /idea.
---

# OPC Idea Miner Skill

Use this skill when the user wants to discover side-business / one-person-company product ideas from fresh public signals and produce a fixed-template startup product analysis report.

## What this skill does

1. Collects public product/inspiration signals from sources such as:
   - Hacker News Algolia search
   - GitHub repository search / trending-like repository signals
   - Product Hunt API v2 GraphQL, when `PRODUCTHUNT_TOKEN` is available
   - Devpost software and hackathon project-gallery pages
   - YC Requests for Startups
   - Hugging Face public trending endpoints, best-effort
   - Optional GDELT news heat
2. Normalizes signals into one schema.
3. Deduplicates and clusters signals by product opportunity category.
4. Scores each opportunity by heat, pain, OPC fit, MVP speed, defensibility, and novelty.
5. Writes a fixed-template Markdown report and a JSON evidence file.

## Slash command

`/idea [optional focus]` runs this skill through Cli Claw skill-command dispatch. It rewrites the slash command into an isolated `assistant_prompt` task that instructs the agent to run `scripts/opc_idea_miner.py` with `--topic`, `--json-stdout`, `--no-report`, fast source limits, and zero request retries for channel responsiveness; the JSON includes `channel_markdown`, `data_quality`, `data_quality_note`, `collection_metrics`, and per-evidence strength labels. The agent should preserve `channel_markdown` unless it must compress, and must not add opportunities outside `top_opportunities`.

## One-command CLI

From this skill directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/opc_idea_miner.py run \
  --config config.example.yaml \
  --out reports/opc_ideas.md \
  --json-out reports/opc_ideas.json
```

Optional environment variables:

```bash
export PRODUCTHUNT_TOKEN="..."  # Product Hunt API v2 token
export GITHUB_TOKEN="..."       # Higher GitHub API rate limits
```

For a no-network smoke test:

```bash
python scripts/opc_idea_miner.py run --sample --out reports/sample_report.md --json-out reports/sample_report.json
```

## Agent operating notes

- If the user invokes `/idea`, run the JSON stdout flow and reply in-channel with `channel_markdown`; do not return local report paths.
- 中文 focus（如 `教育 SaaS`、`AI 销售 CRM`、`出海工具`、`电商导购`）应影响 Top 3 排序；弱数据时保守说明数据不足，不要硬凑机会。
- 需要判断采集慢源/失败源时查看 JSON 的 `collection_metrics`，里面包含 source、status、duration_ms、signal_count 和 error。
- If Product Hunt credentials are missing, keep going with other sources and mention the skipped source.
- Avoid scraping sources that forbid it; prefer official APIs when available.
- Treat scoring as a prioritization heuristic, not investment advice.
- For an OPC/solo founder user, penalize ideas with heavy regulation, hardware dependency, multi-sided marketplaces, or enterprise sales cycles longer than 90 days.
