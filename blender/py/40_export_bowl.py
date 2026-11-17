# Exports the terraces, stairs, rails and tunnels to public/models/bowl.glb (compressed).
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy
objs = [o for o in bpy.data.collections["Bowl"].objects]
bpy.ops.object.select_all(action="DESELECT")
for o in objs:
    o.select_set(True)
    if o.name.startswith("Bowl_"):
        me = o.data; me.color_attributes.active_color = me.color_attributes["Col"]
        me.color_attributes.render_color_index = list(me.color_attributes.keys()).index("Col")
bpy.context.view_layer.objects.active = objs[0]
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
kw = dict(filepath=ROOT + "/public/models/bowl.glb", export_format="GLB", use_selection=True, export_apply=True,
          export_yup=True, export_texcoords=False, export_normals=True, export_extras=True, export_materials="EXPORT")
if "export_vertex_color" in props: kw["export_vertex_color"] = "ACTIVE"
if "export_all_vertex_colors" in props: kw["export_all_vertex_colors"] = False
if "export_active_vertex_color_when_no_material" in props: kw["export_active_vertex_color_when_no_material"] = True
if "export_draco_mesh_compression_enable" in props:
    kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_draco_position_quantization=14,
              export_draco_normal_quantization=8, export_draco_color_quantization=8)
bpy.ops.export_scene.gltf(**kw)
import os
print("exported", len(objs), "objects,", round(os.path.getsize(kw["filepath"]) / 1024), "KB; options:", sorted(k for k in kw if k.startswith("export_")))
