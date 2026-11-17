import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, os
b = bpy.data.materials["S_Ribbon"].node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.01, 0.05, 0.3, 1); b.inputs["Emission Color"].default_value = (0.03, 0.16, 0.8, 1); b.inputs["Emission Strength"].default_value = 1.2
objs = [bpy.data.objects["Structure"], bpy.data.objects["Roof"]]
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
path = ROOT + "/public/models/structure.glb"
bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=False,
                          export_normals=True, export_materials="EXPORT", export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
bpy.ops.wm.save_mainfile()
print("exported", round(os.path.getsize(path) / 1024), "KB")
