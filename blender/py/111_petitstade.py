"""Petit Stade halls (two flat-roofed sports halls beside Amahoro Stadium) -> public/models/petitstade.glb

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/py/111_petitstade.py
Origin = centre of the LARGER hall at ground level. Larger hall 44.5 m (X) x 56 m (Y) x 14 m high;
smaller hall 31 m (X) x 44 m (Y) x 12 m high centred at X=+52, Y=0. Entrances face +Y.
Reuses the stadium helpers and textures from 110_amahoro.py.
"""
import bpy, os, sys, math, importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('amahoro', os.path.join(HERE, '110_amahoro.py'))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
Mesh, obox, cyl, V3 = A.Mesh, A.obox, A.cyl, A.V3

HALLS = [dict(cx=0.0, cy=0.0, w=44.5, d=56.0, h=14.0),
         dict(cx=52.0, cy=0.0, w=31.0, d=44.0, h=12.0)]
Z_G = 4.2          # top of recessed ground floor / bottom of screen
INSET = 1.6        # ground floor recess
PAD = 7.0          # paving beyond the halls


def build(coll):
    M = A.shared_materials(small=True)
    M['seam'] = A.make_mat('Roof_Seam', 'seam.jpg', 'seam_n.jpg', rough=0.55, metal=0.15)
    screen = Mesh('Facade_Screen', M['screen'])
    inner = Mesh('Facade_Inner', M['inner'])
    stone = Mesh('Stone', M['stone'], tile=2.4)
    conc = Mesh('Concrete', M['concrete'])
    glaz = Mesh('Entrance_Glazing', M['glazing'])
    pav = Mesh('Paving', M['paving'])
    kerb = Mesh('Kerb', M['kerb'], tile=2.0)
    mdark = Mesh('Metal_Dark', M['metal_dark'], smooth=True, tile=1.0)
    mlight = Mesh('Metal_Light', M['metal_light'], tile=1.0)
    seam = Mesh('Roof_Seam', M['seam'])
    UP, DN = np.array([0, 0, 1.]), np.array([0, 0, -1.])

    def sides(cx, cy, w, d, off=0.0):
        """4 sides CCW from the SE corner: (start, end, outward normal, name)."""
        x0, x1, y0, y1 = cx - w / 2 - off, cx + w / 2 + off, cy - d / 2 - off, cy + d / 2 + off
        c = [np.array(p, float) for p in ((x1, y0), (x1, y1), (x0, y1), (x0, y0))]
        nr = [np.array(p, float) for p in ((1, 0), (0, 1), (-1, 0), (0, -1))]
        return [(c[k], c[(k + 1) % 4], nr[k], 'ENWS'[k]) for k in range(4)]

    for H in HALLS:
        cx, cy, w, d, h = H['cx'], H['cy'], H['w'], H['d'], H['h']
        zt = h - 0.5                       # top of screen (parapet coping above)
        rows = max(2, int(round((zt - Z_G) / 3.4)))
        ph = (zt - Z_G) / rows
        for (p0, p1, n, nm) in sides(cx, cy, w, d):
            L = np.linalg.norm(p1 - p0)
            t = (p1 - p0) / L
            n3, t3 = V3(n), V3(t)
            # ---- pierced screen wrapped round the upper walls
            nc = max(2, 2 * int(round(L / ph / 2)))
            for k in range(nc):
                a, b = p0 + t * L * k / nc, p0 + t * L * (k + 1) / nc
                u0 = 0.0 if k % 2 == 0 else 0.5
                screen.poly([V3(a, Z_G), V3(b, Z_G), V3(b, zt), V3(a, zt)],
                            [(u0, 0), (u0 + .5, 0), (u0 + .5, rows / 2), (u0, rows / 2)], n3)
                if k:
                    obox(mlight, V3(a, Z_G) - t3 * 0.05 - n3 * 0.03, t3 * 0.1, n3 * 0.2, [0, 0, zt - Z_G],
                         skip=('z0', 'z1', 'y0'))
            # dark wall behind the screen
            ia, ib = p0 - n * 1.0, p1 - n * 1.0
            nb = max(1, int(round(L / 7.5)))
            for k in range(nb):
                a, b = ia + t * L * k / nb, ia + t * L * (k + 1) / nb
                inner.poly([V3(a, Z_G - 0.5), V3(b, Z_G - 0.5), V3(b, zt), V3(a, zt)],
                           [(0, 0.2), (1, 0.2), (1, 0.8), (0, 0.8)], n3)
            # fascia under the screen, parapet coping above
            obox(mlight, V3(p0, Z_G - 0.55) - n3 * 1.0 - t3 * 0.12, t3 * (L + 0.24), n3 * 1.12, [0, 0, 0.6])
            obox(mlight, V3(p0, zt) - n3 * 1.0 - t3 * 0.12, t3 * (L + 0.24), n3 * 1.12, [0, 0, 0.5])
            # ---- recessed ground floor
            g0, g1 = p0 - n * INSET, p1 - n * INSET
            nbay = max(2, int(round(L / 7.4)))
            for k in range(nbay):
                a, b = g0 + t * L * k / nbay, g0 + t * L * (k + 1) / nbay
                if nm == 'N':
                    ty = 'glass' if 0 < k < nbay - 1 else 'stone'
                else:
                    ty = 'gate' if (k % 3 == 1) else ('glass' if k % 3 == 2 and nm != 'S' else 'stone')
                if ty == 'stone':
                    stone.quad(V3(a, 0), V3(b, 0), V3(b, Z_G - 0.5), V3(a, Z_G - 0.5), hint=n3)
                else:
                    u0 = 0.0 if ty == 'glass' else 0.5
                    glaz.poly([V3(a, 0), V3(b, 0), V3(b, Z_G - 0.5), V3(a, Z_G - 0.5)],
                              [(u0, 0), (u0 + .5, 0), (u0 + .5, 1), (u0, 1)], n3)
                # square stone-clad column on the building line
                for kk in ((k, k + 1) if k == nbay - 1 else (k,)):
                    c = p0 + t * L * kk / nbay - n * 0.45
                    obox(stone, V3(c, 0) - t3 * 0.3 - n3 * 0.3, t3 * 0.6, n3 * 0.6, [0, 0, Z_G - 0.5],
                         skip=('z0', 'z1'))
            # soffit over the recess
            conc.quad(V3(g0, Z_G - 0.55), V3(g1, Z_G - 0.55), V3(p1, Z_G - 0.55), V3(p0, Z_G - 0.55), hint=DN)
            # parapet inner face
            pa, pb = p0 - n * 1.0, p1 - n * 1.0
            conc.quad(V3(pa, h - 1.4), V3(pb, h - 1.4), V3(pb, h), V3(pa, h), hint=-n3)
        # ---- entrance canopy + steps on the +Y face
        cw = min(16.0, w * 0.5)
        y1 = cy + d / 2
        obox(mdark, (cx - cw / 2, y1 - INSET, 3.25), (cw, 0, 0), (0, INSET + 3.2, 0), (0, 0, 0.35))
        for sx in (-1, 1):
            cyl(mdark, (cx + sx * (cw / 2 - 0.5), y1 + 2.7, 0.02), 0.14, 3.23, n=8, cap=False)
        obox(stone, (cx - cw / 2 - 1, y1 - INSET, 0.02), (cw + 2, 0, 0), (0, INSET + 2.0, 0), (0, 0, 0.16),
             skip=('z0',))
        # ---- roof: standing seam strips with low ridges running along Y
        ri = 1.0
        rx0, rx1, ry0, ry1 = cx - w / 2 + ri, cx + w / 2 - ri, cy - d / 2 + ri, cy + d / 2 - ri
        nstrip = 4 if w > 40 else 3
        zr = h - 1.4
        sw = (rx1 - rx0) / nstrip
        for k in range(nstrip):
            xa, xm, xb = rx0 + k * sw, rx0 + (k + .5) * sw, rx0 + (k + 1) * sw
            for (xs, xe) in ((xa, xm), (xb, xm)):
                seam.poly([(xs, ry0, zr), (xs, ry1, zr), (xe, ry1, zr + 0.45), (xe, ry0, zr + 0.45)],
                          [(0, 0), ((ry1 - ry0) / 4, 0), ((ry1 - ry0) / 4, sw / 8), (0, sw / 8)], UP)
            obox(mlight, (xm - 0.15, ry0, zr + 0.42), (0.3, 0, 0), (0, ry1 - ry0, 0), (0, 0, 0.1), skip=('z0',))
            for ye, sg in ((ry0, -1), (ry1, 1)):
                conc.poly([(xa, ye, zr), (xb, ye, zr), (xm, ye, zr + 0.45)], None, np.array([0, sg, 0.]))
        # ---- rooftop plant
        rng = np.random.default_rng(int(w * 10))
        for k in range(5 if w > 40 else 3):
            ux = rx0 + 4 + (rx1 - rx0 - 10) * (k % 3) / 2.0
            uy = ry0 + 6 + (ry1 - ry0 - 14) * (k // 3)
            sx_, sy_, sz_ = 2.6 + rng.random(), 1.6 + rng.random() * 0.6, 1.3 + 0.5 * rng.random()
            obox(conc, (ux - 0.3, uy - 0.3, zr), (sx_ + 0.6, 0, 0), (0, sy_ + 0.6, 0), (0, 0, 0.5), skip=('z0',))
            obox(mlight, (ux, uy, zr + 0.5), (sx_, 0, 0), (0, sy_, 0), (0, 0, sz_), skip=('z0',))
            obox(mdark, (ux + 0.2, uy - 0.03, zr + 0.7), (sx_ - 0.4, 0, 0), (0, 0.03, 0), (0, 0, sz_ - 0.4),
                 skip=('y1',))
            cyl(mdark, (ux + sx_ / 2, uy + sy_ / 2, zr + 0.5 + sz_), 0.5, 0.12, n=10)
        # roof access hatch / duct run
        obox(mdark, (rx0 + 2, ry1 - 4, zr + 0.2), (rx1 - rx0 - 4, 0, 0), (0, 0.5, 0), (0, 0, 0.4), skip=('z0',))

    # ---- paving strip around and between the halls, with kerb
    x0 = HALLS[0]['cx'] - HALLS[0]['w'] / 2 - PAD
    x1 = HALLS[1]['cx'] + HALLS[1]['w'] / 2 + PAD
    y0 = -HALLS[0]['d'] / 2 - PAD
    y1 = HALLS[0]['d'] / 2 + PAD + 3
    nx, ny = 8, 6
    for i in range(nx):
        for j in range(ny):
            xa, xb = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            ya, yb = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
            pav.poly([(xa, ya, 0.02), (xb, ya, 0.02), (xb, yb, 0.02), (xa, yb, 0.02)],
                     [(0, 0), ((xb - xa) / 4, 0), ((xb - xa) / 4, (yb - ya) / 4), (0, (yb - ya) / 4)], UP)
    for (p0, p1, n, nm) in sides((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0):
        L = np.linalg.norm(p1 - p0)
        t3, n3 = V3((p1 - p0) / L), V3(n)
        ns = int(math.ceil(L / 20))
        for k in range(ns):
            o = V3(p0, 0) + t3 * L * k / ns
            obox(kerb, o - n3 * 0.3, t3 * L / ns, n3 * 0.3, [0, 0, 0.17], skip=('z0', 'x0', 'x1'), tile=2.0)
    # bollards and two lamp posts along the entrance side
    for x in np.arange(x0 + 3, x1 - 2, 3.5):
        cyl(mdark, (x, y1 - 1.0, 0.02), 0.11, 0.9, n=8)
    for x in (HALLS[0]['cx'] + HALLS[0]['w'] / 2 + 7.1, x0 + 2.5, x1 - 2.5):
        cyl(mdark, (x, y1 - 2.2, 0.02), 0.10, 9.0, n=8, r2=0.07)
        obox(mdark, (x - 0.9, y1 - 2.4, 9.0), (1.8, 0, 0), (0, 0.4, 0), (0, 0, 0.08))
    objs = [m.build(coll) for m in Mesh.all.values() if m.f]
    print('TRIS', {m.name: m.tris() for m in Mesh.all.values()}, 'total', sum(m.tris() for m in Mesh.all.values()))
    return objs


def main():
    coll = A.reset_scene()
    objs = build(coll)
    A.export_glb(objs, os.path.join(A.MODELS, 'petitstade.glb'))
    if os.environ.get('TOUR_RENDER', '1') != '0':
        A.setup_render()
        A.render_view('aerial', (-55, 110, 75), (28, 0, 4), lens=32, prefix='petit_')
        A.render_view('top', (26, 0, 300), (26, 0, 0), ortho=125, res=(1300, 1000), prefix='petit_')
        A.render_view('ground', (10, 75, 1.7), (22, 28, 6), lens=22, prefix='petit_')
        A.render_view('close', (-12, 40, 1.7), (2, 27, 3.2), lens=22, prefix='petit_')


if __name__ == '__main__':
    main()
