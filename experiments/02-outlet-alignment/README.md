# Experiment 2: outlet alignment

**Question:** experiment 1's streamlines showed the fan jet 90° off-axis
from the vents in both variants (vents on the short end faces, fan blowing
along the long or vertical axis) - does that force unwanted recirculation,
and would aligning the vents with the fan's jet (putting them on the wall
directly opposite the fan) improve airflow at the rods?

- `side_mount` - exp 1's baseline, reused as-is (not re-solved): fan on
  +y wall, vents on both short (x) end faces
- `side_aligned` - same fan, vents relocated to the -y wall (directly
  opposite/downstream of the fan). Same total vent count (12) and diameter
  (15mm) as side_mount - placement is the only variable.

## Finding: the original perpendicular placement wins - clearly

| metric | side_mount (perpendicular) | side_aligned (opposite fan) |
|---|---|---|
| mean speed at rod/meat surface | **0.72 m/s** | 0.51 m/s (-29%) |
| uniformity (CV, lower = more even) | 0.89 | 0.89 (no change) |
| internal gauge pressure (mean) | 15.9 Pa | 16.1 Pa (no change) |

This is the opposite of the hypothesis, and the streamlines explain why:
with vents directly opposite the fan, the jet has a short, direct path to
the exit and takes it - air doesn't need to fill or circulate through the
rest of the box to escape, so much of the volume (including the far rod)
sees noticeably weaker flow. With vents on the perpendicular short faces,
the jet has **no** direct path out - it's forced to spread laterally and
circulate through the full box before finding an exit, and that forced
circulation is what was driving the higher average speeds in experiment 1.
The 90° mismatch isn't a flaw here - it's what makes the fan's air actually
get used instead of short-circuited straight to the nearest exit.

**Consequence for experiment 3:** the bigger-vents test uses the original
perpendicular short-face placement (side_mount's layout), not the aligned
one - see `../03-bigger-vents/`.

## Reproduce

```
python3 setup_cfd_cases.py     # writes case-side-aligned/
./run_cfd.sh side_aligned       # mesh + solve (~6-10 min)
./compare.sh                    # writes results/ (reuses exp1's side_mount, no re-solve)
```
(`compare.sh`/`view.sh` find the shared `.venv` automatically - run them
from anywhere, no activation or path-remembering needed)

## View the results

Same pattern as experiment 1: static PNGs in `results/`, or
```
./view.sh all
```
