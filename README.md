# style-signal

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-15%20offline%20unittest-green.svg)](./tests)

A pluggable style signal crawler with a Claude Code skill layer.

`style-signal` is an adapter-based Python CLI for collecting public style ranking/search pages, returning normalized JSON, and turning that data into deterministic style signals. The core package currently supports KREAM, Musinsa, and 29CM adapters. The Claude Code skill in this repo can sit on top of that JSON and generate an editorial HTML report from natural-language Korean prompts.

한국어 요약: KREAM, Musinsa, 29CM 랭킹/검색 데이터를 공통 JSON으로 수집하는 공개 패션 트렌드 CLI이며, Claude Code 스킬 레이어를 통해 자연어 요청 기반 HTML 리포트까지 자동화할 수 있습니다.

## Project Status

| Area | Status | Notes |
| --- | --- | --- |
| CLI | Implemented | `list-sources`, `describe`, `fetch`, `signal` |
| Output contract | Implemented | Stable JSON to stdout; exit code signals success/failure |
| Ready adapters | Implemented | `kream`, `musinsa`, `29cm` |
| Stub adapters | Scaffolded | `ssense`, `farfetch`, `grailed`, `styleshare` return clear TODO errors |
| Fetching | Implemented | Scrapling `stealthy-fetch`, block detection, optional one-time retry |
| Style signal analysis | Implemented | Brand frequency, price-band balance, source guard, evidence manifest |
| Tests | Implemented | 15 offline `unittest` cases; no network calls in test suite |
| Claude Code skill | Implemented | Natural-language workflow in [`SKILL.md`](./SKILL.md) |
| Static HTML `report` command | Planned | Spec/backlog only; not a core CLI command yet |
| Vision/style tagging | Planned | See [`docs/PHASE2_VISION_TAGGING.md`](./docs/PHASE2_VISION_TAGGING.md) |
| SQLite trend store/query | Planned | See [`docs/PHASE3_TIMESERIES_API.md`](./docs/PHASE3_TIMESERIES_API.md) |
| FastAPI server | Planned | Depends on the SQLite query layer |

## Quick Start

```bash
git clone https://github.com/beyondfashion-ai/style-signal.git
cd style-signal

python -m venv .venv
source .venv/bin/activate

pip install -e .
scrapling install
```

List available sources:

```bash
style-signal list-sources
```

Describe a source:

```bash
style-signal describe --source kream
```

Fetch a KREAM Top 100 ranking as JSON:

```bash
style-signal fetch \
  --source kream \
  --curation top100 \
  --gender men \
  --sort popular \
  --limit 40 \
  --retry-on-block
```

Build a deterministic style-signal summary from saved fetch JSON:

```bash
mkdir -p artifacts

style-signal fetch \
  --source kream \
  --curation top100 \
  --gender men \
  --limit 40 \
  > artifacts/kream-result.json

style-signal signal \
  --input artifacts/kream-result.json \
  --manifest-output artifacts/kream-result.manifest.json
```

The same commands can also be run through the module entrypoint:

```bash
python -m style_signal list-sources
python -m style_signal describe --source musinsa
python -m style_signal fetch --source 29cm --keyword sneakers --limit 20
```

`fetch` writes normalized JSON to stdout. If `--raw-output` is omitted, fetched markdown is stored under `artifacts/<source>-result.md` for debugging. `signal` reads that JSON and returns brand signals, price-band balance, source-quality scores, and an evidence manifest hash.

## Use As A Claude Code Skill

Claude Code users can install this repository as a skill and use natural-language Korean prompts such as:

```text
요즘 인기있는 남성신발 알려줘
KREAM에서 여자 가방 인기순 보여줘
남자 스니커즈 트렌드 리포트 만들어줘
요즘 뭐가 인기야
```

Global skill install:

```bash
git clone https://github.com/beyondfashion-ai/style-signal.git ~/.claude/skills/style-signal
```

Project-local skill install:

```bash
mkdir -p .claude/skills
git clone https://github.com/beyondfashion-ai/style-signal.git .claude/skills/style-signal
```

Restart Claude Code or open a new session after installation.

Important distinction: the Python package currently exposes data collection commands only. HTML report generation happens in the Claude Code skill workflow (`SKILL.md` Step 5), where the agent reads the JSON output and writes the report. A standalone dependency-free `report` CLI command is planned but not implemented yet.

## Supported Sources

| Source | Status | Current capability |
| --- | --- | --- |
| KREAM | ready | Top 100 curation, gender/sort options, product parsing |
| Musinsa | ready | Ranking/search URL building and product parsing |
| 29CM | ready | Search URL building and product parsing |
| SSENSE | stub | Adapter scaffold only |
| Farfetch | stub | Adapter scaffold only |
| Grailed | stub | Adapter scaffold only |
| StyleShare | stub | Adapter scaffold only |

Use `style-signal describe --source <name>` to inspect the supported options for each adapter.

## Architecture

The core package separates source-specific behavior behind a common `SourceAdapter` interface:

```text
src/style_signal/
├── cli.py                  # argparse commands and JSON output
├── fetcher.py              # Scrapling wrapper
├── registry.py             # source name -> adapter class
├── schema.py               # Query, Product, FetchResult
├── signals.py              # deterministic style-signal scoring + manifest
└── sources/
    ├── base.py             # SourceAdapter contract
    ├── kream/
    ├── musinsa/
    ├── twentyninecm/
    ├── ssense/
    ├── farfetch/
    ├── grailed/
    └── styleshare/
```

To add a source, create `src/style_signal/sources/<name>/adapter.py`, implement URL building, block detection, and markdown parsing, then register the adapter in `registry.py`. See [`docs/ADAPTERS.md`](./docs/ADAPTERS.md) for the contribution checklist.

The signal layer borrows the public-safe parts of KALEI's internal trend stack: deterministic brand frequency, source-quality gating, score rebalancing, and evidence manifests. It does not copy KALEI private data, Firebase logic, or content-generation workflows. See [`docs/SIGNALS.md`](./docs/SIGNALS.md).

## Development

Run the offline test suite:

```bash
python -m unittest discover tests
```

Inspect the local registry:

```bash
PYTHONPATH=src python -m style_signal list-sources
PYTHONPATH=src python -m style_signal describe --source kream
```

The test suite must stay offline. Parser tests should use synthetic or recorded markdown fixtures under `tests/fixtures/`.

## Roadmap

The public roadmap is intentionally narrow and free-source friendly:

| Phase | Scope | Document |
| --- | --- | --- |
| Phase 1 | Multi-source adapter architecture | [`docs/PHASE1_REFACTOR_PLAN.md`](./docs/PHASE1_REFACTOR_PLAN.md) |
| Phase 2 | Optional Gemini vision/style tagging | [`docs/PHASE2_VISION_TAGGING.md`](./docs/PHASE2_VISION_TAGGING.md) |
| Phase 3 | SQLite snapshots, trend queries, optional FastAPI | [`docs/PHASE3_TIMESERIES_API.md`](./docs/PHASE3_TIMESERIES_API.md) |

Near-term backlog:

1. Clean OSS metadata and docs for the independent `beyondfashion-ai/style-signal` repo.
2. Add a dependency-free `report` command that renders static HTML from fetch JSON.
3. Add SQLite snapshot storage and `query rising-brands` before introducing an API server.
4. Extend the KALEI-inspired signal layer with SQLite historical comparison and rising-brand queries.
5. Promote one global stub adapter, likely `ssense`, to ready status.

See [`docs/NEXT_DEVELOPMENT.md`](./docs/NEXT_DEVELOPMENT.md) and [`docs/OPENSOURCE_ROADMAP.md`](./docs/OPENSOURCE_ROADMAP.md) for the working backlog.

## Data Ethics And Disclaimer

This project is intended for personal learning, research, and open-source tooling experiments.

- Follow each target site's Terms of Service, robots.txt, rate limits, and applicable law.
- Do not run high-volume or abusive scraping workloads.
- Store image URLs only; do not redistribute image bytes or product media assets.
- Generated reports or datasets may include third-party brands, product names, images, prices, and links owned by their respective rightsholders.
- The code is MIT licensed. Data artifacts are licensed separately under [`DATA_LICENSE`](./DATA_LICENSE).
- Additional scraping and source-use notices live in [`NOTICE`](./NOTICE).

In short: use this as a responsible research tool, not as a way to republish or commercialize scraped third-party content.

## Requirements

- Python 3.11+
- macOS or Linux
- `pip`
- Scrapling and Playwright browsers (`pip install -e .` plus `scrapling install`)
- Claude Code CLI only if you want to use the skill workflow

Windows is not currently tested.

## License

Code is licensed under [MIT](./LICENSE).

## Credits

- [Scrapling](https://github.com/D4Vinci/Scrapling) for browser-backed fetching.
- [Claude Code](https://claude.com/claude-code) for the optional skill workflow.
