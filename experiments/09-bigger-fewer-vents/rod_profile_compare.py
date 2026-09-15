#!/usr/bin/env python3
"""
Speed-along-rod profile: exp 7's long_vents_lengthwise (12 x 15mm vents)
vs this experiment's big_vents_lengthwise (6 x 21.21mm vents, same total
open area), both already solved, both with lengthwise rods.

Experiment 7 was recommended over exp 6's pooled-metric winner specifically
because of *where* along a rod the slow spots fall (see exp7's README):
a dead zone confined to one end of the rod is easy to work around when
hanging meat as hooks spaced along its length, unlike a dead zone in the
middle. Experiment 9 wins every pooled metric against exp7 (see this
folder's README) - but pooled metrics are exactly what hid exp6's
middle-of-rod problem in the first place, so before calling exp9 an
unambiguous upgrade, check whether it keeps exp7's favorable "one end"
failure shape or has quietly reintroduced a worse one.

Reuses both already-solved cases - no re-solving.

Run:
    ../../.venv/bin/python rod_profile_compare.py

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
EXP7_ROOT = os.path.join(ROOT, "..", "07-long-vents-lengthwise")
RESULTS_DIR = os.path.join(ROOT, "results")

CM = 0.01
BOTTOM_L, BOTTOM_W = 33 * CM, 23 * CM
TOP_L, TOP_W = 39 * CM, 28 * CM
HEIGHT = 29 * CM
ROD_DIAMETER = 0.008
ROD_HEIGHT_FRAC = 0.65
MEAT_STANDOFF = 0.015
FRACS = [1 / 3, 2 / 3]

EXP7_FOAM = os.path.join(EXP7_ROOT, "case-long-vents-lengthwise", "case-long-vents-lengthwise.foam")
EXP9_FOAM = os.path.join(ROOT, "case-big-vents-lengthwise", "case-big-vents-lengthwise.foam")


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


def _ring_mean_speed(internal, center_fn, thetas):
    pts = np.array([center_fn(th) for th in thetas])
    probe = pv.PolyData(pts).sample(internal)
    valid = probe.point_data["vtkValidPointMask"].astype(bool)
    if not valid.any():
        return np.nan
    return np.linalg.norm(probe.point_data["U"][valid], axis=1).mean()


def profile_lengthwise(internal, n_theta=24, n_along=40):
    """
    Rods at fixed y (two positions), spanning x. "Along the rod" means
    x position, i.e. near-fan (-1) to far-wall (+1).
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
            _ring_mean_speed(internal, lambda th, x=x, y=y: (x, y + r * np.cos(th), z + r * np.sin(th)), thetas)
            for x in alongs
        ]
        profiles.append((alongs / half_len, np.array(means)))
    return profiles


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Loading exp7 long_vents_lengthwise (12 x 15mm vents)...")
    prof7 = profile_lengthwise(load(EXP7_FOAM))

    print("Loading exp9 big_vents_lengthwise (6 x 21.21mm vents)...")
    prof9 = profile_lengthwise(load(EXP9_FOAM))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

    ax = axes[0]
    for i, (pos, spd) in enumerate(prof7):
        ax.plot(pos, spd, marker='o', ms=3, label=f"rod {i+1}")
    ax.set_title(
        "exp7 long_vents_lengthwise (12 x 15mm vents)\n"
        "position along rod = near-fan (-1) to far-wall (+1)"
    )
    ax.set_xlabel("normalized position along rod")
    ax.set_ylabel("mean speed at meat surface (m/s)")
    ax.axvline(0, color='gray', lw=0.5, ls='--')
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[1]
    for i, (pos, spd) in enumerate(prof9):
        ax.plot(pos, spd, marker='o', ms=3, label=f"rod {i+1}")
    ax.set_title(
        "exp9 big_vents_lengthwise (6 x 21.21mm vents)\n"
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

    for name, prof in [("exp7 (12x15mm)", prof7), ("exp9 (6x21.21mm)", prof9)]:
        print(f"\n{name}:")
        for i, (pos, spd) in enumerate(prof):
            print(
                f"  rod {i+1}: mean={np.nanmean(spd):.3f} min={np.nanmin(spd):.3f} "
                f"max={np.nanmax(spd):.3f} std={np.nanstd(spd):.3f}"
            )


if __name__ == "__main__":
    main()
