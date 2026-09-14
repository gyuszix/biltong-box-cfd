"""
Biltong box geometry preview - renders a screenshot of one variant so you
can eyeball the geometry (taper, fan position, vents, rods) without manually
importing STLs in the Blender UI.

Run with:
    blender --background --python preview_variant.py -- side_mount
    blender --background --python preview_variant.py -- lid_mount

(the "--" separates Blender's own args from the script's args)
"""

import bpy
import sys
import os
import math

# ---------------------------------------------------------------------------
# ARGS
# ---------------------------------------------------------------------------

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
VARIANT = argv[0] if argv else "side_mount"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(SCRIPT_DIR, "stl_out", VARIANT)
OUTPUT_PNG = os.path.join(SCRIPT_DIR, "stl_out", f"{VARIANT}_preview.png")

# distinct colors per part so they're easy to tell apart in the render
PART_COLORS = {
    "walls":  (0.7, 0.7, 0.9, 0.35),   # pale blue, semi-transparent
    "fan":    (1.0, 0.2, 0.2, 1.0),    # red
    "outlet": (0.2, 1.0, 0.2, 1.0),    # green
    "rods":   (0.9, 0.6, 0.1, 1.0),    # orange
}

# ---------------------------------------------------------------------------
# SCENE SETUP
# ---------------------------------------------------------------------------

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)


def make_material(name, rgba):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        if rgba[3] < 1.0:
            mat.blend_method = 'BLEND'
            bsdf.inputs["Alpha"].default_value = rgba[3]
    return mat


def import_part(part_name):
    path = os.path.join(STL_DIR, f"{VARIANT}_{part_name}.stl")
    if not os.path.exists(path):
        print(f"  WARNING: missing {path}, skipping")
        return None

    before = set(bpy.data.objects.keys())
    bpy.ops.wm.stl_import(filepath=path)
    after = set(bpy.data.objects.keys())
    new_names = after - before
    if not new_names:
        print(f"  WARNING: import produced no object for {path}")
        return None

    obj = bpy.data.objects[list(new_names)[0]]
    obj.name = f"{VARIANT}_{part_name}"

    mat = make_material(f"mat_{part_name}", PART_COLORS.get(part_name, (0.8, 0.8, 0.8, 1.0)))
    obj.data.materials.append(mat)

    print(f"  imported: {part_name}")
    return obj


def frame_camera_on_objects(objs):
    """Position a camera to frame all given objects, looking at their
    combined bounding box from a 3/4 angle."""
    import mathutils

    min_co = mathutils.Vector((float('inf'),) * 3)
    max_co = mathutils.Vector((float('-inf'),) * 3)
    for obj in objs:
        if obj is None:
            continue
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_co = mathutils.Vector(min(a, b) for a, b in zip(min_co, world_corner))
            max_co = mathutils.Vector(max(a, b) for a, b in zip(max_co, world_corner))

    center = (min_co + max_co) / 2
    size = (max_co - min_co).length

    cam_data = bpy.data.cameras.new("preview_cam")
    cam_obj = bpy.data.objects.new("preview_cam", cam_data)
    bpy.context.collection.objects.link(cam_obj)

    # 3/4 view: offset in x, -y, +z from center, distance scaled to bbox size
    dist = size * 1.4
    cam_obj.location = center + mathutils.Vector((dist * 0.7, -dist * 0.9, dist * 0.6))

    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    bpy.context.scene.camera = cam_obj

    # basic sun light so the render isn't pitch black
    light_data = bpy.data.lights.new(name="sun", type='SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new(name="sun", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.rotation_euler = (math.radians(60), 0, math.radians(45))


def render_to_png(output_path):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = output_path
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.isdir(STL_DIR):
        print(f"ERROR: {STL_DIR} does not exist. Run generate_geometry_v2.py first.")
        sys.exit(1)

    clear_scene()

    print(f"Loading variant: {VARIANT}")
    objs = []
    for part in ("walls", "fan", "outlet", "rods"):
        objs.append(import_part(part))

    frame_camera_on_objects([o for o in objs if o is not None])
    render_to_png(OUTPUT_PNG)

    print(f"\nPreview rendered to: {OUTPUT_PNG}")
