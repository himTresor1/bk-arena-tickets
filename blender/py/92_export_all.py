# Exports every model for the website with UVs. Textures are NOT embedded: the site loads public/textures by material name.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, os
OUT = ROOT + "/public/models/"
def export(objs, name, materials="EXPORT", draco=True):
    for c in bpy.data.collections: c.hide_viewport = False
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=OUT + name, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=True,
              export_normals=True, export_materials=materials, export_image_format="NONE", export_extras=True)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    if "export_vertex_color" in props: kw["export_vertex_color"] = "ACTIVE"
    if "export_all_vertex_colors" in props: kw["export_all_vertex_colors"] = False
    if "export_active_vertex_color_when_no_material" in props: kw["export_active_vertex_color_when_no_material"] = True
    if draco: kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_draco_position_quantization=14, export_draco_texcoord_quantization=12)
    bpy.ops.export_scene.gltf(**kw)
    return name + " " + str(round(os.path.getsize(OUT + name) / 1024)) + " KB"
D = bpy.data
for o in D.collections["Bowl"].objects:
    if o.name.startswith("Bowl_"):
        me = o.data; me.color_attributes.active_color = me.color_attributes["Col"]; me.color_attributes.render_color_index = list(me.color_attributes.keys()).index("Col")
out = [export(list(D.collections["Bowl"].objects), "bowl.glb"),
       export([D.objects["Structure"], D.objects["Roof"]], "structure.glb"),
       export([D.objects["Exterior"], D.objects["Ext_Roof"], D.objects["Ext_Letters"]], "exterior.glb"),
       export([D.objects["Stage"]], "stage.glb"),
       export(list(D.collections["Web"].objects), "chair.glb", materials="NONE", draco=False)]
for c in ("Chair", "Web", "Review", "ExtReview"):
    if D.collections.get(c): D.collections[c].hide_viewport = True
bpy.ops.wm.save_mainfile()
print(" | ".join(out))
