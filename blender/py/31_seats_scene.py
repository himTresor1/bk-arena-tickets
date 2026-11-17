# Places a simplified chair on every seat (one combined mesh, coloured like the real arena) and sets up lights and cameras.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, json, math, random
import numpy as np

L = json.load(open(ROOT + "/blender/layout.json"))
for name in ("Seats", "Stage"):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
seats_c = bpy.data.collections.new("Seats"); bpy.context.scene.collection.children.link(seats_c)
stage = bpy.data.collections.new("Stage"); bpy.context.scene.collection.children.link(stage)

dg = bpy.context.evaluated_depsgraph_get()
def template(name, fold=None):
    o = bpy.data.objects[name]; me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
    v = np.array([vert.co[:] for vert in me.vertices], dtype=np.float64)
    t = np.array([tri.vertices[:] for tri in me.loop_triangles], dtype=np.int64)
    o.evaluated_get(dg).to_mesh_clear()
    if fold is not None:                       # the seat pan: fold it up about its hinge
        a = math.radians(-82); R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        v = v @ R.T + np.array(fold)
    return v, t
bv, bt = template("Back_far"); pv, pt = template("Pan_far", fold=(0, 0.15, 0.45)); fv, ft = template("Frame_far")
V = np.vstack([bv, pv, fv]); T = np.vstack([bt, pt + len(bv), ft + len(bv) + len(pv)])
is_frame = np.zeros(len(V), dtype=bool); is_frame[len(bv) + len(pv):] = True

srgb = lambda h: [((c / 255) ** 2.2) for c in ((h >> 16) & 255, (h >> 8) & 255, h & 255)]
GREEN, YELLOW, BLUE, BLACK = srgb(0x1c7d45), srgb(0xf0c020), srgb(0x3ea6df), [0.01, 0.01, 0.012]
random.seed(4)
pos, rot, col = [], [], []
for cfg in L["sections"]:
    if not cfg.get("enabled", True): continue
    rows = cfg["rows"]
    for (r, s, x, y, z, ry) in cfg["seatList"]:
        pos.append((x, -z, y)); rot.append(ry)
        if cfg["tier"] in ("vip", "floor", "platform"): c = BLACK
        elif cfg["tier"] == "upper": c = random.choices([BLUE, YELLOW, GREEN], [0.7, 0.2, 0.1])[0]
        else:
            f = (r - 1) / max(1, rows - 1); c = random.choices([GREEN, YELLOW, BLUE], [0.2 + (1 - f) * 0.6, 0.42, 0.14 + f * 0.3])[0]
        col.append(c)
pos = np.array(pos); rot = np.array(rot); col = np.array(col); N = len(pos)
cs, sn = np.cos(rot), np.sin(rot)
# rotate the template about Z by ry for every seat, then move it into place
X = V[None, :, 0] * cs[:, None] - V[None, :, 1] * sn[:, None] + pos[:, None, 0]
Y = V[None, :, 0] * sn[:, None] + V[None, :, 1] * cs[:, None] + pos[:, None, 1]
Z = np.broadcast_to(V[None, :, 2], (N, len(V))) + pos[:, None, 2]
co = np.stack([X, Y, Z], axis=-1).reshape(-1, 3)
tri = (T[None, :, :] + (np.arange(N) * len(V))[:, None, None]).reshape(-1, 3)
vcol = np.where(is_frame[None, :, None], np.array(BLACK)[None, None, :], col[:, None, :]).reshape(-1, 3)

me = bpy.data.meshes.new("Seats_All")
me.vertices.add(len(co)); me.vertices.foreach_set("co", co.ravel())
me.loops.add(tri.size); me.loops.foreach_set("vertex_index", tri.ravel())
me.polygons.add(len(tri)); me.polygons.foreach_set("loop_start", np.arange(0, tri.size, 3)); me.polygons.foreach_set("loop_total", np.full(len(tri), 3))
me.update(); me.validate()
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
ca.data.foreach_set("color", np.hstack([vcol, np.ones((len(vcol), 1))]).ravel())
me.polygons.foreach_set("use_smooth", np.ones(len(tri), dtype=bool))
m = bpy.data.materials.get("Seat_Preview") or bpy.data.materials.new("Seat_Preview"); m.use_nodes = True
b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.4
if not any(n.type == "VERTEX_COLOR" for n in m.node_tree.nodes):
    n = m.node_tree.nodes.new("ShaderNodeVertexColor"); n.layer_name = "Col"; m.node_tree.links.new(n.outputs["Color"], b.inputs["Base Color"])
me.materials.append(m)
so = bpy.data.objects.new("Seats_All", me); seats_c.objects.link(so)

# arena floor and court, for context
def plane(name, sx, sy, z, color, rough=0.6):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, z)); o = bpy.context.active_object; o.name = name; o.scale = (sx, sy, 1)
    for c in o.users_collection: c.objects.unlink(o)
    stage.objects.link(o)
    mm = bpy.data.materials.get(name) or bpy.data.materials.new(name); mm.use_nodes = True
    bb = mm.node_tree.nodes["Principled BSDF"]; bb.inputs["Base Color"].default_value = (*color, 1); bb.inputs["Roughness"].default_value = rough
    o.data.materials.append(mm); return o
plane("Floor", 140, 110, -0.01, (0.14, 0.15, 0.145), 0.5)
plane("Court_Apron", 32, 20, 0.02, (0.05, 0.35, 0.62), 0.4)
plane("Court", 28, 15, 0.03, (0.62, 0.3, 0.08), 0.35)

# lighting: a ring of floodlights high over the bowl, plus a little sky fill
from mathutils import Vector
for i in range(10):
    a = i / 10 * math.tau
    d = bpy.data.lights.new("Flood", "AREA"); d.energy = 26000; d.size = 6
    o = bpy.data.objects.new("Flood", d); stage.objects.link(o); o.location = (math.cos(a) * 24, math.sin(a) * 16, 22)
    o.rotation_euler = (Vector((math.cos(a) * 30, math.sin(a) * 22, 2)) - o.location).to_track_quat("-Z", "Y").to_euler()
d = bpy.data.lights.new("Centre", "AREA"); d.energy = 30000; d.size = 12
o = bpy.data.objects.new("Centre", d); stage.objects.link(o); o.location = (0, 0, 23)
sc = bpy.context.scene
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.022, 0.028, 1)

def camera(name, loc, target, lens=35):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 600
    c = bpy.data.objects.new(name, cd); stage.objects.link(c); c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return c
camera("Cam_Aerial", (-52, -68, 58), (4, 4, 0), 30)
camera("Cam_Corner", (2, 3, 4.2), (27, -17, 4.5), 28)          # looking at the south-east corner tunnel (website z south = Blender -y)
camera("Cam_Stand", (6, 2, 5), (-2, -22, 6), 30)               # looking at the south stand with its stairs
sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 900
sc.view_settings.view_transform = "Standard"
bpy.ops.wm.save_mainfile()
print("seats placed:", N, "| triangles", len(tri))
