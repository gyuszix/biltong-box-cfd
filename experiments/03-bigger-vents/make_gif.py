#!/usr/bin/env python3
"""
Render an orbiting-camera GIF of one of the comparison views (both variants
side by side, rotating in sync). GitHub renders animated GIFs directly in
READMEs (unlike the interactive pyvista window from view_interactive.py),
so this is what you'd embed there instead.

Usage:
    ./make_gif.sh                            # writes results/streamlines.gif
    ./make_gif.sh rods                       # orbit the rod-height slice instead
    ./make_gif.sh slice --frames 90 --fps 20 --degrees 360
"""

import argparse
import os

import compare_variants as cv

VIEWS = {
    "streamlines": cv.add_streamlines,
    "slice": cv.add_velocity_slice,
    "rods": cv.add_rod_height_slice,
}


def make_gif(view_name, n_frames, fps, degrees):
    build_fn = VIEWS[view_name]
    p = cv.pv.Plotter(shape=(1, 2), off_screen=True, window_size=(1200, 600))
    for i, (name, vcfg) in enumerate(cv.VARIANTS.items()):
        internal, boundary, _ = cv.load_variant(vcfg)
        p.subplot(0, i)
        build_fn(p, internal, boundary, "turbo", (0.0, 3.0))
        p.add_text(vcfg["label"], font_size=10)

    out_path = os.path.join(cv.RESULTS_DIR, f"{view_name}.gif")
    p.open_gif(out_path, fps=fps)

    n_subplots = len(cv.VARIANTS)
    step = max(1, degrees // n_frames)
    for angle in range(0, degrees, step):
        # both subplots share the same orbit angle each frame, so they
        # rotate in lockstep in the output GIF
        for i in range(n_subplots):
            p.subplot(0, i)
            p.camera.azimuth = angle
        p.write_frame()

    p.close()
    print(f"wrote {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("view", nargs="?", choices=list(VIEWS), default="streamlines",
                     help="which comparison view to orbit (default: streamlines)")
    ap.add_argument("--frames", type=int, default=60, help="number of frames in the loop")
    ap.add_argument("--fps", type=int, default=15, help="playback frames per second")
    ap.add_argument("--degrees", type=int, default=360, help="total rotation (360 = full loop)")
    args = ap.parse_args()

    os.makedirs(cv.RESULTS_DIR, exist_ok=True)
    make_gif(args.view, args.frames, args.fps, args.degrees)
