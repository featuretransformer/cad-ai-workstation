# V2 Golden Benchmark - improved_l2

**Generated:** 2026-10-25 19:43:35  
**Pipeline:** `pipeline`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `3f03c990804c7cd1`  
**Cases:** 40  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **55.0%** | 39.8 - 69.3% |
| Strict Pass (dims + placement + topology + volume + shape) | 55.0% | all prompt levels |
| Valid Solid | 92.5% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 70.0% | mean IoU 0.831 |
| Dimensional Pass (<= 2% per axis) | 60.0% | mean max error 26.1% |
| Placement Pass (corner <= 1 mm) | 60.0% | mean error 14.70 mm |
| Topology Pass (hole count + diameters) | 95.0% | |
| Volume Pass (<= 5%) | 60.0% | |
| Latency p50 / p95 | 26.1s / 82.8s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.925 | 0.622 | 0.650 | 0.610 | 0.950 | 0.798 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 40 | 55.0% | 55.0% | 92.5% | 0.831 | 60.0% | 60.0% | 95.0% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 10 | 90.0% | 90.0% | 90.0% | 0.900 | 90.0% | 90.0% | 100.0% |
| medium | 10 | 60.0% | 60.0% | 90.0% | 0.794 | 70.0% | 70.0% | 100.0% |
| hard | 10 | 20.0% | 20.0% | 100.0% | 0.793 | 20.0% | 30.0% | 90.0% |
| complex | 10 | 50.0% | 50.0% | 90.0% | 0.838 | 60.0% | 50.0% | 90.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| box | 1 | 100% | 100% | 1.000 | 100% | 100% |
| compression_spring | 1 | 100% | 100% | 0.981 | 100% | 100% |
| cone_frustum | 1 | 0% | 0% | 0.000 | 0% | 100% |
| connecting_rod | 1 | 0% | 0% | 0.000 | 0% | 0% |
| counterbore_plate | 1 | 100% | 100% | 1.000 | 100% | 100% |
| cube | 1 | 100% | 100% | 1.000 | 100% | 100% |
| cylinder | 1 | 100% | 100% | 1.000 | 100% | 100% |
| disc | 1 | 100% | 100% | 0.999 | 100% | 100% |
| domed_cap | 1 | 0% | 0% | 0.953 | 0% | 100% |
| filleted_hub_flange | 1 | 0% | 0% | 0.948 | 0% | 100% |
| flanged_bushing | 1 | 0% | 0% | 0.787 | 0% | 100% |
| gear_rack | 1 | 0% | 0% | 0.510 | 0% | 100% |
| grooved_shaft | 1 | 0% | 0% | 0.942 | 0% | 100% |
| gusset_bracket | 1 | 0% | 0% | 0.323 | 0% | 100% |
| hex_bolt | 1 | 0% | 0% | 0.681 | 0% | 100% |
| hex_nut | 1 | 100% | 100% | 1.000 | 100% | 100% |
| i_beam | 1 | 0% | 0% | 0.558 | 0% | 100% |
| l_bracket | 1 | 0% | 0% | 0.385 | 0% | 100% |
| pillow_block | 1 | 0% | 0% | 0.715 | 0% | 0% |
| pipe_elbow | 1 | 100% | 100% | 0.999 | 100% | 100% |
| plate_4_holes | 1 | 100% | 100% | 1.000 | 100% | 100% |
| plate_center_hole | 1 | 100% | 100% | 1.000 | 100% | 100% |
| pocket_block | 1 | 0% | 0% | 1.000 | 100% | 100% |
| round_flange | 1 | 100% | 100% | 0.999 | 100% | 100% |
| slotted_boss_plate | 1 | 0% | 0% | 1.000 | 0% | 100% |
| slotted_plate | 1 | 100% | 100% | 0.997 | 100% | 100% |
| socket_cap_screw | 1 | 0% | 0% | 0.618 | 0% | 100% |
| sphere | 1 | 100% | 100% | 0.999 | 100% | 100% |
| spur_gear | 1 | 100% | 100% | 0.991 | 100% | 100% |
| square_bar | 1 | 100% | 100% | 1.000 | 100% | 100% |
| staircase_block | 1 | 100% | 100% | 1.000 | 100% | 100% |
| star_plate | 1 | 100% | 100% | 1.000 | 100% | 100% |
| stepped_shaft | 1 | 100% | 100% | 0.999 | 100% | 100% |
| t_section_bar | 1 | 100% | 100% | 1.000 | 100% | 100% |
| torus | 1 | 100% | 100% | 0.998 | 100% | 100% |
| tube | 1 | 100% | 100% | 1.000 | 100% | 100% |
| u_channel | 1 | 0% | 0% | 0.000 | 0% | 100% |
| v_block | 1 | 0% | 0% | 0.862 | 0% | 100% |
| v_pulley | 1 | 0% | 0% | 0.999 | 100% | 100% |
| washer | 1 | 100% | 100% | 0.999 | 100% | 100% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| dimensions | 13 |
| placement | 13 |
| volume | 13 |
| shape | 9 |
| invalid_solid | 3 |
| topology | 1 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-E09 | L2 | N | 0.000 | 100.0 | 41.23 | 0/0 |  |
| V2-M03 | L2 | N | 0.000 | 100.0 | 87.75 | 0/0 | Mesh is empty |
| V2-C10 | L2 | N | 0.000 | 100.0 | 114.21 | 0/2 |  |
| V2-H07 | L2 | N | 0.323 | 93.3 | 66.39 | 0/0 |  |
| V2-M02 | L2 | N | 0.385 | 90.0 | 46.22 | 0/0 |  |
| V2-C09 | L2 | N | 0.510 | 128.6 | 29.09 | 0/0 |  |
| V2-M08 | L2 | N | 0.558 | 100.0 | 55.90 | 0/0 |  |
| V2-H09 | L2 | N | 0.618 | 10.5 | 4.00 | 0/0 |  |
| V2-H02 | L2 | N | 0.681 | 13.8 | 6.40 | 0/0 |  |
| V2-H03 | L2 | N | 0.715 | 111.5 | 39.29 | 1/3 |  |
| V2-H06 | L2 | N | 0.787 | 16.7 | 3.00 | 1/1 |  |
| V2-H10 | L2 | N | 0.862 | 66.7 | 39.05 | 0/0 |  |
