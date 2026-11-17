import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, os
def export(names, path, tex):
    bpy.ops.object.select_all(action="DESELECT")
    objs = [bpy.data.objects[n] for n in names]
    for o in objs: o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=tex,
                              export_normals=True, export_materials="EXPORT", export_image_format="JPEG" if tex else "AUTO",
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
    return round(os.path.getsize(path) / 1024)
for c in ("Exterior", "StageSet"): bpy.data.collections[c].hide_viewport = False
a = export(["Exterior", "Ext_Roof", "Ext_Letters"], ROOT + "/public/models/exterior.glb", True)
b = export(["Stage"], ROOT + "/public/models/stage.glb", False)
print("exterior", a, "KB | stage", b, "KB")
