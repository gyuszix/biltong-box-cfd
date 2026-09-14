# Experiment 3: bigger vents

**Question:** the vents are currently the tighter restriction in the
system (total open area ~2120 mm² vs the fan's ~3850 mm²) - does enlarging
them (15mm -> 20mm holes, same count/placement) raise airflow at the
rods? Placement kept as experiment 1's original perpendicular short-face
layout, per experiment 2's finding that it beats putting vents opposite
the fan.

- `side_mount` - exp 1 baseline, reused as-is: 15mm vent holes
- `side_bigvent` - same fan, same placement/count, 20mm vent holes
  (~78% more open area, close to matching the fan's opening area)

## Finding: bigger vents don't help airflow speed, and cost most of the protective pressure

| metric | side_mount (15mm) | side_bigvent (20mm) |
|---|---|---|
| mean speed at rod/meat surface | 0.715 m/s | 0.682 m/s (-5%, essentially flat) |
| uniformity (CV, lower = more even) | 0.886 | 0.881 (no real change) |
| internal gauge pressure (mean) | 15.9 Pa | **6.3 Pa (-60%)** |
| internal gauge pressure (max) | 24.6 Pa | 14.9 Pa |

Airflow at the rods barely moved - within noise of experiment-to-experiment
variation - while the box's internal overpressure (the thing that keeps
leaks/dust/flies pushed outward rather than drawn in, see the discussion in
the top-level project notes) dropped by more than half. Streamlines confirm
it: side_bigvent's flow pattern is nearly a carbon copy of side_mount's.

**Caveat worth being upfront about:** the fan is modeled as a *fixed*
velocity inlet (same 3.68 m/s regardless of downstream resistance), not a
real fan performance curve. A real PC fan's flow rate does rise somewhat as
backpressure drops, so a real box might see a small speed bump from bigger
vents that this model structurally can't capture. But the fixed-inflow
assumption means the *pressure* result is still meaningful and conservative
in the direction that matters: even giving the vents full credit for
relieving backpressure, that relief didn't translate into more speed at the
rods in this model - so there's no evidence here that bigger vents are
worth the pressure trade-off.

**Recommendation:** keep the original 15mm vent holes. There's no
measured airflow benefit to enlarging them, and doing so meaningfully
weakens the box's protective positive pressure for no upside.

## Reproduce

```
python3 setup_cfd_cases.py       # writes case-side-bigvent/
./run_cfd.sh side_bigvent         # mesh + solve (~6-10 min)
./compare.sh                      # writes results/ (reuses exp1's side_mount, no re-solve)
```
(`compare.sh`/`view.sh` find the shared `.venv` automatically - run them
from anywhere, no activation or path-remembering needed)

## View the results

Same pattern as experiment 1: static PNGs in `results/`, or
```
./view.sh all
```
