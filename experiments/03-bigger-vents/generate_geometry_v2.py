"""
Biltong dryer box - geometry generator for experiment 3 (bigger vents)

Run with: blender --background --python generate_geometry_v2.py

Tests ONE new variant: "side_bigvent" - identical to experiment 1's
side_mount (fan on a long wall, vents on both short end faces - the
placement experiment 2 showed beats putting vents opposite the fan), but
with the vent hole diameter increased 15mm -> 20mm (same hole count, ~78%
more total open area). Right now the vents (12 x 15mm =~2120mm^2) are
smaller than the fan opening (~3850mm^2), i.e. the tighter restriction in
the system; 20mm brings total vent area to ~3770mm^2, close to parity with
the fan - a natural target since neither end should be needlessly choking
the other.

Compare against experiment 1's side_mount, reused as-is (not regenerated),
via compare_variants.py in this folder.

All geometry in metres (OpenFOAM's native unit).
"""

import bpy
import math
import os

CM = 0.01

BOTTOM_L = 33 * CM
BOTTOM_W = 23 * CM
TOP_L = 39 * CM
TOP_W = 28 * CM
HEIGHT = 29 * CM

WALL_THICKNESS = 2 * CM / 10  # 2mm, real solid thickness (see exp1 for why this matters)
PATCH_DEPTH = 0.008  # 8mm - fan/outlet patch insert thickness (see exp1 for why)

FAN_FRAME = 0.080
FAN_BLADE_DIA = 0.070
FAN_RADIUS = FAN_BLADE_DIA / 2

ROD_DIAMETER = 0.008
ROD_HEIGHT_FRAC = 0.65
ROD_X_FRACTIONS = [1 / 3, 2 / 3]

VENT_HOLE_DIA = 0.020           # <-- the change under test: was 0.015 in exp1/exp2
VENT_ROWS = 2                    # unchanged: same 6-per-face x 2-face layout as exp1
VENT_COLS = 3
VENT_MARGIN_FRAC = 0.25

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl_out")


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)


def export_stl(obj, filepath):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
    print(f"  exported: {filepath}")


def face_half_dims(z):
    t = z / HEIGHT
    L = BOTTOM_L + (TOP_L - BOTTOM_L) * t
    W = BOTTOM_W + (TOP_W - BOTTOM_W) * t
    return L / 2, W / 2


def make_frustum_shell():
    bl, bw = BOTTOM_L / 2, BOTTOM_W / 2
    tl, tw = TOP_L / 2, TOP_W / 2

    verts = [
        (-bl, -bw, 0), (bl, -bw, 0), (bl, bw, 0), (-bl, bw, 0),
        (-tl, -tw, HEIGHT), (tl, -tw, HEIGHT), (tl, tw, HEIGHT), (-tl, tw, HEIGHT),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]

    mesh = bpy.data.meshes.new("frustum_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("box_shell", mesh)
    bpy.context.collection.objects.link(obj)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    solidify = obj.modifiers.new(name="solidify", type='SOLIDIFY')
    solidify.thickness = WALL_THICKNESS
    solidify.offset = -1
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=solidify.name)

    return obj


def make_cylinder_cutter(radius, depth, location, rotation_euler):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, rotation=rotation_euler
    )
    return bpy.context.active_object


def boolean_diff(target, cutter):
    mod = target.modifiers.new(name="cut", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def make_rods():
    z = HEIGHT * ROD_HEIGHT_FRAC
    half_L, half_W = face_half_dims(z)
    rod_length = (2 * half_W) * 0.9

    rods = []
    for i, frac in enumerate(ROD_X_FRACTIONS):
        x = -half_L + (2 * half_L) * frac
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ROD_DIAMETER / 2,
            depth=rod_length,
            location=(x, 0, z),
            rotation=(math.radians(90), 0, 0),
        )
        rod = bpy.context.active_object
        rod.name = f"rod_{i}"
        rods.append(rod)
    return rods


def vent_hole_positions(dim_a, dim_b):
    margin_a = dim_a * VENT_MARGIN_FRAC
    margin_b = dim_b * VENT_MARGIN_FRAC
    positions = []
    for r in range(VENT_ROWS):
        for c in range(VENT_COLS):
            a = -dim_a / 2 + margin_a + (dim_a - 2 * margin_a) * (c / max(VENT_COLS - 1, 1))
            b = -dim_b / 2 + margin_b + (dim_b - 2 * margin_b) * (r / max(VENT_ROWS - 1, 1))
            positions.append((a, b))
    return positions


def make_short_face_vents(box):
    """Same placement as experiment 1's side_mount: a grid of vents on
    BOTH short end faces - just VENT_HOLE_DIA is bigger."""
    outlet_objs = []
    for y_off, z_off in vent_hole_positions(BOTTOM_W, HEIGHT * 0.8):
        z_pos = z_off + HEIGHT / 2
        half_L_at_z, half_W_at_z = face_half_dims(z_pos)
        y_pos = max(min(y_off, half_W_at_z * (1 - VENT_MARGIN_FRAC)),
                    -half_W_at_z * (1 - VENT_MARGIN_FRAC))

        for x_sign in (-1, 1):
            loc = (x_sign * half_L_at_z, y_pos, z_pos)
            cutter = make_cylinder_cutter(
                radius=VENT_HOLE_DIA / 2, depth=WALL_THICKNESS * 20,
                location=loc, rotation_euler=(0, math.radians(90), 0),
            )
            patch = make_cylinder_cutter(
                radius=VENT_HOLE_DIA / 2, depth=PATCH_DEPTH,
                location=loc, rotation_euler=(0, math.radians(90), 0),
            )
            patch.name = f"outlet_patch_{x_sign}_{z_pos:.3f}_{y_pos:.3f}"
            outlet_objs.append(patch)
            boolean_diff(box, cutter)

    bpy.ops.object.select_all(action='DESELECT')
    for o in outlet_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = outlet_objs[0]
    bpy.ops.object.join()
    return outlet_objs[0]


def build_side_bigvent():
    clear_scene()
    box = make_frustum_shell()

    fan_z = HEIGHT / 2
    half_L, half_W = face_half_dims(fan_z)
    fan_center = (0, half_W, fan_z)  # same fan position/direction as exp1's side_mount

    fan_cutter = make_cylinder_cutter(
        radius=FAN_RADIUS, depth=WALL_THICKNESS * 20,
        location=fan_center, rotation_euler=(math.radians(90), 0, 0),
    )
    fan_patch_obj = make_cylinder_cutter(
        radius=FAN_RADIUS, depth=PATCH_DEPTH,
        location=fan_center, rotation_euler=(math.radians(90), 0, 0),
    )
    fan_patch_obj.name = "fan_patch"
    boolean_diff(box, fan_cutter)

    outlet_obj = make_short_face_vents(box)

    box.name = "side_bigvent_walls"
    rods = make_rods()

    export_variant("side_bigvent", box, fan_patch_obj, outlet_obj, rods)


def export_variant(variant_name, walls_obj, fan_obj, outlet_obj, rod_objs):
    out_dir = os.path.join(OUTPUT_DIR, variant_name)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n--- exporting variant: {variant_name} ---")
    export_stl(walls_obj, os.path.join(out_dir, f"{variant_name}_walls.stl"))
    export_stl(fan_obj, os.path.join(out_dir, f"{variant_name}_fan.stl"))
    export_stl(outlet_obj, os.path.join(out_dir, f"{variant_name}_outlet.stl"))

    bpy.ops.object.select_all(action='DESELECT')
    for r in rod_objs:
        r.select_set(True)
    bpy.context.view_layer.objects.active = rod_objs[0]
    bpy.ops.object.join()
    export_stl(rod_objs[0], os.path.join(out_dir, f"{variant_name}_rods.stl"))


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    build_side_bigvent()
    print(f"\nAll done. STL files in: {OUTPUT_DIR}")
