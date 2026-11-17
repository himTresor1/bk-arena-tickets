# Web versions of the chair, exported to public/models/chair.glb:
#   *_near : the detailed chair, for the block the buyer is looking at
#   *_far  : a simplified chair with the same silhouette, for every other seat
# The seat (Pan) keeps its origin on the hinge so the site can fold it.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, math

old = bpy.data.collections.get("Web")
if old:
    for o in list(old.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
web = bpy.data.collections.new("Web"); bpy.context.scene.collection.children.link(web)
chair = bpy.data.collections["Chair"]; chair.hide_viewport = False
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

def tris(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)

def near(src_name, name, keep_origin=False):
    src = bpy.data.objects[src_name]
    for m in src.modifiers:
        if m.type == "SUBSURF": m.levels = 1
        if m.type == "BEVEL": m.segments = 1
    dg.update()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg)); me.name = name
    if not keep_origin: me.transform(src.matrix_world)
    o = bpy.data.objects.new(name, me); web.objects.link(o)
    if keep_origin: o.location = src.location
    for m in src.modifiers:
        if m.type == "SUBSURF": m.levels = 2
        if m.type == "BEVEL": m.segments = 2
    for p in me.polygons: p.use_smooth = True
    return o

def grid(name, nu, nv, fn, thickness=0.0):
    bm = bmesh.new()
    v = [[bm.verts.new(fn(-1 + 2 * i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu): bm.faces.new((v[j][i], v[j][i + 1], v[j + 1][i + 1], v[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); web.objects.link(o)
    if thickness:
        s = o.modifiers.new("t", "SOLIDIFY"); s.thickness = thickness; s.offset = -1
    for p in me.polygons: p.use_smooth = True
    return o

W = 0.225
def back(u, v):
    corner = 0.86 if v in (0.0, 1.0) else 1.0            # clip the four corners so the outline still reads as rounded
    width = W * (1 - 0.05 * v ** 5) * corner
    y = 0.165 + 0.085 * v - 0.040 * u * u - 0.012 * math.sin(math.pi * v) + 0.02 * (1 - v) ** 3
    return (u * width, y, 0.405 + 0.535 * v)
def pan(u, v):
    z = -0.014 * (1 - u * u) * math.sin(math.pi * min(1, v * 1.15)) - 0.03 * max(0, v - 0.82) ** 2 * 30 + 0.006
    return (u * 0.22 * (1 - 0.06 * v ** 4) * (0.88 if v == 1.0 else 1.0), -v * 0.41, z)

objs = [near("Chair_Back", "Back_near"), near("Chair_Pan", "Pan_near", keep_origin=True), near("Chair_Frame", "Frame_near")]
objs.append(grid("Back_far", 4, 5, back))
p = grid("Pan_far", 2, 3, pan, 0.03); p.location = bpy.data.objects["Chair_Pan"].location; objs.append(p)

# simplified frame: post, beam and the two arms
bm = bmesh.new()
def cube(size, loc, rx=0.0):
    from mathutils import Matrix, Vector
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rx, 4, "X") @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r["verts"])
cube((0.055, 0.035, 0.44), (0, 0.205, 0.22), math.radians(4))
cube((0.52, 0.045, 0.04), (0, 0.17, 0.425))
for sx in (-1, 1):
    cube((0.03, 0.27, 0.03), (sx * 0.248, 0.045, 0.668))
    cube((0.012, 0.1, 0.24), (sx * 0.248, 0.16, 0.54), math.radians(-10))
me = bpy.data.meshes.new("Frame_far"); bm.to_mesh(me); bm.free()
f = bpy.data.objects.new("Frame_far", me); web.objects.link(f); objs.append(f)

bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.gltf(filepath=ROOT + "/public/models/chair.glb", export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True, export_materials="NONE", export_texcoords=False, export_normals=True)
dg = bpy.context.evaluated_depsgraph_get()
out = {}
for o in objs:
    m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles(); out[o.name] = len(m.loop_triangles)
chair.hide_viewport = True; web.hide_render = True
bpy.ops.wm.save_mainfile()
print("triangles:", out, "| near total", sum(v for k, v in out.items() if "near" in k), "| far total", sum(v for k, v in out.items() if "far" in k))
