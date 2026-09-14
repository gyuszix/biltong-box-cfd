#!/usr/bin/env python3
"""
Compare experiment 4's end_mount (fan on -x short face, all 12 vents
consolidated onto the opposite +x short face) against this experiment's
long_face_vents (same fan, rods, vent count/diameter, but the 12 vents
split 6-and-6 across both long faces instead). Renders airflow
visualizations and prints/saves quantitative metrics.

end_mount is NOT re-solved here - reused directly from experiment 4's
already-solved case.

Run after long_face_vents has finished (`./run_cfd.sh long_face_vents`):
    .venv/bin/python compare_variants.py

Outputs go to results/:
    velocity_slice.png     - vertical mid-plane velocity magnitude, side by side
    streamlines.png        - fan-seeded streamlines through the rods, side by side
    rod_height_slice.png   - horizontal slice at rod height, side by side
    metrics.csv            - the numbers behind the pictures
"""

import os

import numpy as np
import pandas as pd
import pyvista as pv

pv.OFF_SCREEN = True

ROOT = os.path.dirname(os.path.abspath(__file__))
EXP4_ROOT = os.path.join(ROOT, "..", "04-fan-short-face")
RESULTS_DIR = os.path.join(ROOT, "results")

CM = 0.01
BOTTOM_L, BOTTOM_W = 33 * CM, 23 * CM
TOP_L, TOP_W = 39 * CM, 28 * CM
HEIGHT = 29 * CM
ROD_DIAMETER = 0.008
ROD_HEIGHT_FRAC = 0.65
ROD_X_FRACTIONS = [1 / 3, 2 / 3]  # unchanged in both variants: rods crosswise
MEAT_STANDOFF = 0.015

VARIANTS = {
    "end_mount": {
        "label": "end_mount (exp 4 baseline: vents on opposite short face)",
        "foam_file": os.path.join(EXP4_ROOT, "case-end-mount", "case-end-mount.foam"),
    },
    "long_face_vents": {
        "label": "long_face_vents (vents split across both long faces)",
        "foam_file": os.path.join(ROOT, "case-long-face-vents", "case-long-face-vents.foam"),
    },
}


def face_half_dims(z):
    t = z / HEIGHT
    L = BOTTOM_L + (TOP_L - BOTTOM_L) * t
    W = BOTTOM_W + (TOP_W - BOTTOM_W) * t
    return L / 2, W / 2


def rod_positions():
    z = HEIGHT * ROD_HEIGHT_FRAC
    half_L, half_W = face_half_dims(z)
    half_len = (2 * half_W) * 0.9 / 2
    rods = []
    for frac in ROD_X_FRACTIONS:
        x = -half_L + (2 * half_L) * frac
        rods.append((x, z, half_len))
    return rods


def rod_ring_points(n_theta=24, n_along=14):
    r = ROD_DIAMETER / 2 + MEAT_STANDOFF
    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    pts = []
    for x, z, half_len in rod_positions():
        ys = np.linspace(-half_len, half_len, n_along)
        for y in ys:
            for th in thetas:
                pts.append((x + r * np.cos(th), y, z + r * np.sin(th)))
    return np.array(pts)


def load_variant(cfg):
    reader = pv.OpenFOAMReader(cfg["foam_file"])
    reader.set_active_time_value(reader.time_values[-1])
    blocks = reader.read()
    internal = blocks["internalMesh"]
    boundary = blocks["boundary"]

    U = internal.point_data["U"]
    internal.point_data["U_mag"] = np.linalg.norm(U, axis=1)
    return internal, boundary, reader.time_values[-1]


def sample_rod_surface_speed(internal):
    pts = rod_ring_points()
    probe = pv.PolyData(pts).sample(internal)
    valid = probe.point_data["vtkValidPointMask"].astype(bool)
    mag = np.linalg.norm(probe.point_data["U"][valid], axis=1)
    return mag


def patch_flux(patch):
    patch = patch.compute_normals(cell_normals=True, point_normals=False, flip_normals=False)
    patch = patch.compute_cell_sizes(length=False, area=True, volume=False)
    normals = patch.cell_data["Normals"]
    areas = patch.cell_data["Area"]
    U = patch.cell_data.get("U")
    if U is None:
        patch = patch.point_data_to_cell_data()
        U = patch.cell_data["U"]
    return float(np.sum(np.einsum("ij,ij->i", U, normals) * areas))


RHO_AIR = 1.204


def compute_metrics(name, cfg):
    internal, boundary, t = load_variant(cfg)

    rod_speed = sample_rod_surface_speed(internal)
    z_rod = HEIGHT * ROD_HEIGHT_FRAC
    slice_at_rods = internal.slice(normal=(0, 0, 1), origin=(0, 0, z_rod))
    slice_mag = slice_at_rods.point_data["U_mag"] if slice_at_rods.n_points else np.array([0.0])

    fan_flux = patch_flux(boundary["fan"])
    outlet_flux = patch_flux(boundary["outlet"])
    mass_imbalance_pct = (
        100 * abs(abs(fan_flux) - abs(outlet_flux)) / max(abs(fan_flux), 1e-9)
    )

    p_bulk_pa = internal.point_data["p"] * RHO_AIR

    return {
        "variant": name,
        "solved_to_time": t,
        "rod_surface_speed_mean": rod_speed.mean(),
        "rod_surface_speed_min": rod_speed.min(),
        "rod_surface_speed_max": rod_speed.max(),
        "rod_surface_speed_std": rod_speed.std(),
        "rod_height_slice_mean_speed": slice_mag.mean(),
        "rod_height_slice_uniformity_cv": slice_mag.std() / max(slice_mag.mean(), 1e-9),
        "fan_inflow_m3s": fan_flux,
        "outlet_outflow_m3s": outlet_flux,
        "mass_balance_error_pct": mass_imbalance_pct,
        "internal_gauge_pressure_pa_mean": p_bulk_pa.mean(),
        "internal_gauge_pressure_pa_max": p_bulk_pa.max(),
    }


def render_side_by_side(build_fn, out_name, cmap="turbo", clim=None):
    p = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(1600, 800))
    for i, (name, cfg) in enumerate(VARIANTS.items()):
        internal, boundary, _ = load_variant(cfg)
        p.subplot(0, i)
        build_fn(p, internal, boundary, cmap, clim)
        p.add_text(cfg["label"], font_size=10)
    out_path = os.path.join(RESULTS_DIR, out_name)
    p.screenshot(out_path)
    print(f"  wrote {out_path}")


def add_velocity_slice(p, internal, boundary, cmap, clim):
    sl = internal.slice(normal=(1, 0, 0), origin=(0, 0, 0))
    p.add_mesh(sl, scalars="U_mag", cmap=cmap, clim=clim, scalar_bar_args={"title": "|U| (m/s)"})
    p.add_mesh(boundary["walls"], color="white", opacity=0.08)
    p.add_mesh(boundary["rods"], color="saddlebrown")
    p.camera_position = "yz"
    p.camera.azimuth = 20
    p.camera.elevation = 15


def add_rod_height_slice(p, internal, boundary, cmap, clim):
    z_rod = HEIGHT * ROD_HEIGHT_FRAC
    sl = internal.slice(normal=(0, 0, 1), origin=(0, 0, z_rod))
    p.add_mesh(sl, scalars="U_mag", cmap=cmap, clim=clim, scalar_bar_args={"title": "|U| (m/s)"})
    p.add_mesh(boundary["walls"], color="white", opacity=0.06)
    p.add_mesh(boundary["rods"], color="saddlebrown")
    p.camera_position = "xy"


def add_streamlines(p, internal, boundary, cmap, clim):
    fan_cells = boundary["fan"].cell_centers().points
    normals = boundary["fan"].compute_normals(cell_normals=True).cell_data["Normals"]
    seeds = fan_cells - normals * 0.01
    seed_poly = pv.PolyData(seeds)
    streams = internal.streamlines_from_source(
        seed_poly, vectors="U", max_length=3.0, integration_direction="forward",
        initial_step_length=0.01, max_step_length=0.02,
    )
    p.add_mesh(streams.tube(radius=0.001), scalars="U_mag", cmap=cmap, clim=clim,
               scalar_bar_args={"title": "|U| (m/s)"})
    p.add_mesh(boundary["walls"], color="white", opacity=0.06)
    p.add_mesh(boundary["rods"], color="saddlebrown")
    p.camera_position = "iso"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Computing metrics...")
    rows = [compute_metrics(name, cfg) for name, cfg in VARIANTS.items()]
    df = pd.DataFrame(rows)
    csv_path = os.path.join(RESULTS_DIR, "metrics.csv")
    df.to_csv(csv_path, index=False)
    print(df.to_string(index=False))
    print(f"  wrote {csv_path}")

    clim = (0.0, 3.0)

    print("\nRendering velocity slice comparison...")
    render_side_by_side(add_velocity_slice, "velocity_slice.png", clim=clim)

    print("Rendering rod-height slice comparison...")
    render_side_by_side(add_rod_height_slice, "rod_height_slice.png", clim=clim)

    print("Rendering streamline comparison...")
    render_side_by_side(add_streamlines, "streamlines.png", clim=clim)

    base = df[df.variant == "end_mount"].iloc[0]
    new = df[df.variant == "long_face_vents"].iloc[0]
    print("\n--- Verdict ---")
    winner = "long_face_vents" if new.rod_surface_speed_mean > base.rod_surface_speed_mean else "end_mount"
    print(
        f"Mean airflow speed at the rod/meat surface: end_mount="
        f"{base.rod_surface_speed_mean:.3f} m/s, long_face_vents="
        f"{new.rod_surface_speed_mean:.3f} m/s.\n"
        f"Uniformity (CV, lower=more even) at rod height: end_mount="
        f"{base.rod_height_slice_uniformity_cv:.2f}, long_face_vents="
        f"{new.rod_height_slice_uniformity_cv:.2f}.\n"
        f"Internal gauge pressure (mean): end_mount={base.internal_gauge_pressure_pa_mean:.1f} Pa, "
        f"long_face_vents={new.internal_gauge_pressure_pa_mean:.1f} Pa.\n"
        f"=> '{winner}' gives stronger average airflow across the meat in this setup."
    )


if __name__ == "__main__":
    main()
