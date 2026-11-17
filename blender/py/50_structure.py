# Everything around the seating bowl: wall between the tiers, upper-tier supports, skyboxes, pillars, roof.
# Website coordinates (x east, y up, z south) are converted to Blender (x, -z, y).
# Two objects are produced: "Structure" (always shown) and "Roof" (only shown from inside, so the aerial view can look in).
import bpy, bmesh, math
from mathutils import Vector, Matrix

RX, RZ, WALL_H = 54.0, 54.0, 23.0  # the building is round
WZ, WX, UPX, UPZ, CR, DECK, SOFFIT, UPY, BACKY = 24.4, 36.1, 32.0, 16.4, 16.6, 6.75, 9.3, 10.9, 15.3
CORNER = (19.5, 7.8)
B = lambda p: Vector((p[0], -p[2], p[1]))
shellZ = lambda x: RZ * math.sqrt(max(0, 1 - (x / RX) ** 2)) - 0.3
shellX = lambda z: RX * math.sqrt(max(0, 1 - (z / RZ) ** 2)) - 0.3

c = bpy.data.collections.get("Structure")
if c:
    for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(c)
coll = bpy.data.collections.new("Structure"); bpy.context.scene.collection.children.link(coll)

def mat(name, color, rough=0.8, metal=0.0, emit=None, strength=1.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
        if hasattr(m, "blend_method"): m.blend_method = "BLEND"
    m.use_backface_culling = False
    return m

M = dict(
    wall=mat("S_Wall", (0.028, 0.03, 0.034), 0.9), dark=mat("S_Dark", (0.012, 0.013, 0.015), 0.95),
    conc=mat("S_Concrete", (0.16, 0.16, 0.155), 0.9), beige=mat("S_Pillar", (0.27, 0.255, 0.215), 0.85),
    steel=mat("S_Steel", (0.012, 0.012, 0.014), 0.45, 0.7), truss=mat("S_Truss", (0.05, 0.055, 0.06), 0.6, 0.6),
    glass=mat("S_Glass", (0.85, 0.93, 1.0), 0.03, 0.0, alpha=0.1),
    window=mat("S_Window", (0.05, 0.04, 0.03), 0.3, emit=(0.55, 0.38, 0.2), strength=0.6),
    led=mat("S_Ribbon", (0.02, 0.1, 0.45), 0.4, emit=(0.06, 0.25, 0.9), strength=2.2),
    exit=mat("S_Exit", (0.02, 0.4, 0.15), 0.5, emit=(0.05, 0.9, 0.3), strength=2.0),
    wood=mat("S_Wood", (0.2, 0.1, 0.045), 0.55), woodlt=mat("S_WoodLight", (0.42, 0.26, 0.13), 0.5),
    carpet=mat("S_Carpet", (0.05, 0.022, 0.02), 1.0), rug=mat("S_Rug", (0.16, 0.13, 0.1), 1.0),
    leather=mat("S_Leather", (0.02, 0.018, 0.017), 0.5), stone=mat("S_Stone", (0.5, 0.48, 0.45), 0.25),
    screen=mat("S_Screen", (0.01, 0.015, 0.03), 0.2, emit=(0.08, 0.14, 0.3), strength=1.2),
    warm=mat("S_LightWarm", (1, 0.9, 0.75), 0.5, emit=(1.0, 0.82, 0.55), strength=6.0),
    flood=mat("S_Flood", (1, 1, 1), 0.5, emit=(1.0, 0.97, 0.9), strength=12.0),
    board=mat("S_Scoreboard", (0.8, 0.8, 0.78), 0.5, emit=(0.9, 0.9, 0.86), strength=0.9),
    yellow=mat("S_AccentYellow", (0.87, 0.52, 0.02), 0.8), blue=mat("S_AccentBlue", (0.05, 0.38, 0.75), 0.8),
    ceil=mat("S_Ceiling", (0.008, 0.009, 0.011), 1.0), panel=mat("S_BoxCeiling", (0.09, 0.085, 0.08), 0.9),
)

class Build:
    def __init__(self, name): self.bm = bmesh.new(); self.mats = []; self.name = name
    def idx(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)
    def _mark(self, verts, m):
        i = self.idx(m)
        for f in {f for v in verts for f in v.link_faces}: f.material_index = i
    def box(self, c, size, m, ry=0.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        T = Matrix.Translation(B(c)) @ Matrix.Rotation(ry, 4, "Z") @ Matrix.Diagonal((size[0], size[2], size[1], 1))
        bmesh.ops.transform(self.bm, matrix=T, verts=r["verts"]); self._mark(r["verts"], m)
    def beam(self, p, q, w, h, m):
        a, b = B(p), B(q); d = b - a
        if d.length < 1e-4: return
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        T = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((w, h, d.length, 1))
        bmesh.ops.transform(self.bm, matrix=T, verts=r["verts"]); self._mark(r["verts"], m)
    def cyl(self, c, radius, height, m, seg=12):
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius, depth=height)
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(B(c)), verts=r["verts"]); self._mark(r["verts"], m)
    def quad(self, pts, m):
        try: f = self.bm.faces.new([self.bm.verts.new(B(p)) for p in pts]); f.material_index = self.idx(m)
        except ValueError: pass
    def finish(self):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(self.name, me); coll.objects.link(ob)
        for m in self.mats: me.materials.append(m)
        return ob

S = Build("Structure")

# ------------------------------------------------------------ wall between the tiers (windows, exits)
def wall_run(fixed, a0, a1, axis, sign, bays):
    """A wall along x (axis 'x', at z = sign*fixed) or along z (axis 'z', at x = sign*fixed), from a0 to a1."""
    P = (lambda u, y, off=0.0: (u, y, sign * (fixed + off))) if axis == "x" else (lambda u, y, off=0.0: (sign * (fixed + off), y, u))
    size = (lambda du, dy, dt: (du, dy, dt)) if axis == "x" else (lambda du, dy, dt: (dt, dy, du))
    L = a1 - a0; mid = (a0 + a1) / 2
    S.box(P(mid, 6.9, 0.15), size(L, 1.8, 0.3), M["wall"])                     # below the windows
    S.box(P(mid, 10.2, 0.15), size(L, 1.4, 0.3), M["wall"])                    # above the windows
    S.box(P(mid, 7.86, 0.05), size(L, 0.12, 0.5), M["conc"])                   # sill
    pitch = L / bays
    for i in range(bays + 1):
        u = a0 + i * pitch
        S.box(P(u, 8.65, 0.15), size(1.0 if 0 < i < bays else 0.5, 1.7, 0.3), M["wall"])      # pier
        if i < bays:
            uc = u + pitch / 2
            S.quad([P(u + 0.5, 7.8, 0.22), P(u + pitch - 0.5, 7.8, 0.22), P(u + pitch - 0.5, 9.5, 0.22), P(u + 0.5, 9.5, 0.22)], M["window"])
            for k in (-1, 0, 1): S.box(P(uc + k * (pitch - 1) / 3, 8.65, 0.2), size(0.06, 1.7, 0.06), M["steel"])
            S.box(P(uc, 8.65, 0.2), size(pitch - 1, 0.06, 0.06), M["steel"])
            if i % 2 == 0: S.box(P(u, 10.25, -0.02), size(0.9, 0.34, 0.05), M["exit"])
wall_run(WZ, -UPX, UPX, "x", -1, 16)                     # north
wall_run(WX, -UPZ, UPZ, "z", 1, 8); wall_run(WX, -UPZ, UPZ, "z", -1, 8)   # east, west
wall_run(WZ, CORNER[0], UPX, "x", 1, 3); wall_run(WZ, -UPX, -CORNER[0], "x", 1, 3)  # south, either side of the skyboxes

# ------------------------------------------------------------ upper tier: fascia with advert ribbon, end frames, walkways
for s in (-1, 1):
    S.box((0, 10.12, s * (WZ - 0.12)), (2 * UPX, 1.66, 0.34), M["wall"])
    S.quad([(-UPX, 9.8, s * (WZ - 0.3)), (UPX, 9.8, s * (WZ - 0.3)), (UPX, 10.75, s * (WZ - 0.3)), (-UPX, 10.75, s * (WZ - 0.3))], M["led"])
    S.box((s * (WX - 0.35), 10.12, 0), (0.4, 1.66, 2 * UPZ), M["wall"])
    S.quad([(s * (WX - 0.56), 9.8, -UPZ), (s * (WX - 0.56), 9.8, UPZ), (s * (WX - 0.56), 10.75, UPZ), (s * (WX - 0.56), 10.75, -UPZ)], M["led"])
for sx in (-1, 1):
    for sz in (-1, 1):
        # north/south tier ends (at x = +-32): raking beam on two columns, with a dark wall just behind
        x = sx * UPX
        S.beam((x, UPY - 0.5, sz * WZ), (x, BACKY - 0.2, sz * (WZ + 8.4)), 0.55, 0.9, M["conc"])
        for zz in (WZ + 1.2, WZ + 7.6):
            top = UPY - 0.9 + (zz - WZ) / 8.4 * (BACKY - UPY + 0.3)
            S.box((x, (DECK + top) / 2, sz * zz), (0.6, top - DECK, 0.6), M["conc"])
        xi = x - sx * 0.35
        S.quad([(xi, DECK, sz * WZ), (xi, DECK, sz * shellZ(UPX)), (xi, BACKY + 0.6, sz * shellZ(UPX)), (xi, BACKY + 0.6, sz * (WZ + 8.6)), (xi, UPY, sz * WZ)], M["dark"])
        # east/west tier ends (at z = +-16.4)
        z = sz * UPZ
        S.beam((sx * WX, UPY - 0.5, z), (sx * (WX + 8.1), BACKY - 0.2, z), 0.9, 0.55, M["conc"])
        for xx in (WX + 1.2, WX + 7.3):
            top = UPY - 0.9 + (xx - WX) / 8.1 * (BACKY - UPY + 0.3)
            S.box((sx * xx, (DECK + top) / 2, z), (0.6, top - DECK, 0.6), M["conc"])
        zi = z - sz * 0.35
        S.quad([(sx * WX, DECK, zi), (sx * shellX(UPZ), DECK, zi), (sx * shellX(UPZ), BACKY + 0.6, zi), (sx * (WX + 8.3), BACKY + 0.6, zi), (sx * WX, UPY, zi)], M["dark"])
def strip(points, m):
    for i in range(len(points) - 1): S.quad([points[i][0], points[i][1], points[i + 1][1], points[i + 1][0]], m)
steps = lambda n, f: [f(i / n) for i in range(n + 1)]
for s in (-1, 1):
    strip(steps(16, lambda t: ((-UPX + 2 * UPX * t, BACKY, s * 32.6), (-UPX + 2 * UPX * t, BACKY, s * shellZ(-UPX + 2 * UPX * t)))), M["wall"])   # walkway behind top rows
    strip(steps(8, lambda t: ((s * 43.8, BACKY, -UPZ + 2 * UPZ * t), (s * shellX(-UPZ + 2 * UPZ * t), BACKY, -UPZ + 2 * UPZ * t))), M["wall"])
    strip(steps(16, lambda t: ((-UPX + 2 * UPX * t, SOFFIT, s * (WZ + 0.3)), (-UPX + 2 * UPX * t, SOFFIT, s * shellZ(-UPX + 2 * UPX * t)))), M["dark"])  # under the tier
    strip(steps(8, lambda t: ((s * (WX + 0.3), SOFFIT, -UPZ + 2 * UPZ * t), (s * shellX(-UPZ + 2 * UPZ * t), SOFFIT, -UPZ + 2 * UPZ * t))), M["dark"])

# ------------------------------------------------------------ corners: concourse floor, rail, pillar with a screen
for sx in (-1, 1):
    for sz in (-1, 1):
        cx, cz = sx * CORNER[0], sz * CORNER[1]
        arc = steps(16, lambda t: (cx + sx * math.cos(t * math.pi / 2) * CR, cz + sz * math.sin(t * math.pi / 2) * CR))
        def out(p):
            k = 1 / math.sqrt((p[0] / RX) ** 2 + (p[1] / RZ) ** 2) - 0.01; return (p[0] * k, DECK, p[1] * k)
        strip([((p[0], DECK, p[1]), out(p)) for p in arc], M["wall"])
        for i in range(len(arc) - 1):                                      # kerb and rail round the top of the corner stand
            a, b = arc[i], arc[i + 1]
            S.quad([(a[0], 6.0, a[1]), (b[0], 6.0, b[1]), (b[0], 6.95, b[1]), (a[0], 6.95, a[1])], M["wall"])
            S.beam((a[0], 7.85, a[1]), (b[0], 7.85, b[1]), 0.05, 0.05, M["steel"]); S.beam((a[0], 7.4, a[1]), (b[0], 7.4, b[1]), 0.03, 0.03, M["steel"])
            if i % 2 == 0: S.beam((a[0], 6.95, a[1]), (a[0], 7.85, a[1]), 0.05, 0.05, M["steel"])
        px, pz, ry = sx * 35.4, sz * 22.2, math.atan2(-sx, -sz); H = WALL_H - DECK
        S.box((px, DECK + H / 2, pz), (5.6, H, 2.6), M["beige"], ry)
        S.box((px, DECK + 0.4, pz), (6.0, 0.8, 3.0), M["conc"], ry)
        fx, fz = -sx * math.sqrt(0.5), -sz * math.sqrt(0.5)                 # the face that looks at the court
        S.box((px + fx * 1.34, 13.6, pz + fz * 1.34), (4.9, 3.0, 0.12), M["steel"], ry)
        S.box((px + fx * 1.41, 13.6, pz + fz * 1.41), (4.5, 2.6, 0.04), M["screen"], ry)
for sx in (-1, 1):                                                          # scoreboards on the two end walls
    S.box((sx * 51.5, 19.4, 0), (0.3, 5.0, 11.6), M["steel"]); S.box((sx * 51.3, 19.4, 0), (0.06, 4.5, 11.0), M["screen"])

# ------------------------------------------------------------ skyboxes (south side): ten glass-fronted rooms
X0, BOXW, FLOOR, FRONT, BACK = -19.5, 3.9, 7.5, WZ + 0.3, WZ + 7.2
H = SOFFIT - FLOOR
S.box((0, 6.8, WZ + 0.15), (39.3, 1.6, 0.3), M["wall"])                                  # solid front below the glass
S.box((0, FLOOR - 0.15, (FRONT + BACK) / 2 - 0.15), (39.3, 0.3, BACK - WZ), M["carpet"]) # floor
S.box((0, FLOOR + 0.15, WZ + 1.95), (39.3, 0.3, 1.25), M["carpet"])                      # step for the back row of armchairs
S.box((0, FLOOR + H / 2, BACK + 0.1), (39.3, H, 0.2), M["wood"])                         # back wall
S.box((0, SOFFIT - 0.04, (FRONT + BACK) / 2), (39.3, 0.08, BACK - FRONT), M["panel"])    # ceiling
S.box((0, FLOOR + 0.12, FRONT - 0.05), (39.3, 0.06, 0.07), M["steel"]); S.box((0, SOFFIT - 0.03, FRONT - 0.05), (39.3, 0.06, 0.07), M["steel"])  # glass frame
S.quad([(X0, FLOOR + 0.1, FRONT - 0.05), (-X0, FLOOR + 0.1, FRONT - 0.05), (-X0, SOFFIT, FRONT - 0.05), (X0, SOFFIT, FRONT - 0.05)], M["glass"])   # clear glass
for i in range(11):
    x = X0 + i * BOXW
    S.box((x, (6.0 + UPY) / 2 + 0.3, WZ + 0.12), (0.34, UPY - 6.0 - 1.0, 0.36), M["conc"])       # concrete column between boxes
    S.box((x, FLOOR + H / 2, (FRONT + BACK) / 2 + 0.1), (0.14, H, BACK - FRONT - 0.2), M["woodlt"])  # wall between boxes
    if i == 10: break
    cx = x + BOXW / 2
    S.box((cx, FLOOR + H / 2, FRONT - 0.05), (0.04, H, 0.05), M["steel"])                    # slim mullion
    for sgn in (-1, 1):                                                                      # wall lights
        S.box((cx + sgn * (BOXW / 2 - 0.1), FLOOR + 1.45, WZ + 4.4), (0.05, 0.28, 0.14), M["warm"])
    for (dx, dz) in ((-0.9, 1.4), (0.9, 1.4), (-0.9, 4.3), (0.9, 4.3), (0, 6.0)):            # ceiling downlights
        S.cyl((cx + dx, SOFFIT - 0.09, WZ + dz), 0.085, 0.03, M["warm"], 10)
    # drinks rail behind the armchairs, with two stools
    S.box((cx, FLOOR + 1.34, WZ + 3.05), (3.2, 0.05, 0.36), M["stone"])
    for dx in (-1.45, 1.45): S.box((cx + dx, FLOOR + 0.82, WZ + 3.05), (0.06, 1.04, 0.06), M["steel"])
    for dx in (-0.6, 0.6):
        S.cyl((cx + dx, FLOOR + 0.78 + 0.3, WZ + 3.6), 0.19, 0.07, M["leather"], 14); S.cyl((cx + dx, FLOOR + 0.39 + 0.3, WZ + 3.6), 0.03, 0.78, M["steel"], 8)
        S.cyl((cx + dx, FLOOR + 0.02 + 0.3, WZ + 3.6), 0.2, 0.03, M["steel"], 14)
    S.box((cx, FLOOR + 0.15, WZ + 3.3), (BOXW - 0.14, 0.3, 1.5), M["carpet"])                # the rail and stools stand on the raised step too
    # lounge: rug, sofa with cushions, coffee table
    S.box((cx - 0.35, FLOOR + 0.012, WZ + 5.75), (2.6, 0.02, 1.9), M["rug"])
    sz_ = WZ + 6.62
    S.box((cx - 0.35, FLOOR + 0.24, sz_), (2.1, 0.3, 0.85), M["leather"]); S.box((cx - 0.35, FLOOR + 0.06, sz_), (2.0, 0.12, 0.75), M["steel"])
    S.box((cx - 0.35, FLOOR + 0.66, sz_ + 0.33), (2.1, 0.6, 0.2), M["leather"])
    for sgn in (-1, 1): S.box((cx - 0.35 + sgn * 1.14, FLOOR + 0.4, sz_), (0.2, 0.62, 0.85), M["leather"])
    S.box((cx - 0.95, FLOOR + 0.56, sz_ + 0.12), (0.42, 0.34, 0.14), M["yellow"], 0.25); S.box((cx + 0.25, FLOOR + 0.56, sz_ + 0.12), (0.42, 0.34, 0.14), M["blue"], -0.2)
    S.box((cx - 0.35, FLOOR + 0.36, WZ + 5.45), (1.1, 0.05, 0.6), M["stone"]); S.box((cx - 0.35, FLOOR + 0.17, WZ + 5.45), (0.9, 0.34, 0.45), M["wood"])
    # bar along the east wall of the box, with fridge, and a television on the back wall
    bx = x + BOXW - 0.42
    S.box((bx, FLOOR + 0.5, WZ + 5.2), (0.5, 1.0, 2.3), M["wood"]); S.box((bx - 0.03, FLOOR + 1.03, WZ + 5.2), (0.62, 0.05, 2.4), M["stone"])
    S.box((bx, FLOOR + 0.45, WZ + 6.75), (0.55, 0.9, 0.55), M["steel"])
    S.box((bx - 0.02, FLOOR + 1.18, WZ + 4.6), (0.12, 0.26, 0.12), M["glass"]); S.box((bx - 0.02, FLOOR + 1.16, WZ + 5.5), (0.1, 0.22, 0.1), M["yellow"])
    S.box((cx - 0.35, FLOOR + 1.5, BACK - 0.03), (1.7, 1.0, 0.06), M["steel"]); S.box((cx - 0.35, FLOOR + 1.5, BACK - 0.07), (1.55, 0.86, 0.02), M["screen"])
    S.box((x + BOXW - 0.75, FLOOR + 1.03, BACK - 0.02), (0.95, 2.06, 0.05), M["dark"])       # door
    S.cyl((x + BOXW - 1.1, FLOOR + 1.0, BACK - 0.08), 0.03, 0.14, M["stone"], 8)
struct = S.finish()

# ------------------------------------------------------------ roof: deck, steel trusses, floodlights, scoreboard cube
R = Build("Roof")
ring = [(math.cos(i / 48 * math.tau) * (RX + 1), WALL_H + 0.6, math.sin(i / 48 * math.tau) * (RZ + 1)) for i in range(48)]
for i in range(48): R.quad([(0, WALL_H + 0.6, 0), ring[i], ring[(i + 1) % 48]], M["ceil"])
TOPY, BOTY = WALL_H + 0.2, 20.4
for x in range(-48, 49, 8):                                   # main trusses span north to south
    half = shellZ(x) - 0.5
    if half < 4: continue
    R.beam((x, TOPY, -half), (x, TOPY, half), 0.22, 0.22, M["truss"]); R.beam((x, BOTY, -half), (x, BOTY, half), 0.22, 0.22, M["truss"])
    n = max(2, round(2 * half / 4.5)); d = 2 * half / n
    for k in range(n + 1):
        z = -half + k * d
        R.beam((x, BOTY, z), (x, TOPY, z), 0.1, 0.1, M["truss"])
        if k < n: R.beam((x, BOTY if k % 2 else TOPY, z), (x, TOPY if k % 2 else BOTY, z + d), 0.1, 0.1, M["truss"])
for z in range(-36, 37, 9):                                   # lighter ties east to west
    half = shellX(z) - 0.5
    R.beam((-half, BOTY, z), (half, BOTY, z), 0.16, 0.16, M["truss"]); R.beam((-half, TOPY, z), (half, TOPY, z), 0.16, 0.16, M["truss"])
for i in range(16):                                           # floodlight banks in a ring over the stands
    a = i / 16 * math.tau; lx, lz = math.cos(a) * 28, math.sin(a) * 19; ry = math.atan2(math.cos(a), math.sin(a))
    R.box((lx, BOTY - 0.25, lz), (3.4, 0.14, 0.5), M["steel"], ry)
    for k in range(4):
        ox = (k - 1.5) * 0.8; px, pz = lx + ox * math.cos(ry), lz - ox * math.sin(ry)
        R.box((px, BOTY - 0.55, pz), (0.6, 0.45, 0.5), M["steel"], ry); R.box((px, BOTY - 0.79, pz), (0.5, 0.03, 0.4), M["flood"], ry)
for (lx, lz) in ((-9, -6), (9, -6), (-9, 6), (9, 6)):          # extra bars over the court
    R.box((lx, BOTY - 0.3, lz), (5.0, 0.2, 0.5), M["steel"])
    for k in range(5): R.box((lx + (k - 2) * 1.0, BOTY - 0.45, lz), (0.7, 0.03, 0.4), M["flood"])
CY = 17.5                                                     # centre-hung scoreboard
R.box((0, CY, 0), (6.5, 4.2, 6.5), M["steel"])
for (dx, dz, sx_, sz_) in ((0, 3.27, 6.1, 0.04), (0, -3.27, 6.1, 0.04), (3.27, 0, 0.04, 6.1), (-3.27, 0, 0.04, 6.1)): R.box((dx, CY + 0.35, dz), (sx_, 3.1, sz_), M["board"])
R.box((0, CY - 1.75, 0), (6.9, 0.55, 6.9), M["steel"]); R.box((0, CY - 2.3, 0), (5.2, 0.5, 5.2), M["steel"])
for (dx, dz) in ((-2.6, -2.6), (2.6, -2.6), (-2.6, 2.6), (2.6, 2.6)): R.beam((dx, CY + 2.1, dz), (dx, BOTY, dz), 0.05, 0.05, M["steel"])
for (dx, dz) in ((-5.2, 0), (5.2, 0), (0, -5.2), (0, 5.2)):   # speaker clusters
    R.box((dx, CY + 0.6, dz), (1.1, 2.4, 1.1), M["dark"]); R.beam((dx, CY + 1.8, dz), (dx, BOTY, dz), 0.04, 0.04, M["steel"])
roof = R.finish()
for o in (struct, roof):
    for p in o.data.polygons: p.use_smooth = False
bpy.ops.wm.save_mainfile()
print("structure:", len(struct.data.polygons), "faces,", len(struct.data.materials), "materials | roof:", len(roof.data.polygons), "faces")
