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
position being physically awkward on the real tote anyway.

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
