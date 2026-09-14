# Experiment 4: fan on the short face, opposite the vents

**Question:** experiments 1-3 only ever put the fan on a long wall (or the
lid). What if the fan goes on a short END face instead, blowing straight
down the box's long axis, with the vents consolidated onto the opposite
short face? This is the one fan position not yet tried, and it puts fan and
vents on the same axis (like experiment 2's "aligned" test) but along the
long axis instead of the short one - and it changes how the flow meets the
rods: side_mount's flow (along y) runs parallel to the rods' length and
hits both rods broadside at once, while here the flow travels along x and
crosses the two rods in series (near rod first, then far rod) before
exiting.

- `side_mount` - exp 1's baseline, reused as-is (not re-solved): fan on the
  +y long wall, 12x15mm vents split across both short (x) faces
- `end_mount` - fan relocated to the -x short face (blowing in +x), all 12
  vents (same diameter, same total count) consolidated onto the opposite
  +x short face. Placement is the only variable - fan speed, vent
  size/count, box geometry, and rod position are all unchanged.

**Buildability caveat:** experiment 1's geometry script explicitly ruled
out short-face fan mounting because the real IKEA SAMLA tote has a moulded
depression on those faces that a fan can't sit flush against. This variant
is simulated anyway, purely to answer "would solving that mounting problem
even be worth it" - if it doesn't beat side_mount, there's no reason to
chase it further.

## Finding: side_mount still wins - aligning fan and vents backfires again, even on a different axis

| metric | side_mount (fan on long wall) | end_mount (fan on short face, opposite vents) |
|---|---|---|
| mean speed at rod/meat surface | **0.715 m/s** | 0.598 m/s (-16%) |
| mean speed, full cross-section at rod height | **0.772 m/s** | 0.514 m/s (-33%) |
| uniformity (CV, lower = more even) | 0.89 | **0.75** (more even, but see below) |
| internal gauge pressure (mean / max) | 15.9 / 24.6 Pa | 14.4 / 20.7 Pa (modestly lower) |
| near-fan rod / near-vent rod mean speed | 0.68 / 0.75 m/s | 0.56 / 0.64 m/s |

end_mount loses on the headline number - airflow at the rods is 16% slower
on average, and 33% slower across the full rod-height cross-section - and
the streamlines show exactly why: with fan and vents on opposite ends of
the *same* axis, the jet punches straight through the box in one coherent
tube from fan to vent (visible as a clean, largely undiffused red column in
the streamline and mid-plane renders) instead of spreading out to fill the
volume. That's the identical failure mode experiment 2 found for
side_aligned - putting the exit directly downstream of the fan lets the air
short-circuit to the nearest opening instead of doing useful work
circulating through the rest of the box. It didn't matter that this time
the "downstream" axis is the long one instead of the short one, or that the
rods now sit in the jet's path in series rather than being blasted
broadside - same principle, same result.

The one genuine silver lining: the CV at rod height (0.75 vs 0.89) says the
*whole cross-section* is more evenly lit up in end_mount rather than one
strong jet plus dead zones - consistent with a single coherent tube filling
more of the box's width/height uniformly as it travels, vs. side_mount's
sharper, more concentrated jet. But that evenness doesn't rescue the two
rods specifically: the near-vent rod still gets meaningfully more airflow
than the near-fan rod in both variants (end_mount: 0.64 vs 0.56 m/s, a 13%
gap; side_mount: 0.75 vs 0.68 m/s, a 9% gap) - end_mount's rod-to-rod
imbalance is if anything slightly *worse*, it's just riding on a lower
overall baseline. So the general cross-section-evenness improvement doesn't
translate into fixing the actual thing that matters (both rods drying at a
similar rate).

Internal pressure dropped a bit (24.6 -> 20.7 Pa max) but not dramatically
- nowhere near enough of a difference to be worth trading away 16% of rod
airflow for.

**Recommendation: no change.** side_mount (fan on one long wall, vents on
both short end faces, perpendicular to the fan's jet) remains the best
configuration found across all four experiments. This result also means
the short-face mounting problem flagged in experiment 1 (real SAMLA totes
have a moulded depression there a fan can't sit flush against) isn't worth
solving even if it *were* mechanically easy - the airflow case for it
doesn't hold up.

## View the results (rendered)

`results/streamlines.png` is the clearest evidence: side_mount's jet visibly
recirculates through the whole box before escaping; end_mount's forms one
straight coherent tube from fan to vent with minimal spreading.

## Reproduce

```
blender --background --python generate_geometry_v2.py   # writes stl_out/end_mount/
python3 setup_cfd_cases.py                                # writes case-end-mount/
./run_cfd.sh end_mount                                    # mesh + solve (~6-10 min)
./compare.sh                                               # writes results/ (reuses exp1's side_mount, no re-solve)
```
(`compare.sh`/`view.sh` find the shared `.venv` automatically - run them
from anywhere, no activation or path-remembering needed)

## View the results

Same pattern as experiment 1: static PNGs in `results/`, or
```
./view.sh all
```

## Files

```
generate_geometry_v2.py    Blender geometry generator -> stl_out/end_mount/*.stl
setup_cfd_cases.py         writes OpenFOAM case files (0/, constant/, system/) + copies STLs
run_cfd.sh                 blockMesh -> snappyHexMesh -> checkMesh -> simpleFoam, via Docker
compare_variants.py        metrics + comparison renders -> results/
compare.sh                 wrapper: runs compare_variants.py with the shared .venv, from anywhere
view_interactive.py        interactive viewer (reuses compare_variants.py's helpers)
view.sh                    wrapper: runs view_interactive.py with the shared .venv, from anywhere
stl_out/                   geometry STLs for end_mount (walls/fan/outlet/rods patches)
case-end-mount/            OpenFOAM case for end_mount (mesh + solution, regenerable)
results/                   metrics.csv + comparison PNGs
```
