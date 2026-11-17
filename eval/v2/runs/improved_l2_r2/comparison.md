# Run comparison

**Baseline:** `eval/v2/runs/baseline_l2`  
**Candidate:** `eval/v2/runs/improved_l2_r2`  
**Common cases:** 40

| Metric | Baseline | Candidate | Delta |
| :--- | ---: | ---: | ---: |
| Overall pass % | 7.50 | 62.50 | +55.00 |
| Strict pass % | 7.50 | 62.50 | +55.00 |
| Valid % | 92.50 | 100.00 | +7.50 |
| Shape match % | 60.00 | 77.50 | +17.50 |
| Dimensions pass % | 57.50 | 75.00 | +17.50 |
| Placement pass % | 15.00 | 67.50 | +52.50 |
| Topology pass % | 72.50 | 87.50 | +15.00 |
| Mean IoU | 0.79 | 0.92 | +0.13 |
| Mean dim error % | 46.02 | 14.69 | -31.34 |
| Mean placement error mm | 26.14 | 9.28 | -16.87 |

## Per-level

| Level | n | Overall (a -> b) | IoU (a -> b) | Dim pass (a -> b) |
| :--- | ---: | :--- | :--- | :--- |
| L2 | 40 | 7.5% -> 62.5% | 0.786 -> 0.920 | 57.5% -> 75.0% |

**Fixed:** 23 cases  
**Regressed:** 1 cases

| Regressed case | Reason |
| :--- | :--- |
| V2-M09 L2 | iou 1.000, dim err 0.0%, placement 0.00 mm |
