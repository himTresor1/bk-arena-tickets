# Cars, trees and shrubs for the tour and the ticket page, modelled here (nothing downloaded) -> public/models/world.glb
#   Blender -b --factory-startup -P blender/py/100_world_models.py              build + export
#   Blender -b --factory-startup -P blender/py/100_world_models.py -- render    ... and render previews to blender/renders/world
#   (add "tex" after -- to repaint the leaf texture)
# The same file, run by ~/.blender-mcp/venv/bin/python with the argument "tex", paints public/textures/tour/leaves.webp (PIL).
#
# Trees are grown by the Sapling Tree Gen add-on (Weber-Penn). Install it once from Blender's own extensions site:
#   Blender -b --online-mode --command extension install sapling_tree_gen -e
# --factory-startup leaves user add-ons switched off, so this script switches Sapling on itself (addon_utils.enable).
# Sapling grows the skeleton (curves with radii) and places the leaves (one rectangle each); this script turns the curves
# into tubes at the triangle budget the website can afford and maps a painted sprig of leaves onto every rectangle.
#
# Every model comes twice: full (Car1_Body, Tree1, Bush ...) and light for phones (Car1L_Body, Tree1L, BushL ...).
# Cars face +z in website terms (Blender -Y), origin on the ground under the middle, metres. Parts, so the site can paint
# each car its own colour:  _Body (paint)  _Glass  _Trim (black: tyres, grille, underside)  _Lights (white: headlights,
# plates)  _Rim (silver)  _Tail (red).  Trees: one mesh each, UVs into leaves.webp, colours per vertex (dark inside and
# underneath, light on top), normals pushed outward so the crown shades softly.
import os, sys, math, random, subprocess, ast
from math import sin, cos, pi, radians, sqrt

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEXF = os.path.join(ROOT, "public", "textures", "tour", "leaves.webp")
REN = os.path.join(ROOT, "blender", "renders", "world")
OUT = os.path.join(ROOT, "public", "models", "world.glb")
VENV_PY = os.path.expanduser("~/.blender-mcp/venv/bin/python")
# where things sit in leaves.webp (pixels, 1024 square): two leaf sprigs, a palm frond, a strip of bark
T = 1024
R_A, R_B, R_FROND, R_BARK = (0, 0, 512, 448), (512, 0, 1024, 448), (0, 448, 1024, 768), (0, 776, 1024, 1016)


# ============================================================ the leaf texture (runs outside Blender)
def make_texture():
    from PIL import Image, ImageDraw
    S = 2; rnd = random.Random(5)
    im = Image.new("RGBA", (T * S, T * S), (150, 190, 105, 0)); d = ImageDraw.Draw(im)
    green = lambda k=1.0: (int(rnd.uniform(165, 215) * k), int(rnd.uniform(212, 248) * k), int(rnd.uniform(112, 160) * k))

    def leaf(base, ang, L, W, col, lance=False):
        n = 12; up, dn = [], []
        for i in range(n + 1):
            t = i / n; w = W * (sin(pi * t) ** (0.75 if not lance else 0.6)) * (1 - 0.3 * t) / 2
            up.append((t * L, w)); dn.append((t * L, -w))
        rot = lambda p: (base[0] + (p[0] * cos(ang) - p[1] * sin(ang)) * S, base[1] + (p[0] * sin(ang) + p[1] * cos(ang)) * S)
        d.polygon([rot(p) for p in up + dn[::-1]], fill=col + (255,))
        d.polygon([rot(p) for p in [(0, 0)] + dn[1:] + [(L, 0)]], fill=tuple(int(c * 0.86) for c in col) + (255,))
        d.line([rot((0, 0)), rot((L, 0))], fill=tuple(min(255, int(c * 1.1)) for c in col) + (255,), width=S)

    def twig(p0, ang, L, n, leafL, leafW, spread, lance=False, bend=0.0):
        pts = [p0]; a = ang
        for i in range(10): a += bend / 10; pts.append((pts[-1][0] + cos(a) * L / 10 * S, pts[-1][1] + sin(a) * L / 10 * S))
        d.line(pts, fill=(150, 138, 104, 255), width=3 * S)
        for i in range(n):
            t = (i + 1) / n; k = min(9, int(t * 10)); q = pts[k]; aa = ang + bend * t
            side = 1 if i % 2 else -1
            leaf(q, aa + side * radians(spread + rnd.uniform(-12, 12)), leafL * (1 - 0.3 * t) * rnd.uniform(0.85, 1.1), leafW * rnd.uniform(0.85, 1.1), green(), lance)
        leaf(pts[-1], ang + bend, leafL * 0.8, leafW, green(1.02), lance)
        return pts

    # sprig A: broad leaves on a stem with side twigs (shade trees, bushes)
    x0, y0, x1, y1 = R_A; base = ((x0 + x1) / 2 * S, (y1 - 2) * S)
    for (t, side) in ((0.16, -1), (0.3, 1), (0.44, -1), (0.56, 1), (0.7, -1)):
        q = (base[0], base[1] - t * 400 * S)
        twig(q, -pi / 2 + side * radians(58), 200 - 150 * (t - 0.16), 6, 86, 42, 52)
    twig(base, -pi / 2, 400, 12, 96, 46, 55)
    # sprig B: narrow hanging leaves (slender trees)
    x0, y0, x1, y1 = R_B; base = ((x0 + x1) / 2 * S, (y1 - 2) * S)
    for (t, side) in ((0.1, -1), (0.22, 1), (0.36, -1), (0.48, 1), (0.6, -1), (0.72, 1)):
        q = (base[0], base[1] - t * 410 * S)
        twig(q, -pi / 2 + side * radians(50), 215 - 150 * (t - 0.1), 9, 92, 17, 38, True, bend=side * 0.5)
    twig(base, -pi / 2, 410, 16, 100, 18, 40, True)
    # palm frond: rachis along the middle, leaflets either side, shorter toward the tip
    x0, y0, x1, y1 = R_FROND; ym = (y0 + y1) / 2
    d.line([(8 * S, ym * S), (1016 * S, ym * S)], fill=(160, 170, 96, 255), width=5 * S)
    for i in range(96):
        t = i / 95; x = 24 + t * 985; l = 158 * (sin(pi * min(1, 0.1 + 0.9 * t)) ** 0.55) * (1 - 0.5 * t) + 14
        for side in (-1, 1):
            a = side * radians(rnd.uniform(56, 70) - 14 * t); col = green(rnd.uniform(0.9, 1.02))
            leaf((x * S, ym * S), a, l * rnd.uniform(0.9, 1.05), 10.5, col, True)
    # bark: pale, with darker streaks running along the trunk
    x0, y0, x1, y1 = 0, 768, 1024, 1024
    d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=(222, 212, 196, 255))
    for i in range(520):
        x = rnd.uniform(x0, x1) * S; y = rnd.uniform(y0, y1) * S; l = rnd.uniform(20, 120) * S; g = rnd.uniform(0.62, 1.0)
        d.line([(x, y), (x + rnd.uniform(-3, 3) * S, y + l)], fill=(int(222 * g), int(210 * g), int(192 * g), 255), width=int(rnd.uniform(1, 4) * S))
    im = im.resize((T, T), Image.LANCZOS)
    os.makedirs(os.path.dirname(TEXF), exist_ok=True); im.save(TEXF, quality=84, method=6)
    print("leaf texture written:", TEXF, round(os.path.getsize(TEXF) / 1024), "KB")


if "bpy" not in sys.modules and "tex" in sys.argv:
    try: import bpy  # noqa: F401  (inside Blender this succeeds and the texture is made by the venv python instead)
    except ImportError: make_texture(); sys.exit(0)

import bpy, addon_utils
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "tex" in ARGS or not os.path.exists(TEXF): subprocess.run([VENV_PY, os.path.abspath(__file__), "tex"], check=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
B = lambda p: (p[0], -p[2], p[1])   # website (x, up, z) -> Blender
UVR = lambda x, y: (x / T, 1 - y / T)


class Geo:
    """One mesh being put together: faces with their own corners, so UVs, colours and normals can differ per corner."""
    def __init__(s): s.v, s.f, s.uv, s.col, s.nrm = [], [], [], [], []

    def face(s, pts, uv=None, col=None, nrm=None, inside=None):
        if inside is not None:   # turn the face so it looks away from a point known to be inside the object
            a, b, c = (np.array(p, float) for p in pts[:3]); cen = np.mean(np.array(pts, float), 0)
            if np.dot(np.cross(b - a, c - a), cen - np.array(inside, float)) < 0:
                pts = pts[::-1]; uv = uv[::-1] if uv else uv; col = col[::-1] if isinstance(col, list) else col; nrm = nrm[::-1] if nrm else nrm
        n = len(s.v); s.v += [tuple(p) for p in pts]; s.f.append(tuple(range(n, n + len(pts))))
        s.uv += uv or [(0, 0)] * len(pts)
        s.col += col if isinstance(col, list) else [col or (1, 1, 1)] * len(pts)
        s.nrm += nrm or [None] * len(pts)

    def tris(s): return sum(len(f) - 2 for f in s.f)

    def build(s, name, weld=False, colours=False, uvs=False, sharp=38):
        me = bpy.data.meshes.new(name); me.from_pydata([B(p) for p in s.v], [], s.f); me.update()
        if uvs:
            me.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(s.uv, np.float32).ravel())
        if colours:
            ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
            ca.data.foreach_set("color", np.concatenate([np.array(s.col, np.float32), np.ones((len(s.col), 1), np.float32)], 1).ravel())
            me.color_attributes.active_color = ca; me.color_attributes.render_color_index = 0
        for p in me.polygons: p.use_smooth = True
        if weld:
            import bmesh
            bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0006); bm.to_mesh(me); bm.free()
            me.set_sharp_from_angle(angle=radians(sharp))
        elif s.nrm and s.nrm[0] is not None:
            me.normals_split_custom_set([tuple(Vector(B(n)).normalized()) for n in s.nrm])
        o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o


# ============================================================ trees (Sapling Tree Gen)
addon_utils.enable("bl_ext.blender_org.sapling_tree_gen", default_set=False)
if not hasattr(bpy.ops.curve, "tree_add"): raise SystemExit("Sapling Tree Gen is not installed: see the top of this file")
PRESETS = os.path.dirname(sys.modules["bl_ext.blender_org.sapling_tree_gen"].__file__) + "/presets/"


def sapling(preset, **over):
    """Grow a tree with Sapling; hand back its stems [(points, radii)] and its leaf rectangles (N, 4, 3), in website axes."""
    d = ast.literal_eval("".join(l for l in open(PRESETS + preset + ".py") if not l.startswith("#")))
    d.update(over); d.update(leafShape="rect", showLeaves=True, scaleV=0.0, makeMesh=False, windAnim=False, useRig=False)
    props = bpy.ops.curve.tree_add.get_rna_type().properties.keys()
    bpy.ops.curve.tree_add(**{k: v for k, v in d.items() if k in props})
    cd = bpy.data.objects["tree_curves"].data; n = len(cd.points)
    pos = np.zeros(n * 3); cd.attributes["position"].data.foreach_get("vector", pos); pos = pos.reshape(-1, 3)
    rad = np.zeros(n); cd.attributes["radius"].data.foreach_get("value", rad)
    W = lambda a: np.stack([a[..., 0], a[..., 2], -a[..., 1]], -1)
    stems = [(W(pos[c.first_point_index:c.first_point_index + c.points_length]), rad[c.first_point_index:c.first_point_index + c.points_length]) for c in cd.curves]
    lv = bpy.data.objects.get("leaves"); quads = np.zeros((0, 4, 3))
    if lv and len(lv.data.vertices):
        v = np.zeros(len(lv.data.vertices) * 3); lv.data.vertices.foreach_get("co", v); quads = W(v.reshape(-1, 4, 3))
    for o in list(bpy.data.objects):
        if o.name.split(".")[0] in ("tree", "tree_curves", "leaves") or (o.parent and o.parent.name == "tree"): bpy.data.objects.remove(o, do_unlink=True)
    return stems, quads


def tube(g, P, Rr, sides, col, rnd):
    P = np.array(P, float); cum = np.concatenate([[0], np.cumsum(np.linalg.norm(P[1:] - P[:-1], axis=1))]); rings = []
    ref = np.array([1.0, 0, 0])
    for k in range(len(P)):
        t = P[min(k + 1, len(P) - 1)] - P[max(k - 1, 0)]; t = t / (np.linalg.norm(t) + 1e-9)
        if abs(np.dot(t, ref)) > 0.9: ref = np.array([0, 0, 1.0])
        a = np.cross(t, ref); a /= np.linalg.norm(a); b = np.cross(t, a); ref = a
        rings.append([(P[k] + (a * cos(j / sides * 2 * pi) + b * sin(j / sides * 2 * pi)) * Rr[k], a * cos(j / sides * 2 * pi) + b * sin(j / sides * 2 * pi)) for j in range(sides + 1)])
    x0, y0, x1, y1 = R_BARK; tri = lambda s: abs((s * 0.22) % 2 - 1)
    for k in range(len(P) - 1):
        for j in range(sides):
            q = [rings[k][j], rings[k][j + 1], rings[k + 1][j + 1], rings[k + 1][j]]
            uv = [UVR(x0 + 8 + (x1 - x0 - 16) * (jj / sides), y0 + (y1 - y0) * tri(cum[kk])) for kk, jj in ((k, j), (k, j + 1), (k + 1, j + 1), (k + 1, j))]
            sh = rnd.uniform(0.85, 1.1)
            g.face([tuple(p[0]) for p in q], uv, [tuple(c * sh * (0.8 if kk == k and k == 0 else 1) for c in col) for kk in (0, 0, 1, 1)], [tuple(p[1]) for p in q], inside=tuple((P[k] + P[k + 1]) / 2))


def card(g, q, region, base, top, shade, rnd, centre, flip=False):
    x0, y0, x1, y1 = region; x0 += 3; x1 -= 3; y0 += 3
    if flip: x0, x1 = x1, x0
    uv = [UVR(x1, y1), UVR(x1, y0), UVR(x0, y0), UVR(x0, y1)]
    c = [tuple(base[i] + (top[i] - base[i]) * shade for i in range(3))] * 2
    lo = tuple(v * 0.62 for v in c[0]); k = rnd.uniform(0.9, 1.1)
    cols = [tuple(v * k for v in lo), tuple(v * k for v in c[0]), tuple(v * k for v in c[0]), tuple(v * k for v in lo)]
    nr = []
    for p in q:
        n = np.array(p) - centre; n = n / (np.linalg.norm(n) + 1e-9) + np.array([0, 0.55, 0]); nr.append(tuple(n / np.linalg.norm(n)))
    g.face([tuple(p) for p in q], uv, cols, nr)


def tree(name, preset, height, region, base, top, bark, cards, bark_tris, light_cards, card_scale=1.0, light_scale=1.0, radius=1.0, seed=1, **over):
    rnd = random.Random(seed)
    stems, quads = sapling(preset, seed=seed, **over)
    allp = np.concatenate([s[0] for s in stems] + ([quads.reshape(-1, 3)] if len(quads) else []))
    k = height / (allp[:, 1].max() - allp[:, 1].min()); y0 = stems[0][0][0][1]
    stems = [((p - [0, y0, 0]) * k, np.maximum(r * k * radius, 0.012)) for p, r in stems]; quads = (quads - [0, y0, 0]) * k
    # leaves: keep `cards` of Sapling's rectangles, spread evenly, each enlarged a little about its foot
    rr_ = np.linalg.norm((quads.mean(1) - quads.mean(1).mean(0))[:, [0, 2]], axis=1); quads = quads[rr_ <= 1.9 * np.median(rr_)]   # drop the odd stray leaf
    if len(quads) > cards: quads = quads[np.linspace(0, len(quads) - 1, cards).astype(int)]
    cen = quads.mean(1); centre = np.array([cen[:, 0].mean(), cen[:, 1].min() * 0.5 + cen[:, 1].mean() * 0.5, cen[:, 2].mean()])
    ymin, ymax = cen[:, 1].min(), cen[:, 1].max(); rmax = np.linalg.norm((cen - centre)[:, [0, 2]], axis=1).max() + 1e-6
    def leaves(g, qs, scale):
        for q in qs:
            foot = (q[0] + q[3]) / 2; q = foot + (q - foot) * scale; c = q.mean(0)
            shade = min(1, max(0, 0.15 + 0.55 * (c[1] - ymin) / (ymax - ymin + 1e-6) + 0.35 * np.linalg.norm((c - centre)[[0, 2]]) / rmax))
            card(g, q, region, base, top, shade, rnd, centre, rnd.random() < 0.5)
    def wood(g, budget, sides):
        order = sorted(range(len(stems)), key=lambda i: -(stems[i][1][0] * np.linalg.norm(stems[i][0][-1] - stems[i][0][0])))
        r0 = stems[0][1][0]
        for n, i in enumerate([0] + [i for i in order if i != 0]):
            P, Rr = stems[i]; s = sides[0] if Rr[0] > 0.45 * r0 else sides[1] if Rr[0] > 0.14 * r0 else sides[2]
            if s < 3: continue
            idx = list(range(len(P))) if s >= sides[0] else sorted(set([0, len(P) // 2, len(P) - 1])) if s == sides[2] else sorted(set(list(range(0, len(P), 2)) + [len(P) - 1]))
            if g.tris() + (len(idx) - 1) * s * 2 > budget and n: break
            tube(g, P[idx], Rr[idx], s, bark, rnd)
    full = Geo(); wood(full, bark_tris, (8, 5, 3)); nb = full.tris(); leaves(full, quads, card_scale)
    lite = Geo(); wood(lite, 66, (5, 3, 0)); nl = lite.tris(); leaves(lite, quads[np.linspace(0, len(quads) - 1, light_cards).astype(int)], card_scale * light_scale)
    print(f"{name}: sapling gave {len(stems)} stems; full {full.tris()} triangles ({nb} wood), light {lite.tris()} ({nl} wood)")
    return [full.build(name, colours=True, uvs=True), lite.build(name + "L", colours=True, uvs=True)]


def palm(name, height, base, top, bark, seed=3):
    """Sapling's palm: its trunk becomes a tube, each of its frond stems a folded ribbon carrying the painted frond."""
    rnd = random.Random(seed)
    stems, _ = sapling("palm", seed=seed, leaves=0, branches=(0, 22, 0, 0))
    allp = np.concatenate([s[0] for s in stems]); k = height / (allp[:, 1].max() - allp[:, 1].min())
    stems = [(p * k, r * k) for p, r in stems]; crown = stems[0][0][-1]
    x0, y0, x1, y1 = R_FROND; ym = (y0 + y1) / 2
    def frond(g, P, width, step):
        P = P[::step] if (len(P) - 1) % step == 0 else np.concatenate([P[::step], P[-1:]])
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(P[1:] - P[:-1], axis=1))]); L = cum[-1]; rows = []
        for i in range(len(P)):
            t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; t /= np.linalg.norm(t) + 1e-9
            side = np.cross(t, [0, 1, 0]); side = side / np.linalg.norm(side) if np.linalg.norm(side) > 0.05 else np.array([1.0, 0, 0])
            down = np.cross(side, t); down = down if down[1] < 0 else -down
            u = x0 + 4 + (x1 - x0 - 8) * cum[i] / L; sh = 0.35 + 0.65 * cum[i] / L
            rows.append((P[i] + side * width / 2 + down * width * 0.2, P[i], P[i] - side * width / 2 + down * width * 0.2, u, sh, -down))
        for a, b in zip(rows, rows[1:]):
            for (i0, i1, v0, v1) in ((0, 1, y0 + 3, ym), (1, 2, ym, y1 - 3)):
                col = [tuple(base[c] + (top[c] - base[c]) * r[4] for c in range(3)) for r in (a, a, b, b)]
                g.face([tuple(a[i0]), tuple(a[i1]), tuple(b[i1]), tuple(b[i0])], [UVR(a[3], v0), UVR(a[3], v1), UVR(b[3], v1), UVR(b[3], v0)], col, [tuple(a[5])] * 2 + [tuple(b[5])] * 2)
    out = []
    for nm, sides, keep, step, tstep in ((name, 8, 1, 2, 2), (name + "L", 5, 2, 4, 4)):
        g = Geo(); P, Rr = stems[0]; idx = sorted(set(list(range(0, len(P), tstep)) + [len(P) - 1]))
        Rt = np.maximum(Rr[idx] * 1.5, 0.11); Rt[0] *= 1.5; tube(g, P[idx], Rt, sides, bark, rnd)
        for i, (Pf, _) in enumerate(stems[1:]):
            if i % keep: continue
            Pf = crown + (Pf - Pf[0]) * 1.55; frond(g, Pf, 1.5 if keep == 1 else 2.0, step)
        print(f"{nm}: {g.tris()} triangles"); out.append(g.build(nm, colours=True, uvs=True))
    return out


G1, G1T = (0.055, 0.16, 0.04), (0.3, 0.5, 0.13); G2, G2T = (0.07, 0.17, 0.065), (0.33, 0.47, 0.19); G3, G3T = (0.06, 0.15, 0.04), (0.3, 0.46, 0.12)
BARK, PALE = (0.2, 0.14, 0.09), (0.5, 0.44, 0.36)
objs = []
# broad shade tree, about 9 m: a short trunk, heavy limbs, a wide rounded crown
objs += tree("Tree1", "black_oak", 9.0, R_A, G1, G1T, BARK, cards=430, bark_tris=420, light_cards=90, card_scale=1.15, light_scale=1.7, radius=1.5, seed=7,
             scale=9.0, levels=3, branches=(0, 18, 7, 0), baseSize=0.3, leaves=12, leafScale=1.5, leafScaleX=1.0, horzLeaves=False, leafDist="6",
             curveRes=(6, 5, 2, 1), length=(1.0, 0.62, 0.45, 0.4), shape="2", ratio=0.03)
# tall slender tree, about 11 m: a straight pale trunk with a narrow crown of hanging leaves
objs += tree("Tree2", "quaking_aspen", 11.0, R_B, G2, G2T, PALE, cards=380, bark_tris=400, light_cards=88, card_scale=1.1, light_scale=1.65, radius=1.4, seed=4,
             scale=11.0, levels=3, branches=(0, 30, 5, 0), baseSize=0.34, leaves=9, leafScale=1.35, leafScaleX=1.0, horzLeaves=False,
             curveRes=(8, 4, 2, 1), ratio=0.022)
objs += palm("Tree3", 7.2, G3, G3T, PALE)
# clipped shrub, about 1.2 m, used in rows as hedges
objs += tree("Bush", "coyote_brush", 1.25, R_A, G1, (0.28, 0.5, 0.13), BARK, cards=70, bark_tris=40, light_cards=24, card_scale=1.0, light_scale=1.6, radius=1.0, seed=2,
             scale=1.3, leaves=5, leafScale=0.6, leafScaleX=1.0, horzLeaves=False)


# ============================================================ cars
def curve(pts):
    """A smooth line through (s, value) points (Catmull-Rom); pts in any order."""
    pts = sorted(pts); xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    def f(x):
        if x <= xs[0]: return ys[0]
        if x >= xs[-1]: return ys[-1]
        i = max(j for j in range(len(xs) - 1) if xs[j] <= x); h = xs[i + 1] - xs[i]; t = (x - xs[i]) / h
        m0 = (ys[i + 1] - ys[i - 1]) / (xs[i + 1] - xs[i - 1]) if i > 0 else (ys[1] - ys[0]) / h
        m1 = (ys[i + 2] - ys[i]) / (xs[i + 2] - xs[i]) if i + 2 < len(xs) else (ys[i + 1] - ys[i]) / h
        return (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m0 + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m1
    return f


def car(n, C, light=False):
    L, W, r, clear = C["L"], C["W"], C["r"], C["clear"]; nose, tail = L / 2, -L / 2
    saF, saR = C["axles"]; Ra = r + 0.075; cowl, rf, rr, rb = C["cabin"]; g0, g1 = C["glass"]
    top, beltc = curve(C["top"]), curve(C["belt"]); roof_w = C.get("roof_w", 0.74); hmax = max(p[1] for p in C["top"])
    P = {k: Geo() for k in ("Body", "Glass", "Trim", "Lights", "Rim", "Tail")}

    def half(s):  # half-width in plan: the corners of the car are rounded off
        tf = max(0, (s - (nose - 1.0)) / 1.0); tr = max(0, ((tail + 0.85) - s) / 0.85)
        return W / 2 * (1 - C.get('taper', 0.2) * tf ** 2.3 - 0.15 * tr ** 2.3)
    def bottom(s):
        y = clear + 0.05 * max(0, (abs(s) - (L / 2 - 0.5)) / 0.5)
        for sa in (saF, saR):
            if abs(s - sa) < Ra - 1e-6: y = max(y, r + (0.8 * Ra if light else sqrt(Ra * Ra - (s - sa) ** 2)))
        return y
    def section(s):
        w = half(s); yb = bottom(s); y0 = clear + 0.05 * max(0, (abs(s) - (L / 2 - 0.5)) / 0.5); tp = top(s); belt = min(beltc(s), tp - 0.035)
        mid = y0 + 0.5 * (belt - y0)
        p3 = max(yb + 0.015, y0 + 0.1); p4 = max(mid, p3 + 0.02); p5 = max(belt - 0.075, p4 + 0.02); belt = max(belt, p5 + 0.03)
        pts = [(0, clear), (w - 0.3, yb), (w - 0.03, yb), (w - 0.014, p3), (w, p4), (w - 0.022, p5), (w - 0.06, belt)]
        if rb <= s <= cowl:
            gt = max(belt, tp - 0.075); f = min(1, max(0, (gt - belt) / (hmax - 0.075 - beltc(0)))); x7 = (w - 0.06) + (w * roof_w + 0.07 - (w - 0.06)) * f
            pts += [(x7, gt), (x7 - 0.075, tp - 0.018), (x7 * 0.5, tp + 0.004), (0, tp + 0.012)]
        else:
            pts += [(w - 0.11, max(belt + 0.004, tp - 0.012)), (w - 0.2, max(belt + 0.008, tp - 0.004)), (w * 0.45, max(belt + 0.01, tp + 0.004)), (0, max(belt + 0.012, tp + 0.008))]
        return pts

    # stations along the car, densest round the wheel arches and at the ends
    key = [nose, nose - 0.05, nose - 0.14, nose - 0.26, cowl, rf, rr, rb, g0, g1, tail, tail + 0.05, tail + 0.14, tail + 0.26] + [p for b in C["pillars"] for p in (b - 0.045, b + 0.045)]
    arch = [sa + Ra * cos(a) for sa in (saF, saR) for a in np.linspace(0, pi, 9)] + [sa + sg * (Ra + 0.02) for sa in (saF, saR) for sg in (-1, 1)]
    if light:
        key = [nose, cowl, rf, rr, rb, tail]; arch = [sa + sg * q for sa in (saF, saR) for sg in (-1, 1) for q in (Ra + 0.02, Ra * 0.55)]
        st = sorted(set(round(s, 3) for s in arch if tail < s < nose)); st = [s for s in st] + [k for k in key if all(abs(k - s) > 0.14 for s in st)]
    else:
        st = key + arch; st += [s for s in np.arange(tail + 0.2, nose - 0.19, 0.19) if all(abs(s - k) > 0.07 for k in st)]
    st = sorted(set(round(float(s), 4) for s in st if tail - 1e-6 <= s <= nose + 1e-6), reverse=True)
    idx = [2, 3, 5, 6, 7, 10] if light else list(range(11))
    secs = [section(s) for s in st]
    def kind(a, b, sm, side=True):
        """Which part a strip of the body belongs to: a, b = the two section points it runs between, sm = where along the car."""
        if b <= 2: return "Trim"
        if (a, b) == (2, 3): return "Trim" if C.get("cladding") else "Body"
        if a >= 3 and b <= 5 and not light:
            if a == 4 and sm > nose - 0.27: return "Lights"
            if a == 4 and sm < tail + 0.27: return "Tail"
        if (a, b) == (6, 7):
            if any(abs(sm - p) < 0.05 for p in C["pillars"]): return "Trim"
            return "Glass" if g1 < sm < g0 else "Body"
        if a >= 7 and b <= 10 and (b > 8 or light):
            if rf < sm < cowl or rb < sm < rr: return "Glass"
        return "Body"
    for k in range(len(st) - 1):
        A, Bq, sa_, sb_ = secs[k], secs[k + 1], st[k], st[k + 1]; sm = (sa_ + sb_) / 2
        for j in range(len(idx) - 1):
            a, b = idx[j], idx[j + 1]; part = P[kind(a, b, sm)]
            for sg in (1, -1):
                part.face([(sg * A[a][0], A[a][1], sa_), (sg * Bq[a][0], Bq[a][1], sb_), (sg * Bq[b][0], Bq[b][1], sb_), (sg * A[b][0], A[b][1], sa_)], inside=(0, 0.55 * hmax, sm))
    # the two ends: bumper, grille, lamps, number plate
    for end, s, S_ in ((1, st[0], secs[0]), (-1, st[-1], secs[-1])):
        for j in range(len(idx) - 1):
            a, b = idx[j], idx[j + 1]; lo, hi = S_[a], S_[b]; lamp = (a, b) == ((3, 5) if light else (4, 5))
            cuts = [-1, -0.46, 0.46, 1] if (lamp or (a, b) == (3, 4)) else [-1, 1]
            for c0, c1 in zip(cuts, cuts[1:]):
                outer = abs(c0) == 1 and len(cuts) > 2
                nm = ("Trim" if b <= 2 or C.get("cladding") else "Body") if b <= 3 else ("Lights" if end > 0 else "Tail") if lamp and outer else "Trim" if end > 0 and len(cuts) > 2 and not outer else "Body"
                P[nm].face([(c0 * lo[0], lo[1], s), (c1 * lo[0], lo[1], s), (c1 * hi[0], hi[1], s), (c0 * hi[0], hi[1], s)], inside=(0, 0.5, s - end * 0.5))
        if not light:
            yb, yt = (S_[3][1] + 0.01, S_[3][1] + 0.12) if end > 0 else (S_[4][1] + 0.02, S_[4][1] + 0.13)
            P["Lights"].face([(-0.24, yb, s + end * 0.012), (0.24, yb, s + end * 0.012), (0.24, yt, s + end * 0.012), (-0.24, yt, s + end * 0.012)], inside=(0, 0.5, s - end * 0.5))
            if end > 0:   # two bright bars across the grille
                for f in (0.3, 0.68):
                    y = S_[4][1] + (S_[5][1] - S_[4][1]) * f; x = S_[4][0] * 0.44
                    P["Rim"].face([(-x, y, s + 0.008), (x, y, s + 0.008), (x, y + 0.022, s + 0.008), (-x, y + 0.022, s + 0.008)], inside=(0, 0.5, s - 0.5))

    def box(part, c, size, inside=None):
        x, y, z = c; a, b, d = size[0] / 2, size[1] / 2, size[2] / 2
        V = [(x + i * a, y + j * b, z + k * d) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): P[part].face([V[i] for i in f], inside=c)
    def wheel(x, s):
        sg = 1 if x > 0 else -1; w = 0.215 if r < 0.36 else 0.255; mid = (x - sg * w / 2, r, s)
        if light:
            N = 7; ring = lambda rad, xo: [(x + sg * xo, r + rad * cos(i / N * 2 * pi), s + rad * sin(i / N * 2 * pi)) for i in range(N)]
            o, i_ = ring(r, 0), ring(r, -w)
            for k in range(N): P["Trim"].face([o[k], o[(k + 1) % N], i_[(k + 1) % N], i_[k]], inside=mid)
            P["Trim"].face(o, inside=mid); P["Rim"].face(ring(r * 0.6, 0.006), inside=mid); return
        N = 14; ring = lambda rad, xo: [(x + sg * xo, r + rad * cos(i / N * 2 * pi), s + rad * sin(i / N * 2 * pi)) for i in range(N)]
        prof = [(0.62 * r, -0.012), (0.9 * r, 0.004), (0.985 * r, -0.03), (r, -0.06), (r, -w + 0.03), (0.9 * r, -w)]
        rings = [ring(a, b) for a, b in prof]
        for a, b in zip(rings, rings[1:]):
            for k in range(N): P["Trim"].face([a[k], a[(k + 1) % N], b[(k + 1) % N], b[k]], inside=mid)
        lip0, lip1 = ring(0.62 * r, -0.012), ring(0.56 * r, -0.03)
        for k in range(N): P["Rim"].face([lip0[k], lip0[(k + 1) % N], lip1[(k + 1) % N], lip1[k]], inside=mid)
        P["Trim"].face(ring(0.57 * r, -0.07), inside=mid)                                    # dark behind the spokes
        P["Rim"].face([(x - sg * 0.022, r + 0.17 * r * cos(i / 10 * 2 * pi), s + 0.17 * r * sin(i / 10 * 2 * pi)) for i in range(10)], inside=mid)
        for q in range(5):                                                                   # five spokes
            a = q / 5 * 2 * pi + 0.3; pt = lambda rad, da, xo: (x + sg * xo, r + rad * cos(a + da), s + rad * sin(a + da))
            P["Rim"].face([pt(0.15 * r, -0.42, -0.024), pt(0.15 * r, 0.42, -0.024), pt(0.575 * r, 0.11, -0.03), pt(0.575 * r, -0.11, -0.03)], inside=mid)
    for sa in (saF, saR):
        for sg in (-1, 1): wheel(sg * (W / 2 - 0.018), sa)
    if not light:
        def at(s, i):  # a point of the body side at station s
            return section(s)[i]
        for sg in (-1, 1):
            # door shut lines and handles
            for s in C["shuts"]:
                for i in (3, 4, 5):
                    a, b = at(s, i), at(s, i + 1)
                    P["Trim"].face([(sg * (a[0] + 0.004), a[1], s - 0.007), (sg * (a[0] + 0.004), a[1], s + 0.007), (sg * (b[0] + 0.004), b[1], s + 0.007), (sg * (b[0] + 0.004), b[1], s - 0.007)], inside=(0, 0.6, s))
            for s in C["handles"]:
                p = at(s, 5); box("Trim", (sg * (p[0] + 0.012), p[1] - 0.03, s), (0.03, 0.03, 0.17))
            # door mirror on a short arm
            m = at(cowl - 0.3, 6); mx, my, mz = m[0] + 0.115, m[1] + 0.045, cowl - 0.3
            box("Body", (sg * mx, my, mz), (0.16, 0.1, 0.06)); box("Trim", (sg * (m[0] + 0.025), my - 0.02, mz), (0.07, 0.03, 0.045))
            P["Glass"].face([(sg * (mx - 0.07), my - 0.04, mz - 0.031), (sg * (mx + 0.07), my - 0.04, mz - 0.031), (sg * (mx + 0.07), my + 0.04, mz - 0.031), (sg * (mx - 0.07), my + 0.04, mz - 0.031)], inside=(sg * mx, my, mz))
            if C.get("rails"):
                s0, s1 = rf - 0.25, rr + 0.15; x = half(0) * roof_w - 0.02
                box("Trim", (sg * x, top((s0 + s1) / 2) + 0.075, (s0 + s1) / 2), (0.04, 0.03, s0 - s1))
                for s in (s0 - 0.08, (s0 + s1) / 2, s1 + 0.08): box("Trim", (sg * x, top(s) + 0.03, s), (0.04, 0.07, 0.07))
        # windscreen wipers' black scuttle and the rear number-plate lamp strip
        box("Trim", (0, top(cowl) + 0.006, cowl + 0.035), (W * 0.74, 0.012, 0.09))
    suffix = f"Car{n}L" if light else f"Car{n}"
    made = [g.build(f"{suffix}_{k}", weld=True) for k, g in P.items() if g.f]
    print(suffix, sum(g.tris() for g in P.values()), "triangles", {k: g.tris() for k, g in P.items() if g.f})
    return made


CARS = {
    # saloon, the size of a Corolla
    1: dict(L=4.62, W=1.775, r=0.318, clear=0.19, axles=(1.38, -1.32), cabin=(1.16, 0.42, -0.98, -1.74), glass=(1.02, -1.42), pillars=[-0.3], shuts=[0.86, -0.3, -1.02], handles=[-0.12, -0.9],
            top=[(2.31, 0.66), (2.25, 0.735), (1.75, 0.84), (1.16, 0.945), (0.42, 1.385), (-0.25, 1.455), (-0.98, 1.4), (-1.74, 1.05), (-2.2, 1.025), (-2.31, 0.94)],
            belt=[(2.31, 0.64), (1.16, 0.895), (0.2, 0.915), (-1.4, 0.965), (-2.31, 0.9)]),
    # 4x4, the size of a Land Cruiser Prado: upright, long roof, black lower cladding, roof rails
    2: dict(L=4.84, W=1.885, r=0.39, clear=0.26, axles=(1.5, -1.29), cabin=(1.1, 0.5, -2.02, -2.38), glass=(0.98, -2.18), pillars=[0.02, -1.08], shuts=[0.9, 0.02, -0.82], handles=[0.2, -0.66], cladding=True, rails=True, roof_w=0.8, taper=0.13,
            top=[(2.42, 1.02), (2.37, 1.09), (1.7, 1.15), (1.1, 1.215), (0.5, 1.76), (-0.5, 1.84), (-2.02, 1.8), (-2.38, 1.24), (-2.42, 1.12)],
            belt=[(2.42, 0.98), (1.1, 1.175), (-2.38, 1.215), (-2.42, 1.12)]),
    # small hatchback, the size of a Vitz
    3: dict(L=3.89, W=1.695, r=0.29, clear=0.17, axles=(1.15, -1.36), cabin=(0.98, 0.28, -1.38, -1.86), glass=(0.86, -1.56), pillars=[-0.22], shuts=[0.72, -0.22, -0.98], handles=[-0.04, -0.82],
            top=[(1.945, 0.67), (1.89, 0.745), (1.45, 0.86), (0.98, 0.965), (0.28, 1.435), (-0.5, 1.5), (-1.38, 1.44), (-1.86, 0.99), (-1.945, 0.88)],
            belt=[(1.945, 0.65), (0.98, 0.925), (-1.86, 1.0), (-1.945, 0.88)]),
}
for n, C in CARS.items(): objs += car(n, C) + car(n, C, light=True)

# ============================================================ export
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
kw = dict(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=True, export_normals=True, export_materials="NONE",
          export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_draco_position_quantization=14, export_draco_normal_quantization=10,
          export_draco_texcoord_quantization=12, export_draco_color_quantization=8)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
if "export_vertex_color" in props: kw["export_vertex_color"] = "ACTIVE"
if "export_all_vertex_colors" in props: kw["export_all_vertex_colors"] = False
if "export_active_vertex_color_when_no_material" in props: kw["export_active_vertex_color_when_no_material"] = True
bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})
print("world.glb", round(os.path.getsize(OUT) / 1024), "KB,", len(objs), "objects")


# ============================================================ previews
def render():
    sc = bpy.context.scene; os.makedirs(REN, exist_ok=True)
    sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1280; sc.render.resolution_y = 800
    sc.view_settings.view_transform = "Standard"; sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 88
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.78, 1.0, 1); bg.inputs[1].default_value = 1.0
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.2; sun.angle = radians(4); so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    so.rotation_euler = Vector((0.45, 0.5, -0.75)).to_track_quat("-Z", "Y").to_euler()
    def mat(name, col, rough=0.5, metal=0.0, emit=0.0):
        m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        if emit: b.inputs["Emission Color"].default_value = (*col, 1); b.inputs["Emission Strength"].default_value = emit
        return m
    gm = mat("ground", (0.23, 0.23, 0.24), 0.9); bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0)); bpy.context.object.data.materials.append(gm)
    leaf = bpy.data.materials.new("leaf"); leaf.use_nodes = True; nt = leaf.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.85
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(TEXF); vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
    nt.links.new(tx.outputs["Color"], mx.inputs[6]); nt.links.new(vc.outputs["Color"], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5; nt.links.new(tx.outputs["Alpha"], gt.inputs[0]); nt.links.new(gt.outputs[0], b.inputs["Alpha"])
    try: leaf.surface_render_method = "DITHERED"
    except Exception: pass
    paints = [(0.75, 0.75, 0.76), (0.42, 0.03, 0.03), (0.03, 0.09, 0.3)]
    M = dict(Glass=mat("glass", (0.02, 0.03, 0.035), 0.06, 0.6), Trim=mat("trim", (0.012, 0.012, 0.013), 0.7), Lights=mat("lights", (1, 0.97, 0.9), 0.3, 0, 1.5),
             Rim=mat("rim", (0.75, 0.76, 0.78), 0.3, 0.9), Tail=mat("tail", (0.5, 0.02, 0.02), 0.35, 0, 0.4))
    for o in objs:
        o.location = (500, 0, 0)
        if o.name.startswith("Car"):
            k = o.name.split("_")[1]; o.data.materials.append(mat("paint" + o.name, paints[int(o.name[3]) - 1], 0.3, 0.5) if k == "Body" else M[k])
        else: o.data.materials.append(leaf)
    cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co; cam.clip_end = 500; cam.clip_start = 0.05
    def shot(name, names, loc, tgt, lens=50, spread=0):
        shown = [o for o in objs if any(o.name == n or o.name.startswith(n + "_") for n in names)]
        for o in shown: o.location = (names.index(o.name.split("_")[0]) * spread, 0, 0)
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); cam.lens = lens
        sc.render.filepath = os.path.join(REN, name + ".jpg"); bpy.ops.render.render(write_still=True)
        for o in shown: o.location = (500, 0, 0)
    for n in (1, 2, 3):
        shot(f"car{n}_front", [f"Car{n}"], (3.6, -5.6, 1.9), (0, 0, 0.7), 50); shot(f"car{n}_rear", [f"Car{n}"], (-3.9, 5.2, 1.7), (0, 0, 0.7), 50)
        shot(f"car{n}_side", [f"Car{n}"], (7.5, 0.2, 1.1), (0, 0, 0.75), 60)
    shot("cars_light", ["Car1L", "Car2L", "Car3L"], (9, -9, 4.5), (2.6, 0, 0.6), 50, spread=2.6)
    shot("tree1", ["Tree1"], (13, -15, 4), (0, 0, 4.6), 45); shot("tree2", ["Tree2"], (13, -17, 4), (0, 0, 5.6), 45)
    shot("tree3", ["Tree3"], (9, -12, 3), (0, 0, 4.2), 45); shot("bush", ["Bush"], (2.2, -2.8, 1.2), (0, 0, 0.6), 45)
    shot("trees_light", ["Tree1L", "Tree2L", "Tree3L", "BushL"], (22, -30, 6), (12, 0, 4.5), 45, spread=9)
    shot("tree1_close", ["Tree1"], (3.5, -5, 1.7), (0, 0, 5.5), 28)


if "render" in ARGS: render()
