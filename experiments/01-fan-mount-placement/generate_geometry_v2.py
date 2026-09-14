"""
Biltong dryer box - CFD geometry generator (v2 - tapered frustum)
Run with: blender --background --python generate_geometry_v2.py

Box shape: tapered frustum (IKEA SAMLA 6-gallon), wider at top than bottom,
to match the real product's nesting taper.

  Bottom: 33 x 23 cm (long x short)
  Top:    39 x 28 cm (long x short)
  Height: 29 cm (constant)

Two fan-mount variants (short-end mounting ruled out - those faces have a
moulded depression the fan can't sit flush against):

  - side_mount: fan on one LONG wall, blowing across the short axis.
  - lid_mount:  fan on the lid, blowing down.

Both variants vent out BOTH short faces - identical outlet configuration in
both cases, so fan position is the only variable that changes between them.

Rods: two rods, oriented parallel to the SHORT axis (perpendicular to the
side-mount fan's airflow direction), so hanging meat presents more surface
area across the airflow rather than sitting inline with it.

Each variant exports 4 STLs (separate patches for OpenFOAM boundary conditions):
  <variant>_walls.stl, <variant>_fan.stl, <variant>_outlet.stl, <variant>_rods.stl

All geometry in metres (OpenFOAM's native unit).
"""

import bpy
import bmesh
import math
import os

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

CM = 0.01  # cm -> m

# Frustum dimensions - x = long axis, y = short axis, z = height
BOTTOM_L = 33 * CM
BOTTOM_W = 23 * CM
TOP_L = 39 * CM
TOP_W = 28 * CM
HEIGHT = 29 * CM

WALL_THICKNESS = 2 * CM / 10  # 2mm, cosmetic only

# Fan/outlet "patch" inserts (the thin discs that plug the holes cut in the
# walls, exported separately so OpenFOAM can tag them as distinct boundary
# patches) need to be noticeably thicker than a real wall - if they're too
# thin, snappyHexMesh can't resolve them as a surface distinct from the
# walls at any reasonable mesh resolution, and most of the opening silently
# gets meshed as solid wall instead of the intended inlet/outlet patch. A few
# mm stub is plenty (it's just a boundary-condition marker, not a real duct).
PATCH_DEPTH = 0.008  # 8mm

# Fan: 80mm PC fan (scaled down from 140mm - overkill for this box volume,
# see prior discussion). Change here if you settle on a different size.
FAN_FRAME = 0.080              # 80mm frame, in metres
FAN_BLADE_DIA = 0.070          # ~70mm blade sweep for an 80mm fan
FAN_RADIUS = FAN_BLADE_DIA / 2

# Rods: parallel to the SHORT axis (y), perpendicular to side-fan flow (x)
ROD_DIAMETER = 0.008           # 8mm
ROD_HEIGHT_FRAC = 0.65         # fraction of height, from bottom
# positions along the LONG axis (x), since rods now span the SHORT axis (y)
ROD_X_FRACTIONS = [1 / 3, 2 / 3]

# Outlet vents: grid of round holes on the wall opposite the fan
VENT_HOLE_DIA = 0.015          # 15mm
VENT_ROWS = 2
VENT_COLS = 3
VENT_MARGIN_FRAC = 0.25

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl_out")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

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
    """
    Linearly interpolate the half-length and half-width of the box's
    cross-section at height z (0 at bottom, HEIGHT at top). Returns
    (half_L, half_W) at that height - used both for building the frustum
    mesh and for correctly placing wall-mounted holes at any height.
    """
    t = z / HEIGHT  # 0 at bottom, 1 at top
    L = BOTTOM_L + (TOP_L - BOTTOM_L) * t
    W = BOTTOM_W + (TOP_W - BOTTOM_W) * t
    return L / 2, W / 2


def make_frustum_shell():
    """
    Build the tapered box as an explicit 8-vertex frustum mesh, centered
    on the long axis (x) and short axis (y), sitting on z=0 (bottom) up
    to z=HEIGHT (top/lid).
    """
    bl, bw = BOTTOM_L / 2, BOTTOM_W / 2
    tl, tw = TOP_L / 2, TOP_W / 2

    verts = [
        (-bl, -bw, 0), (bl, -bw, 0), (bl, bw, 0), (-bl, bw, 0),   # bottom face
        (-tl, -tw, HEIGHT), (tl, -tw, HEIGHT), (tl, tw, HEIGHT), (-tl, tw, HEIGHT),  # top face
    ]
    faces = [
        (0, 1, 2, 3),  # bottom
        (4, 7, 6, 5),  # top (lid)
        (0, 4, 5, 1),  # -y wall
        (1, 5, 6, 2),  # +x wall
        (2, 6, 7, 3),  # +y wall
        (3, 7, 4, 0),  # -x wall
    ]

    mesh = bpy.data.meshes.new("frustum_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("box_shell", mesh)
    bpy.context.collection.objects.link(obj)

    # shift the whole box so it sits centered at origin in x,y, matching
    # the rest of the script's assumption that x in [-L/2, L/2] etc.
    # (already true from vert construction, no shift needed)

    # recenter object origin and re-select for downstream boolean ops
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # ensure normals point outward (required for clean booleans/STL export)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # give the shell real thickness (grown inward, so the surface built above
    # stays the true outer dimension of the tote). A zero-thickness single-
    # sided sheet isn't a valid solid for Blender's boolean modifier - booleans
    # against it silently fail to leave a real through-hole (confirmed via
    # extract_feature_edges finding 0 boundary edges after cutting: a "hole"
    # that doesn't actually connect interior to exterior). Solidifying first
    # makes the fan/outlet cuts real holes through an actual wall.
    solidify = obj.modifiers.new(name="solidify", type='SOLIDIFY')
    solidify.thickness = WALL_THICKNESS
    solidify.offset = -1  # add thickness inward, keep outer surface as-is
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
    """
    Two rods parallel to the SHORT axis (y), at ROD_HEIGHT_FRAC height,
    positioned along the long axis (x) at 1/3 and 2/3 of the box's length
    AT THAT HEIGHT (since the box tapers, "length at height z" varies).
    """
    z = HEIGHT * ROD_HEIGHT_FRAC
    half_L, half_W = face_half_dims(z)
    rod_length = (2 * half_W) * 0.9  # slightly short of the walls at that height

    rods = []
    for i, frac in enumerate(ROD_X_FRACTIONS):
        x = -half_L + (2 * half_L) * frac
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ROD_DIAMETER / 2,
            depth=rod_length,
            location=(x, 0, z),
            rotation=(math.radians(90), 0, 0),  # cylinder axis Z -> rotate to Y
        )
        rod = bpy.context.active_object
        rod.name = f"rod_{i}"
        rods.append(rod)
    return rods


def vent_hole_positions(dim_a, dim_b):
    """Grid of (a, b) local offsets (centered on 0) for vent holes on a face."""
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
    """
    Cut a grid of vent holes into BOTH short faces (x = -half_L and
    x = +half_L, at each height they occur at). Used identically by both
    variants so the outlet configuration never changes - only fan position
    does - keeping the comparison clean.

    Because the box tapers, half_L (and half_W) vary with z, so each hole's
    (y, z) position is generated in a "half_W-at-mid-vent-height" local frame
    and the x position is set to the actual half_L AT THAT HOLE'S HEIGHT so
    the hole cutter cylinder fully perforates the sloped short wall.

    Returns the merged outlet patch object (already joined into one).
    """
    outlet_objs = []
    # use the box's overall width/height range for hole placement, then look
    # up the true half_L/half_W at each hole's actual height
    for y_off, z_off in vent_hole_positions(BOTTOM_W, HEIGHT * 0.8):
        z_pos = z_off + HEIGHT / 2
        half_L_at_z, half_W_at_z = face_half_dims(z_pos)
        # clamp y_off so it stays within the (possibly narrower) width at
        # this height rather than the margin computed from BOTTOM_W
        y_pos = max(min(y_off, half_W_at_z * (1 - VENT_MARGIN_FRAC)),
                    -half_W_at_z * (1 - VENT_MARGIN_FRAC))

        for x_sign in (-1, 1):  # both short faces: -x wall and +x wall
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


# ---------------------------------------------------------------------------
# VARIANT BUILDERS
# ---------------------------------------------------------------------------

def build_side_mount():
    """
    Fan on the +y long wall (blowing in -y direction, across the short axis),
    centered on that wall's length and height. Outlet vents on BOTH short
    faces (matches lid_mount's outlet config, so fan position is the only
    variable that differs between the two variants).

    NOTE: because the box tapers, the wall is slightly sloped (not vertical).
    We mount the fan at the MID-HEIGHT cross-section width/position and
    accept a small angular mismatch between the fan's flat disc and the
    slightly-angled wall - this is a reasonable simplification; the fan
    cylinder cutter still fully perforates the wall at that height.
    """
    clear_scene()
    box = make_frustum_shell()

    fan_z = HEIGHT / 2
    half_L, half_W = face_half_dims(fan_z)
    fan_center = (0, half_W, fan_z)  # +y wall, centered along x, mid-height

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

    box.name = "side_mount_walls"
    rods = make_rods()

    export_variant("side_mount", box, fan_patch_obj, outlet_obj, rods)


def build_lid_mount():
    """
    Fan on the lid (top face, z=HEIGHT), blowing down (-z).
    Outlet vents on BOTH short faces (same config as side_mount).
    """
    clear_scene()
    box = make_frustum_shell()

    fan_center = (0, 0, HEIGHT)
    fan_cutter = make_cylinder_cutter(
        radius=FAN_RADIUS, depth=WALL_THICKNESS * 20,
        location=fan_center, rotation_euler=(0, 0, 0),
    )
    fan_patch_obj = make_cylinder_cutter(
        radius=FAN_RADIUS, depth=PATCH_DEPTH,
        location=fan_center, rotation_euler=(0, 0, 0),
    )
    fan_patch_obj.name = "fan_patch"
    boolean_diff(box, fan_cutter)

    outlet_obj = make_short_face_vents(box)

    box.name = "lid_mount_walls"
    rods = make_rods()

    export_variant("lid_mount", box, fan_patch_obj, outlet_obj, rods)


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


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Box: bottom {BOTTOM_L/CM:.0f}x{BOTTOM_W/CM:.0f}cm, "
          f"top {TOP_L/CM:.0f}x{TOP_W/CM:.0f}cm, height {HEIGHT/CM:.0f}cm")
    print(f"Fan: {FAN_FRAME*1000:.0f}mm frame, {FAN_BLADE_DIA*1000:.0f}mm blade dia")

    build_side_mount()
    build_lid_mount()

    print(f"\nAll done. STL files in: {OUTPUT_DIR}")
