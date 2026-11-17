# V2 Golden Benchmark - patch_m03

**Generated:** 2026-10-25 19:49:49  
**Pipeline:** `pipeline`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `5f034d29a849e89c`  
**Cases:** 1  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **0.0%** | 0.0 - 79.3% |
| Strict Pass (dims + placement + topology + volume + shape) | 0.0% | all prompt levels |
| Valid Solid | 100.0% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 100.0% | mean IoU 0.998 |
| Dimensional Pass (<= 2% per axis) | 100.0% | mean max error 0.0% |
| Placement Pass (corner <= 1 mm) | 100.0% | mean error 0.00 mm |
| Topology Pass (hole count + diameters) | 100.0% | |
| Volume Pass (<= 5%) | 0.0% | |
| Latency p50 / p95 | 27.3s / 27.3s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.000 | 1.000 | 0.062 | 1.000 | 1.000 | 0.996 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 1 | 0.0% | 0.0% | 100.0% | 0.998 | 100.0% | 100.0% | 100.0% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| medium | 1 | 0.0% | 0.0% | 100.0% | 0.998 | 100.0% | 100.0% | 100.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| u_channel | 1 | 0% | 0% | 0.998 | 100% | 100% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| volume | 1 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-M03 | L2 | N | 0.998 | 0.0 | 0.00 | 0/0 |  |
