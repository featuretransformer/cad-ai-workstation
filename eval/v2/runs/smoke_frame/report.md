# V2 Golden Benchmark - smoke_frame

**Generated:** 2026-10-25 19:31:58  
**Pipeline:** `core`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `0b1c49715074f31d`  
**Cases:** 3  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **66.7%** | 20.8 - 93.9% |
| Strict Pass (dims + placement + topology + volume + shape) | 66.7% | all prompt levels |
| Valid Solid | 100.0% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 100.0% | mean IoU 0.999 |
| Dimensional Pass (<= 2% per axis) | 100.0% | mean max error 0.0% |
| Placement Pass (corner <= 1 mm) | 100.0% | mean error 0.00 mm |
| Topology Pass (hole count + diameters) | 100.0% | |
| Volume Pass (<= 5%) | 66.7% | |
| Latency p50 / p95 | 29.5s / 30.6s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.000 | 1.000 | 0.667 | 1.000 | 1.000 | 0.998 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 3 | 66.7% | 66.7% | 100.0% | 0.999 | 100.0% | 100.0% | 100.0% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| medium | 3 | 66.7% | 66.7% | 100.0% | 0.999 | 100.0% | 100.0% | 100.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| staircase_block | 1 | 100% | 100% | 1.000 | 100% | 100% |
| t_section_bar | 1 | 100% | 100% | 1.000 | 100% | 100% |
| u_channel | 1 | 0% | 0% | 0.997 | 100% | 100% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| volume | 1 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-M03 | L2 | N | 0.997 | 0.0 | 0.00 | 0/0 |  |
| V2-M07 | L2 | Y | 1.000 | 0.0 | 0.00 | 0/0 |  |
| V2-M10 | L2 | Y | 1.000 | 0.0 | 0.00 | 0/0 |  |
