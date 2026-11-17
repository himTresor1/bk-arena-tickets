import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy
from mathutils import Vector
B = lambda p: Vector((p[0], -p[2], p[1]))
c = bpy.data.objects["Cam_S_Wide"]; c.location = B((9, 5.6, -20)); c.data.lens = 17
c.rotation_euler = (B((-4, 9.5, 24)) - c.location).to_track_quat("-Z", "Y").to_euler()
sc = bpy.context.scene; sc.camera = c; sc.render.filepath = ROOT + "/blender/renders/struct_wide.png"
bpy.ops.render.render(write_still=True); print("ok")
