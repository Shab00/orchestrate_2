# Evaluation Report

**Run timestamp:** 2026-06-19 14:01:25  
**Total samples:** 20  
**Elapsed time:** 110.2s  
**Overall accuracy (all fields correct):** 60.0%  

## Per-Field Accuracy

| Field | Correct | Total | Accuracy |
|-------|---------|-------|----------|
| evidence_standard_met | 19 | 20 | 95.0% |
| claim_status | 17 | 20 | 85.0% |
| issue_type | 14 | 20 | 70.0% |
| object_part | 18 | 20 | 90.0% |
| severity | 15 | 20 | 75.0% |
| valid_image | 19 | 20 | 95.0% |

## Failed Cases

| user_id | Field | Predicted | Expected |
|---------|-------|-----------|----------|
| user_005 | issue_type | none | scratch |
| user_005 | severity | none | low |
| user_006 | valid_image | false | true |
| user_008 | evidence_standard_met | false | true |
| user_008 | claim_status | not_enough_information | contradicted |
| user_008 | issue_type | unknown | broken_part |
| user_008 | object_part | hood | front_bumper |
| user_008 | severity | unknown | high |
| user_009 | issue_type | glass_shatter | crack |
| user_009 | severity | high | medium |
| user_011 | issue_type | water_damage | stain |
| user_020 | claim_status | supported | contradicted |
| user_020 | issue_type | scratch | none |
| user_020 | severity | low | none |
| user_031 | object_part | box | package_side |
| user_034 | claim_status | supported | contradicted |
| user_034 | issue_type | torn_packaging | none |
| user_034 | severity | medium | none |