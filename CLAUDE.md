# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

1. Copy `.env.example` to `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-...
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running

```bash
python core/orchestrator.py "<Company Name>"
```

Output is saved as a markdown file in `output/`. Example:

```bash
python core/orchestrator.py "Stripe"
# → output/Stripe_brief.md
```

## Architecture

This project is a skill-based AI orchestration system. The orchestrator loads a config, selects the active skill, and delegates work to it.

**Entry point:** `core/orchestrator.py`
- Reads `config.json` to determine the active skill
- Accepts a company name via `argparse`
- Dynamically imports the skill module with `importlib`
- Calls `skill.run(company_name, output_dir)` and prints the result path

**Skill contract:** Every skill module in `skills/` must expose:
```python
def run(company_name: str, output_dir: Path) -> Path:
    ...  # returns the path of the file it wrote
```

**Adding a new skill:**
1. Create `skills/<skill_name>.py` implementing `run(company_name, output_dir)`
2. Add an entry under `"skills"` in `config.json`
3. Set `"active_skill"` in `config.json` to your new skill key

**Current skills:**
- `account_intel` — Calls Claude (Opus 4.6, adaptive thinking, streaming) to generate a pre-call research brief with seven sections: Company Overview, Recent News, Tech Stack, Pain Points, Decision Makers, Talking Points, and Red Flags. Output is a timestamped markdown file.

## Environment

- Platform: Windows 11, shell: bash (use Unix-style paths and syntax)
- `.env` is gitignored — never commit real API keys
