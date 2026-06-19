# Evaluation Report

## Overview

This report summarises the operational costs and performance characteristics of the damage claim verification agent.

---

## Model Calls

| Dataset         | Rows | Calls per Row | Total Calls |
|-----------------|------|---------------|-------------|
| sample_claims   | ~20  | 1 (+ 1 retry) | ~20–40      |
| claims (test)   | ~50  | 1 (+ 1 retry) | ~50–100     |

Each row makes exactly one GPT-4o vision call. A retry is triggered only when the model returns invalid JSON (rare in practice).

---

## Token Usage (approximate)

| Component               | Tokens per Call |
|-------------------------|-----------------|
| System prompt           | ~400 input      |
| User text block         | ~150 input      |
| Evidence requirements   | ~100 input      |
| User history            | ~80 input       |
| Image (per image, ~512px)| ~800 input     |
| Model output            | ~200–400 output |

**Per-claim estimate (2 images):** ~2,330 input + ~300 output = ~2,630 tokens

---

## Images Processed

| Dataset       | Claims | Avg Images/Claim | Total Images |
|---------------|--------|------------------|--------------|
| sample_claims | ~20    | 2                | ~40          |
| claims (test) | ~50    | 2                | ~100         |

---

## Cost Estimate (GPT-4o pricing)

Pricing assumptions (as of mid-2025):
- GPT-4o input: $5.00 / 1M tokens
- GPT-4o output: $15.00 / 1M tokens

| Dataset        | Input Tokens | Output Tokens | Cost       |
|----------------|--------------|---------------|------------|
| sample_claims  | ~46,600      | ~6,000        | ~$0.32     |
| claims (test)  | ~116,500     | ~15,000       | ~$0.81     |
| **Total**      | **~163,100** | **~21,000**   | **~$1.13** |

---

## Latency

| Operation              | Estimated Duration  |
|------------------------|---------------------|
| Per-claim API call     | 3–8 seconds         |
| Sample set (~20 rows)  | ~1.5–3 minutes      |
| Test set (~50 rows)    | ~4–8 minutes        |

A 1-second sleep between calls is applied to stay within rate limits.

---

## TPM / RPM Considerations

- **Rate limit strategy:** 1-second sleep between calls; retry with exponential backoff on 429 errors.
- **TPM usage:** ~2,630 tokens/call × 50 calls ≈ 131,500 tokens for the test set. Well within typical tier-1 limits (e.g. 800K TPM for GPT-4o).
- **RPM usage:** With 1s sleep, effective rate is ~50 RPM — safely below typical 500–3,500 RPM caps.
- **Caching:** During development, responses should be cached (saved as JSON) to avoid repeated API calls. The current implementation does not cache; add caching before heavy testing.
- **Batching:** Each claim is processed sequentially. Parallel processing is possible but adds RPM risk; sequential with sleep is the safest approach.
- **Retry strategy:** On parse failure, one retry is made with an explicit "return only JSON" instruction before falling back to a `not_enough_information` verdict.

---

## Accuracy (sample_claims evaluation)

Run `python -m evaluation.evaluate` to generate per-field accuracy.
Results will be saved to `evaluation/sample_predictions.csv`.

| Field                  | Accuracy |
|------------------------|----------|
| evidence_standard_met  | TBD      |
| claim_status           | TBD      |
| issue_type             | TBD      |
| object_part            | TBD      |
| severity               | TBD      |
| valid_image            | TBD      |

---

## Notes

- Missing images are handled gracefully: the agent returns `not_enough_information` without crashing.
- Text-only claims (no images) are supported via the same fallback path.
- Multilingual claims (Urdu, Hindi, etc.) are handled by GPT-4o's multilingual understanding.
- Prompt injection attempts are blocked before any API call.
