import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, time
sc = bpy.context.scene
for c in ("Chair", "Web", "Review"):
    col = bpy.data.collections.get(c)
    if col: col.hide_render = True
for cam, out in (("Cam_Aerial", "bowl_aerial"), ("Cam_Stand", "bowl_stand"), ("Cam_Corner", "bowl_corner")):
    sc.camera = bpy.data.objects[cam]
    sc.render.filepath = ROOT + "/blender/renders/" + out + ".png"
    t = time.time(); bpy.ops.render.render(write_still=True); print(out, round(time.time() - t, 1), "s")
