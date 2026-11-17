import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, time
sc = bpy.context.scene
sc.cycles.samples = 48
sc.render.filepath = ROOT + "/blender/renders/chair_v1.png"
sc.render.image_settings.file_format = "PNG"
t = time.time()
bpy.ops.render.render(write_still=True)
print("rendered in", round(time.time() - t, 1), "s")
