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
  (future experiments land here as siblings)
```

Each experiment folder has its own README with what it tests, the findings,
and exactly how to reproduce/view it - start there.

## Current recommendation

Based on all four experiments so far: **fan on the long side wall, vents
on both short end faces, 15mm holes** (experiment 1's original side_mount
layout, unchanged by 2, 3, and 4). Aligning vents with the fan's jet made
things worse whether the shared axis was the short one (experiment 2) or
the long one (experiment 4), enlarging the vents didn't help speed while
cutting the box's protective internal overpressure by more than half
(experiment 3), and moving the fan to a short end face lost 16% of rod
airflow for no compensating benefit (experiment 4) - on top of that mount
position being physically awkward on the real tote anyway. Rod orientation
(experiment 5) also stays unchanged: rotating the rods to run lengthwise
raised average rod-surface speed but made evenness worse both along each
rod and across the box, a worse trade than it looked at first glance.
Experiment 6 found a genuinely large improvement *within* the fan-on-
short-face family - moving end_mount's vents onto both long faces instead
of the single face opposite the fan raised rod-surface airflow 69% and
made the whole box more even too - but that's a fix to a layout
(fan on a short end face) that's still ruled out on its own for not
mounting flush on the real tote, and it hasn't been tested head-to-head
against side_mount, so it doesn't change the recommendation above.

![side_mount (the winning config, left) vs lid_mount, streamlines orbiting](experiments/01-fan-mount-placement/results/streamlines.gif)

*(from experiment 1 - side_mount, left, is the configuration above.
Every later experiment tested something else against this same baseline
and it kept winning; see each experiment's own README for its own
comparison GIF.)*

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
  experiments 2 and 4, just applied to end_mount's axis - but end_mount
  itself is still not the recommended layout (see above), so this doesn't
  change the top pick without a future head-to-head against side_mount.**
