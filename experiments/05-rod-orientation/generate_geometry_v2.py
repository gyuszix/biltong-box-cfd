"""
Biltong dryer box - geometry generator for experiment 5 (rod orientation)

Run with: blender --background --python generate_geometry_v2.py

Tests ONE new variant: "rods_lengthwise" - takes experiment 4's end_mount
box (fan on the -x short face blowing in +x, all 12 vents consolidated on
the opposite +x short face) and rotates the two rods 90 degrees so they run
LENGTHWISE (along x, parallel to the fan's flow axis) instead of CROSSWISE
(along y, perpendicular to it, as in every previous experiment). Fan/vent
placement, box geometry, fan speed and vent size/count are all unchanged -
rod orientation is the only variable.

Compare against experiment 4's end_mount, reused as-is (not regenerated),
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
ROD_Y_FRACTIONS = [1 / 3, 2 / 3]  # rods spaced across y, span x (lengthwise)

VENT_HOLE_DIA = 0.015
VENT_ROWS = 3
VENT_COLS = 4
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


def make_rods_lengthwise():
    """
    Rods rotated 90 degrees from every previous experiment: run along x
    (parallel to end_mount's fan-to-vent flow axis) instead of along y.
    Spaced at two y positions instead of two x positions.
    """
    z = HEIGHT * ROD_HEIGHT_FRAC
    half_L, half_W = face_half_dims(z)
    rod_length = (2 * half_L) * 0.9  # same 10%-margin convention as the crosswise rods

    rods = []
    for i, frac in enumerate(ROD_Y_FRACTIONS):
        y = -half_W + (2 * half_W) * frac
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ROD_DIAMETER / 2,
            depth=rod_length,
            location=(0, y, z),
            rotation=(0, math.radians(90), 0),
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


def make_single_short_face_vents(box, x_sign):
    """
    Cut a 3x4 grid (12 holes) into ONE short face only (x_sign = -1 or +1) -
    identical to experiment 4's version, unchanged.
    """
    outlet_objs = []
    for y_off, z_off in vent_hole_positions(BOTTOM_W, HEIGHT * 0.8):
        z_pos = z_off + HEIGHT / 2
        half_L_at_z, half_W_at_z = face_half_dims(z_pos)
        y_pos = max(min(y_off, half_W_at_z * (1 - VENT_MARGIN_FRAC)),
                    -half_W_at_z * (1 - VENT_MARGIN_FRAC))

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


def build_rods_lengthwise():
    """
    Same fan/vent layout as experiment 4's end_mount (fan on -x short face
    blowing in +x, 12 vents consolidated on the opposite +x short face), but
    rods run lengthwise (along x) instead of crosswise (along y).
    """
    clear_scene()
    box = make_frustum_shell()

    fan_z = HEIGHT / 2
    half_L, half_W = face_half_dims(fan_z)
    fan_center = (-half_L, 0, fan_z)  # -x wall, centered, mid-height

    fan_cutter = make_cylinder_cutter(
        radius=FAN_RADIUS, depth=WALL_THICKNESS * 20,
        location=fan_center, rotation_euler=(0, math.radians(90), 0),
    )
    fan_patch_obj = make_cylinder_cutter(
        radius=FAN_RADIUS, depth=PATCH_DEPTH,
        location=fan_center, rotation_euler=(0, math.radians(90), 0),
    )
    fan_patch_obj.name = "fan_patch"
    boolean_diff(box, fan_cutter)

    outlet_obj = make_single_short_face_vents(box, x_sign=1)

    box.name = "rods_lengthwise_walls"
    rods = make_rods_lengthwise()

    export_variant("rods_lengthwise", box, fan_patch_obj, outlet_obj, rods)


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
    build_rods_lengthwise()
    print(f"\nAll done. STL files in: {OUTPUT_DIR}")
