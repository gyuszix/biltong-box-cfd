"""
Biltong dryer box - geometry generator for experiment 2 (outlet alignment)

Run with: blender --background --python generate_geometry_v2.py

Tests ONE new variant: "side_aligned" - same fan as experiment 1's
side_mount (on a long wall, blowing across the short axis), but the vent
grid moves from the two short end faces (perpendicular to the jet, exp 1's
placement) to the wall directly opposite the fan (aligned with the jet).
Same total vent count/diameter as exp 1's outlet (12 holes x 15mm), just
relocated - only the placement axis changes.

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

VENT_HOLE_DIA = 0.015          # same as experiment 1
ALIGNED_VENT_ROWS = 3           # 3 x 4 = 12 holes total, same count as exp1's 6-per-face x 2 faces
ALIGNED_VENT_COLS = 4
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

    # real thickness, grown inward - required for booleans to leave clean
    # through-holes (see experiment 1's notes: a zero-thickness shell
    # doesn't cut cleanly)
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


def grid_positions(dim_a, dim_b, rows, cols):
    """Grid of (a, b) local offsets (centered on 0), analogous to exp1's
    vent_hole_positions but with explicit rows/cols."""
    margin_a = dim_a * VENT_MARGIN_FRAC
    margin_b = dim_b * VENT_MARGIN_FRAC
    positions = []
    for r in range(rows):
        for c in range(cols):
            a = -dim_a / 2 + margin_a + (dim_a - 2 * margin_a) * (c / max(cols - 1, 1))
            b = -dim_b / 2 + margin_b + (dim_b - 2 * margin_b) * (r / max(rows - 1, 1))
            positions.append((a, b))
    return positions


def make_opposite_wall_vents(box):
    """
    Cut a 3x4 grid of vents (12 total, same count/diameter as experiment
    1's outlet) into the -y wall - the wall directly opposite the fan (on
    the +y wall, blowing -y) - instead of experiment 1's two short end
    faces. Isolates placement as the only variable vs experiment 1's
    side_mount: same fan, same total vent area, different vent location.
    """
    outlet_objs = []
    for x_off, z_off in grid_positions(TOP_L * 0.8, HEIGHT * 0.8, ALIGNED_VENT_ROWS, ALIGNED_VENT_COLS):
        z_pos = z_off + HEIGHT / 2
        half_L_at_z, half_W_at_z = face_half_dims(z_pos)
        x_pos = max(min(x_off, half_L_at_z * (1 - VENT_MARGIN_FRAC)),
                    -half_L_at_z * (1 - VENT_MARGIN_FRAC))

        loc = (x_pos, -half_W_at_z, z_pos)  # -y wall, opposite the +y-mounted fan
        cutter = make_cylinder_cutter(
            radius=VENT_HOLE_DIA / 2, depth=WALL_THICKNESS * 20,
            location=loc, rotation_euler=(math.radians(90), 0, 0),
        )
        patch = make_cylinder_cutter(
            radius=VENT_HOLE_DIA / 2, depth=PATCH_DEPTH,
            location=loc, rotation_euler=(math.radians(90), 0, 0),
        )
        patch.name = f"outlet_patch_{x_pos:.3f}_{z_pos:.3f}"
        outlet_objs.append(patch)
        boolean_diff(box, cutter)

    bpy.ops.object.select_all(action='DESELECT')
    for o in outlet_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = outlet_objs[0]
    bpy.ops.object.join()
    return outlet_objs[0]


def build_side_aligned():
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

    outlet_obj = make_opposite_wall_vents(box)

    box.name = "side_aligned_walls"
    rods = make_rods()

    export_variant("side_aligned", box, fan_patch_obj, outlet_obj, rods)


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
    build_side_aligned()
    print(f"\nAll done. STL files in: {OUTPUT_DIR}")
