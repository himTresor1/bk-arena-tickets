# BK Arena tip-up stadium chair. Units: metres. The chair faces -Y, Z is up, origin on the floor under the seat.
# Parts are separate objects so the website can fold the seat: Chair_Back, Chair_Pan (origin on the hinge), Chair_Frame.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, math
from mathutils import Vector

def clean():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for b in list(coll):
            if b.users == 0: coll.remove(b)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)

def collection(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c

def mat(name, color, rough, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    return m

def grid_object(name, nu, nv, fn, coll, material, thickness, subsurf=2):
    """A quad grid shaped by fn(u, v) -> (x, y, z), u in [-1, 1], v in [0, 1], thickened and smoothed."""
    bm = bmesh.new()
    verts = [[bm.verts.new(fn(-1 + 2 * i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    me.materials.append(material)
    s = ob.modifiers.new("Thickness", "SOLIDIFY"); s.thickness = thickness; s.offset = -1
    ss = ob.modifiers.new("Smooth", "SUBSURF"); ss.levels = subsurf; ss.render_levels = subsurf + 1
    for p in me.polygons: p.use_smooth = True
    return ob

def box(name, size, loc, coll, material, rot=(0, 0, 0), bevel=0.004):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.scale = size; ob.location = loc; ob.rotation_euler = rot
    me.materials.append(material)
    if bevel:
        b = ob.modifiers.new("Bevel", "BEVEL"); b.width = bevel; b.segments = 2
    return ob

clean()
parts = collection("Chair")
plastic = mat("Seat_Plastic", (0.02, 0.19, 0.06), 0.32, coat=0.25)   # tinted per seat on the website
steel = mat("Frame_Steel", (0.012, 0.012, 0.014), 0.45, metal=0.7)
label = mat("Seat_Label", (0.9, 0.9, 0.88), 0.6)

W = 0.225  # half width of the shell

# ---- Backrest: tall shell, rounded corners, wraps slightly round the sitter, leans back
def back(u, v):
    width = W * (1 - 0.05 * v ** 5)
    y = 0.165 + 0.085 * v - 0.040 * u * u - 0.012 * math.sin(math.pi * v) + 0.02 * (1 - v) ** 3
    return (u * width, y, 0.405 + 0.535 * v)
ob_back = grid_object("Chair_Back", 6, 8, back, parts, plastic, 0.016)

# number plate near the top of the back, as on the real seats
plate = box("Chair_Label", (0.07, 0.003, 0.03), (0, back(0, 0.86)[1] - 0.003, back(0, 0.86)[2]), parts, label, rot=(math.radians(-8), 0, 0), bevel=0.002)
plate.parent = ob_back

# ---- Seat: shallow dish with a rolled front edge. Modelled folded down; origin on the hinge line.
HINGE = Vector((0, 0.15, 0.45))
def pan(u, v):  # v = 0 at the hinge, 1 at the front edge
    depth = 0.41
    y = -v * depth
    z = -0.014 * (1 - u * u) * math.sin(math.pi * min(1, v * 1.15)) - 0.03 * max(0, v - 0.82) ** 2 * 30 + 0.006
    width = 0.22 * (1 - 0.06 * v ** 4)
    return (u * width, y, z)
ob_pan = grid_object("Chair_Pan", 6, 7, pan, parts, plastic, 0.03)
ob_pan.location = HINGE

# ---- Steel frame: floor plate, post, beam under the hinge, side plates with arm pads
frame_parts = [
    box("f_plate", (0.14, 0.18, 0.012), (0, 0.19, 0.006), parts, steel),
    box("f_post", (0.055, 0.035, 0.44), (0, 0.205, 0.22), parts, steel, rot=(math.radians(4), 0, 0)),
    box("f_beam", (0.52, 0.045, 0.04), (0, 0.17, 0.425), parts, steel),
]
for sx in (-1, 1):
    x = sx * 0.248
    frame_parts += [
        box("f_side", (0.012, 0.11, 0.26), (x, 0.165, 0.53), parts, steel, rot=(math.radians(-10), 0, 0)),
        box("f_strut", (0.012, 0.045, 0.27), (x, 0.06, 0.56), parts, steel, rot=(math.radians(52), 0, 0)),
        box("f_arm", (0.042, 0.27, 0.028), (x, 0.045, 0.668), parts, steel, bevel=0.01),
    ]
# join the frame into one object
bpy.ops.object.select_all(action="DESELECT")
for o in frame_parts: o.select_set(True)
bpy.context.view_layer.objects.active = frame_parts[0]
bpy.ops.object.join()
ob_frame = bpy.context.view_layer.objects.active; ob_frame.name = "Chair_Frame"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.shade_smooth()
if hasattr(ob_frame.data, "use_auto_smooth"): ob_frame.data.use_auto_smooth = True

ob_pan["hinge"] = list(HINGE)
ob_pan["fold_up_degrees"] = 82
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/blender/bk_arena.blend")
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for o in (ob_back, ob_pan, ob_frame, plate):
    e = o.evaluated_get(dg); m = e.to_mesh(); m.calc_loop_triangles(); tris += len(m.loop_triangles); e.to_mesh_clear()
print("chair built:", [o.name for o in parts.objects], "| triangles (smoothed):", tris)
