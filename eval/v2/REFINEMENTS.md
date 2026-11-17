# Pipeline refinements driven by the V2 benchmark

This documents what the 40-part `tests/final test` benchmark exposed about the
pipeline, what was changed in response, and what the measured effect was.

All numbers below are the **L2 prompt level** (the level that contains a complete
parametric specification), 40 parts, single sample per part, graded by
`eval/v2` (see `README.md` for the metric definitions).

| Run | Overall pass | Valid | Shape match | Dim pass | Placement | Topology |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline (commit `7494aa3`) | **7.5 %** | 92.5 % | 60.0 % | 57.5 % | 15.0 % | 72.5 % |
| Refined, pass@1 | **55.0 %** | 92.5 % | 70.0 % | 60.0 % | 60.0 % | 95.0 % |
| Refined, pass@2 (one retry of failures) | **62.5 %** | 100 % | 77.5 % | 75.0 % | 67.5 % | 87.5 % |

Mean silhouette IoU 0.786 → 0.920; mean dimensional error 46.0 % → 14.7 %;
mean placement error 26.1 mm → 9.3 mm. 23 of 40 parts were fixed, 1 regressed
(a pocket-depth arithmetic error, see below).

---

## 1. What the baseline showed

Running the unmodified pipeline on all 40 L2 prompts produced 3 passes. The
records made the failure causes unambiguous:

1. **Placement, not geometry, was the dominant failure.** 34 of 40 parts failed
   the placement check, and the error was almost always *exactly half the part's
   height* (2.5, 5.0, 12.5, 15.0, 20.0 mm). `build123d` primitives are centred on
   the origin by default; every prompt says "base on the XY plane", and the
   model ignored that sentence. Several parts were geometrically perfect
   (IoU 1.000) yet scored zero.
2. **Orientation was invisible to the old metric.** The U-channel was built with
   its 80 mm length along X instead of Y. The previous dimensional check
   tolerated an X/Y swap, so it reported 0 % error. Axis assignment is now
   graded strictly, because a rotated part is a different part.
3. **Curved families had no representation.** The CADIR schema listed gear,
   torus etc. only as free-form sketches, so the model fell back to
   boxes/cylinders: the spur gear became a plain cylinder, the torus became a
   washer, the spring became an extruded circle. The cone was emitted as a
   `revolve` with no sketch — the interpreter silently emitted *nothing*, the
   executor failed, and no repair was triggered because the failure was not
   diagnosable.
4. **Unrequested edge dressing.** Chamfers/fillets appeared on ~40 % of parts
   that never asked for them, shifting volume and (in one case) turning a
   through-hole plate into a 2.1 %-volume error.
5. **Axis confusion on multi-box parts.** T-section and I-beam were built with
   the web's 80 mm length along X instead of Y.

---

## 2. Changes

### 2.1 Deterministic placement frame (`backend/agents/frame_spec.py`)

A prompt parser reads the frame sentence and returns the minimal rigid
translation the finished solid needs:

| Flag | Trigger | Meaning |
| :--- | :--- | :--- |
| `frame_z_base` | "base on the XY plane", "base bottom on z = 0", `z = 0 to …`, "corner at the origin" | lowest point → z = 0 |
| `frame_center_x/y` | "centred on the origin [in X and Y]" | bbox centre → x/y = 0 |
| `frame_corner_x/y` | "outer corner at the origin", "back face on x = 0", `x = 0 to …` | bbox min → 0 |

The frame is stored on the `CADIRDocument` (`frame_z_base`, `frame_center_x`,
`frame_center_y`, `frame_corner_x`, `frame_corner_y`) and applied by the
interpreter as one `translate` of the finished solid. Corner-origin parts
(l-bracket, U-channel, T/I section, staircase, V-block, rack) are **not**
centred, and 3-D-centred parts (sphere, torus, domed cap, socket screw) are
**not** pushed onto z = 0. Every rule was validated against the 40-part ground
truth: no rule fires on a part whose expected frame contradicts it.

*Effect: placement pass 15 % → 60/67.5 %, the single largest win.*

### 2.2 High-level parametric primitives (`cad/cadir/interpreter.py`, `schema.py`)

The model no longer has to invent trigonometry. Seven new feature types are
compiled deterministically from engineering parameters supplied in
`feature.params`:

| Feature | Params | Generated B-Rep | Benchmark accuracy |
| :--- | :--- | :--- | :--- |
| `torus` | `major_r`, `minor_r` | revolve a circle | volume exact (12337.0 mm³) |
| `helix_spring` | `wire_d`, `mean_d`, `pitch`, `turns` | `Helix` + circular sweep | −0.8 % volume |
| `spur_gear` | `module`, `teeth`, `pressure_angle`, `face_width`, `bore_d` | trapezoidal tooth polygon + bore | +3.0 % volume, IoU 0.991 |
| `pipe_bend` | `od`, `id`, `bend_radius`, `bend_angle`, `leg1`, `leg2` | line + `CenterArc` + line sweep | volume exact (26167.5 mm³) |
| `star_prism` | `points`, `outer_r`, `inner_r`, `thickness`, `bore_d` | 2N-vertex star polygon | volume exact (11519.6 mm³) |
| `cone_frustum` | `base_d`, `top_d`, `height` | revolve a trapezoid | volume exact (21991.1 mm³) |
| `l_bracket` | `leg_x`, `leg_z`, `thickness`, `width` | extrude an L profile | volume exact (8500.0 mm³) |

Two supporting changes matter as much as the primitives:

* `CADIRFeature` now uses `extra="allow"` so engineering parameters survive
  Pydantic validation, and the design agent's sanitiser no longer flattens the
  `params` dict.
* A missing sketch now **raises a diagnosable error** instead of emitting an
  empty script, so the self-healing loop actually engages.

*Effect: the four complex families that used to collapse now pass; valid solids
92.5 % → 100 % after retries.*

### 2.3 Family recipes + single-pass routing (`backend/agents/family_recipes.py`)

38 mechanical families are mapped to keyword patterns and a short, authoritative
build recipe expressed in CADIR operations: "a U-channel is a block minus an
open-top pocket", "a hex nut is a regular-polygon prism whose radius is
AF/√3", "a pillow-block bore is a hole with axis (0,1,0)", and so on. The recipe
is injected into the design agent's system prompt together with an explicit
axis-mapping table ("wide" → X, "long along Y" → Y, "tall" → Z), and a rule
forbidding unrequested fillets/chamfers.

`complexity_classifier` now routes families with a coherent recipe through the
single-pass design agent instead of the incremental per-feature decomposition,
which used to lose the global dimension frame and cost several extra model
round-trips.

*Effect: U-channel IoU 0.409 → 0.998, T-section 0.594 → 1.000, staircase
0.657 → 1.000, hex nut dimensional error 495 % → 0 %.*

### 2.4 Benchmark harness (`eval/v2/`)

The V2 set could not be scored by the existing harness: it has no STEP ground
truth, only `expected` contracts and renders. `eval/v2` therefore measures six
independent aspects (validity, dimensions, volume, placement, bore topology,
rendered shape), scores L2/L3 strictly and L0/L1 on recognition, is resumable,
and can diff two runs case-by-case. See `eval/v2/README.md`.

---

## 3. What still fails, and why

| Failure | Parts | Root cause | Next step |
| :--- | :--- | :--- | :--- |
| Stacked cut depth | U-channel, pocket block | The model mixes "base at 0..H" and "centred at origin" coordinate conventions for *cut* features, so a pocket that is 8 mm deep lands 2 mm off. | Make the interpreter place `new_body` primitives base-on-XY when `frame_z_base` is set, so all downstream coordinates share one convention. |
| Detailed fastener dimensions | hex bolt, socket screw, bushing, grooved shaft | Wrong head/hub heights when several z-ranges stack (6.4/46.4, −30/8, 3/18). | Derive a per-axis envelope from the prompt and verify the measured bbox against it, feeding mismatches back as a repair instruction. |
| No primitive for rack / connecting rod / V-block / domed cap / V-pulley | 5 parts | These need a profile the model cannot reliably point-plot. | Add `gear_rack`, `link_rod`, `v_block`, `revolved_profile` primitives (same pattern as 2.2). |
| Rate limits → deterministic fallback | intermittently ~15 % of cases | Groq free-tier tokens; the fallback synthesises a plausible but wrong part. | Run evaluation with 2–3 samples, or a paid key pool; expose `generation_source` in the record. |

A note on stochasticity: LLM temperature 0.15 still produces run-to-run
variation — two heavy parts (l-bracket, gusset) hallucinated a cylinder in one
run and were correct in the next. That is why the table reports both pass@1 and
pass@2.
