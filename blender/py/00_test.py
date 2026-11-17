import bpy
print("Blender", bpy.app.version_string, "| file:", bpy.data.filepath or "(unsaved)")
print("objects:", [o.name for o in bpy.data.objects])
print("engines:", [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
print("scene engine:", bpy.context.scene.render.engine)
