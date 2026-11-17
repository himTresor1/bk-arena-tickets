import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, math
from mathutils import Vector
sc = bpy.context.scene; D = bpy.data
world = D.collections["World"]; world.hide_render = False; rev = D.collections["ExtReview"]; rev.hide_render = False
keep = {"World", "ExtReview"}
hidden = [c for c in D.collections if c.name not in keep and not c.hide_render]
for c in hidden: c.hide_render = True
def mat(name, color, rough=0.5, metal=0.0, vertex=False):
    m = D.materials.get(name) or D.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if vertex and not any(n.type == "VERTEX_COLOR" for n in m.node_tree.nodes):
        n = m.node_tree.nodes.new("ShaderNodeVertexColor"); n.layer_name = "Col"; m.node_tree.links.new(n.outputs["Color"], b.inputs["Base Color"])
    return m
paints = [mat("W_Paint1", (0.5, 0.02, 0.02), 0.3, 0.4), mat("W_Paint2", (0.75, 0.75, 0.74), 0.3, 0.5), mat("W_Paint3", (0.02, 0.07, 0.25), 0.3, 0.4)]
glass, trim, light, leaf = mat("W_Glass", (0.02, 0.03, 0.035), 0.05, 0.6), mat("W_Trim", (0.01, 0.01, 0.012), 0.6), mat("W_Light", (0.95, 0.95, 0.9), 0.2), mat("W_Leaf", (1, 1, 1), 0.8, vertex=True)
pos = {"Car1": (-9, 0), "Car2": (-4, 0), "Car3": (1, 0), "Tree1": (8, 6), "Tree2": (15, 5), "Tree3": (21, 4), "Bush": (6, -1)}
for o in world.objects:
    key = o.name.split("_")[0]; x, y = pos[key]; o.location = (x, y, 0)
    if key.startswith("Car"): o.rotation_euler = (0, 0, math.radians(-35))
    o.data.materials.clear()
    part = o.name.split("_")[-1]
    o.data.materials.append({"Body": paints[int(key[3]) - 1] if key.startswith("Car") else leaf, "Glass": glass, "Trim": trim, "Lights": light}.get(part, leaf))
cd = D.cameras.new("WorldCam"); cd.lens = 38; cam = D.objects.new("WorldCam", cd); rev.objects.link(cam)
cam.location = (5, -24, 5.5); cam.rotation_euler = (Vector((6, 2, 2.6)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bg = sc.world.node_tree.nodes["Background"]; old = tuple(bg.inputs[0].default_value); bg.inputs[0].default_value = (0.38, 0.55, 0.62, 1)
sc.camera = cam; sc.cycles.samples = 48; sc.render.filepath = ROOT + "/blender/renders/world_models.png"
bpy.ops.render.render(write_still=True)
bg.inputs[0].default_value = old
for o in world.objects: o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); o.data.materials.clear()
D.objects.remove(cam, do_unlink=True)
for c in hidden: c.hide_render = False
world.hide_render = True; rev.hide_render = True
bpy.ops.wm.save_mainfile(); print("rendered")
