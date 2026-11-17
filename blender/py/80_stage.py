# Centre stage for concerts and shows (an original design): round deck with four runways, lit edge, overhead lighting ring,
# hanging speaker arrays and a crowd barrier. Website coordinates -> Blender (x, -z, y). One object: "Stage".
import bpy, bmesh, math
from mathutils import Vector, Matrix
B = lambda p: Vector((p[0], -p[2], p[1]))
c = bpy.data.collections.get("StageSet")
if c:
    for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
coll = bpy.data.collections.new("StageSet"); bpy.context.scene.collection.children.link(coll)
def mat(name, color, rough=0.6, metal=0.0, emit=None, strength=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    m.use_backface_culling = False; return m
M = dict(deck=mat("St_Deck", (0.012, 0.012, 0.014), 0.35), skirt=mat("St_Skirt", (0.004, 0.004, 0.005), 0.9),
         edge=mat("St_Edge", (0.9, 0.7, 0.05), 0.4, emit=(1.0, 0.72, 0.05), strength=3.0), blue=mat("St_Blue", (0.02, 0.3, 0.8), 0.4, emit=(0.02, 0.45, 1.0), strength=3.0),
         truss=mat("St_Truss", (0.35, 0.36, 0.38), 0.35, 0.9), black=mat("St_Black", (0.006, 0.006, 0.007), 0.5),
         lamp=mat("St_Lamp", (1, 1, 1), 0.3, emit=(1.0, 0.95, 0.85), strength=10.0), led=mat("St_Screen", (0.01, 0.02, 0.05), 0.2, emit=(0.05, 0.3, 0.6), strength=1.6),
         steel=mat("St_Barrier", (0.5, 0.52, 0.55), 0.3, 0.9), riser=mat("St_Riser", (0.1, 0.1, 0.11), 0.5))
bm = bmesh.new(); mats = []
def idx(m):
    if m not in mats: mats.append(m)
    return mats.index(m)
def mark(verts, m):
    i = idx(m)
    for f in {f for v in verts for f in v.link_faces}: f.material_index = i
def cyl(c, r, h, m, seg=32, r2=None):
    out = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(B(c)), verts=out["verts"]); mark(out["verts"], m)
def box(c, size, m, ry=0.0):
    out = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(B(c)) @ Matrix.Rotation(ry, 4, "Z") @ Matrix.Diagonal((size[0], size[2], size[1], 1)), verts=out["verts"]); mark(out["verts"], m)
def beam(p, q, w, m):
    a, b = B(p), B(q); d = b - a
    out = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((w, w, d.length, 1)), verts=out["verts"]); mark(out["verts"], m)

H = 1.4
cyl((0, H / 2, 0), 5.2, H, M["skirt"], 48)                      # main round deck
cyl((0, H + 0.02, 0), 5.2, 0.04, M["deck"], 48)
cyl((0, H - 0.12, 0), 5.26, 0.1, M["edge"], 48)                 # lit edge
cyl((0, H + 0.2, 0), 2.3, 0.32, M["riser"], 40); cyl((0, H + 0.37, 0), 2.32, 0.03, M["blue"], 40); cyl((0, H + 0.4, 0), 2.2, 0.04, M["deck"], 40)   # centre riser
for k in range(4):                                              # runways on the diagonals, with steps down to the floor
    a = math.pi / 4 + k * math.pi / 2; dx, dz = math.cos(a), math.sin(a); ry = -a
    box((dx * 6.4, H / 2, dz * 6.4), (3.0, H, 2.2), M["skirt"], ry); box((dx * 6.4, H + 0.02, dz * 6.4), (3.0, 0.04, 2.2), M["deck"], ry)
    for side in (-1, 1): box((dx * 6.4 - dz * side * 1.12, H - 0.12, dz * 6.4 + dx * side * 1.12), (3.0, 0.1, 0.05), M["edge"], ry)
    for s in range(4): box((dx * (8.1 + s * 0.3), (H - (s + 1) * 0.28) / 2, dz * (8.1 + s * 0.3)), (0.3, H - (s + 1) * 0.28, 2.0), M["skirt"], ry)
for k in range(8):                                              # floor monitors facing the performers
    a = k * math.pi / 4; box((math.cos(a) * 4.4, H + 0.2, math.sin(a) * 4.4), (0.7, 0.36, 0.5), M["black"], -a + math.pi / 2)
beam((0, H + 0.4, 0), (0, H + 1.95, 0), 0.03, M["truss"]); cyl((0, H + 1.98, 0), 0.04, 0.12, M["black"], 10); cyl((0, H + 0.43, 0), 0.22, 0.03, M["black"], 16)  # mic stand
# overhead lighting ring hung from the roof
RY, RR = 10.2, 7.0
pts = [(math.cos(i / 16 * math.tau) * RR, math.sin(i / 16 * math.tau) * RR) for i in range(16)]
for i in range(16):
    (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % 16]
    for dy in (0, 0.6): beam((x0, RY + dy, z0), (x1, RY + dy, z1), 0.09, M["truss"])
    beam((x0, RY, z0), (x0, RY + 0.6, z0), 0.06, M["truss"]); beam((x0, RY, z0), (x1, RY + 0.6, z1), 0.05, M["truss"])
    cyl((x0, RY - 0.3, z0), 0.2, 0.42, M["black"], 12); cyl((x0, RY - 0.53, z0), 0.16, 0.03, M["lamp"], 12)        # moving light
    mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
    box((mx, RY - 0.2, mz), (0.9, 0.16, 0.2), M["blue"] if i % 2 else M["edge"], math.atan2(x1 - x0, z1 - z0) + math.pi / 2)
    if i % 4 == 0: beam((x0, RY + 0.6, z0), (x0, 20.4, z0), 0.04, M["truss"])                                         # hang cable
for k in range(4):                                              # four screens under the ring, and speaker arrays between them
    a = k * math.pi / 2; dx, dz = math.cos(a), math.sin(a)
    box((dx * 5.6, RY - 2.2, dz * 5.6), (0.12, 2.7, 4.6), M["black"], -a); box((dx * 5.52, RY - 2.2, dz * 5.52), (0.04, 2.45, 4.3), M["led"], -a)
    b = a + math.pi / 4; bx, bz = math.cos(b) * 7.2, math.sin(b) * 7.2
    for s in range(6): box((bx - math.cos(b) * s * 0.07, RY - 0.9 - s * 0.42, bz - math.sin(b) * s * 0.07), (1.2, 0.38, 0.7), M["black"], -b + math.pi / 2)
    beam((bx, RY - 0.7, bz), (bx, RY + 0.3, bz), 0.04, M["truss"])
for i in range(40):                                             # crowd barrier (gaps where the runways come out)
    a0, a1 = i / 40 * math.tau, (i + 1) / 40 * math.tau; mid = math.degrees((a0 + a1) / 2) % 90
    if abs(mid - 45) < 9: continue
    p0, p1 = (math.cos(a0) * 7.9, math.sin(a0) * 7.9), (math.cos(a1) * 7.9, math.sin(a1) * 7.9)
    beam((p0[0], 1.1, p0[1]), (p1[0], 1.1, p1[1]), 0.05, M["steel"]); beam((p0[0], 0.55, p0[1]), (p1[0], 0.55, p1[1]), 0.03, M["steel"]); beam((p0[0], 0, p0[1]), (p0[0], 1.1, p0[1]), 0.04, M["steel"])
me = bpy.data.meshes.new("Stage"); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new("Stage", me); coll.objects.link(ob)
for m in mats: me.materials.append(m)
bpy.ops.wm.save_mainfile(); print("stage:", len(me.polygons), "faces")
