# Damage Claim Verification Agent

Multi-modal AI system that verifies damage claims using GPT-4o vision. Built for the HackerRank Orchestrate 24-hour hackathon.

## What it does

For each claim the agent:
1. Loads submitted images and encodes them as base64 for GPT-4o vision
2. Extracts the damage claim from the user conversation (supports English, Urdu, Hindi)
3. Checks user history for risk context
4. Filters evidence requirements by object type (car / laptop / package)
5. Returns a structured JSON verdict with 9 fields: `evidence_standard_met`, `issue_type`, `object_part`, `claim_status`, `severity`, `valid_image`, `risk_flags`, `supporting_image_ids`, and justifications

## Architecture

```
main.py                    # CLI entry point (typer)
agent/
  claim_agent.py           # GPT-4o vision call + retry logic
  schemas.py               # Pydantic ClaimVerdict model
  safety.py                # Prompt injection gates
prompts/
  system.py                # CLAIM_SYSTEM_PROMPT with few-shot examples
data/
  loader.py                # CSV + image loading utilities
evaluation/
  evaluate.py              # Per-field accuracy + markdown report
claims/
  claims.csv               # Test claims (input)
  sample_claims.csv        # Labelled samples (evaluation)
  user_history.csv         # User risk history
  evidence_requirements.csv# Minimum evidence checklist
  images/                  # Claim images
```

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
```

## Run on test claims → output.csv

```bash
python main.py claims
```

Optional overrides:
```bash
python main.py claims \
  --claims-csv claims/claims.csv \
  --user-history-csv claims/user_history.csv \
  --evidence-csv claims/evidence_requirements.csv \
  --output-csv output.csv
```

## Evaluate against sample_claims.csv

```bash
python -m evaluation.evaluate
```

Outputs:
- `evaluation/sample_predictions.csv` — per-row predictions
- `evaluation/evaluation_report.md` — per-field accuracy + failure table

## Evaluation results

Two strategies were compared:

| Strategy | esm | claim_status | issue_type | object_part | severity | valid_image |
|----------|-----|-------------|------------|-------------|----------|-------------|
| gpt-4o-mini (baseline) | 75% | 65% | 60% | 75% | 55% | 75% |
| **gpt-4o + few-shot (final)** | **95%** | **85%** | **70%** | **90%** | **75%** | **95%** |

### Final strategy: GPT-4o with structured few-shot prompting

- **Model:** `gpt-4o` with `detail: high` image encoding
- **Prompt:** `CLAIM_SYSTEM_PROMPT` in `prompts/system.py` — includes strict field definitions, critical classification rules, and 5 few-shot examples covering the hardest edge cases (broken_part vs crack, glass_shatter vs crack, wrong object, contradicted packaging, multilingual claims)
- **Safety:** Prompt injection detection before any LLM call
- **Retry:** Automatic JSON parse retry + rate-limit backoff
- **Per-claim sleep:** 2s to stay within TPM/RPM limits

### Operational analysis

| Metric | Value |
|--------|-------|
| Model | gpt-4o |
| Images per claim | 1–3 (detail: high) |
| Avg tokens per call | ~1,500 input / ~300 output |
| Approx cost per claim | ~$0.02–0.05 |
| Runtime (20 samples) | ~130s |
| Sleep between calls | 2s |
| Retry on rate limit | 5 attempts, exponential backoff |

## Key design decisions

1. **Images are primary source of truth** — the prompt explicitly forbids inventing damage not visible in images
2. **Few-shot examples** — 5 targeted examples for the highest-confusion pairs (broken_part/crack, glass_shatter/crack, contradicted/none, multilingual scratch)
3. **User language preference** — when the user names a damage type and the image is ambiguous, trust the user
4. **Safety gates** — regex-based prompt injection detection runs before every LLM call
5. **Graceful fallback** — if JSON parsing fails twice, returns a safe `not_enough_information` verdict rather than crashing
