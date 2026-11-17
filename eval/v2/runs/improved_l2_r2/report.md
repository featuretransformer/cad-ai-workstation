# V2 Golden Benchmark - improved_l2_r2 (pass@2)

**Generated:** 2026-10-25 19:51:14  
**Pipeline:** `pipeline`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `3f03c990804c7cd1`  
**Cases:** 40  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **62.5%** | 47.0 - 75.8% |
| Strict Pass (dims + placement + topology + volume + shape) | 62.5% | all prompt levels |
| Valid Solid | 100.0% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 77.5% | mean IoU 0.920 |
| Dimensional Pass (<= 2% per axis) | 75.0% | mean max error 14.7% |
| Placement Pass (corner <= 1 mm) | 67.5% | mean error 9.28 mm |
| Topology Pass (hole count + diameters) | 87.5% | |
| Volume Pass (<= 5%) | 70.0% | |
| Latency p50 / p95 | 23.5s / 63.9s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.000 | 0.752 | 0.741 | 0.685 | 0.875 | 0.881 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 40 | 62.5% | 62.5% | 100.0% | 0.920 | 75.0% | 67.5% | 87.5% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 10 | 100.0% | 100.0% | 100.0% | 1.000 | 100.0% | 100.0% | 100.0% |
| medium | 10 | 70.0% | 70.0% | 100.0% | 0.955 | 90.0% | 80.0% | 100.0% |
| hard | 10 | 30.0% | 30.0% | 100.0% | 0.861 | 50.0% | 40.0% | 80.0% |
| complex | 10 | 50.0% | 50.0% | 100.0% | 0.862 | 60.0% | 50.0% | 70.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| box | 1 | 100% | 100% | 1.000 | 100% | 100% |
| compression_spring | 1 | 100% | 100% | 0.981 | 100% | 100% |
| cone_frustum | 1 | 100% | 100% | 0.999 | 100% | 100% |
| connecting_rod | 1 | 0% | 0% | 0.389 | 0% | 0% |
| counterbore_plate | 1 | 100% | 100% | 1.000 | 100% | 100% |
| cube | 1 | 100% | 100% | 1.000 | 100% | 100% |
| cylinder | 1 | 100% | 100% | 1.000 | 100% | 100% |
| disc | 1 | 100% | 100% | 0.999 | 100% | 100% |
| domed_cap | 1 | 0% | 0% | 0.911 | 0% | 0% |
| filleted_hub_flange | 1 | 0% | 0% | 0.948 | 0% | 100% |
| flanged_bushing | 1 | 0% | 0% | 0.787 | 0% | 100% |
| gear_rack | 1 | 0% | 0% | 0.459 | 0% | 100% |
| grooved_shaft | 1 | 0% | 0% | 0.876 | 100% | 0% |
| gusset_bracket | 1 | 0% | 0% | 0.867 | 0% | 100% |
| hex_bolt | 1 | 0% | 0% | 0.681 | 0% | 100% |
| hex_nut | 1 | 100% | 100% | 1.000 | 100% | 100% |
| i_beam | 1 | 0% | 0% | 0.558 | 0% | 100% |
| l_bracket | 1 | 100% | 100% | 1.000 | 100% | 100% |
| pillow_block | 1 | 0% | 0% | 0.715 | 0% | 0% |
| pipe_elbow | 1 | 100% | 100% | 0.999 | 100% | 100% |
| plate_4_holes | 1 | 100% | 100% | 1.000 | 100% | 100% |
| plate_center_hole | 1 | 100% | 100% | 1.000 | 100% | 100% |
| pocket_block | 1 | 0% | 0% | 1.000 | 100% | 100% |
| round_flange | 1 | 100% | 100% | 0.999 | 100% | 100% |
| slotted_boss_plate | 1 | 100% | 100% | 1.000 | 100% | 100% |
| slotted_plate | 1 | 100% | 100% | 0.997 | 100% | 100% |
| socket_cap_screw | 1 | 0% | 0% | 0.716 | 0% | 100% |
| sphere | 1 | 100% | 100% | 0.999 | 100% | 100% |
| spur_gear | 1 | 100% | 100% | 0.991 | 100% | 100% |
| square_bar | 1 | 100% | 100% | 1.000 | 100% | 100% |
| staircase_block | 1 | 100% | 100% | 1.000 | 100% | 100% |
| star_plate | 1 | 100% | 100% | 1.000 | 100% | 100% |
| stepped_shaft | 1 | 100% | 100% | 0.999 | 100% | 100% |
| t_section_bar | 1 | 100% | 100% | 1.000 | 100% | 100% |
| torus | 1 | 100% | 100% | 0.998 | 100% | 100% |
| tube | 1 | 100% | 100% | 1.000 | 100% | 100% |
| u_channel | 1 | 0% | 0% | 0.998 | 100% | 100% |
| v_block | 1 | 0% | 0% | 0.971 | 100% | 100% |
| v_pulley | 1 | 0% | 0% | 0.946 | 100% | 0% |
| washer | 1 | 100% | 100% | 0.999 | 100% | 100% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| placement | 13 |
| volume | 12 |
| dimensions | 10 |
| shape | 9 |
| topology | 5 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-C10 | L2 | N | 0.389 | 92.4 | 108.05 | 1/2 |  |
| V2-C09 | L2 | N | 0.459 | 76.1 | 38.76 | 0/0 |  |
| V2-M08 | L2 | N | 0.558 | 100.0 | 55.90 | 0/0 |  |
| V2-H02 | L2 | N | 0.681 | 13.8 | 6.40 | 0/0 |  |
| V2-H03 | L2 | N | 0.715 | 111.5 | 39.29 | 1/3 |  |
| V2-H09 | L2 | N | 0.716 | 28.9 | 15.00 | 0/0 |  |
| V2-H06 | L2 | N | 0.787 | 16.7 | 3.00 | 1/1 |  |
| V2-H07 | L2 | N | 0.867 | 117.3 | 37.09 | 0/0 |  |
| V2-H05 | L2 | N | 0.876 | 0.0 | 0.00 | 1/0 |  |
| V2-C06 | L2 | N | 0.911 | 9.1 | 15.00 | 1/0 |  |
| V2-C05 | L2 | N | 0.946 | 0.0 | 15.00 | 1/1 |  |
| V2-C07 | L2 | N | 0.948 | 21.4 | 7.50 | 1/1 |  |
