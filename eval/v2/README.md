# V2 Golden Benchmark — 40 mechanical parts, 4 prompt levels

A geometry-grounded benchmark for the AI-native CAD pipeline, built around the
`tests/final test/` dataset that ships with this repository.

```
tests/final test/
├── golden_cad_prompts_v2.jsonl          40 records: prompts (L0–L3) + expected geometry
└── renders_v2_all/
    ├── renders_v2/                      512×512 isometric reference renders
    └── renders_v2_annotated/            same renders with dimension callouts
```

Every record carries its own geometric contract, so **scoring never parses the
prompt**:

```json
"expected": {
  "bbox_mm": [40.0, 20.0, 10.0],
  "volume_mm3": 8000.0,
  "placement_min_xyz_mm": [-20.0, -10.0, 0.0],
  "placement_max_xyz_mm": [20.0, 10.0, 10.0],
  "features": {"holes": 0}
}
```

40 parts × 4 prompt levels × 3 difficulty tiers + 1 complex tier = **160 cases**.

### Current results (L2, 40 parts)

| Run | Overall pass | Valid | Shape match | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline (`runs/baseline_l2`) | 7.5 % | 92.5 % | 60.0 % | 57.5 % | 15.0 % | 72.5 % |
| Refined pass@1 (`runs/improved_l2`) | 55.0 % | 92.5 % | 70.0 % | 60.0 % | 60.0 % | 95.0 % |
| Refined pass@2 (`runs/improved_l2_r2`) | 62.5 % | 100 % | 77.5 % | 75.0 % | 67.5 % | 87.5 % |

See [`REFINEMENTS.md`](REFINEMENTS.md) for the failure analysis behind the
changes and the remaining gaps.

---

## 1. What is measured

| Aspect | How it is measured | Pass bar |
| :--- | :--- | :--- |
| **Validity** | STEP imports in OpenCASCADE, volume > 0, exported STL present | required |
| **Dimensions** | per-axis bbox error vs `expected.bbox_mm` (orientation strict) | ≤ 2 % per axis |
| **Volume** | solid volume from the B-Rep vs `expected.volume_mm3` | ≤ 5 % |
| **Placement** | max corner displacement vs `expected.placement_min/max` | ≤ 1 mm |
| **Topology** | cylindrical bore count + diameters, reconstructed from B-Rep faces and classified concave/convex by point containment | exact count, diameters ≤ 5 % |
| **Shape** | candidate STL re-rendered with the *exact* reference camera (orthographic iso 45°/35.264°, 512×512, sharp feature edges) → silhouette IoU + boundary chamfer | IoU ≥ 0.90 |

The reference renders are reproduced pixel-for-pixel by the harness: a correct
model scores IoU 1.000 and zero edge difference, which was verified during
calibration (a rebuilt 40×20×10 box and a 60×40×5 plate score 1.0000 / 0.9998).

Because the renderer auto-frames the projected bounding box, **shape** is
scale/translation invariant and therefore independent of **dimensions** and
**placement** — the three cannot hide each other's errors. Interior features that
do not change the outline (a pocket, a groove, a counterbore) are caught by the
volume and bore-topology checks instead of the silhouette.

### Level-aware scoring

* **L2 / L3** contain a complete specification → graded **strictly**
  (`dimensions ∧ volume ∧ placement ∧ topology` **and** `shape`).
* **L0 / L1** deliberately omit dimensions → graded on **recognition**
  (valid solid and a matching shape); their strict score is still reported as a
  diagnostic, but it is not a fair pass criterion for an under-specified prompt.

---

## 2. Running

All commands use the project virtualenv and run from the repository root.

```powershell
# Full L2 sweep (40 cases, ~3 parallel workers)
.\backend\.venv\Scripts\python.exe -m eval.v2.runner run --tag baseline_l2 --levels L2 --workers 3

# All four prompt levels (160 cases)
.\backend\.venv\Scripts\python.exe -m eval.v2.runner run --tag full --levels L0,L1,L2,L3 --workers 3

# A subset while iterating
.\backend\.venv\Scripts\python.exe -m eval.v2.runner run --tag probe --levels L2 `
    --ids V2-C01,V2-C03,V2-C04 --generator core --workers 2

# Rebuild a report / rescore an old run under current thresholds
.\backend\.venv\Scripts\python.exe -m eval.v2.runner report  --run eval/v2/runs/baseline_l2
.\backend\.venv\Scripts\python.exe -m eval.v2.runner rescore --run eval/v2/runs/baseline_l2

# Before / after comparison
.\backend\.venv\Scripts\python.exe -m eval.v2.runner compare `
    --baseline eval/v2/runs/baseline_l2 --candidate eval/v2/runs/improved_l2
```

Options:

| Flag | Meaning |
| :--- | :--- |
| `--generator pipeline` | the real product workflow, including downstream DFM/cost/CAM agents (baseline) |
| `--generator core` | the same geometry-producing prefix of the graph, stopping at the geometry validator — several fewer LLM calls per case, identical geometry |
| `--input-mode text+image` | feeds the reference render to the multimodal path |
| `--annotated-input` | uses the dimension-annotated renders as image input (leaks the answer — diagnostics only) |
| `--samples k` | pass@k style sampling |
| `--gallery` | writes side-by-side reference/generated images for failures |
| `--resume` | continues an interrupted run from `records.jsonl` |

---

## 3. Outputs

```
eval/v2/runs/<tag>/
├── run_meta.json      generator, dataset fingerprint, commit, timings
├── records.jsonl      one flat record per case (all measurements + pass flags)
├── results.csv        tabular export
├── summary.json       aggregates (by level, tier, family, aspect, taxonomy)
├── report.md          human-readable report
└── gallery/           failure images (reference | generated)
```

---

## 4. Module map

| File | Responsibility |
| :--- | :--- |
| `dataset.py` | loads/normalises the benchmark, resolves renders, fingerprints the ground truth |
| `metrics.py` | geometry extraction (B-Rep + mesh), bore reconstruction, frame-invariant shape comparison, case scoring, rescoring |
| `generate.py` | generation adapters (`pipeline`, `core`) that drive the LangGraph workflow |
| `runner.py` | CLI, thread pool, resumable record writing, failure gallery |
| `report.py` | aggregation, markdown/CSV reports, run-to-run diff |

---

## 5. Known limitations

* The dataset ships renders, not STEP ground truth. Shape is therefore compared
  in image space. Rebuilding the golden B-Reps would allow point-cloud Chamfer /
  F-score / volumetric IoU (the older `eval/metrics/` module) on top of this
  harness.
* Silhouette IoU is blind to internal features; volume + bore topology cover the
  common cases, but a wrong internal rib would only show up in volume.
* L0/L1 are intentionally under-specified: the strict score for those levels
  measures "guessing the golden dimensions", which is not a meaningful target.
* LLM provider rate limits can push some cases onto the deterministic fallback,
  which makes single-run numbers slightly noisy. Use `--samples 2` for headline
  numbers.
