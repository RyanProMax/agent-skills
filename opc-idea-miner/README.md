# OPC Idea Miner

OPC Idea Miner is a small CLI + agent skill that mines public innovation signals and produces a fixed-template startup product analysis report for solo developers / one-person-company builders.

## Quick start

```bash
cd opc-idea-miner-skill
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/opc_idea_miner.py run --config config.example.yaml --out reports/opc_ideas.md --json-out reports/opc_ideas.json
```

No-network smoke test:

```bash
python scripts/opc_idea_miner.py run --sample --out reports/sample_report.md --json-out reports/sample_report.json
```

## Data sources

- Hacker News via Algolia API
- GitHub Search API
- Product Hunt API v2 GraphQL, if `PRODUCTHUNT_TOKEN` is set
- Devpost software search and hackathon project-gallery URLs
- YC Requests for Startups
- Hugging Face trending endpoints, best-effort
- Optional GDELT DOC API heat checks

## Outputs

- Markdown report: fixed template for product opportunity analysis
- JSON file: normalized raw signals, clustered opportunities, skipped sources, config snapshot

## Notes

This tool uses public data sources and lightweight heuristics. It is designed for idea discovery and prioritization, not as proof of market demand. Always validate with real users before building.
