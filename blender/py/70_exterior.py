# The outside of BK Arena, matched to drone footage: round drum, cream roof, dusty-pink patterned screen over dark glass,
# cream terrace with white letters, beige colonnade. Colours were measured from video frames (see blender/HANDOVER.md).
# Website coordinates (x east, y up, z south) -> Blender (x, -z, y). Objects: "Exterior" and "Ext_Roof" (the site fades the roof on entry).
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

R, WALL_H = 54.0, 23.0
B = lambda p: Vector((p[0], -p[2], p[1]))
srgb = lambda h: tuple(((c / 255) ** 2.2) for c in ((h >> 16) & 255, (h >> 8) & 255, h & 255))

c = bpy.data.collections.get("Exterior")
if c:
    for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
coll = bpy.data.collections.new("Exterior"); bpy.context.scene.collection.children.link(coll)

def mat(name, color, rough=0.8, metal=0.0, emit=None, strength=1.0, tex=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if tex:
        n = next((x for x in nt.nodes if x.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
        n.image = tex; nt.links.new(n.outputs["Color"], b.inputs["Base Color"])
    m.use_backface_culling = False
    return m

# ---- the screen's pattern, painted as an image: chevrons, nested diamonds, rings, repeating round the drum
def lattice_image():
    W, H, N = 1536, 512, 3
    yy, xx = np.mgrid[0:H, 0:W]; panel = xx // (W // N); px = (xx % (W // N)) / (W // N); py = yy / H
    p = 0.088; on = lambda f: (np.mod(f / p, 1.0) < 0.52)
    chev = on(py + np.abs(np.mod(px * 2, 1.0) - 0.5) * 1.1)
    d = np.abs(px - 0.5) + np.abs(py - 0.5); diam = np.where(d < 0.5, on(d), on((px + py) * 0.9 + np.where(px > 0.5, 0.3, 0)))
    rings = on(np.hypot(px - 0.5, py - 0.5) + 0.02)
    metal = np.where(panel == 0, chev, np.where(panel == 1, diam, rings))
    frame = (px < 0.022) | (px > 0.978) | (py < 0.03) | (py > 0.97)
    metal = metal | frame
    m, g = np.array(srgb(0xc6a898)), np.array(srgb(0x1a2119))
    shade = 0.9 + 0.1 * np.sin(yy / H * 3.14)[..., None]
    rgb = np.where(metal[..., None], m * shade, g)
    img = bpy.data.images.get("lattice") or bpy.data.images.new("lattice", W, H, alpha=False)
    img.pixels.foreach_set(np.dstack([rgb, np.ones((H, W, 1))]).astype(np.float32)[::-1].ravel())
    img.filepath_raw = ROOT + "/blender/tex/lattice.png"; img.file_format = "PNG"; img.save(); img.pack()
    return img

M = dict(
    roof=mat("E_Roof", srgb(0xddcfb5), 0.85), edge=mat("E_RoofEdge", srgb(0xa5968a), 0.7),
    lattice=mat("E_Lattice", (1, 1, 1), 0.6, 0.3, tex=lattice_image()), behind=mat("E_Behind", srgb(0x1a2119), 0.9),
    glass=mat("E_Glass", srgb(0x42676f), 0.12, 0.35), glassdk=mat("E_GlassDark", srgb(0x2e4849), 0.15, 0.3),
    mull=mat("E_Mullion", srgb(0x22302f), 0.5, 0.5), cream=mat("E_Cream", srgb(0xd9d1be), 0.85), beige=mat("E_Beige", srgb(0xc9b996), 0.85),
    rail=mat("E_Rail", srgb(0xc9cac6), 0.4, 0.6), letters=mat("E_Letters", srgb(0xf6f6f2), 0.5, emit=srgb(0xf6f6f2), strength=0.35),
    soffit=mat("E_Soffit", srgb(0xe6dcc6), 0.9, emit=srgb(0xffe2b0), strength=0.15), door=mat("E_Door", srgb(0x1c2a2c), 0.2, 0.4),
)

class Build:
    def __init__(self, name): self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new("UVMap"); self.mats = []; self.name = name
    def idx(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)
    def quad(self, pts, m, uvs=None):
        try: f = self.bm.faces.new([self.bm.verts.new(B(p)) for p in pts])
        except ValueError: return
        f.material_index = self.idx(m)
        if uvs:
            for l, uv in zip(f.loops, uvs): l[self.uv].uv = uv
    def ring(self, r0, y0, r1, y1, m, a0=0.0, a1=math.tau, seg=144, urep=0):
        for i in range(seg):
            t0, t1 = i / seg, (i + 1) / seg; u0, u1 = a0 + (a1 - a0) * t0, a0 + (a1 - a0) * t1
            P = lambda a, r, y: (math.cos(a) * r, y, math.sin(a) * r)
            self.quad([P(u0, r0, y0), P(u1, r0, y0), P(u1, r1, y1), P(u0, r1, y1)], m,
                      [(t0 * urep, 0), (t1 * urep, 0), (t1 * urep, 1), (t0 * urep, 1)] if urep else None)
    def box(self, c, size, m, ry=0.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        T = Matrix.Translation(B(c)) @ Matrix.Rotation(ry, 4, "Z") @ Matrix.Diagonal((size[0], size[2], size[1], 1))
        bmesh.ops.transform(self.bm, matrix=T, verts=r["verts"]); i = self.idx(m)
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = i
    def beam(self, p, q, w, h, m):
        a, b = B(p), B(q); d = b - a
        if d.length < 1e-4: return
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        T = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((w, h, d.length, 1))
        bmesh.ops.transform(self.bm, matrix=T, verts=r["verts"]); i = self.idx(m)
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = i
    def cyl(self, c, radius, height, m, seg=14):
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius, depth=height)
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(B(c)), verts=r["verts"]); i = self.idx(m)
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = i
    def finish(self):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(self.name, me); coll.objects.link(ob)
        for m in self.mats: me.materials.append(m)
        return ob

F1, GLASS_TOP, LAT0, LAT1, EDGE = 6.6, 15.6, 15.3, 22.5, 23.8
E = Build("Exterior")
# ground floor: beige wall with dark glazed bays, glass doors at the main (south) entrance, round columns, lit ceiling
SEG = 120
for i in range(SEG):
    a0, a1 = i / SEG * math.tau, (i + 1) / SEG * math.tau; mid = math.degrees((a0 + a1) / 2)
    entrance = abs(mid - 90) < 16
    m = M["door"] if entrance else (M["glassdk"] if i % 5 in (1, 2, 3) else M["beige"])
    P = lambda a, r, y: (math.cos(a) * r, y, math.sin(a) * r)
    E.quad([P(a0, R - 4, 0), P(a1, R - 4, 0), P(a1, R - 4, F1), P(a0, R - 4, F1)], m)
    if m is not M["beige"]:
        E.beam(P(a0, R - 3.95, 0), P(a0, R - 3.95, F1), 0.1, 0.1, M["mull"]); E.beam(P(a0, R - 3.95, 3.2), P(a1, R - 3.95, 3.2), 0.08, 0.08, M["mull"])
E.ring(R - 4, F1, R + 3, F1, M["soffit"])
for i in range(32):
    a = (i + 0.5) / 32 * math.tau
    E.cyl((math.cos(a) * (R + 2), F1 / 2, math.sin(a) * (R + 2)), 0.62, F1, M["beige"])
# first-floor terrace: cream slab and a light rail
E.ring(R + 3, F1 - 0.25, R + 3, F1 + 0.85, M["cream"]); E.ring(R, F1 + 0.85, R + 3, F1 + 0.85, M["cream"])
for i in range(180):
    a0, a1 = i / 180 * math.tau, (i + 1) / 180 * math.tau
    P = lambda a, y: (math.cos(a) * (R + 2.85), y, math.sin(a) * (R + 2.85))
    E.beam(P(a0, F1 + 1.95), P(a1, F1 + 1.95), 0.05, 0.05, M["rail"]); E.beam(P(a0, F1 + 1.4), P(a1, F1 + 1.4), 0.025, 0.025, M["rail"])
    if i % 2 == 0: E.beam(P(a0, F1 + 0.85), P(a0, F1 + 1.95), 0.04, 0.04, M["rail"])
# glass drum with mullions and two transoms
E.ring(R, F1 + 0.85, R, GLASS_TOP, M["glass"])
for i in range(180):
    a0, a1 = i / 180 * math.tau, (i + 1) / 180 * math.tau
    P = lambda a, y: (math.cos(a) * (R + 0.05), y, math.sin(a) * (R + 0.05))
    E.beam(P(a0, F1 + 0.85), P(a0, GLASS_TOP), 0.07, 0.07, M["mull"])
    for y in (10.2, 13.0): E.beam(P(a0, y), P(a1, y), 0.06, 0.06, M["mull"])
# patterned screen standing proud of the glass, leaning out towards the roof; dark behind it
E.ring(R + 0.25, GLASS_TOP - 0.3, R + 0.9, LAT1, M["behind"])
E.ring(R + 1.1, LAT0, R + 2.4, LAT1, M["lattice"], urep=16)
E.ring(R + 0.9, LAT0, R + 1.1, LAT0, M["edge"])
# roof edge
E.ring(R + 2.45, LAT1, R + 2.6, EDGE, M["edge"]); E.ring(R + 0.9, LAT1, R + 2.45, LAT1, M["edge"])
ext = E.finish()

# roof: low cream dome
Rf = Build("Ext_Roof")
K = 12
for k in range(K):
    p0, p1 = k / K * math.pi / 2, (k + 1) / K * math.pi / 2
    Rf.ring((R + 2.6) * math.cos(p0), EDGE + 6.2 * math.sin(p0), (R + 2.6) * math.cos(p1) if k < K - 1 else 0.01, EDGE + 6.2 * math.sin(p1), M["roof"], seg=96)
roof = Rf.finish()
for p in roof.data.polygons: p.use_smooth = True

# "BK ARENA" in white letters on the terrace edge, facing the forecourt
letters = []
text = "BK ARENA"; step = math.radians(2.55); r = R + 3.25
for k, ch in enumerate(text):
    if ch == " ": continue
    a = math.radians(90) - (k - (len(text) - 1) / 2) * step
    cu = bpy.data.curves.new("L_" + ch, "FONT"); cu.body = ch; cu.size = 3.0; cu.extrude = 0.12; cu.align_x = "CENTER"
    o = bpy.data.objects.new("L_" + ch, cu); coll.objects.link(o)
    o.location = B((math.cos(a) * r, F1 + 1.05, math.sin(a) * r)); o.rotation_euler = (math.pi / 2, 0, math.pi / 2 - a)
    letters.append(o)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action="DESELECT")
for o in letters: o.select_set(True)
bpy.context.view_layer.objects.active = letters[0]
bpy.ops.object.convert(target="MESH"); bpy.ops.object.join()
lo = bpy.context.view_layer.objects.active; lo.name = "Ext_Letters"; lo.data.materials.clear(); lo.data.materials.append(M["letters"])
bpy.ops.wm.save_mainfile()
print("exterior:", len(ext.data.polygons), "faces | roof:", len(roof.data.polygons), "| letters:", len(lo.data.polygons))
