# Builds the seating bowl from blender/layout.json: stepped concrete terraces, aisle stairs, tunnels and rails.
# Website coordinates are (x east, y up, z south); Blender is (x, -z, y). One mesh per section: Bowl_<id>.
import os
ROOT = os.path.expanduser("~/bk-arena")  # where this project lives
import bpy, bmesh, json, math

L = json.load(open(ROOT + "/blender/layout.json"))
B = lambda x, y, z: (x, -z, y)                      # website -> Blender
TUN = L["tunnel"]["halfWidth"]; ROOF = L["tunnel"]["roofY"]; CORNER = L["corner"]

for name in ("Bowl", "Review"):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
bowl = bpy.data.collections.new("Bowl"); bpy.context.scene.collection.children.link(bowl)

def material(name, color=(1, 1, 1), rough=0.9, metal=0.0, vertex=False, emit=None, two_sided=True):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if vertex and not any(n.type == "VERTEX_COLOR" for n in nt.nodes):
        n = nt.nodes.new("ShaderNodeVertexColor"); n.layer_name = "Col"; nt.links.new(n.outputs["Color"], b.inputs["Base Color"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 4.0
    m.use_backface_culling = not two_sided
    return m

CONCRETE = material("Bowl_Concrete", vertex=True, rough=0.92)
STEEL = material("Rail_Steel", (0.012, 0.012, 0.014), 0.45, 0.7)
TUNNEL = material("Tunnel_Wall", (0.006, 0.006, 0.007), 0.9)
DOOR = material("Tunnel_Door", (1, 0.9, 0.72), 0.5, emit=(1, 0.88, 0.68))

# surface colours painted per face (shading is baked on top later)
KICK = (0.2, 0.22, 0.2)   # the grey board along the front of the lower bowl, as in the arena
# the terraces are black concrete, like the arena floor; only the step edges and the front board are lighter
TREAD, RISER, STEP, NOSE, SIDE = (0.022, 0.023, 0.025), (0.012, 0.0125, 0.014), (0.034, 0.035, 0.037), (0.78, 0.79, 0.80), (0.012, 0.012, 0.014)

class Mesh:
    def __init__(self):
        self.bm = bmesh.new(); self.col = self.bm.loops.layers.float_color.new("Col"); self.n = 0
    def quad(self, pts, color):
        try:
            f = self.bm.faces.new([self.bm.verts.new(B(*p)) for p in pts])
        except ValueError:
            return
        for l in f.loops: l[self.col] = (*color, 1)
        self.n += 1
    def finish(self, name, mat, coll=bowl):
        me = bpy.data.meshes.new(name); self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(name, me); coll.objects.link(ob); me.materials.append(mat)
        return ob

def build_straight(cfg, m):
    a = math.radians(cfg["facing"]); ox, oz = math.cos(a), math.sin(a); tx, tz = -oz, ox
    sp = cfg.get("spacing", 0.5); rd = cfg["rowDepth"]; rise = cfg["rise"]; y0 = cfg["baseY"]; rows = cfg["rows"]; seats = cfg["seats"]
    lower = cfg["tier"] == "lower"
    Wt = seats * sp / 2 + 0.12; Ws = Wt + 0.28
    P = lambda l, d, y: (cfg["x"] + ox * d + tx * l, y, cfg["z"] + oz * d + tz * l)
    edges = [-Wt + 2 * Wt * i / seats for i in range(seats + 1)]
    floor = 0.0 if lower else y0 - 1.5
    for r in range(rows):
        d0 = r * rd - 0.4; d1 = d0 + rd; dm = (d0 + d1) / 2; y = y0 + r * rise; low = (y - rise) if r else floor
        for i in range(seats):
            la, lb = edges[i], edges[i + 1]
            m.quad([P(la, d0, low), P(lb, d0, low), P(lb, d0, y), P(la, d0, y)], KICK if (r == 0 and lower) else RISER)
            m.quad([P(la, d0, y), P(lb, d0, y), P(lb, dm, y), P(la, dm, y)], TREAD)
            m.quad([P(la, dm, y), P(lb, dm, y), P(lb, d1, y), P(la, d1, y)], TREAD)
        for s in (-1, 1):                                             # aisle steps: two per row
            la, lb = s * Wt, s * Ws
            def step(da, db, ylow, yy):
                m.quad([P(la, da, ylow), P(lb, da, ylow), P(lb, da, yy), P(la, da, yy)], RISER)
                m.quad([P(la, da, yy + 0.004), P(lb, da, yy + 0.004), P(lb, da + 0.06, yy + 0.004), P(la, da + 0.06, yy + 0.004)], NOSE)
                m.quad([P(la, da, yy), P(lb, da, yy), P(lb, db, yy), P(la, db, yy)], STEP)
                m.quad([P(lb, da, floor), P(lb, db, floor), P(lb, db, yy), P(lb, da, yy)], SIDE)   # closes the outer side
            if r == 0 and lower:                                      # steps up from the arena floor
                n = max(1, round(y0 / 0.3)); h = y0 / n
                for k in range(n - 1, 0, -1): step(d0 - k * 0.3, d0 - (k - 1) * 0.3, y0 - (k + 1) * h, y0 - k * h)
                step(d0, dm, y0 - h, y)
            else:
                step(d0, dm, (y - rise / 2) if r else floor, y)
            step(dm, d1, y, y + rise / 2)
            m.quad([P(la, dm, y), P(la, d1, y), P(la, d1, y + rise / 2), P(la, dm, y + rise / 2)], RISER)  # cheek between seats and the higher step
    return Wt

def build_arc(cfg, m):
    rd = cfg["rowDepth"]; rise = cfg["rise"]; y0 = cfg["baseY"]; rows = cfg["rows"]; cx, cz = cfg["cx"], cfg["cz"]
    a0 = math.floor(cfg["a0"] / 90) * 90.0; a1 = math.ceil(cfg["a1"] / 90) * 90.0   # meet the straight stands either side
    cut = cfg.get("cut"); lower = cfg["tier"] == "lower"; floor = 0.0 if lower else y0 - 1.5
    P = lambda ang, rho, y: (cx + math.cos(ang) * rho, y, cz + math.sin(ang) * rho)
    for r in range(rows):
        d0 = r * rd - 0.4; r_in = cfg["r0"] + d0; r_out = r_in + rd; r_mid = (r_in + r_out) / 2
        y = y0 + r * rise; low = (y - rise) if r else floor
        A0, A1 = math.radians(a0), math.radians(a1)
        if cut:                                                        # stop at the tunnel wall
            off = math.asin(min(1, TUN / r_in)); ca = math.radians(cut["a"])
            if abs(cfg["a1"] - cut["a"]) < abs(cfg["a0"] - cut["a"]): A1 = ca - off
            else: A0 = ca + off
        if A1 - A0 < 0.02: continue
        n = max(2, round(r_mid * (A1 - A0) / 0.5))
        for i in range(n):
            u0 = A0 + (A1 - A0) * i / n; u1 = A0 + (A1 - A0) * (i + 1) / n
            m.quad([P(u0, r_in, low), P(u1, r_in, low), P(u1, r_in, y), P(u0, r_in, y)], KICK if (r == 0 and lower) else RISER)
            m.quad([P(u0, r_in, y), P(u1, r_in, y), P(u1, r_mid, y), P(u0, r_mid, y)], TREAD)
            m.quad([P(u0, r_mid, y), P(u1, r_mid, y), P(u1, r_out, y), P(u0, r_out, y)], TREAD)

# ---- rails: a mesh of thin boxes along the front of each tier
rails = bmesh.new()
def bar(p, q, t=0.04):
    from mathutils import Vector, Matrix
    a, b = Vector(B(*p)), Vector(B(*q)); d = b - a
    if d.length < 1e-4: return
    r = bmesh.ops.create_cube(rails, size=1.0)
    M = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((t, t, d.length, 1))
    bmesh.ops.transform(rails, matrix=M, verts=r["verts"])
def rail_run(points, y, height):
    for i in range(len(points) - 1):
        (xa, za), (xb, zb) = points[i], points[i + 1]
        bar((xa, y + height, za), (xb, y + height, zb)); bar((xa, y + height * 0.55, za), (xb, y + height * 0.55, zb), 0.025)
    step = max(1, round(1.4 / max(0.05, math.dist(points[0], points[1]))))
    for i in range(0, len(points), step): bar((points[i][0], y, points[i][1]), (points[i][0], y + height, points[i][1]))
    bar((points[-1][0], y, points[-1][1]), (points[-1][0], y + height, points[-1][1]))

count = 0
for cfg in L["sections"]:
    if cfg["tier"] not in ("lower", "upper") or not cfg.get("enabled", True) or cfg["rise"] <= 0: continue
    m = Mesh()
    if cfg["shape"] == "arc":
        build_arc(cfg, m)
        if cfg["tier"] == "lower":
            rho = cfg["r0"] - 0.45; cut = cfg.get("cut"); a0 = math.floor(cfg["a0"] / 90) * 90.0; a1 = math.ceil(cfg["a1"] / 90) * 90.0
            A0, A1 = math.radians(a0), math.radians(a1)
            if cut:
                off = math.asin(TUN / rho); ca = math.radians(cut["a"])
                if abs(cfg["a1"] - cut["a"]) < abs(cfg["a0"] - cut["a"]): A1 = ca - off
                else: A0 = ca + off
            k = max(2, round(rho * (A1 - A0) / 0.7))
            rail_run([(cfg["cx"] + math.cos(A0 + (A1 - A0) * i / k) * rho, cfg["cz"] + math.sin(A0 + (A1 - A0) * i / k) * rho) for i in range(k + 1)], cfg["baseY"], 1.0)
    else:
        Wt = build_straight(cfg, m)
        a = math.radians(cfg["facing"]); ox, oz = math.cos(a), math.sin(a); tx, tz = -oz, ox
        k = max(2, round(2 * Wt / 0.7))
        rail_run([(cfg["x"] - ox * 0.45 + tx * (-Wt + 2 * Wt * i / k), cfg["z"] - oz * 0.45 + tz * (-Wt + 2 * Wt * i / k)) for i in range(k + 1)], cfg["baseY"], 1.0 if cfg["tier"] == "lower" else 0.95)
    ob = m.finish("Bowl_" + cfg["id"], CONCRETE)
    ob["rows"] = cfg["rows"]; ob["seats"] = cfg.get("seats", 0); ob["section"] = cfg["id"]
    count += 1
me = bpy.data.meshes.new("Rails"); rails.to_mesh(me); rails.free()
ro = bpy.data.objects.new("Rails", me); bowl.objects.link(ro); me.materials.append(STEEL)

# ---- tunnels through the four corners
t = bmesh.new()
def tq(pts, mat_index):
    f = t.faces.new([t.verts.new(B(*p)) for p in pts]); f.material_index = mat_index
for sx in (-1, 1):
    for sz in (-1, 1):
        cx, cz = sx * CORNER["x"], sz * CORNER["z"]; dx, dz = sx * math.sqrt(0.5), sz * math.sqrt(0.5); ux, uz = -dz, dx
        at = lambda r, s: (cx + dx * r + ux * s, cz + dz * r + uz * s)
        top = lambda r: 0.9 + ((r - CORNER["r"]) / 0.8) * 0.42 + 0.3
        R0, R1, RM = 4.6, 16.6, 11.2
        for s in (-TUN, TUN):
            a, b = at(R0, s), at(R1, s)
            tq([(a[0], 0, a[1]), (b[0], 0, b[1]), (b[0], top(R1), b[1]), (a[0], top(R0), a[1])], 0)
            for wo in (0.18,):                                         # give the wall some thickness and a cap
                so = s + math.copysign(wo, s); a2, b2 = at(R0, so), at(R1, so)
                tq([(a[0], top(R0), a[1]), (b[0], top(R1), b[1]), (b2[0], top(R1), b2[1]), (a2[0], top(R0), a2[1])], 0)
                tq([(a[0], 0, a[1]), (a2[0], 0, a2[1]), (a2[0], top(R0), a2[1]), (a[0], top(R0), a[1])], 0)
        m1, m2, e1, e2 = at(RM, -TUN), at(RM, TUN), at(R1 - 0.1, -TUN), at(R1 - 0.1, TUN)
        tq([(m1[0], 3.6, m1[1]), (m2[0], 3.6, m2[1]), (m2[0], ROOF, m2[1]), (m1[0], ROOF, m1[1])], 0)
        tq([(m1[0], ROOF, m1[1]), (m2[0], ROOF, m2[1]), (e2[0], ROOF, e2[1]), (e1[0], ROOF, e1[1])], 0)
        tq([(m1[0], 3.6, m1[1]), (m2[0], 3.6, m2[1]), (e2[0], 3.6, e2[1]), (e1[0], 3.6, e1[1])], 0)
        tq([(e1[0], 0, e1[1]), (e2[0], 0, e2[1]), (e2[0], 3.6, e2[1]), (e1[0], 3.6, e1[1])], 1)
me = bpy.data.meshes.new("Tunnels"); t.to_mesh(me); t.free()
to = bpy.data.objects.new("Tunnels", me); bowl.objects.link(to); me.materials.append(TUNNEL); me.materials.append(DOOR)

bpy.ops.wm.save_mainfile()
faces = sum(len(o.data.polygons) for o in bowl.objects)
print("bowl built:", count, "sections,", faces, "faces, rails", len(ro.data.polygons), "faces")
