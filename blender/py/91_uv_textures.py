# Gives every model box-projected UVs in metres, and wires the shared textures (public/textures) into the Blender materials
# so renders show them. The website applies the same image files by material name, so they are not embedded in the exports.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, os
TEX = ROOT + "/public/textures/"
TILE = dict(concrete=4, floor=6, paving=2.4, asphalt=3, metal=1, wood=2, plastic=0.3, fabric=0.5, leather=0.4, roof=6, grass=8, led=0.5)
MATS = {  # material -> texture
    "Bowl_Concrete": "concrete", "Tunnel_Wall": "concrete", "Rail_Steel": "metal",
    "S_Wall": "concrete", "S_Dark": "concrete", "S_Concrete": "concrete", "S_Pillar": "concrete", "S_Stone": "concrete", "S_Ceiling": "concrete", "S_BoxCeiling": "concrete",
    "S_Steel": "metal", "S_Truss": "metal", "S_Wood": "wood", "S_WoodLight": "wood", "S_Carpet": "fabric", "S_Rug": "fabric", "S_Leather": "leather",
    "S_AccentYellow": "fabric", "S_AccentBlue": "fabric", "S_Screen": "led", "S_Ribbon": "led", "S_Scoreboard": "led",
    "E_Roof": "roof", "E_RoofEdge": "metal", "E_Cream": "concrete", "E_Beige": "concrete", "E_Soffit": "concrete", "E_Rail": "metal", "E_Mullion": "metal", "E_Letters": "plastic", "E_Behind": "concrete",
    "St_Deck": "wood", "St_Riser": "wood", "St_Skirt": "fabric", "St_Truss": "metal", "St_Barrier": "metal", "St_Black": "plastic", "St_Screen": "led",
    "Seat_Plastic": "plastic", "Frame_Steel": "metal", "Seat_Preview": "plastic",
}
def image(name):
    path = TEX + name
    return bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
def wire(m, tex):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    if any(n.name == "BK_Color" for n in nt.nodes): return
    uv = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); s = 1 / TILE[tex]; mp.inputs["Scale"].default_value = (s, s, s)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    col = nt.nodes.new("ShaderNodeTexImage"); col.name = "BK_Color"; col.image = image(tex + "_color.jpg"); nt.links.new(mp.outputs["Vector"], col.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Fac"].default_value = 1.0
    old = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].links else None
    if old: nt.links.new(old, mix.inputs["Color1"])
    else: mix.inputs["Color1"].default_value = b.inputs["Base Color"].default_value
    nt.links.new(col.outputs["Color"], mix.inputs["Color2"]); nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    if tex == "led":
        nt.links.new(col.outputs["Color"], b.inputs["Emission Strength"]); return
    if os.path.exists(TEX + tex + "_normal.jpg"):
        nm = nt.nodes.new("ShaderNodeTexImage"); nm.image = image(tex + "_normal.jpg"); nm.image.colorspace_settings.name = "Non-Color"; nt.links.new(mp.outputs["Vector"], nm.inputs["Vector"])
        nn = nt.nodes.new("ShaderNodeNormalMap"); nn.inputs["Strength"].default_value = 0.6; nt.links.new(nm.outputs["Color"], nn.inputs["Color"]); nt.links.new(nn.outputs["Normal"], b.inputs["Normal"])
for name, tex in MATS.items():
    m = bpy.data.materials.get(name)
    if m: wire(m, tex)

def box_uv(ob, keep=()):
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    skip = {i for i, s in enumerate(me.materials) if s and s.name in keep}
    for f in bm.faces:
        if f.material_index in skip: continue
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
    bm.to_mesh(me); bm.free()
count = 0
for cname in ("Bowl", "Structure", "Exterior", "StageSet", "Web"):
    for o in bpy.data.collections[cname].objects:
        if o.type == "MESH": box_uv(o, keep=("E_Lattice",)); count += 1
bpy.ops.wm.save_mainfile()
print("uv + textures:", count, "objects,", sum(1 for n in MATS if bpy.data.materials.get(n)), "materials")
