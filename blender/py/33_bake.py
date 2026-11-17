# Bakes soft contact shadows (ambient occlusion) into the concrete's vertex colours, then fixes the light levels.
import bpy, time
import numpy as np
sc = bpy.context.scene
obs = [o for o in bpy.data.collections["Bowl"].objects if o.name.startswith("Bowl_")]
for o in obs:
    me = o.data
    if "Base" not in me.color_attributes:            # keep the unshaded paint so the bake can be redone
        base = me.color_attributes.new("Base", "FLOAT_COLOR", "CORNER")
        buf = np.empty(len(me.loops) * 4, dtype=np.float32); me.color_attributes["Col"].data.foreach_get("color", buf); base.data.foreach_set("color", buf)
    if "AO" not in me.color_attributes: me.color_attributes.new("AO", "FLOAT_COLOR", "CORNER")
    me.color_attributes.active_color = me.color_attributes["AO"]
sc.render.engine = "CYCLES"; sc.cycles.samples = 32
sc.render.bake.target = "VERTEX_COLORS"
sc.world.light_settings.distance = 2.5
bpy.ops.object.select_all(action="DESELECT")
for o in obs: o.select_set(True)
bpy.context.view_layer.objects.active = obs[0]
t = time.time(); bpy.ops.object.bake(type="AO"); print("baked", len(obs), "objects in", round(time.time() - t, 1), "s")
lo = 1.0
for o in obs:
    me = o.data; n = len(me.loops) * 4
    base = np.empty(n, dtype=np.float32); ao = np.empty(n, dtype=np.float32)
    me.color_attributes["Base"].data.foreach_get("color", base); me.color_attributes["AO"].data.foreach_get("color", ao)
    base = base.reshape(-1, 4); ao = ao.reshape(-1, 4)
    shade = 0.25 + 0.75 * ao[:, :3]                   # never fully black
    lo = min(lo, float(ao[:, 0].min()))
    out = base.copy(); out[:, :3] = base[:, :3] * shade
    me.color_attributes["Col"].data.foreach_set("color", out.ravel())
    me.color_attributes.active_color = me.color_attributes["Col"]
    me.color_attributes.render_color_index = list(me.color_attributes.keys()).index("Col")
for o in bpy.data.collections["Stage"].objects:
    if o.type == "LIGHT": o.data.energy = 2600 if o.name.startswith("Centre") else 2100
sc.cycles.samples = 64
bpy.ops.wm.save_mainfile()
print("darkest AO value", round(lo, 3))
