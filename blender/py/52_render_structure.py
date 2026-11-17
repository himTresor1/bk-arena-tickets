import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, time
from mathutils import Vector
B = lambda p: Vector((p[0], -p[2], p[1]))
stage = bpy.data.collections["Stage"]
for o in list(stage.objects):
    if o.name.startswith(("Cam_S", "BoxLight")): bpy.data.objects.remove(o, do_unlink=True)
def camera(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 600
    c = bpy.data.objects.new(name, cd); stage.objects.link(c); c.location = B(loc)
    c.rotation_euler = (B(target) - B(loc)).to_track_quat("-Z", "Y").to_euler(); return c
camera("Cam_S_BoxInside", (-0.45, 9.0, 31.1), (-2.7, 8.05, 25.0), 16)
camera("Cam_S_BoxFront", (-2, 9.2, 15.5), (-2, 8.5, 28), 32)
camera("Cam_S_Wide", (10, 13.5, -30), (-6, 7, 22), 20)
camera("Cam_S_Corner", (4, 5, -4), (34, 11, 21), 24)
for i in range(10):                      # a soft light in each skybox so the render shows the interiors
    d = bpy.data.lights.new("BoxLight", "POINT"); d.energy = 120; d.color = (1, 0.85, 0.65); d.shadow_soft_size = 0.4
    o = bpy.data.objects.new("BoxLight", d); stage.objects.link(o); o.location = B((-19.5 + (i + 0.5) * 3.9, 8.9, 28.6))
sc = bpy.context.scene; sc.cycles.samples = 64
for c in ("Chair", "Web", "Review"):
    col = bpy.data.collections.get(c)
    if col: col.hide_render = True
for cam in ("Cam_S_BoxInside", "Cam_S_BoxFront", "Cam_S_Wide", "Cam_S_Corner"):
    sc.camera = bpy.data.objects[cam]; sc.render.filepath = ROOT + "/blender/renders/struct_" + cam[6:].lower() + ".png"
    t = time.time(); bpy.ops.render.render(write_still=True); print(cam, round(time.time() - t, 1), "s")
bpy.ops.wm.save_mainfile()
