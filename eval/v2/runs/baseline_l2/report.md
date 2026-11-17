# V2 Golden Benchmark - baseline_l2

**Generated:** 2026-10-25 19:51:15  
**Pipeline:** `pipeline`  
**Input mode:** `text-only`  
**Dataset fingerprint:** `3f03c990804c7cd1`  
**Cases:** 40  
**Repository commit:** `7494aa3`

## 1. Headline

| Metric | Score | 95% CI / note |
| :--- | ---: | :--- |
| **Overall Pass** | **7.5%** | 2.6 - 19.9% |
| Strict Pass (dims + placement + topology + volume + shape) | 7.5% | all prompt levels |
| Valid Solid | 92.5% | exported, watertight, volume > 0 |
| Shape Match (silhouette IoU >= 0.90) | 60.0% | mean IoU 0.786 |
| Dimensional Pass (<= 2% per axis) | 57.5% | mean max error 46.0% |
| Placement Pass (corner <= 1 mm) | 15.0% | mean error 26.14 mm |
| Topology Pass (hole count + diameters) | 72.5% | |
| Volume Pass (<= 5%) | 47.5% | |
| Latency p50 / p95 | 27.4s / 62.9s | |

## 2. Aspect scores (0-1, higher is better)

| Validity | Dimensions | Volume | Positioning | Topology | Shape |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.925 | 0.594 | 0.522 | 0.223 | 0.725 | 0.725 |

## 3. By prompt level

| Level | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L2 | 40 | 7.5% | 7.5% | 92.5% | 0.786 | 57.5% | 15.0% | 72.5% |

## 4. By difficulty tier

| Tier | n | Overall | Strict | Valid | IoU | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| easy | 10 | 10.0% | 10.0% | 90.0% | 0.893 | 90.0% | 10.0% | 100.0% |
| medium | 10 | 20.0% | 20.0% | 100.0% | 0.824 | 60.0% | 20.0% | 80.0% |
| hard | 10 | 0.0% | 0.0% | 100.0% | 0.859 | 40.0% | 20.0% | 70.0% |
| complex | 10 | 0.0% | 0.0% | 80.0% | 0.570 | 40.0% | 10.0% | 40.0% |

## 5. By part family

| Family | n | Overall | Strict | IoU | Dim pass | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| box | 1 | 0% | 0% | 1.000 | 100% | 100% |
| compression_spring | 1 | 0% | 0% | 0.000 | 0% | 100% |
| cone_frustum | 1 | 0% | 0% | 0.000 | 0% | 100% |
| connecting_rod | 1 | 0% | 0% | 0.389 | 0% | 0% |
| counterbore_plate | 1 | 0% | 0% | 0.991 | 100% | 100% |
| cube | 1 | 0% | 0% | 1.000 | 100% | 100% |
| cylinder | 1 | 0% | 0% | 0.986 | 100% | 100% |
| disc | 1 | 0% | 0% | 0.999 | 100% | 100% |
| domed_cap | 1 | 0% | 0% | 0.567 | 0% | 100% |
| filleted_hub_flange | 1 | 0% | 0% | 0.939 | 0% | 100% |
| flanged_bushing | 1 | 0% | 0% | 0.825 | 0% | 100% |
| gear_rack | 1 | 0% | 0% | 0.966 | 100% | 100% |
| grooved_shaft | 1 | 0% | 0% | 0.432 | 0% | 0% |
| gusset_bracket | 1 | 0% | 0% | 0.974 | 100% | 100% |
| hex_bolt | 1 | 0% | 0% | 0.930 | 0% | 100% |
| hex_nut | 1 | 0% | 0% | 0.761 | 0% | 0% |
| i_beam | 1 | 0% | 0% | 0.986 | 100% | 100% |
| l_bracket | 1 | 100% | 100% | 1.000 | 100% | 100% |
| pillow_block | 1 | 0% | 0% | 0.715 | 0% | 0% |
| pipe_elbow | 1 | 0% | 0% | 0.000 | 0% | 0% |
| plate_4_holes | 1 | 0% | 0% | 0.987 | 100% | 100% |
| plate_center_hole | 1 | 0% | 0% | 0.960 | 100% | 100% |
| pocket_block | 1 | 100% | 100% | 0.981 | 100% | 100% |
| round_flange | 1 | 0% | 0% | 0.964 | 100% | 100% |
| slotted_boss_plate | 1 | 0% | 0% | 0.975 | 0% | 100% |
| slotted_plate | 1 | 0% | 0% | 0.932 | 100% | 0% |
| socket_cap_screw | 1 | 0% | 0% | 0.940 | 100% | 100% |
| sphere | 1 | 100% | 100% | 0.988 | 100% | 100% |
| spur_gear | 1 | 0% | 0% | 0.738 | 100% | 0% |
| square_bar | 1 | 0% | 0% | 1.000 | 100% | 100% |
| staircase_block | 1 | 0% | 0% | 0.657 | 100% | 100% |
| star_plate | 1 | 0% | 0% | 0.417 | 0% | 0% |
| stepped_shaft | 1 | 0% | 0% | 0.929 | 0% | 100% |
| t_section_bar | 1 | 0% | 0% | 0.594 | 0% | 100% |
| torus | 1 | 0% | 0% | 0.718 | 100% | 0% |
| tube | 1 | 0% | 0% | 0.994 | 100% | 100% |
| u_channel | 1 | 0% | 0% | 0.409 | 0% | 100% |
| v_block | 1 | 0% | 0% | 0.841 | 0% | 0% |
| v_pulley | 1 | 0% | 0% | 0.967 | 100% | 0% |
| washer | 1 | 0% | 0% | 0.998 | 100% | 100% |

## 6. Failure taxonomy

| Cause | Failures |
| :--- | ---: |
| placement | 31 |
| volume | 18 |
| dimensions | 14 |
| shape | 13 |
| topology | 10 |
| invalid_solid | 3 |

## 7. Lowest-scoring cases

| Part | Level | Pass | IoU | Dim err % | Placement mm | Holes gen/exp | Error |
| :--- | :--- | :---: | ---: | ---: | ---: | :---: | :--- |
| V2-E09 | L2 | N | 0.000 | 100.0 | 41.23 | 0/0 |  |
| V2-C02 | L2 | N | 0.000 | 100.0 | 97.21 | 0/1 |  |
| V2-C03 | L2 | N | 0.000 | 100.0 | 52.09 | 0/0 |  |
| V2-C10 | L2 | N | 0.389 | 92.4 | 108.16 | 1/2 |  |
| V2-M03 | L2 | N | 0.409 | 166.7 | 70.71 | 0/0 |  |
| V2-C08 | L2 | N | 0.417 | 92.1 | 51.05 | 1/1 |  |
| V2-H05 | L2 | N | 0.432 | 66.7 | 75.00 | 1/0 |  |
| V2-C06 | L2 | N | 0.567 | 142.4 | 49.97 | 0/0 |  |
| V2-M07 | L2 | N | 0.594 | 170.0 | 65.55 | 0/0 |  |
| V2-M10 | L2 | N | 0.657 | 0.0 | 35.00 | 0/0 |  |
| V2-H03 | L2 | N | 0.715 | 111.5 | 39.29 | 1/3 |  |
| V2-C04 | L2 | N | 0.718 | 0.0 | 0.00 | 1/0 |  |
