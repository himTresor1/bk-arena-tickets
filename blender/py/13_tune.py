import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, time
sc = bpy.context.scene
for name, power in (("key", 330), ("fill", 90), ("rim", 160)):
    bpy.data.objects[name].data.energy = power
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
bpy.data.materials["Concrete"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.09, 0.095, 1)
for n in ("Plastic_Green", "Plastic_Yellow", "Plastic_Blue"):
    b = bpy.data.materials[n].node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.38
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 0.1
sc.cycles.samples = 96
sc.render.filepath = ROOT + "/blender/renders/chair_v2.png"
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_mainfile()
print("ok")
