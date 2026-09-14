# Biltong box CFD

Airflow simulation for a DIY biltong (dried meat) dryer built from an IKEA
SAMLA tote + PC fan. Each design question (where to put the fan, how big the
vents should be, etc.) gets its own self-contained folder under
`experiments/`, so results stay separable as the design space grows.

## Layout

```
experiments/
  01-fan-mount-placement/   fan on the side wall vs fan on the lid
  02-outlet-alignment/      vents opposite the fan vs on the side walls
  03-bigger-vents/          15mm vs 20mm vent holes
  04-fan-short-face/        fan on a short end face vs fan on the long wall
  05-rod-orientation/       rods lengthwise vs crosswise (exp 4's fan layout, rods rotated 90deg)
  06-vent-long-faces/       vents on both long faces vs the single opposite short face (exp 4's fan layout)
  07-long-vents-lengthwise/ exp 5's rods + exp 6's vents, combined (fan short face, rods lengthwise, vents on long faces)
  (future experiments land here as siblings)
```

Each experiment folder has its own README with what it tests, the findings,
and exactly how to reproduce/view it - start there.

## Recommended configuration: `long_vents_lengthwise` (experiment 7)

Fan on a short end face, rods **lengthwise** at two y positions, 12 vents
split 6-and-6 across both long side faces. Recommended for the actual
build target - meat hung as multiple hooks spaced along each rod, the
normal way to load a biltong box - even though it's not the top scorer on
pooled metrics; see "why lengthwise, not crosswise" below.

| metric | long_vents_lengthwise (exp 7, recommended) | side_mount (best *buildable* layout, exp 1) |
|---|---|---|
| mean speed at rod/meat surface | **1.01 m/s** | 0.72 m/s |
| mean speed, full cross-section at rod height | 0.74 m/s | 0.77 m/s |
| uniformity (CV, lower = more even) | **0.70** | 0.89 |
| internal gauge pressure (mean) | 17.7 Pa | 15.9 Pa |

![rods_lengthwise (left) vs long_vents_lengthwise, streamlines orbiting](experiments/07-long-vents-lengthwise/results/streamlines.gif)

*(from experiment 7 - `long_vents_lengthwise`, right, is the recommended
configuration; `rods_lengthwise`, left, is its own baseline. See the full
ranking table below for how every configuration simulated in this project
stacks up on pooled metrics.)*

### Why lengthwise, not crosswise, once the vents are on the long faces

Experiment 6's `long_face_vents` (identical fan and vents, rods left
**crosswise**) actually wins on every *pooled* metric - higher mean speed,
higher full cross-section mean, better whole-box uniformity. But pooled
metrics average away *where along a rod* the slow spots are, and that's
exactly what matters once you're hanging several meat strips as hooks
spaced along the same rod:

![Speed profile along each rod, crosswise (exp 6) vs lengthwise (exp 7)](experiments/07-long-vents-lengthwise/results/rod_profile_along_length.png)

- **Crosswise rods (exp 6):** both rods dip to their slowest point right
  at the box's centerline and rise toward *both* side walls (where the
  vents now sit) - a dead zone in the **middle of every rod**, exactly
  where hooks are most naturally spaced, no matter how you load them.
- **Lengthwise rods (exp 7):** both rods are slow only over roughly the
  first 15-20% of their length nearest the fan, then hold a fairly flat,
  high plateau across the rest - a dead zone confined to **one
  predictable end**, avoidable by just not hanging anything there.

A dead zone you can plan hook placement around beats a dead zone baked
into the middle of every rod - see experiment 7's README for the full
numbers and caveats behind this call.

**Shared caveat with experiment 6:** both configurations inherit their fan
position from experiment 4's `end_mount` (fan on a short end face) - a
mount position experiment 1 explicitly ruled out for not sitting flush
against the real IKEA SAMLA tote's moulded short-face depression. Neither
has been simulated head-to-head against `side_mount` in the same box
(different fan walls entirely), so beating `side_mount`'s numbers isn't
quite the same claim as "would win an apples-to-apples comparison on a
buildable box." If the short-face mounting problem doesn't get solved,
`side_mount` (below) is the strongest option that's actually buildable
today.

## Currently buildable recommendation

Of the configurations that don't require solving the short-face fan-mount
problem: **fan on the long side wall, vents on both short end faces, 15mm
holes** (experiment 1's original side_mount layout, unchanged by
experiments 2, 3, and 4). Aligning vents with the fan's jet made things
worse whether the shared axis was the short one (experiment 2) or the long
one (experiment 4), enlarging the vents didn't help speed while cutting
the box's protective internal overpressure by more than half (experiment
3), and moving the fan to a short end face lost 16% of rod airflow for no
compensating benefit on its own (experiment 4). Rod orientation
(experiment 5) also stays unchanged there: rotating the rods to run
lengthwise raised average rod-surface speed but made evenness worse both
along each rod and across the box, a worse trade than it looked at first
glance.

## Full ranking (every configuration simulated, sorted by rod-surface mean speed)

| # | variant | experiment | rod-surface mean | full cross-section mean | uniformity (CV) | rod-surface min | pressure (mean) |
|---|---|---|---|---|---|---|---|
| 1 | long_face_vents (best pooled metrics; middle-of-rod dead zone) | 6 | **1.01 m/s** | **0.82 m/s** | **0.60** | 0.072 | 17.7 Pa |
| 2 | **long_vents_lengthwise (recommended; end-of-rod dead zone)** | 7 | 1.01 m/s | 0.74 m/s | 0.70 | 0.046 | 17.7 Pa |
| 3 | side_mount | 1 | 0.72 m/s | 0.77 m/s | 0.89 | 0.096 | 15.9 Pa |
| 4 | rods_lengthwise | 5 | 0.69 m/s | 0.45 m/s | 0.82 | 0.036 | 13.9 Pa |
| 5 | side_bigvent | 3 | 0.68 m/s | 0.78 m/s | 0.88 | 0.092 | 6.3 Pa |
| 6 | end_mount | 4 | 0.60 m/s | 0.51 m/s | 0.75 | 0.100 | 14.4 Pa |
| 7 | lid_mount | 1 | 0.56 m/s | 0.69 m/s | 0.97 | 0.093 | 16.7 Pa |
| 8 | side_aligned | 2 | 0.51 m/s | 0.52 m/s | 0.89 | 0.080 | 16.1 Pa |

Rows 1 and 2 (both from the "vents on long faces" family) are a
statistical tie on rod-surface mean speed (1.009 vs 1.012 m/s, well
within this project's noise floor) - row 2 is recommended anyway because
of *where* along the rod its slow spots fall, not because it scores
higher; see "why lengthwise, not crosswise" above and experiment 7's
README for the full picture.

## Shared setup (once, for any experiment)

- Docker (for OpenFOAM, via the `opencfd/openfoam-default` image - pulled
  automatically on first `run_cfd.sh` run)
- Python venv at `.venv/` (pyvista, vtk, numpy, matplotlib, pandas, imageio):
  ```
  python3 -m venv .venv
  .venv/bin/pip install pyvista vtk numpy matplotlib pandas imageio
  ```
- Blender (`brew install --cask blender`) for the geometry generator scripts

## Experiments

- [`01-fan-mount-placement`](experiments/01-fan-mount-placement/README.md) -
  fan on the long wall vs fan on the lid. **Finding: side-mount gives
  stronger average airflow across the meat, at the cost of less even
  distribution between the two rods than lid-mount.**
- [`02-outlet-alignment`](experiments/02-outlet-alignment/README.md) -
  vents opposite the fan (aligned with its jet) vs on the side walls
  (perpendicular, exp 1's layout). **Finding: perpendicular wins clearly
  (0.72 vs 0.51 m/s) - aligned vents let the jet short-circuit straight to
  the exit instead of circulating through the box.**
- [`03-bigger-vents`](experiments/03-bigger-vents/README.md) - 15mm vs
  20mm vent holes, same placement/count. **Finding: no real airflow
  benefit (0.715 vs 0.682 m/s, within noise), but internal protective
  overpressure drops by more than half (15.9 -> 6.3 Pa) - not worth it.**
- [`04-fan-short-face`](experiments/04-fan-short-face/README.md) - fan on
  a short end face (blowing down the long axis, vents consolidated on the
  opposite short face) vs fan on the long wall (exp 1's layout).
  **Finding: side_mount wins again (0.72 vs 0.60 m/s, -16%) - same
  short-circuiting failure mode as experiment 2's aligned vents, just
  along the other axis. Also moot in practice: that fan position was
  already ruled out in experiment 1 for not sitting flush on the real
  tote.**
- [`05-rod-orientation`](experiments/05-rod-orientation/README.md) - rods
  lengthwise (parallel to the flow) vs crosswise (perpendicular, every
  prior experiment's default), same fan/vent layout as exp 4's end_mount.
  **Finding: mixed, not a clean win - average rod-surface speed rises 15%
  (0.60 -> 0.69 m/s), but the minimum surface speed drops ~65%, evenness
  along each rod gets 20% worse, and the whole-cross-section mean/
  uniformity both get worse too. Root cause: crosswise rods are forced
  through the jet's hot core, while lengthwise rods end up flanking it
  instead - partly a side effect of reusing the same spacing convention
  across a different axis, not a clean test of orientation alone.**
- [`06-vent-long-faces`](experiments/06-vent-long-faces/README.md) - vents
  split across both long faces vs consolidated on the single short face
  opposite the fan (exp 4's end_mount layout). **Finding: a decisive,
  mostly-clean win - rod-surface mean speed up 69% (0.60 -> 1.01 m/s),
  full-cross-section mean up 60% and more even (CV 0.75 -> 0.60), internal
  overpressure up rather than down. Only the rod-surface minimum gets
  worse (-28%). Same "perpendicular beats aligned" mechanism as
  experiments 2 and 4, just applied to end_mount's axis. Best pooled
  metrics of any configuration simulated in this project - see "Recommended
  configuration" above for why experiment 7 is favored over this one
  anyway, and the shared buildability caveat both inherit from end_mount.**
- [`07-long-vents-lengthwise`](experiments/07-long-vents-lengthwise/README.md) -
  experiment 5's lengthwise rods stacked on top of experiment 6's
  long-face vents, compared against exp 5's rods_lengthwise baseline.
  **Finding: still a big win over its own baseline (rod-surface mean up
  47%, full cross-section up 65%), and on pooled metrics alone exp 6's
  long_face_vents (crosswise) still edges it out on full-cross-section
  mean (0.82 vs 0.74 m/s) and uniformity (0.60 vs 0.70). But a follow-up
  speed-vs-position-along-rod analysis
  (`results/rod_profile_along_length.png`) found the two failure modes are
  shaped very differently: crosswise rods have their dead zone in the
  *middle* of every rod (unavoidable however you space hooks along it),
  while lengthwise rods have it confined to *one end* (avoidable). That's
  why this is the recommended configuration above despite not topping the
  pooled-metric table.**
