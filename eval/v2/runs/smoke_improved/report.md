# V2 Golden Benchmark - smoke_improved

**Generated:** 2026-10-25 19:28:58  
**Pipeline:** `core`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `8f85acdbf82e1932`  
**Cases:** 10  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **50.0%** | 23.7 - 76.3% |
| Strict Pass (dims + placement + topology + volume + shape) | 50.0% | all prompt levels |
| Valid Solid | 90.0% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 70.0% | mean IoU 0.803 |
| Dimensional Pass (<= 2% per axis) | 70.0% | mean max error 31.2% |
| Placement Pass (corner <= 1 mm) | 60.0% | mean error 15.27 mm |
| Topology Pass (hole count + diameters) | 80.0% | |
| Volume Pass (<= 5%) | 70.0% | |
| Latency p50 / p95 | 29.2s / 64.3s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.900 | 0.699 | 0.687 | 0.599 | 0.800 | 0.769 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 10 | 50.0% | 50.0% | 90.0% | 0.803 | 70.0% | 60.0% | 80.0% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 2 | 50.0% | 50.0% | 50.0% | 0.500 | 50.0% | 50.0% | 100.0% |
| medium | 3 | 33.3% | 33.3% | 100.0% | 0.811 | 66.7% | 33.3% | 100.0% |
| hard | 1 | 0.0% | 0.0% | 100.0% | 0.715 | 0.0% | 0.0% | 0.0% |
| complex | 4 | 75.0% | 75.0% | 100.0% | 0.970 | 100.0% | 100.0% | 75.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| box | 1 | 100% | 100% | 1.000 | 100% | 100% |
| compression_spring | 1 | 100% | 100% | 0.942 | 100% | 100% |
| cone_frustum | 1 | 0% | 0% | 0.000 | 0% | 100% |
| hex_nut | 1 | 100% | 100% | 1.000 | 100% | 100% |
| pillow_block | 1 | 0% | 0% | 0.715 | 0% | 0% |
| pipe_elbow | 1 | 0% | 0% | 0.982 | 100% | 0% |
| spur_gear | 1 | 100% | 100% | 0.991 | 100% | 100% |
| t_section_bar | 1 | 0% | 0% | 0.436 | 0% | 100% |
| torus | 1 | 100% | 100% | 0.965 | 100% | 100% |
| u_channel | 1 | 0% | 0% | 0.998 | 100% | 100% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| placement | 3 |
| volume | 2 |
| dimensions | 2 |
| shape | 2 |
| topology | 2 |
| invalid_solid | 1 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-E09 | L2 | N | 0.000 | 100.0 | 41.23 | 0/0 |  |
| V2-M07 | L2 | N | 0.436 | 100.0 | 28.28 | 0/0 |  |
| V2-H03 | L2 | N | 0.715 | 111.5 | 39.29 | 1/3 |  |
| V2-C02 | L2 | N | 0.982 | 0.0 | 0.00 | 2/1 |  |
| V2-M03 | L2 | N | 0.998 | 0.0 | 43.88 | 0/0 |  |
| V2-C03 | L2 | Y | 0.942 | 0.0 | 0.01 | 0/0 |  |
| V2-C04 | L2 | Y | 0.965 | 0.0 | 0.00 | 0/0 |  |
| V2-C01 | L2 | Y | 0.991 | 0.1 | 0.02 | 1/1 |  |
| V2-M05 | L2 | Y | 1.000 | 0.0 | 0.00 | 1/1 |  |
| V2-E01 | L2 | Y | 1.000 | 0.0 | 0.00 | 0/0 |  |
