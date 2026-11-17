import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, math
from mathutils import Vector
B = lambda p: Vector((p[0], -p[2], p[1]))
srgb = lambda h: tuple(((c / 255) ** 2.2) for c in ((h >> 16) & 255, (h >> 8) & 255, h & 255))
c = bpy.data.collections.get("ExtReview")
if c:
    for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
rev = bpy.data.collections.new("ExtReview"); bpy.context.scene.collection.children.link(rev)
bpy.ops.mesh.primitive_circle_add(vertices=64, radius=400, fill_type="NGON", location=(0, 0, -0.05)); g = bpy.context.active_object; g.name = "ExtGround"
for cc in g.users_collection: cc.objects.unlink(g)
rev.objects.link(g)
m = bpy.data.materials.get("ExtPaving") or bpy.data.materials.new("ExtPaving"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*srgb(0xd7cfbc), 1); g.data.materials.append(m)
sun_d = bpy.data.lights.new("ExtSun", "SUN"); sun_d.energy = 3.2; sun_d.angle = 0.3
sun = bpy.data.objects.new("ExtSun", sun_d); rev.objects.link(sun); sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
def cam(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 2000
    o = bpy.data.objects.new(name, cd); rev.objects.link(o); o.location = B(loc)
    o.rotation_euler = (B(target) - B(loc)).to_track_quat("-Z", "Y").to_euler(); return o
cams = [cam("ExtFront", (0, 30, 175), (0, 11, 0), 40), cam("ExtClose", (20, 30, 95), (6, 19, 50), 45)]
sc = bpy.context.scene
world_col = tuple(sc.world.node_tree.nodes["Background"].inputs[0].default_value)
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (*srgb(0xa4c2ca), 1); sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
stage = bpy.data.collections["Stage"]; stage.hide_render = True
sc.cycles.samples = 64
for cm in cams:
    sc.camera = cm; sc.render.filepath = ROOT + "/blender/renders/ext_" + cm.name[3:].lower() + ".png"; bpy.ops.render.render(write_still=True)
sc.world.node_tree.nodes["Background"].inputs[0].default_value = world_col
stage.hide_render = False; rev.hide_render = True
bpy.ops.wm.save_mainfile(); print("rendered")
