# Cars, trees and shrubs for the world outside the arena, modelled here (not downloaded) and exported to public/models/world.glb.
# Cars face +z in website terms (Blender -Y), origin on the ground under the middle of the car. Each car is four parts so the site
# can paint the body any colour: Car<N>_Body, _Glass, _Trim (tyres, bumpers, grille), _Lights. Trees carry their colours per vertex.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
B = lambda p: Vector((p[0], -p[2], p[1]))
c = bpy.data.collections.get("World")
if c:
    for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
coll = bpy.data.collections.new("World"); bpy.context.scene.collection.children.link(coll)

def finish(bm, name, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    for p in me.polygons: p.use_smooth = smooth
    return o

def section(hw, yb, yt, z, top=0.86):
    ch = min(0.1, (yt - yb) * 0.4)
    return [(-hw * 0.92, yb, z), (hw * 0.92, yb, z), (hw, yb + ch, z), (hw, yt - ch, z), (hw * top, yt, z), (-hw * top, yt, z), (-hw, yt - ch, z), (-hw, yb + ch, z)]
def loft(bm, sections):
    rings = [[bm.verts.new(B(p)) for p in s] for s in sections]
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
def box(bm, c, size):
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(B(c)) @ Matrix.Diagonal((size[0], size[2], size[1], 1)), verts=r["verts"])
def wheel(bm, x, z, r, w):
    out = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=w)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(B((x, r, z))) @ Matrix.Rotation(math.pi / 2, 4, "Y"), verts=out["verts"])

def car(n, L, belt, roof, hw, cab0, cab1, wheel_r):
    """L = half length, belt = height of the window line, roof = roof height, cab0..cab1 = where the cabin sits along the car."""
    h = L
    body = bmesh.new()
    loft(body, [section(hw * 0.84, 0.36, belt * 0.62, -h), section(hw * 0.97, 0.26, belt * 0.93, -h + 0.16), section(hw, 0.24, belt, cab0 - 0.1),
                section(hw, 0.24, belt, cab1 + 0.1), section(hw * 0.97, 0.26, belt * 0.9, h - 0.5), section(hw * 0.84, 0.36, belt * 0.6, h)])
    loft(body, [section(hw * 0.78, roof - 0.05, roof + 0.02, cab0 + 0.55, 0.9), section(hw * 0.78, roof - 0.03, roof + 0.03, cab1 - 0.75, 0.9)])   # roof panel
    glass = bmesh.new()
    loft(glass, [section(hw * 0.9, belt - 0.02, belt, cab0, 0.95), section(hw * 0.8, belt - 0.02, roof, cab0 + 0.5, 0.9),
                 section(hw * 0.8, belt - 0.02, roof, cab1 - 0.7, 0.9), section(hw * 0.9, belt - 0.02, belt, cab1, 0.95)])
    trim = bmesh.new()
    for x in (-hw + 0.04, hw - 0.04):
        for z in (-h * 0.62, h * 0.62): wheel(trim, x, z, wheel_r, 0.24)
    box(trim, (0, 0.33, h - 0.02), (hw * 1.5, 0.2, 0.1)); box(trim, (0, 0.33, -h + 0.02), (hw * 1.5, 0.2, 0.1)); box(trim, (0, 0.52, h + 0.005), (hw * 0.8, 0.14, 0.04))
    lights = bmesh.new()
    for x in (-hw * 0.62, hw * 0.62): box(lights, (x, belt * 0.56, h - 0.02), (0.3, 0.1, 0.08))
    return [finish(body, f"Car{n}_Body"), finish(glass, f"Car{n}_Glass"), finish(trim, f"Car{n}_Trim"), finish(lights, f"Car{n}_Lights", False)]

objs = car(1, 2.2, 0.98, 1.42, 0.9, -1.25, 1.0, 0.32)          # saloon
objs += car(2, 2.35, 1.18, 1.76, 0.95, -2.15, 1.0, 0.38)        # 4x4, the commonest shape on Kigali's roads
objs += car(3, 1.9, 1.0, 1.52, 0.86, -1.75, 0.85, 0.3)          # small hatchback

# ---- planting: colours are painted per vertex (darker underneath and inside, lighter on top)
random.seed(11)
def blob(bm, col, c, r, squash, base, top):
    out = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
    for v in out["verts"]:
        d = 1 + 0.16 * (random.random() - 0.5)
        local = Vector((v.co.x * d, v.co.y * d, v.co.z * d * squash))
        t = (local.z / (r * squash) + 1) / 2
        shade = 0.55 + 0.45 * t + 0.08 * (random.random() - 0.5)
        v.co = B(c) + local
        for l in v.link_loops: l[col] = (*[base[i] + (top[i] - base[i]) * t * 0.6 for i in range(3)], 1)
        for l in v.link_loops: l[col] = (l[col][0] * shade, l[col][1] * shade, l[col][2] * shade, 1)
def trunk(bm, col, pts, r0, r1, colour):
    rings = []
    for i, p in enumerate(pts):
        r = r0 + (r1 - r0) * i / (len(pts) - 1)
        rings.append([bm.verts.new(B((p[0] + math.cos(a) * r, p[1], p[2] + math.sin(a) * r))) for a in [k / 7 * math.tau for k in range(7)]])
    for a, b in zip(rings, rings[1:]):
        for i in range(7):
            f = bm.faces.new((a[i], a[(i + 1) % 7], b[(i + 1) % 7], b[i]))
            for l in f.loops: l[col] = (*[colour[k] * (0.8 + 0.2 * random.random()) for k in range(3)], 1)
def new():
    bm = bmesh.new(); return bm, bm.loops.layers.float_color.new("Col")
G1, G1T = (0.05, 0.16, 0.035), (0.2, 0.36, 0.08); G2, G2T = (0.07, 0.17, 0.06), (0.24, 0.34, 0.13); BARK, PALE = (0.1, 0.07, 0.045), (0.3, 0.26, 0.2)

bm, col = new()                                                   # broadleaf shade tree
trunk(bm, col, [(0, 0, 0), (0.05, 1.6, 0.02), (0.12, 3.2, -0.05), (0.2, 4.4, 0.0)], 0.3, 0.14, BARK)
trunk(bm, col, [(0.1, 2.9, 0), (-0.8, 4.2, 0.5)], 0.13, 0.07, BARK); trunk(bm, col, [(0.1, 3.0, 0), (0.9, 4.3, -0.6)], 0.12, 0.07, BARK)
for (p, r) in (((0.2, 5.6, 0), 2.3), ((-1.5, 4.9, 0.8), 1.7), ((1.6, 5.0, -0.9), 1.8), ((0.3, 5.0, 1.7), 1.6), ((-0.4, 5.2, -1.7), 1.7), ((0.1, 6.9, 0.2), 1.5)):
    blob(bm, col, p, r, 0.8, G1, G1T)
objs.append(finish(bm, "Tree1"))
bm, col = new()                                                   # tall slender tree
trunk(bm, col, [(0, 0, 0), (0.05, 3, 0.03), (0.0, 6, -0.04), (0.06, 8.5, 0)], 0.2, 0.07, PALE)
for (p, r) in (((0, 5.2, 0.1), 1.25), ((0.3, 6.8, -0.2), 1.35), ((-0.2, 8.3, 0.1), 1.15), ((0.1, 9.7, 0), 0.85), ((-0.5, 6.0, 0.5), 0.9)):
    blob(bm, col, p, r, 1.15, G2, G2T)
objs.append(finish(bm, "Tree2"))
bm, col = new()                                                   # palm
trunk(bm, col, [(0, 0, 0), (0.12, 1.7, 0), (0.35, 3.4, 0.05), (0.7, 5.1, 0.1), (1.1, 6.6, 0.1)], 0.24, 0.15, PALE)
top = Vector((1.1, 6.6, 0.1))
for k in range(11):
    a = k / 11 * math.tau + random.random() * 0.2; reach = 3.0 + random.random() * 0.7; prev = None
    for s in range(6):
        t = s / 5; out = reach * t; drop = 1.1 * t * t * (1.6 if k % 2 else 1.0) - 0.9 * t
        ctr = (top.x + math.cos(a) * out, top.y - drop + 0.2, top.z + math.sin(a) * out); wdt = 0.42 * math.sin(math.pi * min(1, t * 1.05 + 0.08)) + 0.04
        px, pz = -math.sin(a) * wdt, math.cos(a) * wdt
        cur = (bm.verts.new(B((ctr[0] + px, ctr[1] - 0.12, ctr[2] + pz))), bm.verts.new(B((ctr[0], ctr[1], ctr[2]))), bm.verts.new(B((ctr[0] - px, ctr[1] - 0.12, ctr[2] - pz))))
        if prev:
            for i in range(2):
                f = bm.faces.new((prev[i], prev[i + 1], cur[i + 1], cur[i]))
                for l in f.loops: l[col] = (*[(G2[j] + (G2T[j] - G2[j]) * (0.4 + 0.6 * t)) for j in range(3)], 1)
        prev = cur
objs.append(finish(bm, "Tree3"))
bm, col = new()                                                   # clipped shrub
for (p, r) in (((0, 0.55, 0), 0.75), ((0.6, 0.45, 0.25), 0.6), ((-0.55, 0.5, -0.2), 0.62), ((0.1, 0.5, -0.6), 0.55)):
    blob(bm, col, p, r, 0.85, G1, (0.22, 0.4, 0.1))
objs.append(finish(bm, "Bush"))
for o in objs:
    if "Col" in o.data.color_attributes: o.data.color_attributes.active_color = o.data.color_attributes["Col"]

bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
import os
path = ROOT + "/public/models/world.glb"
kw = dict(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=False, export_normals=True, export_materials="NONE")
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
if "export_vertex_color" in props: kw["export_vertex_color"] = "ACTIVE"
if "export_active_vertex_color_when_no_material" in props: kw["export_active_vertex_color_when_no_material"] = True
bpy.ops.export_scene.gltf(**kw)
coll.hide_render = True
bpy.ops.wm.save_mainfile()
print("world models:", {o.name: len(o.data.polygons) for o in objs}, round(os.path.getsize(path) / 1024), "KB")
