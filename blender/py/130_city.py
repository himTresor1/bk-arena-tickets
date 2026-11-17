# Builds the district around the sports complex from the site plan (blender/site.json, made by scripts/site_from_osm.py):
# roads with kerbs, pavements and markings, car parks with bays, pitches, courts, the training track, lawns, and every
# mapped building with walls, windows and a roof. Writes public/models/city.glb and public/tour/site.json (trees, cars, lamps).
# Run:  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/py/130_city.py
# Site axes: x = east, y = up, z = south, origin at the centre of BK Arena. Textures are applied by material name in src/tour.js.
import bpy, json, math, os, random
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT = os.path.expanduser("~/bk-arena")
S = json.load(open(ROOT + "/blender/site.json"))
rng = random.Random(11)
lin = lambda h: tuple(((((h >> s) & 255) / 255) ** 2.2) for s in (16, 8, 0))  # hex colour -> linear, as glTF wants

# ---- where the hand-built venues stand (must match src/tour.js)
ARENA = (0.0, 0.0)
STADIUM = next(s for s in S["stadiums"] if "Amahoro" in (s["name"] or ""))["pts"]
ZARIA = {"c": (-410.7, 463.3), "ang": math.radians(-23.0), "half": (122.0, 50.0)}   # centre, direction of its long side, half sizes
HALLS = {"c": (-222.0, 380.0), "ang": math.radians(-5.8), "half": (56.0, 30.0)}
COMPLEX = [(-60, -141), (-160, -50), (-260, 69), (-354, 200), (-447, 350), (-516, 475), (-513, 548), (-372, 498), (-210, 429),
           (-29, 351), (96, 298), (184, 273), (199, 250), (165, 175), (234, 81), (221, -12), (202, -56), (102, -75), (59, -119)]


class Mesh:
    def __init__(self, name, colored=False):
        self.name, self.colored, self.v, self.uv, self.c, self.f = name, colored, [], [], [], []

    def add(self, pts, uvs, col=(1, 1, 1), up=(0, 1, 0)):
        a, b, c = (np.array(p, dtype=float) for p in pts[:3])
        if np.dot(np.cross(b - a, c - a), up) < 0: pts, uvs = pts[::-1], uvs[::-1]
        n = len(self.v)
        self.v += [tuple(p) for p in pts]; self.uv += [tuple(u) for u in uvs]; self.c += [col] * len(pts)
        for i in range(1, len(pts) - 1): self.f.append((n, n + i, n + i + 1))


M = {n: Mesh(n, n in ("C_House", "C_Office", "C_Sheet", "C_RoofFlat")) for n in
     ("C_Road", "C_Parking", "C_Marking", "C_Kerb", "C_Sidewalk", "C_Paving", "C_Lawn", "C_Turf", "C_Track", "C_Soccer", "C_Pitch5", "C_Tennis",
      "C_Basket", "C_Fence", "C_House", "C_Office", "C_Sheet", "C_RoofFlat", "C_Path", "C_PavingB")}


# ---------- small geometry helpers (all in the ground plane, points are (x, z))
def clean(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 0.05: out.append(p)
    return out

def area2(p): return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2

def inside(p, poly):
    x, z = p; hit = False; n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1: hit = not hit
    return hit

def obb(pts):
    """Smallest rectangle round a polygon: centre, long axis, short axis, length, width."""
    P = np.array(pts, dtype=float); best = None
    for i in range(len(P)):
        d = P[(i + 1) % len(P)] - P[i]; l = np.linalg.norm(d)
        if l < 0.3: continue
        u = d / l; v = np.array([-u[1], u[0]]); a, b = P @ u, P @ v
        A = (a.max() - a.min()) * (b.max() - b.min())
        if best is None or A < best[0]: best = (A, u, v, a.min(), a.max(), b.min(), b.max())
    _, u, v, a0, a1, b0, b1 = best
    c = u * (a0 + a1) / 2 + v * (b0 + b1) / 2; L, W = a1 - a0, b1 - b0
    if W > L: u, v, L, W = v, -u, W, L
    return c, u, v, L, W

def rect(c, ang, half):
    u = np.array([math.cos(ang), math.sin(ang)]); v = np.array([-u[1], u[0]]); c = np.array(c)
    return [tuple(c + u * sx * half[0] + v * sz * half[1]) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

def flat(mesh, pts, y, col=(1, 1, 1), uv=None):
    pts = clean(list(pts))
    if len(pts) < 3: return
    for t in tessellate_polygon([[Vector((x, z, 0)) for x, z in pts]]):
        mesh.add([(pts[i][0], y, pts[i][1]) for i in t], [uv(pts[i]) if uv else pts[i] for i in t], col)

def offsets(pts, half):
    """Both edges of a strip `half` wide either side of a line, and the distance along it at each point."""
    P = np.array(clean(pts), dtype=float); n = len(P)
    if n < 2: return None
    d = P[1:] - P[:-1]; ln = np.linalg.norm(d, axis=1); d = d / ln[:, None]; nr = np.stack([-d[:, 1], d[:, 0]], 1)
    vn = np.zeros((n, 2)); vn[0], vn[-1] = nr[0], nr[-1]
    for i in range(1, n - 1):
        m = nr[i - 1] + nr[i]; l = np.linalg.norm(m)
        m = nr[i] if l < 1e-6 else m / l
        vn[i] = m / max(0.5, float(np.dot(m, nr[i])))
    return P, vn, np.concatenate([[0], np.cumsum(ln)])

def walk(pts, step):
    """Points every `step` metres along a line: (position, direction, distance)."""
    P = np.array(clean(pts), dtype=float); out = []; s = 0.0; nxt = step / 2
    for i in range(len(P) - 1):
        d = P[i + 1] - P[i]; l = np.linalg.norm(d)
        if l < 1e-6: continue
        d = d / l
        while nxt <= s + l: out.append((P[i] + d * (nxt - s), d, nxt)); nxt += step
        s += l
    return out


# ---------- roads
VEH = ("trunk", "trunk_link", "primary", "primary_link", "secondary", "tertiary", "residential", "unclassified", "service")
MAIN = ("trunk", "primary", "secondary", "tertiary")
roads = [r for r in S["roads"] if r["cls"] in VEH and len(clean(r["pts"])) > 1]
segA, segB, segW, segR = [], [], [], []
for k, r in enumerate(roads):
    p = clean(r["pts"])
    for a, b in zip(p[:-1], p[1:]): segA.append(a); segB.append(b); segW.append(r["width"] / 2); segR.append(k)
segA, segB, segW, segR = np.array(segA), np.array(segB), np.array(segW), np.array(segR)
segD = segB - segA; segL2 = (segD ** 2).sum(1)

def road_gap(p, skip=-1):
    """Distance from a point to the nearest road edge (negative = on a road). `skip` leaves one road out."""
    t = np.clip(((p - segA) * segD).sum(1) / segL2, 0, 1)
    d = np.linalg.norm(p - (segA + segD * t[:, None]), axis=1) - segW
    if skip >= 0: d = np.where(segR == skip, 1e9, d)
    return float(d.min())

parks = [clean(a["pts"]) for a in S["parking"]]
park_box = [(min(p[0] for p in a), max(p[0] for p in a), min(p[1] for p in a), max(p[1] for p in a)) for a in parks]
def in_parking(p):
    for a, (x0, x1, z0, z1) in zip(parks, park_box):
        if x0 <= p[0] <= x1 and z0 <= p[1] <= z1 and inside(p, a): return True
    return False

# Ground that belongs to a hand-built venue: nothing of the district (kerbs, bays, lamps, paths) is laid inside it.
_sc = np.array(STADIUM).mean(0); _stad = [tuple(_sc + (np.array(p) - _sc) * 1.2) for p in STADIUM]
_hall = rect(HALLS["c"], HALLS["ang"], (HALLS["half"][0] + 11, HALLS["half"][1] + 11))
def _zw(X, Y):  # a point of the Zaria model (its own metres, before the export offset) -> site
    a, b, c, s_ = X - 25.0, Y - 11.0, math.cos(math.radians(23.0)), math.sin(math.radians(23.0))
    return (ZARIA["c"][0] + a * c - b * s_, ZARIA["c"][1] - a * s_ - b * c)
_zar = [_zw(*q) for q in ((55, -17), (72, -17), (78, -37), (145, -37), (145, 28), (114, 61), (-25, 61), (-25, 35), (55, 35))]
def venue(p): return inside(p, _stad) or inside(p, _hall) or inside(p, _zar)

CENTRE = np.array([-110.0, 190.0])
cars, lamps, traffic = [], [], []
Y_ROAD = 0.08
for k, r in enumerate(roads):
    P, vn, cum = offsets(r["pts"], r["width"] / 2)
    half = r["width"] / 2; L, R = P + vn * half, P - vn * half
    for i in range(len(P) - 1):
        if venue(tuple(P[i])) and venue(tuple(P[i + 1])): continue
        M["C_Road"].add([(L[i][0], Y_ROAD, L[i][1]), (R[i][0], Y_ROAD, R[i][1]), (R[i + 1][0], Y_ROAD, R[i + 1][1]), (L[i + 1][0], Y_ROAD, L[i + 1][1])],
                        [tuple(L[i]), tuple(R[i]), tuple(R[i + 1]), tuple(L[i + 1])])
    if not r["closed"]:
        for e in (P[0], P[-1]):  # a round end, so roads that meet at an angle leave no notch
            ring = [(e[0] + math.cos(a) * half, e[1] + math.sin(a) * half) for a in np.linspace(0, math.tau, 11)[:-1]]
            flat(M["C_Road"], ring, Y_ROAD)
    aisle = r["cls"] == "service" and in_parking(tuple(P[len(P) // 2]))
    main = r["cls"] in MAIN
    near = np.linalg.norm(P.mean(0) - CENTRE) < 620
    # kerbs (black and white, as in Kigali) and pavements, in short pieces so they stop where another road joins
    if not aisle and (main or near):
        for side in (1, -1):
            for pos, d, s in walk(r["pts"], 4.0):
                n = np.array([-d[1], d[0]]) * side; mid = pos + n * (half + 0.12)
                if road_gap(mid, k) < 0.25 or in_parking(tuple(mid)) or venue(tuple(pos + n * (half + 3.0))) or venue(tuple(pos)): continue
                a, b = pos - d * 2.0, pos + d * 2.0
                i0, i1, o0, o1 = a + n * half, b + n * half, a + n * (half + 0.24), b + n * (half + 0.24)
                u0, u1 = (s - 2.0) / 2 % 1, (s - 2.0) / 2 % 1 + 2.0
                K = M["C_Kerb"]
                K.add([(i0[0], 0.2, i0[1]), (i1[0], 0.2, i1[1]), (o1[0], 0.2, o1[1]), (o0[0], 0.2, o0[1])], [(u0, 0.35), (u1, 0.35), (u1, 0.65), (u0, 0.65)])
                K.add([(i0[0], Y_ROAD, i0[1]), (i1[0], Y_ROAD, i1[1]), (i1[0], 0.2, i1[1]), (i0[0], 0.2, i0[1])], [(u0, 0), (u1, 0), (u1, 0.35), (u0, 0.35)], up=(-n[0], 0, -n[1]))
                K.add([(o0[0], 0, o0[1]), (o1[0], 0, o1[1]), (o1[0], 0.2, o1[1]), (o0[0], 0.2, o0[1])], [(u0, 1), (u1, 1), (u1, 0.65), (u0, 0.65)], up=(n[0], 0, n[1]))
                if main or (near and r["cls"] != "service"):
                    w0, w1 = a + n * (half + 2.4), b + n * (half + 2.4)
                    M["C_Sidewalk"].add([(o0[0], 0.19, o0[1]), (o1[0], 0.19, o1[1]), (w1[0], 0.19, w1[1]), (w0[0], 0.19, w0[1])], [tuple(o0), tuple(o1), tuple(w1), tuple(w0)])
                    M["C_Sidewalk"].add([(w0[0], 0, w0[1]), (w1[0], 0, w1[1]), (w1[0], 0.19, w1[1]), (w0[0], 0.19, w0[1])], [tuple(w0), tuple(w1), tuple(w1), tuple(w0)], up=(n[0], 0, n[1]))
    # centre line dashes on two-way main roads
    if main and not r["oneway"]:
        for pos, d, s in walk(r["pts"], 9.0):
            n = np.array([-d[1], d[0]]) * 0.08; a, b = pos - d * 1.5, pos + d * 1.5
            M["C_Marking"].add([(a[0] + n[0], Y_ROAD + 0.02, a[1] + n[1]), (b[0] + n[0], Y_ROAD + 0.02, b[1] + n[1]), (b[0] - n[0], Y_ROAD + 0.02, b[1] - n[1]), (a[0] - n[0], Y_ROAD + 0.02, a[1] - n[1])], [(0, 0)] * 4)
    if main:
        traffic.append({"pts": [[round(float(x), 1), round(float(z), 1)] for x, z in P], "w": r["width"], "oneway": r["oneway"]})
        for j, (pos, d, s) in enumerate(walk(r["pts"], 38.0)):
            side = 1 if j % 2 else -1; n = np.array([-d[1], d[0]]) * side; q = pos + n * (half + 1.0)
            if road_gap(q, k) > 0.6 and not venue(tuple(q)): lamps.append([round(float(q[0]), 1), round(float(q[1]), 1), round(math.atan2(-n[0], -n[1]), 2)])
    # parking bays either side of an aisle, with some cars in them
    if aisle:
        for pos, d, s in walk(r["pts"], 2.5):
            for side in (1, -1):
                n = np.array([-d[1], d[0]]) * side; a = pos - d * 1.25
                p0, p1, mid = a + n * 2.7, a + n * 7.6, pos + n * 5.2
                if not in_parking(tuple(p1)) or road_gap(p1, k) < 0.3 or road_gap(mid, k) < 2.4 or venue(tuple(p1)) or venue(tuple(p0)): continue
                w = d * 0.06
                M["C_Marking"].add([(p0[0] - w[0], 0.075, p0[1] - w[1]), (p0[0] + w[0], 0.075, p0[1] + w[1]), (p1[0] + w[0], 0.075, p1[1] + w[1]), (p1[0] - w[0], 0.075, p1[1] - w[1])], [(0, 0)] * 4)
                if rng.random() < 0.3 and np.linalg.norm(pos - CENTRE) < 520:
                    cars.append([round(float(mid[0]), 2), round(float(mid[1]), 2), round(math.atan2(n[0], n[1]) + (math.pi if rng.random() < 0.5 else 0), 2), rng.randrange(3), rng.randrange(8)])

for r in S["roads"]:
    if r["cls"] in ("footway", "path", "cycleway"):
        P, vn, cum = offsets(r["pts"], r["width"] / 2); L, R = P + vn * r["width"] / 2, P - vn * r["width"] / 2
        for i in range(len(P) - 1):
            if venue(tuple(P[i])) and venue(tuple(P[i + 1])): continue
            M["C_Path"].add([(L[i][0], 0.05, L[i][1]), (R[i][0], 0.05, R[i][1]), (R[i + 1][0], 0.05, R[i + 1][1]), (L[i + 1][0], 0.05, L[i + 1][1])], [tuple(L[i]), tuple(R[i]), tuple(R[i + 1]), tuple(L[i + 1])])

for a in parks: flat(M["C_Parking"], a, 0.06)

# ---------- lawns and paved aprons of the complex
flat(M["C_Lawn"], COMPLEX, 0.02)
flat(M["C_Paving"], [(math.cos(a) * 72, math.sin(a) * 72) for a in np.linspace(0, math.tau, 49)[:-1]], 0.04)
ENT = math.radians(225)  # the arena's entrance faces north-west: curved terraces of paving fan out in front of it
def on_terraces(p): return math.hypot(*p) < 124 and abs((math.atan2(p[1], p[0]) - ENT + math.pi) % math.tau - math.pi) < 1.1
for k in range(6):
    r0, r1 = 72 + k * 8.5, 80.5 + k * 8.5; A = np.linspace(ENT - 1.05, ENT + 1.05, 29)
    flat(M["C_Paving" if k % 2 else "C_PavingB"], [(math.cos(a) * r1, math.sin(a) * r1) for a in A] + [(math.cos(a) * r0, math.sin(a) * r0) for a in A[::-1]], 0.04)
sc = np.array(STADIUM).mean(0); stadium_apron = [tuple(sc + (np.array(p) - sc) * 1.13) for p in STADIUM]
flat(M["C_Paving"], stadium_apron, 0.04)
flat(M["C_Paving"], rect(HALLS["c"], HALLS["ang"], (HALLS["half"][0] + 8, HALLS["half"][1] + 8)), 0.04)
flat(M["C_Paving"], rect(ZARIA["c"], ZARIA["ang"], ZARIA["half"]), 0.04)

# ---------- pitches, courts and the training track
def fence(c, u, v, L, W, h=4.0, pad=1.5):
    q = [c + u * sx * (L / 2 + pad) + v * sz * (W / 2 + pad) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]; l = float(np.linalg.norm(b - a)); n = (a + b) / 2 - c
        M["C_Fence"].add([(a[0], 0, a[1]), (b[0], 0, b[1]), (b[0], h, b[1]), (a[0], h, a[1])], [(0, 0), (l, 0), (l, h), (0, h)], up=(n[0], 0, n[1]))

sports_boxes = []
for p in S["pitches"]:
    c, u, v, L, W = obb(p["pts"])
    if np.linalg.norm(c - sc) < 40: continue  # the pitch inside Amahoro Stadium comes with the stadium model
    if c[0] < -250: continue  # the old pitches by the car park: Zaria Court now stands there and brings its own two
    name = "C_Soccer" if p["sport"] == "soccer" else "C_Basket" if p["sport"] == "basketball" else "C_Pitch5" if c[0] < -250 else "C_Tennis"
    q = [c + u * sx * L / 2 + v * sz * W / 2 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    M[name].add([(x, 0.1, z) for x, z in q], [(0, 0), (1, 0), (1, 1), (0, 1)])
    if name != "C_Soccer": fence(c, u, v, L, W, 5.0 if name == "C_Pitch5" else 4.0)
    sports_boxes.append([tuple(c + u * sx * (L / 2 + 3) + v * sz * (W / 2 + 3)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
for t in S["tracks"]:
    c, u, v, L, W = obb(t["outer"])
    if np.linalg.norm(c - sc) < 40: continue
    lanes = 6; wide = lanes * 1.22; R = W / 2; s = (L - W) / 2; loop = []
    for k in range(4):  # straight, bend, straight, bend
        if k % 2 == 0:
            sg = 1 if k == 0 else -1
            for t_ in np.linspace(-s, s, 7)[:-1]: loop.append((c + u * t_ * sg + v * R * sg * -1, v * -sg))
        else:
            sg = 1 if k == 1 else -1
            for a in np.linspace(-math.pi / 2, math.pi / 2, 25)[:-1]:
                dirn = u * math.cos(a) * sg + v * math.sin(a) * sg; loop.append((c + u * s * sg + dirn * R, dirn))
    dist = 0.0
    for i in range(len(loop)):
        (p0, n0), (p1, n1) = loop[i], loop[(i + 1) % len(loop)]; l = float(np.linalg.norm(p1 - p0)); i0, i1 = p0 - n0 * wide, p1 - n1 * wide
        M["C_Track"].add([(p0[0], 0.09, p0[1]), (p1[0], 0.09, p1[1]), (i1[0], 0.09, i1[1]), (i0[0], 0.09, i0[1])], [(dist / 4, 0), ((dist + l) / 4, 0), ((dist + l) / 4, 1), (dist / 4, 1)]); dist += l
    flat(M["C_Turf"], [tuple(p - n * wide) for p, n in loop], 0.085)
    sports_boxes.append([tuple(c + u * sx * (L / 2 + 4) + v * sz * (W / 2 + 4)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])

# ---------- buildings
WALLS = [lin(h) for h in (0xe9dfc8, 0xe4d3b0, 0xf1ead9, 0xd9c7a3, 0xeed9b9, 0xe8e2d6, 0xd8b99a, 0xc98f6a, 0xf0e3c0, 0xdcd6c8, 0xe6c9a8, 0xcdb89c)]
ROOFS = [lin(h) for h in (0x9a4a35, 0xa5533a, 0x8c4433, 0xb05e44, 0x7f4a3a, 0x9a4a35, 0xa5533a, 0x6f7f96, 0x4f6f9a, 0x8f9499, 0xa9aeb0, 0x5f7f62, 0x8a5a44, 0xb7b2a6)]
FLATS = [lin(h) for h in (0x9a9890, 0x8d8b85, 0xa7a49b, 0x7f7d78)]
EPS = 0.006
zr, hr = rect(ZARIA["c"], ZARIA["ang"], (ZARIA["half"][0] + 4, ZARIA["half"][1] + 4)), rect(HALLS["c"], HALLS["ang"], HALLS["half"])
kept = []

def walls(mesh, ring, sgn, floors, fh, top, tiles, col, door_edge):
    """Wall panels one module wide and one floor high, each showing one picture from the facade sheet."""
    blank, door, wins = tiles
    for i in range(len(ring)):
        a, b = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)]); d = b - a; l = float(np.linalg.norm(d))
        if l < 0.2: continue
        d = d / l; n = np.array([d[1], -d[0]]) * sgn; up = (n[0], 0, n[1])
        mods = max(1, round(l / 3.2)) if l >= 2.0 else 1
        for m in range(mods):
            p, q = a + d * l * m / mods, a + d * l * (m + 1) / mods
            for f in range(floors):
                if l < 2.0: t = blank
                elif f == 0 and i == door_edge and m == mods // 2: t = door
                else: t = blank if rng.random() < 0.22 else rng.choice(wins)
                u0, u1 = t / 4 + EPS, (t + 1) / 4 - EPS
                mesh.add([(p[0], f * fh, p[1]), (q[0], f * fh, q[1]), (q[0], (f + 1) * fh, q[1]), (p[0], (f + 1) * fh, p[1])], [(u0, EPS), (u1, EPS), (u1, 1 - EPS), (u0, 1 - EPS)], col, up)
            ya, yb = top(p), top(q)  # the strip from the last floor up to the roof line
            if max(ya, yb) > floors * fh + 0.02:
                u0, u1 = blank / 4 + EPS, (blank + 1) / 4 - EPS
                mesh.add([(p[0], floors * fh, p[1]), (q[0], floors * fh, q[1]), (q[0], yb, q[1]), (p[0], ya, p[1])], [(u0, 0.3), (u1, 0.3), (u1, 0.5), (u0, 0.5)], col, up)

for b in S["buildings"]:
    ring = clean(b["pts"]); A = abs(area2(ring))
    if len(ring) < 3 or A < 12 or b["kind"] == "stadium": continue
    cen = np.array(ring).mean(0)
    if np.linalg.norm(cen) < 78 or inside(cen, stadium_apron) or inside(cen, zr) or inside(cen, hr): continue
    c, u, v, L, W = obb(ring); lv = b["levels"]; biz = b["kind"] in ("commercial", "office", "retail", "hotel", "apartments", "public", "school", "university")
    if lv is None: lv = rng.choice((2, 3, 4)) if biz else rng.choice((2, 3)) if A > 900 else rng.choice((1, 1, 2)) if A > 350 else 1
    lv = min(lv, 9); office = lv >= 3 or biz or A > 700
    sgn = 1 if area2(ring) > 0 else -1; col = rng.choice(WALLS)
    door_edge = max(range(len(ring)), key=lambda i: math.dist(ring[i], ring[(i + 1) % len(ring)]))
    boxy = A / (L * W) > 0.84
    kept.append((ring, (min(p[0] for p in ring), max(p[0] for p in ring), min(p[1] for p in ring), max(p[1] for p in ring))))
    if office:
        fh = 3.4; h = lv * fh
        walls(M["C_Office"], ring, sgn, lv, fh, lambda p: h + 1.0, (2, 1, (0, 0, 3)), col, door_edge)
        flat(M["C_RoofFlat"], ring, h + 0.85, rng.choice(FLATS))
    elif boxy and W < 24:
        fh = 3.0; h = lv * fh; rc = rng.choice(ROOFS); e = 0.45; rise = (W / 2 + e) * math.tan(math.radians(rng.uniform(15, 24))); sl = math.hypot(W / 2 + e, rise)
        walls(M["C_House"], ring, sgn, lv, fh, lambda p: h, (1, 2, (0, 0, 3)), col, door_edge)
        P0, P1, P2, P3 = (c + u * sx * (L / 2 + e) + v * sz * (W / 2 + e) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
        R0, R1 = c - u * (L - W) / 2, c + u * (L - W) / 2; ry = h + rise; Sh = M["C_Sheet"]
        E = lambda p: (p[0], h, p[1]); T = lambda p: (p[0], ry, p[1]); k = (L - W) / 2 + (W / 2 + e)
        Sh.add([E(P0), E(P1), T(R1), T(R0)], [(0, 0), (L + 2 * e, 0), (L / 2 + e + (L - W) / 2, sl), (L / 2 + e - (L - W) / 2, sl)], rc, (-v[0] * 0.3, 1, -v[1] * 0.3))
        Sh.add([E(P2), E(P3), T(R0), T(R1)], [(0, 0), (L + 2 * e, 0), (L / 2 + e + (L - W) / 2, sl), (L / 2 + e - (L - W) / 2, sl)], rc, (v[0] * 0.3, 1, v[1] * 0.3))
        Sh.add([E(P1), E(P2), T(R1)], [(0, 0), (W + 2 * e, 0), (W / 2 + e, sl)], rc, (u[0] * 0.3, 1, u[1] * 0.3))
        Sh.add([E(P3), E(P0), T(R0)], [(0, 0), (W + 2 * e, 0), (W / 2 + e, sl)], rc, (-u[0] * 0.3, 1, -u[1] * 0.3))
    else:  # an odd-shaped house: one sloping sheet over the whole plan
        fh = 3.0; h = lv * fh; rc = rng.choice(ROOFS); slope = rng.uniform(0.1, 0.16)
        top = lambda p: h + 0.15 + slope * (float(np.dot(np.array(p) - c, v)) + W / 2)
        walls(M["C_House"], ring, sgn, lv, fh, top, (1, 2, (0, 0, 3)), col, door_edge)
        big = [tuple(cen + (np.array(p) - cen) * 1.04) for p in ring]
        for t in tessellate_polygon([[Vector((x, z, 0)) for x, z in big]]):
            M["C_Sheet"].add([(big[i][0], top(big[i]) + 0.03, big[i][1]) for i in t], [(float(np.dot(np.array(big[i]) - c, u)), float(np.dot(np.array(big[i]) - c, v))) for i in t], rc)

# ---------- trees: scattered where nothing else stands, and in rows along the two avenues
grid = {}
for ring, (x0, x1, z0, z1) in kept:
    for gx in range(int(x0 // 30), int(x1 // 30) + 1):
        for gz in range(int(z0 // 30), int(z1 // 30) + 1): grid.setdefault((gx, gz), []).append((x0 - 2, x1 + 2, z0 - 2, z1 + 2))
def free(p, gap=2.2):
    for x0, x1, z0, z1 in grid.get((int(p[0] // 30), int(p[1] // 30)), ()):
        if x0 <= p[0] <= x1 and z0 <= p[1] <= z1: return False
    if road_gap(np.array(p)) < gap or in_parking(p) or venue(p): return False
    if math.hypot(*p) < 76 or on_terraces(p) or inside(p, stadium_apron) or inside(p, zr) or inside(p, hr): return False
    return not any(inside(p, q) for q in sports_boxes)
trees, taken = [], set()
def plant(p, kind=None, big=1.0):
    key = (int(p[0] // 5), int(p[1] // 5))
    if key in taken: return
    taken.add(key); trees.append([round(float(p[0]), 1), round(float(p[1]), 1), round(rng.uniform(0.8, 1.45) * big, 2), round(rng.uniform(0, 6.28), 2), rng.randrange(3) if kind is None else kind])
for r_ in roads:
    if r_["cls"] in ("secondary", "tertiary"):
        for j, (pos, d, s) in enumerate(walk(r_["pts"], 16.0)):
            for side in (1, -1):
                q = pos + np.array([-d[1], d[0]]) * side * (r_["width"] / 2 + 4.2)
                if np.linalg.norm(pos - CENTRE) < 700 and free(tuple(q), 3.0): plant(q, j % 2, 1.25)
for x, z in S["trees"]:
    if free((x, z), 1.0): plant((x, z))
tries = 0
while len(trees) < 1500 and tries < 40000:
    tries += 1; p = (rng.uniform(-820, 690), rng.uniform(-440, 850))
    if inside(p, COMPLEX) and rng.random() > 0.3: continue
    if free(p): plant(p)

os.makedirs(ROOT + "/public/tour", exist_ok=True)
blocks = [[[round(float(x), 1), round(float(z), 1)] for x, z in ring] for ring, _ in kept]  # house outlines, so a walker cannot pass through walls
json.dump({"trees": trees, "cars": cars, "lamps": lamps, "traffic": traffic, "blocks": blocks}, open(ROOT + "/public/tour/site.json", "w"), separators=(",", ":"))

# ---------- into Blender and out as one file
objs = []
for m in M.values():
    if not m.f: continue
    V = np.array(m.v, dtype=np.float32); V = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1); F = np.array(m.f, dtype=np.int32)
    me = bpy.data.meshes.new(m.name); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
    uv = me.uv_layers.new(name="UVMap"); uv.data.foreach_set("uv", np.array(m.uv, dtype=np.float32)[F.ravel()].ravel())
    if m.colored:
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT"); C = np.concatenate([np.array(m.c, dtype=np.float32), np.ones((len(m.c), 1), dtype=np.float32)], 1)
        ca.data.foreach_set("color", C.ravel()); me.color_attributes.active_color = ca; me.color_attributes.render_color_index = 0
    mat = bpy.data.materials.new(m.name); mat.use_nodes = True; me.materials.append(mat)
    o = bpy.data.objects.new(m.name, me); bpy.context.scene.collection.objects.link(o); objs.append(o)
    print(m.name, len(F), "triangles")
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
kw = dict(filepath=ROOT + "/public/models/city.glb", export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=True,
          export_normals=True, export_materials="EXPORT", export_image_format="NONE",
          export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_draco_position_quantization=18, export_draco_texcoord_quantization=14)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
if "export_vertex_color" in props: kw["export_vertex_color"] = "ACTIVE"
if "export_all_vertex_colors" in props: kw["export_all_vertex_colors"] = False
if "export_active_vertex_color_when_no_material" in props: kw["export_active_vertex_color_when_no_material"] = True
bpy.ops.export_scene.gltf(**kw)
print("city.glb", round(os.path.getsize(ROOT + "/public/models/city.glb") / 1024), "KB |", len(trees), "trees", len(cars), "cars", len(lamps), "lamps", len(kept), "buildings")
