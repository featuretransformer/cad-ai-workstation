# AI-Native CAD Evaluation Harness

A reliable, geometry-grounded evaluation benchmark that measures the accuracy of generated 3D CAD models on **Shape**, **Dimensions**, and **Positioning**.

---

## 1. Architecture & Design Principles

* **Geometry-First Evaluation:** Ground-truth dimensions are extracted directly from OpenCASCADE B-Rep solids and manifold triangular meshes (`.step` and `.stl`), never parsed from prompt text strings.
* **Strict Failure Accounting:** Failed generations (syntax errors, non-manifold boundaries, kernel crashes, unclosed solids) are never dropped or ignored; they count as failures with a score of zero.
* **Leakage-Free Benchmark:** The Golden Set (`eval/golden_set/`) is strictly isolated from the retrieval knowledge base (`knowledge.db`). Test partition IDs are excluded from training and few-shot retrieval.
* **Reproducible Freeze:** The golden test set manifest and geometry files are frozen with a SHA-256 hash stored in `eval/golden_set/golden_set.sha256`.

---

## 2. Directory Structure

```
eval/
├── README.md                      # Documentation, metric definitions, and CLI guide
├── build_golden_set.py            # Generates STEP, STL, renders, and manifest
├── run_eval.py                    # Pluggable evaluation harness CLI
├── golden_set/
│   ├── manifest.jsonl             # Frozen metadata with geometry-derived dimensions
│   ├── golden_set.sha256          # SHA-256 integrity hash
│   ├── golden_cad_prompts.jsonl   # Curated multi-level prompt dataset
│   ├── step/                      # Ground-truth G001.step ... G030.step & .stl
│   └── renders/                   # 512x512 clean isometric renders (azimuth 45°, elevation 35.264°)
├── metrics/
│   ├── __init__.py                # Unified evaluate_cad_model() entry point
│   ├── extractor.py               # B-Rep & mesh geometry feature extractor
│   ├── shape.py                   # Normalised & Raw Chamfer, Point-Cloud F-Score, Volumetric IoU
│   ├── dimensions.py              # Bounding box, volume, hole diameter, and 2% pass rate
│   └── positioning.py             # Hungarian hole matching and Kabsch rotation alignment diagnostic
├── tests/
│   ├── test_metrics_units.py      # Unit tests for individual metric functions
│   └── test_harness_self.py       # Self-tests: 100% ground truth identity + deliberate mutant failures
└── reports/
    ├── baseline_report.md         # Markdown summary report with confidence intervals
    ├── eval_results.jsonl         # Detailed per-item machine-readable records
    ├── eval_results.csv           # Tabular export for analysis
    └── visualizations/            # Side-by-side failure gallery (Ground Truth vs Candidate)
```

---

## 3. Metrics Specification

### Shape Metrics (`eval/metrics/shape.py`)
Evaluated in both **Normalised Mode** (centred at origin, scaled isotropically to unit cube) and **Raw Mode** (true mm units and placement):
* **Chamfer Distance:** Symmetrical mean Euclidean distance over 50,000 uniform surface points sampled via KDTree:
  $$CD(P_{gt}, P_{gen}) = \frac{1}{2} \left( \frac{1}{|P_{gt}|} \sum_{p \in P_{gt}} \min_{q \in P_{gen}} \|p - q\|_2 + \frac{1}{|P_{gen}|} \sum_{q \in P_{gen}} \min_{p \in P_{gt}} \|q - p\|_2 \right)$$
* **Surface F-Score:** Harmonic mean of precision and recall at threshold $\tau = 0.01$ (normalised) or $\tau = 1.0\text{ mm}$ (raw):
  $$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
* **Volumetric IoU:** 3D point containment grid intersection over union:
  $$\text{IoU} = \frac{|V_{gt} \cap V_{gen}|}{|V_{gt} \cup V_{gen}|}$$

### Dimensional Metrics (`eval/metrics/dimensions.py`)
* **Bounding Box Error:** Relative percentage error on sorted principal dimensions ($|L_{gen} - L_{gt}| / L_{gt} \times 100\%$).
* **Volume Error:** Relative percentage error on solid volume ($|V_{gen} - V_{gt}| / V_{gt} \times 100\%$).
* **Hole Diameters:** Nearest-neighbor matched cylindrical bore diameter relative error.
* **Pass Rate within 2%:** Percentage of dimensional checks with error $\le 2\%$.
* **Median & P90 Error:** Robust percentiles across all dimensional checks.

### Positioning Metrics (`eval/metrics/positioning.py`)
* **Centroid Offset:** Euclidean distance between bounding origins $\|\mathbf{c}_{gen} - \mathbf{c}_{gt}\|_2\text{ in mm}$.
* **Hole Count Exact Match:** Boolean match on detected cylindrical through-bores.
* **Feature-Centre Error:** Mean Euclidean distance in mm across matched hole pairs (Hungarian algorithm via `scipy.optimize.linear_sum_assignment`).
* **Axis-Alignment Diagnostic:** Solves for optimal 3D rigid rotation matrix $R \in \text{SO}(3)$ using the Kabsch algorithm (SVD). Diagnoses whether feature position errors vanish ($< 1\text{ mm}$) under rigid rotation, identifying coordinate-frame orientation errors vs true geometric defects.

---

## 4. Exact Run Commands

### Step 1: Run Harness Self-Tests
Verify that ground-truth scores 100% and that mutated models fail the targeted metrics:
```powershell
.\backend\.venv\Scripts\python.exe -m pytest eval\tests -v
```

### Step 2: (Optional) Rebuild / Refresh Golden Set
Regenerate ground-truth STEP files, geometry dimensions, and 512x512 isometric renders:
```powershell
.\backend\.venv\Scripts\python.exe eval\build_golden_set.py
```

### Step 3: Run Full Evaluation Harness
Run the baseline evaluation across all 30 parts and all prompt levels (L0 to L3):
```powershell
.\backend\.venv\Scripts\python.exe eval\run_eval.py --mode text-only --levels L0,L1,L2,L3 --k 1
```

### Step 4: Run Targeted Evaluation Subsets
Evaluate only parametric specifications (L2) on Hard components (hex nuts, flanges) with $k=3$ samples per part:
```powershell
.\backend\.venv\Scripts\python.exe eval\run_eval.py --levels L2 --tiers hard --k 3
```

Evaluate Multimodal (Text + Image) mode:
```powershell
.\backend\.venv\Scripts\python.exe eval\run_eval.py --mode text+image --levels L2 --limit 10
```
