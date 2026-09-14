#!/usr/bin/env python3
"""
Open an interactive 3D window to explore the solved CFD cases - rotate,
zoom, pan. Reuses the loading/rendering helpers from compare_variants.py.

Usage:
    .venv/bin/python view_interactive.py slice        # velocity slice, both variants
    .venv/bin/python view_interactive.py rods          # rod-height cross-section
    .venv/bin/python view_interactive.py streamlines    # fan-seeded streamlines
    .venv/bin/python view_interactive.py all            # all three, one window each

Controls: left-drag to rotate, scroll to zoom, right-drag to pan, 'q' or
close the window to move to the next one (in "all" mode) or exit.
"""

import sys

import compare_variants as cv

cv.pv.OFF_SCREEN = False

VIEWS = {
    "slice": ("Velocity magnitude - vertical mid-plane", cv.add_velocity_slice),
    "rods": ("Velocity magnitude - horizontal slice at rod height", cv.add_rod_height_slice),
    "streamlines": ("Streamlines from the fan inlet", cv.add_streamlines),
}


def show(name, title, build_fn):
    print(f"\nOpening: {title}  (close the window to continue)")
    p = cv.pv.Plotter(shape=(1, 2), off_screen=False, window_size=(1600, 800), title=title)
    for i, (variant, vcfg) in enumerate(cv.VARIANTS.items()):
        internal, boundary, _ = cv.load_variant(vcfg)
        p.subplot(0, i)
        build_fn(p, internal, boundary, "turbo", (0.0, 3.0))
        p.add_text(vcfg["label"], font_size=10)
    p.link_views()
    p.show()


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "all":
        for name, (title, fn) in VIEWS.items():
            show(name, title, fn)
    elif which in VIEWS:
        title, fn = VIEWS[which]
        show(which, title, fn)
    else:
        print(f"Unknown view '{which}'. Choose from: {', '.join(VIEWS)}, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
