# Run comparison

**Baseline:** `eval/v2/runs/baseline_l2`  
**Candidate:** `eval/v2/runs/improved_l2`  
**Common cases:** 40

| Metric | Baseline | Candidate | Delta |
| :--- | ---: | ---: | ---: |
| Overall pass % | 7.50 | 55.00 | +47.50 |
| Strict pass % | 7.50 | 55.00 | +47.50 |
| Valid % | 92.50 | 92.50 | +0.00 |
| Shape match % | 60.00 | 70.00 | +10.00 |
| Dimensions pass % | 57.50 | 60.00 | +2.50 |
| Placement pass % | 15.00 | 60.00 | +45.00 |
| Topology pass % | 72.50 | 95.00 | +22.50 |
| Mean IoU | 0.79 | 0.83 | +0.04 |
| Mean dim error % | 46.02 | 26.14 | -19.88 |
| Mean placement error mm | 26.14 | 14.70 | -11.44 |

## Per-level

| Level | n | Overall (a -> b) | IoU (a -> b) | Dim pass (a -> b) |
| :--- | ---: | :--- | :--- | :--- |
| L2 | 40 | 7.5% -> 55.0% | 0.786 -> 0.831 | 57.5% -> 60.0% |

**Fixed:** 21 cases  
**Regressed:** 2 cases

| Regressed case | Reason |
| :--- | :--- |
| V2-M02 L2 | iou 0.385, dim err 90.0%, placement 46.22 mm |
| V2-M09 L2 | iou 1.000, dim err 0.0%, placement 0.00 mm |
