# Leather skybox armchair, as near/far web versions added to public/models/chair.glb alongside the stadium chair.
# Same conventions as the stadium chair: faces -Y, origin on the floor, the seat cushion ("Pan") has its origin on the hinge point.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, math
from mathutils import Matrix, Vector
web = bpy.data.collections["Web"]
for o in list(web.objects):
    if o.name.startswith("Vip_"): bpy.data.objects.remove(o, do_unlink=True)
HINGE = Vector((0, 0.15, 0.45))

def part(name, boxes, bevel, origin=None, cyls=()):
    bm = bmesh.new()
    for (size, loc, rx) in boxes:
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Rotation(rx, 4, "X") @ Matrix.Diagonal((*size, 1)), verts=r["verts"])
    for (radius, depth, loc, seg) in cyls:
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius, depth=depth)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(loc), verts=r["verts"])
    if origin is not None: bmesh.ops.translate(bm, vec=-origin, verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); web.objects.link(o)
    if origin is not None: o.location = origin
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 3; b.limit_method = "ANGLE"
        for p in me.polygons: p.use_smooth = True
    return o

lean = math.radians(-9)
body = [((0.56, 0.56, 0.22), (0, 0.0, 0.31), 0), ((0.09, 0.56, 0.27), (-0.235, 0.0, 0.535), 0), ((0.09, 0.56, 0.27), (0.235, 0.0, 0.535), 0),
        ((0.56, 0.14, 0.62), (0, 0.285, 0.69), lean), ((0.4, 0.07, 0.2), (0, 0.215, 0.89), lean)]
cushion = [((0.37, 0.48, 0.13), (0, -0.02, 0.485), 0)]
legs_c = [(0.05, 0.2, (0, 0.02, 0.1), 10), (0.22, 0.03, (0, 0.02, 0.015), 16)]
objs = [part("Vip_Back_near", body, 0.035), part("Vip_Pan_near", cushion, 0.04, HINGE), part("Vip_Frame_near", [], 0, cyls=legs_c),
        part("Vip_Back_far", body[:4], 0), part("Vip_Pan_far", cushion, 0, HINGE), part("Vip_Frame_far", [((0.1, 0.1, 0.2), (0, 0.02, 0.1), 0)], 0)]

bpy.ops.object.select_all(action="DESELECT")
web.hide_viewport = False
for o in web.objects: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.gltf(filepath=ROOT + "/public/models/chair.glb", export_format="GLB", use_selection=True,
                          export_apply=True, export_yup=True, export_materials="NONE", export_texcoords=False, export_normals=True)
dg = bpy.context.evaluated_depsgraph_get(); out = {}
for o in objs:
    m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles(); out[o.name] = len(m.loop_triangles)
bpy.ops.wm.save_mainfile()
print("exported", [o.name for o in web.objects], out)
