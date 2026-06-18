# orchestrate_2

Python AI triage agent scaffold for a 24-hour hackathon.

## Architecture overview

- `agent/agent.py` — OpenAI tool-calling loop (max 3 rounds) with forced JSON output parsing.
- `agent/tools.py` — Tool registry + dispatcher with typed tool responses.
- `agent/schemas.py` — Pydantic structured output model (`action`, `justification`, `evidence`, `confidence`).
- `agent/safety.py` — Deterministic regex safety gates run before any LLM call.
- `retrieval/retriever.py` — Hybrid BM25 + sentence-transformer + FAISS retrieval for markdown knowledge.
- `prompts/system.py` — Strict JSON system prompt contract.
- `main.py` — Typer CLI entrypoint.

## Project structure

```
.
├── agent/
├── prompts/
├── retrieval/
├── tests/
├── main.py
├── requirements.txt
└── .env.example
```

## How to run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy and configure env vars:
   ```bash
   cp .env.example .env
   ```
3. Add markdown files under a folder (default: `knowledge/`).
4. Run the CLI:
   ```bash
   python main.py run "Summarize the highest-priority issue"
   ```
