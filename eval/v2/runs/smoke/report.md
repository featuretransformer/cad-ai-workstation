# V2 Golden Benchmark - smoke

**Generated:** 2026-10-25 19:12:18  
**Pipeline:** `core`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `efcab20c29f0f947`  
**Cases:** 2  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **0.0%** | 0.0 - 65.8% |
| Strict Pass (dims + placement + topology + volume + shape) | 0.0% | all prompt levels |
| Valid Solid | 100.0% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 100.0% | mean IoU 0.980 |
| Dimensional Pass (<= 2% per axis) | 100.0% | mean max error 0.0% |
| Placement Pass (corner <= 1 mm) | 0.0% | mean error 3.75 mm |
| Topology Pass (hole count + diameters) | 50.0% | |
| Volume Pass (<= 5%) | 100.0% | |
| Latency p50 / p95 | 67.1s / 67.1s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.000 | 1.000 | 0.947 | 0.250 | 0.500 | 0.970 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 2 | 0.0% | 0.0% | 100.0% | 0.980 | 100.0% | 0.0% | 50.0% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 2 | 0.0% | 0.0% | 100.0% | 0.980 | 100.0% | 0.0% | 50.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| box | 1 | 0% | 0% | 1.000 | 100% | 100% |
| plate_center_hole | 1 | 0% | 0% | 0.960 | 100% | 0% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| placement | 2 |
| topology | 1 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-E07 | L2 | N | 0.960 | 0.0 | 2.50 | 0/1 |  |
| V2-E01 | L2 | N | 1.000 | 0.0 | 5.00 | 0/0 |  |
