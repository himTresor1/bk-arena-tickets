# Review set-up: a short row of chairs on a concrete step, in the arena's real colours, lit like a product shot.
import bpy, math
from mathutils import Vector

old = bpy.data.collections.get("Review")
if old:
    for o in list(old.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
rev = bpy.data.collections.new("Review"); bpy.context.scene.collection.children.link(rev)

def mat(name, color, rough, metal=0.0, coat=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    return m

srgb = lambda h: tuple(((c / 255) ** 2.2) for c in ((h >> 16) & 255, (h >> 8) & 255, h & 255))
colours = [mat("Plastic_Green", srgb(0x1c7d45), 0.32, coat=0.25), mat("Plastic_Yellow", srgb(0xf0c020), 0.32, coat=0.25),
           mat("Plastic_Blue", srgb(0x3ea6df), 0.32, coat=0.25)]
order = [1, 0, 2, 1, 0]          # colours along the row
folded = [True, True, False, True, True]

src = {n: bpy.data.objects[n] for n in ("Chair_Back", "Chair_Pan", "Chair_Frame", "Chair_Label")}
for i, (ci, up) in enumerate(zip(order, folded)):
    x = (i - 2) * 0.5
    copies = {}
    for n, o in src.items():
        c = o.copy(); rev.objects.link(c); copies[n] = c
        if n != "Chair_Label": c.location = o.location + Vector((x, 0, 0))
        if n in ("Chair_Back", "Chair_Pan"):
            c.material_slots[0].link = "OBJECT"; c.material_slots[0].material = colours[ci]
    copies["Chair_Label"].parent = copies["Chair_Back"]
    if up: copies["Chair_Pan"].rotation_euler = (math.radians(-82), 0, 0)
bpy.data.collections["Chair"].hide_render = True; bpy.data.collections["Chair"].hide_viewport = True

# concrete terrace: the step the chairs stand on, the riser behind, and the step in front
concrete = mat("Concrete", (0.2, 0.2, 0.2), 0.85)
def slab(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.active_object; o.name = name; o.scale = size
    for c in o.users_collection: c.objects.unlink(o)
    rev.objects.link(o); o.data.materials.append(concrete); return o
slab("step", (6, 0.8, 0.42), (0, -0.05, -0.21))
slab("step_back", (6, 0.8, 0.42), (0, 0.75, 0.21))
slab("step_front", (6, 3, 0.42), (0, -1.95, -0.63))

# lights and camera
def area(name, loc, target, power, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA"); d.energy = power; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); rev.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o
area("key", (-2.2, -3.0, 3.2), (0, 0, 0.6), 900, 2.5)
area("fill", (3.0, -2.0, 1.6), (0, 0, 0.6), 250, 3.0, (0.85, 0.92, 1))
area("rim", (0.5, 2.5, 2.6), (0, 0, 0.7), 400, 2.0)
cam_d = bpy.data.cameras.new("ReviewCam"); cam_d.lens = 50
cam = bpy.data.objects.new("ReviewCam", cam_d); rev.objects.link(cam)
cam.location = (-1.55, -2.55, 1.25)
cam.rotation_euler = (Vector((0.1, 0.05, 0.55)) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()

sc = bpy.context.scene; sc.camera = cam
sc.render.engine = "CYCLES"; sc.cycles.samples = 96; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1400, 900, 100
sc.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in type(sc.view_settings).bl_rna.properties["view_transform"].enum_items] else sc.view_settings.view_transform
w = sc.world or bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.014, 0.018, 1)
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"; prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception as ex:
    print("GPU not set:", ex)
bpy.ops.wm.save_mainfile()
print("review scene ready; engine", sc.render.engine, "device", sc.cycles.device)
