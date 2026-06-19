# claims/

This directory holds all data files used by the damage claim verification agent.

## Required files

Place the following files here before running the agent:

| File | Description |
|------|-------------|
| `claims.csv` | Input claims to process (user_id, image_paths, user_claim, claim_object) |
| `sample_claims.csv` | Labeled examples with expected outputs (used for evaluation) |
| `user_history.csv` | Historical claim counts and risk patterns per user |
| `evidence_requirements.csv` | Minimum image evidence checklist by object/issue type |

## Images

Images referenced in the CSVs use paths like `images/test/case_001/img_1.jpg`.

Place image folders directly inside this `claims/` directory so the full path is:

```
claims/images/test/case_001/img_1.jpg
claims/images/sample/case_001/img_1.jpg
```

## Running the agent

```bash
# Process claims/claims.csv → output.csv
python main.py claims

# Evaluate against sample_claims.csv
python -m evaluation.evaluate
```
