#!/usr/bin/env python3
"""
Speed-along-rod profile: exp 6's long_face_vents (crosswise rods) vs this
experiment's long_vents_lengthwise (lengthwise rods), both already solved.

The headline metrics in each experiment's README (mean/min/std across the
whole rod surface) answer "which layout has more airflow on average" but
collapse away *where* along a rod the slow spots sit. For a rod that's
going to hold several meat pieces on hooks spaced along its length, that
shape matters as much as the average: a dead zone in the middle of every
rod (bad for however you space your hooks) is a very different practical
problem than a dead zone confined to one end (avoidable by not hanging
anything right there).

This script samples mean speed in rings around each rod at 40 positions
along its length and plots the profile, instead of collapsing it to one
number. Reuses both already-solved cases - no re-solving.

Run (after both exp 6's case-long-face-vents and this experiment's
case-long-vents-lengthwise have been solved):
    .venv/bin/python rod_profile_compare.py
(or ./compare.sh-style: there's no wrapper for this one, it's a one-off
analysis script - just call the shared venv directly, e.g.
`../../.venv/bin/python rod_profile_compare.py` from this directory)

Output: results/rod_profile_along_length.png
"""

import os

import numpy as np
import pyvista as pv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

pv.OFF_SCREEN = True

ROOT = os.path.dirname(os.path.abspath(__file__))
EXP6_ROOT = os.path.join(ROOT, "..", "06-vent-long-faces")
RESULTS_DIR = os.path.join(ROOT, "results")

CM = 0.01
BOTTOM_L, BOTTOM_W = 33 * CM, 23 * CM
TOP_L, TOP_W = 39 * CM, 28 * CM
HEIGHT = 29 * CM
ROD_DIAMETER = 0.008
ROD_HEIGHT_FRAC = 0.65
MEAT_STANDOFF = 0.015
FRACS = [1 / 3, 2 / 3]

EXP6_FOAM = os.path.join(EXP6_ROOT, "case-long-face-vents", "case-long-face-vents.foam")
EXP7_FOAM = os.path.join(ROOT, "case-long-vents-lengthwise", "case-long-vents-lengthwise.foam")


def face_half_dims(z):
    t = z / HEIGHT
    L = BOTTOM_L + (TOP_L - BOTTOM_L) * t
    W = BOTTOM_W + (TOP_W - BOTTOM_W) * t
    return L / 2, W / 2


def load(foam_file):
    reader = pv.OpenFOAMReader(foam_file)
    reader.set_active_time_value(reader.time_values[-1])
    blocks = reader.read()
    return blocks["internalMesh"]


def _ring_mean_speed(internal, center_fn, r, thetas):
    """center_fn(theta) -> (x, y, z) point on the sampling ring."""
    pts = np.array([center_fn(th) for th in thetas])
    probe = pv.PolyData(pts).sample(internal)
    valid = probe.point_data["vtkValidPointMask"].astype(bool)
    if not valid.any():
        return np.nan
    return np.linalg.norm(probe.point_data["U"][valid], axis=1).mean()


def profile_crosswise(internal, n_theta=24, n_along=40):
    """
    exp 6: rods at fixed x (two positions), spanning y. "Along the rod"
    means y position, i.e. side wall (-1, near one vent bank) to side wall
    (+1, near the other).
    """
    z = HEIGHT * ROD_HEIGHT_FRAC
    half_L, half_W = face_half_dims(z)
    r = ROD_DIAMETER / 2 + MEAT_STANDOFF
    half_len = (2 * half_W) * 0.9 / 2
    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    alongs = np.linspace(-half_len, half_len, n_along)

    profiles = []
    for frac in FRACS:
        x = -half_L + (2 * half_L) * frac
        means = [
            _ring_mean_speed(internal, lambda th, x=x, y=y: (x + r * np.cos(th), y, z + r * np.sin(th)), r, thetas)
            for y in alongs
        ]
        profiles.append((alongs / half_len, np.array(means)))
    return profiles


def profile_lengthwise(internal, n_theta=24, n_along=40):
    """
    exp 7: rods at fixed y (two positions), spanning x. "Along the rod"
    means x position, i.e. near-fan (-1) to far-wall (+1).
    """
    z = HEIGHT * ROD_HEIGHT_FRAC
    half_L, half_W = face_half_dims(z)
    r = ROD_DIAMETER / 2 + MEAT_STANDOFF
    half_len = (2 * half_L) * 0.9 / 2
    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    alongs = np.linspace(-half_len, half_len, n_along)

    profiles = []
    for frac in FRACS:
        y = -half_W + (2 * half_W) * frac
        means = [
            _ring_mean_speed(internal, lambda th, x=x, y=y: (x, y + r * np.cos(th), z + r * np.sin(th)), r, thetas)
            for x in alongs
        ]
        profiles.append((alongs / half_len, np.array(means)))
    return profiles


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Loading exp6 long_face_vents (crosswise rods)...")
    prof6 = profile_crosswise(load(EXP6_FOAM))

    print("Loading exp7 long_vents_lengthwise (lengthwise rods)...")
    prof7 = profile_lengthwise(load(EXP7_FOAM))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

    ax = axes[0]
    for i, (pos, spd) in enumerate(prof6):
        ax.plot(pos, spd, marker='o', ms=3, label=f"rod {i+1}")
    ax.set_title(
        "exp6 long_face_vents (crosswise rods)\n"
        "position along rod = side wall (-1) to side wall (+1), toward each vent bank"
    )
    ax.set_xlabel("normalized position along rod")
    ax.set_ylabel("mean speed at meat surface (m/s)")
    ax.axvline(0, color='gray', lw=0.5, ls='--')
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[1]
    for i, (pos, spd) in enumerate(prof7):
        ax.plot(pos, spd, marker='o', ms=3, label=f"rod {i+1}")
    ax.set_title(
        "exp7 long_vents_lengthwise (lengthwise rods)\n"
        "position along rod = near-fan (-1) to far-wall (+1)"
    )
    ax.set_xlabel("normalized position along rod")
    ax.axvline(0, color='gray', lw=0.5, ls='--')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "rod_profile_along_length.png")
    plt.savefig(out_path, dpi=130)
    print(f"wrote {out_path}")

    for name, prof in [("exp6 crosswise", prof6), ("exp7 lengthwise", prof7)]:
        print(f"\n{name}:")
        for i, (pos, spd) in enumerate(prof):
            print(
                f"  rod {i+1}: mean={np.nanmean(spd):.3f} min={np.nanmin(spd):.3f} "
                f"max={np.nanmax(spd):.3f} std={np.nanstd(spd):.3f}"
            )


if __name__ == "__main__":
    main()
