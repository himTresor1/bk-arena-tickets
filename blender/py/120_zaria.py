# Zaria Court, Kigali: web-ready model for the three.js walk/fly tour.
#   Blender -b --factory-startup -P blender/py/120_zaria.py            build + export public/models/zaria.glb
#   Blender -b --factory-startup -P blender/py/120_zaria.py -- render  ... and render previews to blender/renders/zaria
#   (add "tex" after -- to force the textures to be regenerated)
# The same file, run by ~/.blender-mcp/venv/bin/python with the argument "tex", paints the textures (PIL + numpy).
# Units metres, Z up, origin at site centre, +X along the avenue, avenue on the -Y side.
import os, sys, math, random, subprocess
from math import sin, cos, pi, radians, sqrt

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX = os.path.join(ROOT, "blender", "tex", "zaria")
REN = os.path.join(ROOT, "blender", "renders", "zaria")
OUT = os.path.join(ROOT, "public", "models", "zaria.glb")
VENV_PY = os.path.expanduser("~/.blender-mcp/venv/bin/python")
COURT_V0 = 1 - 608 / 1024  # court picture is the top 608 rows of court.jpg, pool water the rest


# ============================================================ textures (runs outside Blender)
def make_textures(out):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    os.makedirs(out, exist_ok=True)
    R = np.random.default_rng(11)

    def noise(n, fx, fy=None):
        fy = fy or fx
        g = R.random((fy, fx)).astype(np.float32)
        im = Image.fromarray(np.tile(g, (3, 3))).resize((3 * n, 3 * n), Image.BICUBIC)
        return np.asarray(im)[n:2 * n, n:2 * n]

    def fbm(n, fs=(4, 8, 16, 32, 64), p=0.55):
        a = np.zeros((n, n), np.float32); w = 1.0; tot = 0.0
        for f in fs:
            a += w * noise(n, f); tot += w; w *= p
        return a / tot

    def grain(n, s):
        return ((R.random((n, n)).astype(np.float32) - 0.5) * s)[..., None]

    def col(c):
        return np.array(c, np.float32)

    def save(a, name, q=80):
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        p = os.path.join(out, name)
        if name.endswith(".png"): im.save(p, optimize=True)
        else: im.convert("RGB").save(p, quality=q, optimize=True)

    def grid(n):
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        return xx / n, yy / n

    # ---- brick: 10 bricks x 28 courses per tile (2.3 m x 2.24 m)
    n = 1024
    u, v = grid(n); u = u * 10; v = v * 28
    row = np.floor(v).astype(int); bu = u + 0.5 * (row % 2); bi = np.floor(bu).astype(int) % 10
    fu = bu - np.floor(bu); fv = v - row
    t = R.random((28, 10, 3)).astype(np.float32)[row % 28, bi]
    c = col((174, 92, 62)) * (0.80 + 0.40 * t[..., 0:1]) + (t[..., 1:2] - 0.5) * col((34, 14, -4))
    c = np.where(t[..., 2:3] > 0.88, c * 0.70 + col((8, 2, 8)), c)
    c = np.where(t[..., 2:3] < 0.07, c * 1.12 + col((14, 10, 0)), c)
    lf = fbm(n)[..., None]
    c = c * (0.90 + 0.2 * lf) + grain(n, 16) + (fbm(n, (64, 128))[..., None] - 0.5) * 22
    c = c * np.where(fv > 0.88, 0.86, 1.0)[..., None] * np.where((fv > 0.125) & (fv < 0.2), 1.07, 1.0)[..., None]
    mort = (fu < 0.045) | (fv < 0.125)
    mc = col((176, 164, 148)) * (0.9 + 0.2 * lf) + grain(n, 12)
    save(np.where(mort[..., None], mc, c), "brick.jpg", 78)
    h = np.clip(((~mort).astype(np.float32) + 0.25 * (t[..., 0] - 0.5)) * 180 + 30, 0, 255).astype(np.uint8)
    h = Image.fromarray(h).resize((512, 512), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.6))
    h = np.asarray(h).astype(np.float32) / 180.0; h = np.pad(h, 1, mode="wrap")
    dx = (h[1:-1, 2:] - h[1:-1, :-2]) * 1.6; dy = (h[2:, 1:-1] - h[:-2, 1:-1]) * 1.6
    nrm = np.stack([-dx, dy, np.ones_like(dx)], -1); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    save(nrm * 127.5 + 127.5, "brick_n.jpg", 80)

    # ---- herringbone pavers, 0.2 x 0.1 m, tile 1.6 m
    def herring(n, base, var, joint, name, q):
        u, v = grid(n); u = u * 16; v = v * 16
        cx = np.floor(u).astype(int); cy = np.floor(v).astype(int); k = (cx - cy) % 4
        ax = np.where(k == 1, cx - 1, cx); ay = np.where(k == 2, cy - 1, cy)
        horiz = k < 2
        lx = u - ax; ly = v - ay
        j = 0.05
        jt = np.where(horiz, (lx < j) | (lx > 2 - j) | (ly < j) | (ly > 1 - j), (lx < j) | (lx > 1 - j) | (ly < j) | (ly > 2 - j))
        t = R.random((16, 16, 2, 3)).astype(np.float32)[ax % 16, ay % 16, horiz.astype(int)]
        c = col(base) * (0.84 + 0.32 * t[..., 0:1]) + (t[..., 1:2] - 0.5) * col(var)
        c = np.where(t[..., 2:3] > 0.9, c * 0.8, c)
        c = c * (0.9 + 0.2 * fbm(n)[..., None]) + grain(n, 14)
        save(np.where(jt[..., None], col(joint) + grain(n, 10), c), name, q)
    herring(1024, (168, 86, 60), (30, 16, 0), (96, 74, 62), "pave_red.jpg", 74)
    herring(512, (206, 172, 146), (16, 14, 10), (140, 124, 110), "pave_buff.jpg", 76)

    # ---- concrete, render, stone
    n = 512
    u, v = grid(n)
    c = col((164, 161, 154)) * (0.88 + 0.24 * fbm(n)[..., None]) + grain(n, 12)
    c *= np.where((v * 5 % 1) < 0.012, 0.9, 1.0)[..., None] * np.where((u * 2.5 % 1) < 0.006, 0.93, 1.0)[..., None]
    c *= np.where(noise(n, 128) > 0.93, 0.86, 1.0)[..., None]
    save(c, "concrete.jpg", 76)
    n = 256
    save(col((228, 212, 180)) * (0.95 + 0.1 * fbm(n)[..., None]) + grain(n, 7), "render.jpg", 80)
    n = 512
    u, v = grid(n); v8 = v * 8; rw = np.floor(v8).astype(int); u4 = u * 4 + 0.5 * (rw % 2)
    t = R.random((8, 4, 2)).astype(np.float32)[rw % 8, np.floor(u4).astype(int) % 4]
    c = col((142, 138, 132)) * (0.78 + 0.4 * t[..., 0:1]) + (t[..., 1:2] - 0.5) * col((16, 8, -6))
    c = c * (0.85 + 0.3 * fbm(n, (16, 32, 64, 128))[..., None]) + grain(n, 22)
    jt = ((u4 % 1) < 0.02) | ((v8 % 1) < 0.045)
    save(np.where(jt[..., None], col((70, 68, 66)), c), "stone.jpg", 76)

    # ---- timbers
    def boards(n, k, base, gap, gapc, name, alpha=False, q=80, streak=18, edge=True):
        u, v = grid(n); p = u * k; bi = np.floor(p).astype(int) % k; f = p - np.floor(p)
        t = R.random((k, 2)).astype(np.float32)[bi]
        st = (noise(n, 96, 3) - 0.5)[..., None]
        c = col(base) * (0.88 + 0.24 * t[..., 0:1]) + st * streak * 2 + (t[..., 1:2] - 0.5) * col((14, 8, 0)) + grain(n, 6)
        if edge: c = c * (0.82 + 0.18 * np.clip(np.minimum(f - gap, 1 - f) * 8, 0, 1))[..., None]
        g = f < gap
        if alpha:
            a = np.where(g, 0, 255).astype(np.float32)[..., None]
            save(np.concatenate([c, a], -1), name)
        else:
            save(np.where(g[..., None], col(gapc), c), name, q)
    boards(512, 12, (206, 138, 70), 0.2, (34, 22, 14), "timber_slat.jpg")
    boards(256, 8, (204, 150, 86), 0.32, None, "slat_alpha.png", alpha=True)
    boards(512, 8, (204, 152, 128), 0.03, (120, 86, 72), "deck.jpg", streak=8, edge=False, q=76)
    boards(256, 6, (112, 40, 32), 0.04, (40, 14, 12), "timber_red.jpg", streak=12)
    n = 256
    st = (noise(n, 64, 4) - 0.5)[..., None]
    save(col((112, 96, 80)) * (0.8 + 0.4 * fbm(n)[..., None]) + st * 60 + grain(n, 14), "bark.jpg", 76)

    # ---- roofs
    n = 512
    u, v = grid(n); f = (u * 4) % 1
    c = col((50, 124, 100)) * (0.93 + 0.14 * fbm(n)[..., None]) + (noise(n, 64, 3) - 0.5)[..., None] * 10 + grain(n, 5)
    c = c * np.where(f < 0.035, 1.22, np.where(f < 0.075, 0.72, 1.0))[..., None]
    save(c, "roof_green.jpg", 80)
    n = 256
    u, v = grid(n)
    c = col((206, 210, 206)) * (0.86 + 0.14 * np.sin(u * 2 * pi * 16))[..., None] * (0.94 + 0.12 * fbm(n)[..., None])
    c = c * np.where((v * 2 % 1) < 0.02, 0.8, 1.0)[..., None]
    save(c, "roof_under.jpg", 80)

    # ---- perforated red truss plate (alpha): web = lower 75 %, solid red paint = top 20 %
    W, H = 512, 256
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    c = np.zeros((H, W, 3), np.float32) + col((204, 66, 40)) + (R.random((H, W, 1)).astype(np.float32) - 0.5) * 10
    cy = H - 0.375 * H
    d = np.sqrt(((xx - W / 2) / 105.0) ** 2 + ((yy - cy) / 52.0) ** 2)
    c = c * np.where((d > 1) & (d < 1.12), 1.15, 1.0)[..., None]
    web = yy > H * 0.25
    c = c * np.where(web & ((yy < H * 0.25 + 8) | (yy > H - 8)), 0.8, 1.0)[..., None]
    c = c * np.where(web & ((xx < 5) | (xx > W - 5)), 0.78, 1.0)[..., None]
    a = np.where(web & (d < 1), 0, 255).astype(np.float32)[..., None]
    save(np.concatenate([c, a], -1), "steel_red.png")

    # ---- court (32 x 19 m, generic colours, no logos) + pool water
    S = 64
    im = Image.new("RGB", (32 * S, 19 * S), (44, 150, 96)); d = ImageDraw.Draw(im)
    def P(x, y): return ((x + 2) * S, (y + 2) * S)
    def rect(x0, y0, x1, y1, fill=None, w=0):
        d.rectangle([P(x0, y0), P(x1, y1)], fill=fill, outline=(255, 255, 255) if w else None, width=w)
    LW = int(0.07 * S)
    rect(0, 0, 28, 15, (34, 82, 196))
    for side in (0, 1):
        def X(x): return 28 - x if side else x
        cols = [(206, 44, 48), (246, 204, 44), (40, 164, 84)]
        if side: cols = cols[::-1]
        for i, cc in enumerate(cols):
            xa, xb = sorted((X(5.8 * i / 3), X(5.8 * (i + 1) / 3)))
            rect(xa, 5.05, xb, 9.95, cc)
        xa, xb = sorted((X(0), X(5.8))); rect(xa, 5.05, xb, 9.95, None, LW)
        cx, cy = P(X(5.8), 7.5); r = 1.8 * S
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=LW)
        cx, cy = P(X(1.575), 7.5); r = 6.75 * S
        d.arc([cx - r, cy - r, cx + r, cy + r], *((102.1, 257.9) if side else (-77.9, 77.9)), fill=(255, 255, 255), width=LW)
        for yl in (0.9, 14.1):
            xa, xb = sorted((X(0), X(2.99))); d.line([P(xa, yl), P(xb, yl)], fill=(255, 255, 255), width=LW)
    cx, cy = P(14, 7.5); r = 1.8 * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 204, 44), outline=(255, 255, 255), width=LW)
    r = 0.6 * S; d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(206, 44, 48))
    d.line([P(14, 0), P(14, 5.7)], fill=(255, 255, 255), width=LW); d.line([P(14, 9.3), P(14, 15)], fill=(255, 255, 255), width=LW)
    rect(0, 0, 28, 15, None, LW)
    court = np.asarray(im.resize((1024, 608), Image.LANCZOS)).astype(np.float32)
    court += (fbm(1024, (128, 256))[:608, :, None] - 0.5) * 10
    yy, xx = np.mgrid[0:416, 0:1024].astype(np.float32)
    ca = fbm(1024, (12, 24, 48))[:416]; ca = np.abs(ca - 0.5) * 2
    w = col((70, 196, 214)) * (0.9 + 0.1 * fbm(1024, (4, 8))[:416, :, None]) + np.clip(1 - ca * 9, 0, 1)[..., None] * 46
    w *= np.where(((xx / 1024 * 26) % 1 < 0.04) | ((yy / 416 * 17) % 1 < 0.06), 0.93, 1.0)[..., None]
    save(np.concatenate([court, w], 0), "court.jpg", 82)

    # ---- foliage
    def leaves(n, bg, pal, count, size, name, q=72, grass=0):
        S2 = 2; im = Image.new("RGB", (n * S2, n * S2), bg); d = ImageDraw.Draw(im)
        for i in range(count):
            x, y = R.random(2) * n * S2; a = R.random() * 2 * pi; L = size * S2 * (0.6 + 0.8 * R.random()); wd = L * 0.42
            k = i / count; p = pal[int(R.random() * len(pal))]
            cc = tuple(int(q_ * (0.45 + 0.75 * k) + R.integers(-10, 10)) for q_ in p)
            ca_, sa_ = cos(a), sin(a)
            shape = [(-1, 0), (-0.4, 0.8), (0.4, 0.75), (1, 0), (0.4, -0.75), (-0.4, -0.8)]
            for ox in (-n * S2, 0, n * S2):
                for oy in (-n * S2, 0, n * S2):
                    if not (-L < x + ox < n * S2 + L and -L < y + oy < n * S2 + L): continue
                    d.polygon([(x + ox + px * L * ca_ - py * wd * sa_, y + oy + px * L * sa_ + py * wd * ca_) for px, py in shape], fill=cc)
                    d.line([(x + ox - L * ca_, y + oy - L * sa_), (x + ox + L * ca_, y + oy + L * sa_)], fill=tuple(int(q_ * 0.8) for q_ in cc), width=1)
        for i in range(grass):
            x, y = R.random(2) * n * S2; a = -pi / 2 + (R.random() - 0.5) * 1.6; L = (6 + R.random() * 14) * S2
            p = pal[int(R.random() * len(pal))]; cc = tuple(int(q_ * (0.7 + 0.6 * R.random())) for q_ in p)
            for ox in (-n * S2, 0, n * S2):
                for oy in (-n * S2, 0, n * S2):
                    d.line([(x + ox, y + oy), (x + ox + L * cos(a), y + oy + L * sin(a))], fill=cc, width=S2)
        save(np.asarray(im.resize((n, n), Image.LANCZOS)).astype(np.float32), name, q)
    leaves(512, (18, 38, 16), [(74, 124, 44), (92, 140, 52), (58, 108, 40), (110, 150, 60)], 2600, 13, "leaves_a.jpg")
    leaves(512, (14, 30, 18), [(44, 92, 46), (56, 104, 52), (38, 80, 44), (72, 112, 50)], 3400, 10, "leaves_b.jpg")
    leaves(512, (44, 58, 30), [(96, 140, 56), (120, 150, 70), (70, 116, 52), (150, 160, 84), (84, 128, 80)], 1500, 7, "planting.jpg", grass=2600)
    n = 256
    save(col((84, 126, 54)) * (0.8 + 0.4 * fbm(n, (8, 16, 32, 64, 128))[..., None]) + grain(n, 22), "lawn.jpg", 74)

    # ---- alpha cards (base at the bottom): palm frond | conifer branch | two leafy sprigs (lower: light, upper: dark)
    S2 = 2; W, H = 170 * S2, 512 * S2
    im = Image.new("RGBA", (3 * W, H), (60, 104, 40, 0)); d = ImageDraw.Draw(im)
    for k in range(46):
        t = k / 45.0; y = H * (0.97 - 0.94 * t); L = W * 0.47 * (0.35 + 0.65 * sin(pi * min(1, t * 1.15 + 0.12)) ** 0.7)
        for sgn in (-1, 1):
            g = int(R.integers(-16, 16)); cc = (70 + g, 122 + g, 40 + g // 2, 255)
            d.polygon([(W / 2, y + 3.4 * S2), (W / 2, y - 3.4 * S2), (W / 2 + sgn * L, y - L * 0.9)], fill=cc)
    d.line([(W / 2, H * 0.99), (W / 2, H * 0.02)], fill=(120, 132, 60, 255), width=4 * S2)
    for k in range(22):
        t = k / 21.0; y = H * (0.97 - 0.9 * t); L = W * 0.47 * (0.3 + 0.7 * (1 - t) ** 0.6)
        for sgn in (-1, 1):
            x1 = W * 1.5 + sgn * L; y1 = y - L * 0.8
            d.line([(W * 1.5, y), (x1, y1)], fill=(60, 60, 40, 255), width=3 * S2)
            for j in range(1, 13):
                s = j / 12.0; px = W * 1.5 + (x1 - W * 1.5) * s; py = y + (y1 - y) * s; nl = (10 + 6 * (1 - s)) * S2
                for an in (-1.9, -1.2):
                    g = int(R.integers(-12, 12)); d.line([(px, py), (px + nl * cos(an + 0.3 * sgn), py + nl * sin(an))], fill=(36 + g, 80 + g, 42 + g, 255), width=4 * S2)
                d.line([(px, py), (px + sgn * nl * 0.6, py + nl * 0.5)], fill=(30, 70, 38, 255), width=4 * S2)
    d.line([(W * 1.5, H * 0.99), (W * 1.5, H * 0.04)], fill=(70, 62, 44, 255), width=5 * S2)
    for half, pal in ((1, [(74, 124, 44), (92, 140, 52), (58, 108, 40), (110, 150, 60)]), (0, [(44, 92, 46), (56, 104, 52), (38, 80, 44), (72, 112, 50)])):
        y0 = half * H / 2; cxm = W * 2.5
        d.line([(cxm, y0 + H * 0.49), (cxm, y0 + H * 0.2)], fill=(80, 66, 46, 255), width=3 * S2)
        for i in range(120):
            k = i / 120.0; a = R.random() * 2 * pi; rr = R.random() ** 0.6
            x = cxm + rr * W * 0.4 * cos(a); y = y0 + H * 0.24 + rr * H * 0.2 * sin(a) + (H * 0.04 if sin(a) > 0 else 0)
            an = R.random() * 2 * pi; L = (11 + 7 * R.random()) * S2; wd = L * 0.45; ca_, sa_ = cos(an), sin(an)
            pc = pal[int(R.random() * len(pal))]; cc = tuple(int(q_ * (0.55 + 0.7 * k)) for q_ in pc) + (255,)
            shape = [(-1, 0), (-0.4, 0.8), (0.4, 0.75), (1, 0), (0.4, -0.75), (-0.4, -0.8)]
            d.polygon([(x + px * L * ca_ - py * wd * sa_, y + px * L * sa_ + py * wd * ca_) for px, py in shape], fill=cc)
    a = np.asarray(im.resize((512, 512), Image.LANCZOS)).astype(np.float32)
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
    for (c0, c1, r0, r1, cc) in ((0, 171, 0, 512, (66, 118, 38)), (171, 341, 0, 512, (34, 74, 40)), (341, 512, 256, 512, (74, 120, 44)), (341, 512, 0, 256, (44, 90, 46))):
        a[r0:r1, c0:c1, :3] = np.where(a[r0:r1, c0:c1, 3:] > 0, a[r0:r1, c0:c1, :3], col(cc))
    save(a, "foliage.png")

    # ---- window, lit interior, flat swatches, glass, lamp
    n = 256
    im = Image.new("RGB", (n, n), (38, 34, 32)); d = ImageDraw.Draw(im)
    for x0, x1 in ((10, 124), (132, 246)):
        for y in range(10, 246):
            k = (y - 10) / 236.0
            d.line([(x0, y), (x1, y)], fill=(int(96 - 50 * k), int(122 - 62 * k), int(140 - 66 * k)))
        d.polygon([(x0 + 20, 10), (x0 + 48, 10), (x0 + 8, 120), (x0, 120), (x0, 80)], fill=(128, 152, 166))
    d.rectangle([134, 12, 168, 244], fill=(150, 140, 122))
    for x in range(138, 168, 6): d.line([(x, 12), (x, 244)], fill=(124, 114, 98))
    save(np.asarray(im.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32), "glazing.jpg", 82)
    im = Image.new("RGB", (n, n), (150, 104, 62)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, n, 40], fill=(232, 190, 120)); d.rectangle([0, 176, n, n], fill=(92, 58, 36)); d.rectangle([0, 168, n, 178], fill=(214, 170, 110))
    for sy in (70, 110, 150):
        d.rectangle([14, sy, n - 14, sy + 4], fill=(70, 44, 28))
        for x in range(20, n - 22, 9):
            hh = int(R.integers(14, 30)); g = int(R.integers(90, 200)); d.rectangle([x, sy - hh, x + 5, sy], fill=(g, int(g * 0.8), int(g * 0.55)))
    for x in (40, 128, 216): d.ellipse([x - 12, 14, x + 12, 34], fill=(255, 244, 210))
    save(np.asarray(im.filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32), "interior.jpg", 80)
    sw = [(40, 40, 43), (168, 170, 174), (234, 226, 206), (242, 242, 240), (16, 16, 18), (226, 106, 40), (40, 110, 92), (74, 54, 40)]
    a = np.concatenate([np.zeros((64, 64, 3), np.float32) + col(s) for s in sw], 1) + (R.random((64, 512, 1)).astype(np.float32) - 0.5) * 8
    save(a, "solids.jpg", 90)
    save(np.zeros((32, 32, 3), np.float32) + col((150, 186, 196)) + (R.random((32, 32, 1)).astype(np.float32) - 0.5) * 6, "glass.jpg", 85)
    save(np.zeros((16, 16, 3), np.float32) + col((255, 206, 140)), "light.jpg", 90)
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(-256, 512, 32):
        d.line([(k, 0), (k + 256, 256)], fill=(86, 104, 96, 255), width=4); d.line([(k, 256), (k + 256, 0)], fill=(86, 104, 96, 255), width=4)
    im.save(os.path.join(out, "fence.png"))
    Image.open(os.path.join(ROOT, "public", "textures", "tour", "pitch5.jpg")).save(os.path.join(out, "pitch5.jpg"), quality=88)
    from PIL import ImageFont, ImageDraw as _ID
    sg = Image.new("RGBA", (2048, 256), (255, 255, 255, 0)); d = _ID.Draw(sg); font = None
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        try: font = ImageFont.truetype(f, 236); break
        except Exception: pass
    if font is None: font = ImageFont.load_default()
    x = 20
    for ch in "ZARIA COURT":  # the venue's name in plain white letters, spaced like free-standing letters
        if ch != " ": d.text((x, 128), ch, font=font, fill=(250, 250, 248, 255), anchor="lm")
        x += (d.textlength(ch, font=font) if ch != " " else 70) + 22
    sg = sg.crop((0, 0, min(2048, int(x)), 256)).resize((2048, 256))
    sg.save(os.path.join(out, "sign.png"))
    print("textures written to", out)


try:
    import bpy
except ImportError:
    bpy = None
if bpy is None:
    make_textures(TEX)
    sys.exit(0)

import bmesh
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "tex" in ARGS or not os.path.exists(os.path.join(TEX, "light.jpg")):
    subprocess.run([VENV_PY, os.path.abspath(__file__), "tex"], check=True)

# ============================================================ geometry builder
TS = {"brick": (2.3, 2.24), "pave_red": (1.6, 1.6), "pave_buff": (1.6, 1.6), "concrete": (3, 3), "render": (3, 3), "stone": (2, 2),
      "timber_slat": (0.96, 2.0), "slat_alpha": (1.28, 1.28), "deck": (1.12, 2.24), "timber_red": (1.2, 1.2), "bark": (1.0, 1.0),
      "roof_green": (1.8, 1.8), "roof_under": (2, 2), "leaves_a": (1.5, 1.5), "leaves_b": (1.3, 1.3), "planting": (3, 3), "lawn": (2, 2),
      "glass": (2, 2), "fence": (2, 2), "interior": (3, 3), "light": (1, 1), "glazing": (1.6, 2.4)}
ROT45 = {"pave_red", "pave_buff"}
SW = {"m_dark": 0, "m_steel": 1, "cream": 2, "white": 3, "black": 4, "orange": 5, "teal": 6, "soil": 7}
SMOOTH = {"leaves_a": 180, "leaves_b": 180, "bark": 100, "foliage": 180}
S2 = sqrt(0.5)


class Builder:
    def __init__(s):
        s.m = {}; s.st = [Matrix()]

    def push(s, x=0, y=0, z=0, rz=0):
        s.st.append(s.st[-1] @ Matrix.Translation((x, y, z)) @ Matrix.Rotation(radians(rz), 4, "Z"))

    def pop(s):
        s.st.pop()

    def poly(s, mat, pts, uv=None, rot=False):
        if mat in SW:
            i = SW[mat]; uv = [((i + 0.3 + 0.4 * (k % 2)) / 8, 0.3 + 0.4 * (k // 2 % 2)) for k in range(len(pts))]; mat = "solids"
        elif mat == "red":
            uv = [(0.3 + 0.4 * (k % 2), 0.86 + 0.08 * (k // 2 % 2)) for k in range(len(pts))]; mat = "steel_red"
        elif uv is None:
            tw, th = TS.get(mat, (2, 2))
            a = Vector(pts[1]) - Vector(pts[0]); b = Vector(pts[2]) - Vector(pts[0]); n = a.cross(b)
            ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            if az > 0.6 * n.length:
                if mat in ROT45: uv = [((p[0] + p[1]) * S2 / tw, (p[1] - p[0]) * S2 / th) for p in pts]
                elif rot: uv = [(p[1] / tw, p[0] / th) for p in pts]
                else: uv = [(p[0] / tw, p[1] / th) for p in pts]
            elif ay >= ax: uv = [(p[0] / tw, p[2] / th) for p in pts]
            else: uv = [(p[1] / tw, p[2] / th) for p in pts]
            if rot and az <= 0.6 * n.length: uv = [(q[1] * th / tw, q[0] * tw / th) for q in uv]
        V, F, U = s.m.setdefault(mat, ([], [], []))
        T = s.st[-1]; i = len(V)
        V.extend((T @ Vector(p))[:] for p in pts); F.append(tuple(range(i, i + len(pts)))); U.extend(uv)

    def box(s, mat, x0, y0, z0, x1, y1, z1, f="xXyYZ", top=None, rot=False):
        if "x" in f: s.poly(mat, [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], rot=rot)
        if "X" in f: s.poly(mat, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], rot=rot)
        if "y" in f: s.poly(mat, [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], rot=rot)
        if "Y" in f: s.poly(mat, [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], rot=rot)
        if "Z" in f or top: s.poly(top or mat, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], rot=rot)
        if "z" in f: s.poly(mat, [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], rot=rot)

    def cyl(s, mat, cx, cy, z0, z1, r0, r1=None, n=12, cap="t", a0=0, a1=360, capmat=None):
        r1 = r0 if r1 is None else r1
        ang = [radians(a0 + (a1 - a0) * i / n) for i in range(n + 1)]
        tw, th = TS.get(mat, (2, 2))
        for i in range(n):
            a, b = ang[i], ang[i + 1]
            p = [(cx + r0 * cos(a), cy + r0 * sin(a), z0), (cx + r0 * cos(b), cy + r0 * sin(b), z0), (cx + r1 * cos(b), cy + r1 * sin(b), z1), (cx + r1 * cos(a), cy + r1 * sin(a), z1)]
            uv = [(r0 * a / tw, z0 / th), (r0 * b / tw, z0 / th), (r0 * b / tw, z1 / th), (r0 * a / tw, z1 / th)]
            if r1 < 1e-6: p = p[:3]; uv = uv[:3]
            elif r0 < 1e-6: p = [p[0], p[2], p[3]]; uv = [uv[0], uv[2], uv[3]]
            s.poly(mat, p, uv)
        if "t" in cap and r1 > 1e-6: s.poly(capmat or mat, [(cx + r1 * cos(a), cy + r1 * sin(a), z1) for a in ang[:n]])
        if "b" in cap and r0 > 1e-6: s.poly(capmat or mat, [(cx + r0 * cos(a), cy + r0 * sin(a), z0) for a in reversed(ang[:n])])

    def tube(s, mat, p0, p1, r, n=5, r1=None, phase=0.0):
        p0 = Vector(p0); p1 = Vector(p1); r1 = r if r1 is None else r1
        z = (p1 - p0); L = z.length
        if L < 1e-6: return
        z = z / L; x = z.orthogonal().normalized(); y = z.cross(x)
        tw, th = TS.get(mat, (2, 2))
        ring = [(cos(phase + 2 * pi * i / n), sin(phase + 2 * pi * i / n)) for i in range(n + 1)]
        for i in range(n):
            (ca, sa), (cb, sb) = ring[i], ring[i + 1]
            pts = [p0 + (x * ca + y * sa) * r, p0 + (x * cb + y * sb) * r, p1 + (x * cb + y * sb) * r1, p1 + (x * ca + y * sa) * r1]
            uv = [(i / n * 6.28 * r / tw, 0), ((i + 1) / n * 6.28 * r / tw, 0), ((i + 1) / n * 6.28 * r / tw, L / th), (i / n * 6.28 * r / tw, L / th)]
            s.poly(mat, [q[:] for q in pts], uv)


def ipl(tab, x):
    for (a, va), (b, vb) in zip(tab, tab[1:]):
        if x <= b: return va + (vb - va) * (x - a) / (b - a)
    return tab[-1][1]


# ============================================================ facade parts (local frame: wall runs along +x, outside is -y)
def frame(b, x0, x1, z0, z1, y, w=0.06, d=0.07, mull=0.0, tr=None, mat="m_dark"):
    b.box(mat, x0, y, z0, x0 + w, y + d, z1); b.box(mat, x1 - w, y, z0, x1, y + d, z1)
    b.box(mat, x0, y, z1 - w, x1, y + d, z1, "yz"); b.box(mat, x0, y, z0, x1, y + d, z0 + w, "yZ")
    if mull:
        k = max(1, round((x1 - x0) / mull))
        for i in range(1, k):
            x = x0 + (x1 - x0) * i / k; b.box(mat, x - w / 2, y, z0, x + w / 2, y + d, z1, "xXy")
    if tr and z1 - z0 > tr + 0.5: b.box(mat, x0, y, z0 + tr, x1, y + d, z0 + tr + w, "yzZ")


def fill(b, kind, x0, x1, z0, z1, y, t):
    w = x1 - x0
    q = lambda yy: [(x0, yy, z0), (x1, yy, z0), (x1, yy, z1), (x0, yy, z1)]
    if kind == "win":
        k = max(1, round(w / 1.7))
        b.poly("glazing", q(y + 0.12), [(0, 0), (k, 0), (k, 1), (0, 1)])
        b.box("concrete", x0 - 0.04, y - 0.04, z0 - 0.06, x1 + 0.04, y + 0.12, z0)
    elif kind in ("glass", "shop"):
        b.poly("glass", q(y + 0.1)); frame(b, x0, x1, z0, z1, y + 0.06, mull=1.35, tr=2.25)
        if kind == "shop":
            k = max(1, round(w / 3.2))
            b.poly("interior", q(y + 3.0), [(0, 0), (k, 0), (k, 1), (0, 1)])
            b.poly("white", [(x0, y + 3.0, z1), (x1, y + 3.0, z1), (x1, y + 0.1, z1), (x0, y + 0.1, z1)])
            b.poly("cream", [(x0, y + 0.1, z0), (x0, y + 3.0, z0), (x0, y + 3.0, z1), (x0, y + 0.1, z1)])
            b.poly("cream", [(x1, y + 3.0, z0), (x1, y + 0.1, z0), (x1, y + 0.1, z1), (x1, y + 3.0, z1)])
    elif kind == "door":
        b.poly("timber_red", q(y + 0.1)); frame(b, x0, x1, z0, z1, y + 0.04, w=0.07)
        if w > 1.3: b.box("m_dark", x0 + w / 2 - 0.02, y + 0.07, z0, x0 + w / 2 + 0.02, y + 0.1, z1, "xXy")
        b.box("m_steel", x0 + w / 2 + (0.08 if w > 1.3 else w / 2 - 0.25), y + 0.04, z0 + 1.0, x0 + w / 2 + (0.12 if w > 1.3 else w / 2 - 0.21), y + 0.1, z0 + 1.25)
    elif kind == "gate":
        b.poly("timber_red", q(y + 0.1)); frame(b, x0, x1, z0, z1, y + 0.03, w=0.09)
        for zz in (z0 + 0.5, z1 - 0.5): b.box("m_dark", x0, y + 0.05, zz, x1, y + 0.1, zz + 0.07, "yzZ")
        b.box("m_dark", x0 + w / 2 - 0.03, y + 0.05, z0, x0 + w / 2 + 0.03, y + 0.1, z1, "xXy")
    elif kind == "dark":
        d = t + 4.0
        b.poly("black", q(y + d))
        b.poly("m_dark", [(x0, y + d, z1), (x1, y + d, z1), (x1, y + t, z1), (x0, y + t, z1)])
        b.poly("m_dark", [(x0, y + t, z0), (x0, y + d, z0), (x0, y + d, z1), (x0, y + t, z1)])
        b.poly("m_dark", [(x1, y + d, z0), (x1, y + t, z0), (x1, y + t, z1), (x1, y + d, z1)])
    elif kind == "slat":
        b.poly("slat_alpha", q(y + 0.1)); frame(b, x0, x1, z0, z1, y + 0.03, w=0.08)
        b.poly("interior", q(y + 1.6), [(0, 0), (1, 0), (1, 1), (0, 1)])


def wall(b, mat, x0, x1, z0, z1, ops=(), t=0.3, y=0.0):
    cur = x0
    for (a, c, za, zb, kind) in sorted(ops):
        if a > cur + 1e-4: b.box(mat, cur, y, z0, a, y + t, z1)
        if za > z0 + 1e-4: b.box(mat, a, y, z0, c, y + t, za)
        if zb < z1 - 1e-4: b.box(mat, a, y, zb, c, y + t, z1, "yYzZ")
        fill(b, kind, a, c, za, zb, y, t); cur = c
    if x1 > cur + 1e-4: b.box(mat, cur, y, z0, x1, y + t, z1)


def grail(b, pts, h=1.1, post=1.6):  # glass balustrade along a polyline of base points
    for p, q in zip(pts, pts[1:]):
        p = Vector(p); q = Vector(q); up = Vector((0, 0, h))
        b.poly("glass", [p[:], q[:], (q + up * 0.96)[:], (p + up * 0.96)[:]])
        b.tube("m_steel", p + up, q + up, 0.028, 4)
        k = max(1, round((q - p).length / post))
        for i in range(k + 1):
            c = p.lerp(q, i / k); b.tube("m_steel", c, c + up, 0.022, 4)


def mrail(b, pts, h=1.0, post=1.3, mat="m_dark", bars=1):
    for p, q in zip(pts, pts[1:]):
        p = Vector(p); q = Vector(q); up = Vector((0, 0, h))
        b.tube(mat, p + up, q + up, 0.025, 4)
        for j in range(bars): b.tube(mat, p + up * (j + 1) / (bars + 1), q + up * (j + 1) / (bars + 1), 0.015, 3)
        k = max(1, round((q - p).length / post))
        for i in range(k + 1):
            c = p.lerp(q, i / k); b.tube(mat, c, c + up, 0.02, 4)


# ============================================================ furniture and planting
def table_set(b, x, y, z=0.0, rz=0.0, chairs=4, top="white", seat="m_dark"):
    b.push(x, y, z, rz)
    b.cyl(top, 0, 0, 0.72, 0.75, 0.42, n=8, cap="tb"); b.tube("m_dark", (0, 0, 0.02), (0, 0, 0.72), 0.03, 4); b.cyl("m_dark", 0, 0, 0, 0.02, 0.24, n=6, cap="t")
    for i in range(chairs):
        b.push(0, 0, 0, i * 360.0 / chairs + 45); b.push(0.72, 0, 0)
        b.box(seat, -0.21, -0.21, 0.42, 0.21, 0.21, 0.46, "xXyYZz"); b.box(seat, 0.18, -0.2, 0.62, 0.21, 0.2, 0.86, "xXyYZz"); b.box("m_dark", 0.18, -0.2, 0.46, 0.21, -0.17, 0.62, "xXyY"); b.box("m_dark", 0.18, 0.17, 0.46, 0.21, 0.2, 0.62, "xXyY")
        for (lx, ly) in ((-0.19, -0.19), (0.16, -0.19), (-0.19, 0.16), (0.16, 0.16)): b.box("m_dark", lx, ly, 0, lx + 0.03, ly + 0.03, 0.42, "xXyY")
        b.pop(); b.pop()
    b.pop()


def umbrella(b, x, y, z=0.0, r=1.6, mat="cream"):
    b.push(x, y, z)
    b.tube("m_steel", (0, 0, 0), (0, 0, 2.75), 0.03, 4); b.box("m_dark", -0.3, -0.3, 0, 0.3, 0.3, 0.09)
    for i in range(8):
        a, c = i * pi / 4, (i + 1) * pi / 4
        p0 = (r * cos(a), r * sin(a), 2.2); p1 = (r * cos(c), r * sin(c), 2.2); ap = (0, 0, 2.8)
        b.poly(mat, [p0, p1, ap]); b.poly(mat, [p1, p0, (0, 0, 2.74)])
        b.poly(mat, [(p0[0], p0[1], 2.06), (p1[0], p1[1], 2.06), p1, p0])
    b.pop()


def lounger(b, x, y, z=0.0, rz=0.0):
    b.push(x, y, z, rz)
    b.box("m_dark", -0.3, -0.9, 0.0, 0.3, 0.9, 0.24, "xXyY")
    b.box("white", -0.33, -0.95, 0.24, 0.33, 0.35, 0.34, "xXyYZ")
    b.poly("white", [(-0.33, 0.35, 0.34), (0.33, 0.35, 0.34), (0.33, 0.95, 0.72), (-0.33, 0.95, 0.72)])
    b.poly("white", [(0.33, 0.35, 0.24), (-0.33, 0.35, 0.24), (-0.33, 0.95, 0.62), (0.33, 0.95, 0.62)])
    for sx in (-0.33, 0.33):
        pts = [(sx, 0.35, 0.24), (sx, 0.95, 0.62), (sx, 0.95, 0.72), (sx, 0.35, 0.34)]
        b.poly("white", pts if sx > 0 else pts[::-1])
    b.poly("white", [(0.33, 0.95, 0.62), (-0.33, 0.95, 0.62), (-0.33, 0.95, 0.72), (0.33, 0.95, 0.72)])
    b.pop()


def bench(b, x, y, rz=0.0, L=2.2):
    b.push(x, y, 0, rz)
    for sx in (-L / 2 + 0.15, L / 2 - 0.45): b.box("concrete", sx, -0.22, 0, sx + 0.3, 0.22, 0.4, "xXyY")
    b.box("timber_slat", -L / 2, -0.26, 0.4, L / 2, 0.26, 0.47, "xXyYZz", rot=True)
    b.pop()


def sofa(b, x, y, z, rz=0.0, L=2.0):
    b.push(x, y, z, rz)
    b.box("m_dark", -L / 2, -0.42, 0.05, L / 2, 0.42, 0.4, top="cream"); b.box("m_dark", -L / 2, 0.3, 0.4, L / 2, 0.45, 0.8)
    for sx in (-L / 2, L / 2 - 0.14): b.box("m_dark", sx, -0.42, 0.4, sx + 0.14, 0.3, 0.6)
    b.pop()


def lamp_tree(b, x, y, h=4.4, seed=0):
    r = random.Random(seed); b.push(x, y, 0, r.uniform(0, 360))
    b.tube("m_steel", (0, 0, 0), (0, 0, h * 0.62), 0.075, 6, r1=0.06); b.cyl("m_steel", 0, 0, 0, 0.03, 0.2, n=6)
    top = Vector((0, 0, h * 0.62))
    for i in range(5):
        a = i * 2 * pi / 5 + r.uniform(-0.3, 0.3); L = r.uniform(1.4, 2.4); el = r.uniform(0.35, 1.1)
        d = Vector((cos(a) * cos(el), sin(a) * cos(el), sin(el))); st = top - Vector((0, 0, r.uniform(0, 0.9)))
        e = st + d * L; b.tube("m_steel", st, e, 0.028, 4, r1=0.018)
        b.tube("light", e - d * 0.5, e + d * 0.04, 0.026, 4, phase=0.4)
    b.pop()


ICO = {}
def ico(sub):
    if sub not in ICO:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        bm.verts.ensure_lookup_table()
        ICO[sub] = ([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces]); bm.free()
    return ICO[sub]


def blob(b, mat, c, r, rnd, sub=3, amp=0.22):
    vs, fs = ico(sub); ph = [rnd.uniform(0, 6.28) for _ in range(3)]; out = []
    for v in vs:
        f = 1 + amp * (sin(v.x * 3.1 + ph[0]) * cos(v.y * 2.7 + ph[1]) + sin(v.z * 3.3 + ph[2])) * 0.7 + rnd.uniform(-0.09, 0.09)
        f += 0.5 * amp * sin(v.x * 7.3 + ph[1]) * sin(v.y * 6.1 + ph[2]) * cos(v.z * 6.7 + ph[0])
        z = v.z * (0.62 if v.z < -0.25 else 1.0)
        out.append((c[0] + v.x * f * r[0], c[1] + v.y * f * r[1], c[2] + z * f * r[2]))
    for f in fs: b.poly(mat, [out[i] for i in f])


def sprigs(b, c, r, rnd, n=6, size=1.2, dark=False):
    v0, v1 = (0.505, 0.995) if dark else (0.005, 0.495)
    for i in range(n):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.25, 1))).normalized()
        p = Vector(c) + Vector((d.x * r[0], d.y * r[1], d.z * r[2])) * 0.92
        sd = d.cross(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))).normalized(); h = size * rnd.uniform(0.8, 1.25); w = h * 0.34
        a = p - d * h * 0.35; t = p + d * h * 0.65
        b.poly("foliage", [(a - sd * w)[:], (a + sd * w)[:], (t + sd * w)[:], (t - sd * w)[:]], [(0.67, v0), (0.995, v0), (0.995, v1), (0.67, v1)])


def trunk(b, pts, r0, r1, n=6):
    k = len(pts) - 1
    for i in range(k):
        b.tube("bark", pts[i], pts[i + 1], r0 + (r1 - r0) * i / k, n, r1=r0 + (r1 - r0) * (i + 1) / k)


def tree(b, kind, x, y, s=1.0, seed=0, z=0.0):
    rnd = random.Random(seed); b.push(x, y, z, rnd.uniform(0, 360))
    if kind == "broad":  # dense rounded crown
        h = 3.2 * s; lean = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3))
        trunk(b, [(0, 0, 0), (lean[0] * 0.4, lean[1] * 0.4, h * 0.5), (lean[0], lean[1], h), (lean[0], lean[1], h + 1.2 * s)], 0.26 * s, 0.14 * s)
        blob(b, "leaves_a", (lean[0], lean[1], h + 2.5 * s), (2.3 * s, 2.3 * s, 2.0 * s), rnd, amp=0.3)
        for i in range(7):
            a = i * 2 * pi / 7 + rnd.uniform(-0.4, 0.4); d = rnd.uniform(1.5, 2.6) * s; zc = h + rnd.uniform(0.6, 2.6) * s
            c = (lean[0] + d * cos(a), lean[1] + d * sin(a), zc)
            b.tube("bark", (lean[0], lean[1], h - 0.3 * s), (c[0] * 0.8, c[1] * 0.8, zc - 0.5 * s), 0.09 * s, 4, r1=0.05 * s)
            rr = (1.6 * s * rnd.uniform(0.75, 1.2), 1.6 * s * rnd.uniform(0.75, 1.2), 1.3 * s * rnd.uniform(0.8, 1.2))
            blob(b, "leaves_a", c, rr, rnd, amp=0.3); sprigs(b, c, rr, rnd, 7, 1.3 * s)
        sprigs(b, (lean[0], lean[1], h + 2.5 * s), (2.3 * s, 2.3 * s, 2.0 * s), rnd, 8, 1.3 * s)
    elif kind == "flat":  # layered, flat-topped
        h = 3.6 * s
        trunk(b, [(0, 0, 0), (0.15, 0.1, h * 0.6), (0.4, 0.2, h)], 0.22 * s, 0.12 * s)
        for i in range(6):
            a = i * 2 * pi / 6 + rnd.uniform(-0.3, 0.3); d = (rnd.uniform(1.6, 3.0) if i else 0) * s; zc = h + rnd.uniform(0.2, 1.3) * s
            c = (0.4 + d * cos(a), 0.2 + d * sin(a), zc)
            if i: b.tube("bark", (0.4, 0.2, h - 0.2), (c[0] * 0.85, c[1] * 0.85, zc - 0.3 * s), 0.08 * s, 4, r1=0.04 * s)
            rr = (2.1 * s * rnd.uniform(0.8, 1.2), 2.1 * s * rnd.uniform(0.8, 1.2), 1.1 * s)
            rr = (rr[0], rr[1], 1.45 * s); blob(b, "leaves_b", c, rr, rnd, amp=0.3); sprigs(b, c, rr, rnd, 8, 1.2 * s, dark=True)
    elif kind == "small":  # ornamental
        h = 1.9 * s
        trunk(b, [(0, 0, 0), (0.05, 0, h)], 0.1 * s, 0.07 * s, n=5)
        blob(b, "leaves_a", (0, 0, h + 1.0 * s), (1.25 * s, 1.25 * s, 1.35 * s), rnd, amp=0.3); sprigs(b, (0, 0, h + 1.0 * s), (1.25 * s, 1.25 * s, 1.35 * s), rnd, 10, 0.9 * s)
        blob(b, "leaves_a", (0.5 * s, 0.3 * s, h + 0.5 * s), (0.9 * s, 0.9 * s, 0.8 * s), rnd, sub=2)
    elif kind == "conifer":  # tall slim araucaria
        h = 13.0 * s
        trunk(b, [(0, 0, 0), (0.05, 0, h * 0.5), (0, 0.05, h)], 0.2 * s, 0.03 * s, n=6)
        zt = 2.6 * s; i = 0
        while zt < h:
            t = (zt - 2.6 * s) / (h - 2.6 * s); L = (2.7 - 2.1 * t ** 1.3) * s; nb = 7 if t < 0.7 else 5
            for j in range(nb):
                a = j * 2 * pi / nb + i * 0.7 + rnd.uniform(-0.15, 0.15)
                frond(b, (0, 0, zt), a, L * rnd.uniform(0.85, 1.1), -0.22, -0.34, w=0.8 * L / 2.5 * s + 0.4, n=3, uo=0.5)
            zt += (1.05 - 0.45 * t) * s; i += 1
        for j in range(4): frond(b, (0, 0, h - 0.2), j * pi / 2, 0.8 * s, 1.6, 0.3, w=0.5, n=1, uo=0.5)
    elif kind == "palm":
        h = 5.5 * s; lean = rnd.uniform(0.3, 0.9)
        pts = [(lean * (i / 6.0) ** 2, 0, h * i / 6.0) for i in range(7)]
        trunk(b, pts, 0.24 * s, 0.15 * s, n=7)
        top = pts[-1]
        for j in range(18):
            a = j * 2 * pi / 18 * 2.4 + rnd.uniform(-0.2, 0.2); ring = j / 17.0
            frond(b, (top[0], top[1], top[2] - 0.1), a, (3.0 + rnd.uniform(-0.3, 0.4)) * s, 1.25 - 1.5 * ring, 0.75 + 0.5 * ring, w=1.15 * s, n=4, uo=0.0)
        blob(b, "bark", (top[0], top[1], top[2] - 0.15), (0.32 * s, 0.32 * s, 0.4 * s), rnd, sub=1, amp=0.05)
    b.pop()


def frond(b, base, yaw, L, lift, droop, w=0.9, n=4, uo=0.0):
    u0, u1 = (0.34, 0.655) if uo else (0.008, 0.325)
    base = Vector(base); d = Vector((cos(yaw), sin(yaw), 0)); sd = Vector((-sin(yaw), cos(yaw), 0)); pr = None
    for i in range(n + 1):
        t = i / n
        c = base + d * (L * t * (1 - 0.25 * t * max(0, droop))) + Vector((0, 0, 1)) * (lift * L * t - droop * L * t * t)
        hw = 0.5 * w * (0.55 + 0.45 * sin(pi * min(1.0, t + 0.25)))
        cur = (c - sd * hw, c + sd * hw, t)
        if pr:
            b.poly("foliage", [pr[0][:], pr[1][:], cur[1][:], cur[0][:]], [(u0, pr[2]), (u1, pr[2]), (u1, t), (u0, t)])
            if uo:
                up = Vector((0, 0, 1)); h0 = (pr[1] - pr[0]).length * 0.3; h1 = hw * 0.6; c0 = (pr[0] + pr[1]) / 2
                b.poly("foliage", [(c0 - up * h0)[:], (c0 + up * h0)[:], (c + up * h1)[:], (c - up * h1)[:]], [(u0, pr[2]), (u1, pr[2]), (u1, t), (u0, t)])
        pr = cur


def shrubs(b, x0, y0, x1, y1, z, n, seed, r=(0.5, 1.0), mats=("leaves_a", "leaves_b", "leaves_a")):
    rnd = random.Random(seed)
    for i in range(n):
        rr = rnd.uniform(*r); x = rnd.uniform(x0, x1); y = rnd.uniform(y0, y1)
        m = rnd.choice(mats); blob(b, m, (x, y, z + rr * 0.45), (rr, rr, rr * rnd.uniform(0.6, 1.0)), rnd, sub=2, amp=0.3)
        sprigs(b, (x, y, z + rr * 0.45), (rr, rr, rr * 0.8), rnd, 3, 0.75 * rr + 0.25, dark=(m == "leaves_b"))


def tufts(b, x0, y0, x1, y1, z, n, seed, h=0.9):
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(x0, x1); y = rnd.uniform(y0, y1); hh = h * rnd.uniform(0.6, 1.2); a0 = rnd.uniform(0, pi)
        for j in range(3):
            a = a0 + j * pi / 3; dx, dy = cos(a) * hh * 0.42, sin(a) * hh * 0.42
            b.poly("foliage", [(x - dx, y - dy, z), (x + dx, y + dy, z), (x + dx * 1.5, y + dy * 1.5, z + hh), (x - dx * 1.5, y - dy * 1.5, z + hh)], [(0.008, 0.02), (0.325, 0.02), (0.325, 0.6), (0.008, 0.6)])


def bin_(b, x, y, z=0.0):
    b.cyl("m_dark", x, y, z, z + 0.85, 0.24, n=8, cap="t", capmat="black"); b.cyl("m_steel", x, y, z + 0.85, z + 0.9, 0.26, n=8, cap="")


def bed(b, x0, y0, x1, y1, h=0.45, top="planting", side="brick"):
    b.box(side, x0, y0, 0, x1, y1, h, "xXyY")
    for (a, c, d, e) in ((x0, y0, x1, y0 + 0.3), (x0, y1 - 0.3, x1, y1), (x0, y0 + 0.3, x0 + 0.3, y1 - 0.3), (x1 - 0.3, y0 + 0.3, x1, y1 - 0.3)):
        b.box("concrete", a - 0.03, c - 0.03, h, d + 0.03, e + 0.03, h + 0.07, "xXyYZ")
    b.poly(top, [(x0 + 0.3, y0 + 0.3, h), (x1 - 0.3, y0 + 0.3, h), (x1 - 0.3, y1 - 0.3, h), (x0 + 0.3, y1 - 0.3, h)])


# ============================================================ the site
FH = 3.3
HX0, HX1, HY0, HY1 = -63.0, -3.0, -31.0, -16.0           # hotel
TX0, TX1, TY0, TY1 = -1.0, 15.0, -24.0, -7.0             # tower
TZ = [0.0, 4.5, 7.8, 11.1, 14.4]
PD = 4.5                                                  # podium deck level
PX1 = 59.0; PYS = -35.0; PYN = -7.0                       # podium east edge, avenue wall, north edge
RY0, RYM, RY1 = 4.5, 21.0, 37.5                          # court roof: south eave, ridge, north eave
ROOF = [(RY0, 6.0), (RYM, 19.5), (RY1, 6.0)]              # symmetric gable (y, z), ridge runs east-west
RX0, RX1, PROW = 19.0, 54.0, 6.0                          # the ridge sticks out at the east gable
TRUSS_X = [20.0 + 5.5 * k for k in range(7)]
SN = 10; RISE = PD / SN                                   # steps up to the raised side
NY0, NGO = 34.0, 0.9                                      # north terraces start, going
EX0, EGO = 45.0, 0.8                                      # east bleachers start, going
SWX = -16.0                                               # west end of the big stair
OX, OY = 25.0, 11.0                                       # model origin offset applied on export
def rx1(y): return RX1 + PROW * (1 - abs(y - RYM) / (RYM - RY0))
OCT = (-10.0, 11.0)
def zr(y): return ipl(ROOF, y)
def canopy_z(y): return 17.2 + (y + 27.0) / 24.0 * 1.4   # tower canopy soffit


def hotel_face(b, L, f0=0, ent=None):
    nb = int(round(L / 4.0))
    for f in range(f0, 4):
        z = f * FH
        segs = [(0, L)] if not (f == 0 and ent) else [(0, ent[0] * 4.0), (ent[1] * 4.0, L)]
        for (a, c) in segs:
            b.box("render", a, -0.14, z - (0.32 if f else 0), c, 0.06, z + 0.85)
            b.poly("glass", [(a, -0.04, z + 0.85), (c, -0.04, z + 0.85), (c, -0.04, z + 1.12), (a, -0.04, z + 1.12)])
            b.tube("m_dark", (a, -0.04, z + 1.13), (c, -0.04, z + 1.13), 0.025, 4)
        if f == 0 and ent: b.box("render", ent[0] * 4.0, -0.14, FH - 0.32, ent[1] * 4.0, 0.06, FH, "yzZ")
        if f: b.box("render", 0, 0.06, z - 0.3, L, 1.6, z, "zZ", top="concrete")
        for i in range(nb + 1):
            x = min(max(i * 4.0, 0.15), L - 0.15)
            b.box("brick", x - 0.15, -0.1, z + (0.85 if not (f == 0 and ent and ent[0] <= i <= ent[1]) else 0), x + 0.15, 1.6, z + FH - 0.3, "xXy")
            b.box("brick", x - 0.15, 0.06, z, x + 0.15, 1.6, z + 0.85, "xX")
        for i in range(nb):
            x = i * 4.0
            if f == 0 and ent and ent[0] <= i < ent[1]:
                wall(b, "render", x + 0.15, x + 3.85, z, z + FH - 0.3, [(x + 0.3, x + 3.7, 0.05, 2.85, "shop")], t=0.25, y=1.6)
            else:
                wall(b, "render", x + 0.15, x + 3.85, z, z + FH - 0.3, [(x + 0.7, x + 3.3, z + 0.04, z + 2.4, "win")], t=0.25, y=1.6)
    b.box("render", 0, -0.14, 4 * FH - 0.32, L, 0.3, 4 * FH + 1.0)
    b.box("concrete", 0, -0.2, 4 * FH + 1.0, L, 0.36, 4 * FH + 1.08, "xXyYZz")


def build_hotel(b):
    b.push(HX0, HY0); hotel_face(b, 60, f0=1); b.pop()
    b.push(HX1, HY1, 0, 180); hotel_face(b, 60, ent=(6, 10)); b.pop()
    for x in (HX0 - 0.3, HX1):
        b.box("brick", x, HY0 - 0.2, 0, x + 0.3, HY1 + 0.2, 4 * FH + 1.0)
        b.box("concrete", x - 0.04, HY0 - 0.24, 4 * FH + 1.0, x + 0.34, HY1 + 0.24, 4 * FH + 1.08, "xXyYZ")
    b.poly("concrete", [(HX0, HY0, 13.3), (HX1, HY0, 13.3), (HX1, HY1, 13.3), (HX0, HY1, 13.3)])
    b.box("render", -39, -27.5, 13.3, -27, -20.5, 16.0); b.box("concrete", -39.2, -27.7, 16.0, -26.8, -20.3, 16.15, "xXyYZz")
    b.push(-33, -20.5, 13.3, 180); wall(b, "render", -1.2, 1.2, 0, 2.5, [(-0.5, 0.5, 0, 2.1, "door")], t=0.05, y=-0.05); b.pop()
    for (x, y) in ((-55, -24), (-52, -24), (-49, -24), (-18, -23), (-15, -23), (-12, -23), (-9, -26)):
        b.box("m_steel", x, y, 13.3, x + 1.6, y + 1.0, 14.3); b.box("m_dark", x + 0.2, y - 0.01, 13.5, x + 1.4, y, 14.1, "y")
    # entrance canopy on the plaza side: green edge, timber soffit, stone piers
    b.push(HX1, HY1, 0, 180)
    x0, x1, y0, z0, z1 = 22.5, 41.5, -8.5, 3.7, 4.25
    b.poly("timber_slat", [(x0, 0, z0), (x1, 0, z0), (x1, y0, z0), (x0, y0, z0)])
    b.box("teal", x0, y0, z0, x1, -0.14, z1, "xXyY", top="roof_green")
    b.box("teal", x0, y0, z0 - 0.02, x1, -0.14, z0, "xXy")
    for x in (24.0, 40.0): b.box("stone", x - 0.5, -7.9, 0, x + 0.5, -6.9, z0)
    for x in (29.3, 34.7): b.tube("m_dark", (x, -7.4, 0), (x, -7.4, z0), 0.09, 6)
    b.box("concrete", 23.0, -8.0, 0, 41.0, 1.6, 0.12, "xXyYZ", top="pave_buff")
    for x in (27, 32, 37):
        b.tube("m_dark", (x, -3.5, z0), (x, -3.5, z0 - 0.7), 0.01, 3); blob(b, "light", (x, -3.5, z0 - 0.85), (0.16, 0.16, 0.16), random.Random(1), sub=1, amp=0)
    b.pop()
    # low avenue wing: brick wall, timber gates, planted roof
    b.push(-65, PYS)
    wall(b, "brick", 0, 64, 0, 3.4, [(14, 18, 0, 2.7, "gate"), (40, 44, 0, 2.7, "gate"), (6, 7.1, 0, 2.2, "door"), (28, 29.1, 0, 2.2, "door"), (52, 53.1, 0, 2.2, "door"),
                                     (22, 24.5, 2.2, 2.9, "win"), (33, 35.5, 2.2, 2.9, "win"), (58, 60.5, 2.2, 2.9, "win")], t=0.35)
    b.box("concrete", -0.06, -0.2, 3.4, 64, 0.45, 3.52, "xXyYZz")
    for x in (0, 9.5, 13.3, 18.3, 25.5, 31, 36.5, 39.3, 44.3, 49.5, 55.5, 61.5): b.box("brick", x, -0.14, 0, x + 0.4, 0, 3.4, "xXy")
    b.pop()
    b.box("brick", -65, PYS + 0.35, 0, -64.65, HY0, 3.4); b.box("concrete", -65.06, PYS, 3.4, -64.6, HY0, 3.52, "xXyYZz")
    b.box("brick", -65, HY0 - 0.3, 0, HX0 - 0.3, HY0, 3.4, "Y")
    b.poly("planting", [(-64.65, PYS + 0.45, 3.42), (-1, PYS + 0.45, 3.42), (-1, HY0, 3.42), (-64.65, HY0, 3.42)])
    shrubs(b, -64, PYS + 0.5, -2, HY0 - 0.6, 3.42, 70, 5, r=(0.45, 0.95)); tufts(b, -64, PYS + 0.6, -2, HY0 - 0.5, 3.42, 110, 6, h=0.9)
    for (a, c) in ((-62.8, -45.2), (-24.8, -3.3)):
        bed(b, a, HY1 + 0.16, c, HY1 + 1.2, h=0.4); shrubs(b, a + 0.5, HY1 + 0.5, c - 0.5, HY1 + 0.9, 0.4, int((c - a) / 1.6), int(a), r=(0.35, 0.55)); tufts(b, a + 0.4, HY1 + 0.45, c - 0.4, HY1 + 0.95, 0.4, int((c - a) / 1.2), int(a) + 1, h=0.7)


def build_tower(b):
    xs = [-0.4, 4.5, 9.75, 14.7]; ys = [-23.4, -15.5, -7.62]
    for x in xs:
        for y in ys: b.box("concrete", x - 0.25, y - 0.25, 0, x + 0.25, y + 0.25, canopy_z(y) + 0.02, "xXyY")
    # floor slabs (stair holes in the open east bay)
    def slab(z, rects, top="concrete"):
        for (a, c, d, e) in rects: b.box("concrete", a, c, z - 0.35, d, e, z, "xXyYZz", top=top)
    slab(TZ[1], [(TX0, TY0, TX1, TY1)], top="deck")
    slab(TZ[2], [(TX0, TY0, 13.3, TY1), (13.3, TY0, TX1, -20.0), (13.3, -14.7, TX1, TY1), (14.6, -20.0, TX1, -14.7)])
    slab(TZ[3], [(TX0, TY0, 11.9, TY1), (13.2, TY0, TX1, TY1), (11.9, TY0, 13.2, -20.0), (11.9, -14.7, 13.2, TY1)], top="deck")
    slab(TZ[4], [(TX0, TY0, TX1, TY1)], top="deck")
    # ground floor: brick, shopfront to the plaza
    b.push(TX1, TY1, 0, 180)
    wall(b, "brick", 0, 16, 0, 4.15, [(1.5, 8.0, 0.12, 3.4, "shop"), (10.6, 11.7, 0, 2.4, "door")], t=0.35)
    b.pop()
    b.push(TX0, TY1, 0, -90); wall(b, "brick", 0, 17, 0, 4.15, [(8, 9.1, 0, 2.3, "door")], t=0.35); b.pop()
    # enclosed brick floors (levels 1 and 2) over the west two bays
    for lv in (1, 2):
        z0 = TZ[lv]; z1 = TZ[lv + 1] - 0.35
        b.push(9.75, TY1, 0, 180)
        ops = [(0.5, 9.0, z0 + 0.35, z0 + 2.55, "win")] if lv == 1 else [(1.2, 7.6, z0 + 0.45, z0 + 2.6, "win")]
        wall(b, "brick", 0, 10.75, z0, z1, ops, t=0.35); b.pop()
        b.push(TX0, TY0); wall(b, "brick", 0, 10.75, z0, z1, [(1.0, 4.4, z0 + 0.9, z0 + 2.5, "win"), (6.0, 9.6, z0 + 0.9, z0 + 2.5, "win")], t=0.35); b.pop()
        b.push(9.75, TY0, 0, 90); wall(b, "brick", 0, 17, z0, z1, [(1.0, 7.5, z0 + 0.05, z0 + 2.6, "shop"), (9.2, 16.0, z0 + 0.05, z0 + 2.6, "shop")], t=0.3); b.pop()
        b.push(TX0, TY1, 0, -90); wall(b, "brick", 0, 17, z0, z1, [(3, 5, z0 + 1.0, z0 + 2.3, "win"), (11, 13, z0 + 1.0, z0 + 2.3, "win")], t=0.35); b.pop()
        b.poly("cream", [(9.4, TY0 + 0.4, z0 + 0.02), (9.4, TY1 - 0.4, z0 + 0.02), (9.4, TY1 - 0.4, z1), (9.4, TY0 + 0.4, z1)][::-1])
    # terrace bar boxes on levels 3 and 4
    for lv in (3, 4):
        z0 = TZ[lv]; z1 = (TZ[lv + 1] - 0.35) if lv == 3 else canopy_z(-20)
        b.push(7.0, TY0, 0, 90); wall(b, "brick", 0, 8, z0, z1, [(0.8, 2.0, z0, z0 + 2.3, "door"), (3.0, 7.2, z0 + 0.05, z0 + 2.5, "shop")], t=0.3); b.pop()
        b.push(7.0, -16.0, 0, 180); wall(b, "brick", 0, 8, z0, z1, [(1.0, 7.0, z0 + 1.0, z0 + 2.4, "win")], t=0.3); b.pop()
        b.push(TX0, TY0); wall(b, "brick", 0, 8, z0, z1, [(1.5, 6.5, z0 + 1.0, z0 + 2.4, "win")], t=0.3); b.pop()
        b.push(TX0, -16.0, 0, -90); wall(b, "brick", 0, 8, z0, z1, [], t=0.3); b.pop()
    # stair drum
    dc = (1.2, -8.6)
    b.cyl("brick", dc[0], dc[1], 0, canopy_z(dc[1]) + 0.05, 2.8, n=28, cap="")
    for z in TZ[1:]: b.cyl("concrete", dc[0], dc[1], z - 0.35, z, 2.84, n=28, cap="")
    # open east bay: two stair flights and bracing
    def flight(x0, x1, ya, yb, za, zb, n=19):
        for i in range(n):
            t0 = i / n; t1 = (i + 1) / n; y0 = ya + (yb - ya) * t0; y1 = ya + (yb - ya) * t1; z = za + (zb - za) * t1
            b.box("concrete", x0, min(y0, y1), z - 0.2, x1, max(y0, y1), z, "xXyYZz")
        d = (zb - za) / n
        b.poly("concrete", [(x0, ya, za - 0.22), (x0, yb, zb - 0.22 - d), (x1, yb, zb - 0.22 - d), (x1, ya, za - 0.22)] if yb > ya else
               [(x1, ya, za - 0.22), (x1, yb, zb - 0.22 - d), (x0, yb, zb - 0.22 - d), (x0, ya, za - 0.22)])
        for x in (x0 + 0.04, x1 - 0.04): mrail(b, [(x, ya, za), (x, yb, zb)], h=0.95, post=1.0)
    flight(13.3, 14.6, -20.0, -14.7, TZ[1], TZ[2]); flight(11.9, 13.2, -14.7, -20.0, TZ[2], TZ[3])
    for (za, zb) in ((TZ[1], TZ[2] - 0.35), (TZ[2], TZ[3] - 0.35)):
        b.tube("concrete", (10.0, TY1 + 0.25, za), (14.5, TY1 + 0.25, zb), 0.13, 4, phase=pi / 4)
    # glass balustrades
    grail(b, [(9.9, TY1 - 0.05, TZ[1]), (TX1, TY1 - 0.05, TZ[1])])
    grail(b, [(10.0, TY1 - 0.05, TZ[2]), (TX1 - 0.05, TY1 - 0.05, TZ[2]), (TX1 - 0.05, TY0 + 0.05, TZ[2]), (10.0, TY0 + 0.05, TZ[2])])
    grail(b, [(13.25, -20.0, TZ[2]), (13.25, -14.7, TZ[2])]); grail(b, [(13.25, -20.0, TZ[3]), (13.25, -14.7, TZ[3])]); grail(b, [(11.85, -20.0, TZ[3]), (11.85, -14.7, TZ[3])])
    for lv in (3, 4):
        z = TZ[lv]
        grail(b, [(TX0 + 0.05, -16.0, z), (TX0 + 0.05, -11.0, z)])
        grail(b, [(3.9, TY1 - 0.05, z), (TX1 - 0.05, TY1 - 0.05, z), (TX1 - 0.05, TY0 + 0.05, z), (7.0, TY0 + 0.05, z)])
    # terrace furniture and lights
    rnd = random.Random(3)
    for lv in (3, 4):
        for (x, y) in ((6.5, -9.3), (9.6, -9.3), (9.0, -12.5), (5.5, -13.0), (10.0, -22.0), (13.6, -22.0), (13.9, -11.5)):
            if lv == 3 and x > 11.5 and -20.5 < y < -14: continue
            table_set(b, x, y, TZ[lv], rnd.uniform(0, 90), chairs=rnd.choice((2, 3, 4)))
    for x in (4.5, 7.2, 9.9, 12.6):
        z = canopy_z(-8.5); b.tube("m_dark", (x, -8.5, z), (x, -8.5, z - 0.5), 0.01, 3); blob(b, "light", (x, -8.5, z - 0.62), (0.14, 0.14, 0.14), rnd, sub=1, amp=0)
    for lv in (2, 3):
        for x in (5.0, 9.0, 13.0): b.box("light", x - 0.3, -9.0, TZ[lv + 1] - 0.38, x + 0.3, -8.94, TZ[lv + 1] - 0.35, "xXyYz")
    # the big canopy: timber soffit, green fascia, tilted up to the plaza
    cx0, cx1, cy0, cy1 = -2.5, 18.5, -27.0, -3.0; za, zb = canopy_z(cy0), canopy_z(cy1); th = 0.75
    b.poly("timber_slat", [(cx0, cy1, zb), (cx1, cy1, zb), (cx1, cy0, za), (cx0, cy0, za)])
    b.poly("roof_green", [(cx0, cy0, za + th), (cx1, cy0, za + th), (cx1, cy1, zb + th), (cx0, cy1, zb + th)], rot=True)
    b.poly("teal", [(cx0, cy0, za), (cx1, cy0, za), (cx1, cy0, za + th), (cx0, cy0, za + th)])
    b.poly("teal", [(cx1, cy1, zb), (cx0, cy1, zb), (cx0, cy1, zb + th), (cx1, cy1, zb + th)])
    b.poly("teal", [(cx1, cy0, za), (cx1, cy1, zb), (cx1, cy1, zb + th), (cx1, cy0, za + th)])
    b.poly("teal", [(cx0, cy1, zb), (cx0, cy0, za), (cx0, cy0, za + th), (cx0, cy1, zb + th)])


def build_podium(b):
    # avenue wall with parking bays, gates and planter parapet
    b.push(-1, PYS)
    wall(b, "brick", 0, 60, 0, 5.0, [(8, 12, 0, 2.9, "gate"), (3, 4.1, 0, 2.2, "door"), (17, 21.5, 0.0, 3.1, "dark"), (24, 28.5, 0.0, 3.1, "dark"), (34, 38.5, 0, 3.1, "dark"), (41, 45.5, 0, 3.1, "dark"),
                                     (48, 52.5, 0, 3.1, "dark"), (55, 56.1, 0, 2.2, "door")], t=0.4)
    b.box("concrete", -0.06, -0.2, 5.0, 60.06, 0.5, 5.12, "xXyYZz"); b.box("concrete", 0, -0.03, 4.1, 60, 0, 4.4, "yzZ")
    for x in (0, 7.2, 12.8, 16.2, 22.75, 29.3, 33.2, 39.75, 46.75, 53.3, 59.6): b.box("brick", x, -0.14, 0, x + 0.4, 0, 5.0, "xXy")
    b.pop()
    b.push(PX1, PYS, 0, 90)
    wall(b, "brick", 0, 28, 0, PD, [(2, 3.1, 0, 2.2, "door"), (5.5, 9.5, 0, 3.0, "dark"), (11.5, 14.5, 0.9, 2.6, "win"), (24.6, 27.2, 0, 2.9, "shop")], t=0.4)
    b.box("concrete", 0, -0.03, PD - 0.35, 28, 0, PD, "yzZ"); b.box("brick", 0, 0, PD, 5.0, 0.4, 5.0); b.box("concrete", -0.06, -0.06, 5.0, 5.0, 0.46, 5.12, "xXyYZz")
    b.pop()
    b.push(-1, -24, 0, -90); wall(b, "brick", 0, 11, 0, 5.0, [(4, 5.1, 0, 2.2, "door")], t=0.4); b.box("concrete", -0.06, -0.06, 5.0, 11, 0.46, 5.12, "xXyYZz"); b.pop()
    b.push(19, PYN, 0, 180); wall(b, "brick", 0, 4, 0, PD - 0.35, [(0.5, 3.5, 0, 3.1, "slat")], t=0.35); b.box("concrete", 0, -0.02, PD - 0.35, 4, 0.35, PD, "xXyY"); b.pop()
    # top surfaces
    b.poly("planting", [(-0.6, PYS + 0.5, 4.8), (PX1 - 0.4, PYS + 0.5, 4.8), (PX1 - 0.4, -30, 4.8), (-0.6, -30, 4.8)])
    b.box("concrete", -0.6, -30.0, PD, PX1 - 0.4, -29.75, 4.92)
    for (a, c, d, e) in ((-0.6, -29.75, PX1, -24), (15, -24, 43.5, PYN), (43.5, -24, PX1, -20), (43.5, -10.5, PX1, PYN), (57.5, -20, PX1, -10.5)):
        b.poly("deck", [(a, c, PD), (d, c, PD), (d, e, PD), (a, e, PD)])
    shrubs(b, 0, PYS + 0.9, PX1 - 1, -30.6, 4.8, 150, 9, r=(0.45, 1.05))
    shrubs(b, 0, PYS + 0.15, PX1 - 1, PYS + 0.5, 4.75, 40, 10, r=(0.4, 0.7))
    tufts(b, 0, PYS + 0.8, PX1 - 1, -30.4, 4.8, 170, 12, h=1.0)
    rnd = random.Random(21)
    for i in range(7): tree(b, "small", 3 + i * 8.3 + rnd.uniform(-1, 1), -32.3 + rnd.uniform(-0.8, 0.8), rnd.uniform(0.7, 1.0), 40 + i, z=4.8)
    # pool
    b.box("stone", 43.5, -20, PD, 57.5, -10.5, PD + 0.12, "xXyY")
    for (a, c, d, e) in ((43.5, -20, 57.5, -19.5), (43.5, -11, 57.5, -10.5), (43.5, -19.5, 44, -11), (57, -19.5, 57.5, -11)):
        b.poly("stone", [(a, c, PD + 0.12), (d, c, PD + 0.12), (d, e, PD + 0.12), (a, e, PD + 0.12)])
    b.box("court", 44, -19.5, PD - 0.1, 57, -11, PD + 0.12, "")
    wq = [(44, -19.5), (57, -19.5), (57, -11), (44, -11)]
    b.poly("court", [(x, y, PD - 0.02) for x, y in wq], [(0.01, 0.01), (0.99, 0.01), (0.99, COURT_V0 - 0.01), (0.01, COURT_V0 - 0.01)])
    for (p, q) in zip(wq, wq[1:] + wq[:1]):
        b.poly("court", [(q[0], q[1], PD - 0.02), (p[0], p[1], PD - 0.02), (p[0], p[1], PD + 0.12), (q[0], q[1], PD + 0.12)], [(0.1, 0.02), (0.9, 0.02), (0.9, 0.05), (0.1, 0.05)])
    # balustrades
    grail(b, [(PX1 - 0.05, -30, PD), (PX1 - 0.05, -12.0, PD)]); grail(b, [(PX1 - 0.05, -10.5, PD), (PX1 - 0.05, PYN, PD)])
    grail(b, [(15, PYN + 0.02, PD), (19, PYN + 0.02, PD)])
    # round planter with the palm
    pc = (29.0, -14.5)
    b.cyl("concrete", pc[0], pc[1], PD, PD + 1.1, 3.3, n=28, cap="")
    for i in range(28):
        a, c = radians(i * 360 / 28), radians((i + 1) * 360 / 28)
        b.poly("concrete", [(pc[0] + 3.3 * cos(a), pc[1] + 3.3 * sin(a), PD + 1.1), (pc[0] + 3.3 * cos(c), pc[1] + 3.3 * sin(c), PD + 1.1),
                            (pc[0] + 2.95 * cos(c), pc[1] + 2.95 * sin(c), PD + 1.1), (pc[0] + 2.95 * cos(a), pc[1] + 2.95 * sin(a), PD + 1.1)])
        b.poly("concrete", [(pc[0] + 2.95 * cos(c), pc[1] + 2.95 * sin(c), PD + 0.9), (pc[0] + 2.95 * cos(a), pc[1] + 2.95 * sin(a), PD + 0.9),
                            (pc[0] + 2.95 * cos(a), pc[1] + 2.95 * sin(a), PD + 1.1), (pc[0] + 2.95 * cos(c), pc[1] + 2.95 * sin(c), PD + 1.1)])
    b.cyl("soil", pc[0], pc[1], PD + 0.85, PD + 0.9, 2.95, n=28, cap="t")
    tree(b, "palm", pc[0], pc[1], 1.25, 77, z=PD + 0.9)
    shrubs(b, pc[0] - 1.6, pc[1] - 1.6, pc[0] + 1.6, pc[1] + 1.6, PD + 0.9, 7, 78, r=(0.4, 0.6))
    # pergola: star-framed timber slat bays on dark posts
    for i in range(5):
        x0 = 9.5 + 6.5 * i; x1 = x0 + 6.5; y0, y1 = -29.9, -24.1; zc = PD + 2.9; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; ct = (cx, cy, zc + 0.9)
        rim = [(x0, y0), (cx, y0), (x1, y0), (x1, cy), (x1, y1), (cx, y1), (x0, y1), (x0, cy)]
        for k in range(8):
            p, q = rim[k], rim[(k + 1) % 8]
            b.poly("slat_alpha", [(p[0], p[1], zc), (q[0], q[1], zc), ct], rot=(k % 4 in (1, 2)) ^ (i % 2 == 1))
            b.tube("m_dark", (p[0], p[1], zc), ct, 0.05, 4); b.tube("m_dark", (p[0], p[1], zc - 0.02), (q[0], q[1], zc - 0.02), 0.05, 4)
        for (x, y) in ((x0, y0), (x0, y1)) + (((x1, y0), (x1, y1)) if i == 4 else ()):
            b.box("m_dark", x - 0.07, y - 0.07, PD, x + 0.07, y + 0.07, zc, "xXyY")
        sofa(b, cx - 1.2, -28.9, PD, 180, 2.2); sofa(b, cx + 1.6, -25.0, PD, 0, 2.2)
        b.box("timber_slat", cx - 0.5, -27.4, PD, cx + 0.5, -26.6, PD + 0.35, "xXyYZ")
    # loungers, umbrellas, cafe tables
    for i in range(6):
        x = 44.4 + i * 2.2; lounger(b, x, -22.2, PD, 180)
        if i % 2 == 0: umbrella(b, x + 1.1, -22.4, PD, 1.5)
    for i in range(5):
        x = 34.5 + i * 1.75; lounger(b, x, -11.5 - 0.5 * i, PD, 200 + 4 * i)
    for (x, y) in ((36, -9.3), (39.6, -10.6), (42.2, -13.2), (41.8, -17.3), (35.2, -19.6), (40.2, -21.2)): umbrella(b, x, y, PD, 1.7)
    for i in range(3): lounger(b, 58.2, -18.5 + i * 2.6, PD, 90)
    rnd = random.Random(8)
    for (x, y) in ((18, -10), (21.5, -12.5), (18.5, -15.5), (22.5, -18), (18, -20.5), (24.5, -9.6), (26.5, -21), (31, -20.5), (34, -8.6), (30, -8.8), (20, -22.5), (38.5, -14.5)):
        table_set(b, x, y, PD, rnd.uniform(0, 90), chairs=rnd.choice((2, 4, 4)), top="timber_slat")
    for (x, y) in ((17.5, -8.5), (23.8, -18.6), (33.5, -22.2)): umbrella(b, x, y + 1.2, PD, 1.7)
    # outside stair down the east side
    b.box("concrete", PX1, -12.0, 0, 61.5, -10.5, PD, "XyY", top="deck")
    for i in range(27):
        z = PD - (i + 1) * PD / 27.0; y1 = -12.0 - i * 0.31; b.box("concrete", PX1, y1 - 0.31, 0, 61.5, y1, z, "XyZ")
    mrail(b, [(61.45, -10.5, PD), (61.45, -12.0, PD), (61.45, -12.0 - 27 * 0.31, 0.0)], h=1.0, mat="m_steel")
    mrail(b, [(PX1 + 0.08, -12.0, PD), (PX1 + 0.08, -12.0 - 27 * 0.31, 0.0)], h=1.0, mat="m_steel")
    mrail(b, [(PX1, -10.52, PD), (61.45, -10.52, PD)], h=1.0, mat="m_steel")


def build_court(b):
    """Covered court: open to the plaza on the west, court laid north-south, bleachers at the east end
    climbing to the pitch level, terraced steps along the north, brick terrace wall along the south."""
    x0 = RX0
    for (ya, za), (yb, zb) in zip(ROOF, ROOF[1:]):
        xa, xb = rx1(ya), rx1(yb)
        b.poly("roof_green", [(x0, ya, za), (xa, ya, za), (xb, yb, zb), (x0, yb, zb)])
        b.poly("roof_under", [(x0, yb, zb - 0.15), (xb, yb, zb - 0.15), (xa, ya, za - 0.15), (x0, ya, za - 0.15)])
        b.poly("teal", [(x0, yb, zb - 0.4), (x0, ya, za - 0.4), (x0, ya, za + 0.03), (x0, yb, zb + 0.03)])
        b.poly("teal", [(xa, ya, za - 0.4), (xb, yb, zb - 0.4), (xb, yb, zb + 0.03), (xa, ya, za + 0.03)])
    (ya, za), (yb, zb) = ROOF[0], ROOF[-1]
    b.poly("teal", [(x0, ya, za - 0.4), (RX1, ya, za - 0.4), (RX1, ya, za + 0.03), (x0, ya, za + 0.03)])
    b.poly("teal", [(RX1, yb, zb - 0.4), (x0, yb, zb - 0.4), (x0, yb, zb + 0.03), (RX1, yb, zb + 0.03)])
    b.box("teal", x0, RYM - 0.4, zr(RYM) - 0.05, RX1 + PROW, RYM + 0.4, zr(RYM) + 0.1, "xXyYZ")
    y = RY0 + 0.4
    while y < RY1 - 0.2:
        z = zr(y) - 0.15; b.box("red", x0 + 0.1, y - 0.05, z - 0.2, rx1(y) - 0.2, y + 0.05, z, "yYz"); y += 1.85
    # perforated trusses on paired dark columns at both eaves
    h = (RY1 - RY0) / 8.0
    nodes = [(RY0 + h * k, d) for k, d in enumerate((0.4, 0.9, 1.2, 1.4, 1.8, 1.4, 1.2, 0.9, 0.4))]
    for xk in TRUSS_X:
        s = 0.0
        for (ya, da), (yb, db) in zip(nodes, nodes[1:]):
            ta, tb = zr(ya) - 0.15, zr(yb) - 0.15; L = sqrt((yb - ya) ** 2 + (tb - ta) ** 2); k = max(1, round(L / 1.25)); s2 = s + k
            b.poly("steel_red", [(xk, ya, ta - da), (xk, yb, tb - db), (xk, yb, tb), (xk, ya, ta)], [(s, 0.01), (s2, 0.01), (s2, 0.74), (s, 0.74)])
            b.poly("steel_red", [(xk - 0.16, ya, ta - da), (xk + 0.16, ya, ta - da), (xk + 0.16, yb, tb - db), (xk - 0.16, yb, tb - db)], [(0.3, 0.86), (0.7, 0.86), (0.7, 0.94), (0.3, 0.94)])
            s = s2
        for (yc, dd) in ((RY0 + 0.9, 0.5), (RY1 - 0.9, 0.5)):
            top = zr(yc) - 0.15 - dd
            for dx in (-0.2, 0.08): b.box("m_dark", xk + dx, yc - 0.15, 0.35, xk + dx + 0.12, yc + 0.15, top + 0.3, "xXyY")
            b.box("concrete", xk - 0.32, yc - 0.3, 0, xk + 0.32, yc + 0.3, 0.38)
            b.box("m_dark", xk - 0.22, yc - 0.2, top - 0.02, xk + 0.22, yc + 0.2, top + 0.02, "xXyYz")
    for yl in (RYM - 8.0, RYM + 8.0):
        z = zr(yl) - 2.2; b.box("light", 22, yl - 0.04, z, 50, yl + 0.04, z + 0.06, "xXyYzZ")
        for xk in TRUSS_X[1:-1]: b.tube("m_dark", (xk + 0.5, yl, z + 0.08), (xk + 0.5, yl, zr(yl) - 0.3), 0.01, 3)
    # court floor (long side north-south) and hoops
    b.poly("pave_buff", [(RX0, 5.0, 0.02), (EX0, 5.0, 0.02), (EX0, NY0, 0.02), (RX0, NY0, 0.02)])
    b.poly("court", [(24.5, 6.0, 0.045), (40.5, 6.0, 0.045), (40.5, 33.0, 0.045), (24.5, 33.0, 0.045)], [(0, COURT_V0), (0, 1), (1, 1), (1, COURT_V0)])
    for (by, rz) in ((7.7, 90), (31.3, -90)):
        b.push(32.5, by, 0, rz)
        b.box("m_dark", -1.5, -0.5, 0, -0.5, 0.5, 0.5, top="black"); b.tube("m_dark", (-1.0, 0, 0.5), (-1.0, 0, 3.0), 0.09, 6); b.tube("m_dark", (-1.0, 0, 3.0), (1.15, 0, 3.35), 0.07, 5)
        b.box("white", 1.15, -0.9, 2.9, 1.2, 0.9, 3.95, "xXyYZz"); b.box("orange", 1.2, -0.3, 3.05, 1.21, 0.3, 3.5, "X")
        for i in range(8):
            a, c = i * pi / 4, (i + 1) * pi / 4
            b.tube("orange", (1.44 + 0.23 * cos(a), 0.23 * sin(a), 3.05), (1.44 + 0.23 * cos(c), 0.23 * sin(c), 3.05), 0.012, 3)
        b.pop()
    # terraced steps along the north (they run on west as the big plaza stair) and bleachers at the east end
    for i in range(SN):
        zt = (i + 1) * RISE; ya = NY0 + NGO * i; yb = ya + NGO; xa = EX0 + EGO * i; xb = xa + EGO
        b.box("brick", SWX, ya, zt - RISE, xb, yb, zt, "y", top="pave_red")
        b.box("brick", xa, 5.0, zt - RISE, xb, ya, zt, "x", top="pave_red")
        b.box("brick", SWX - 0.35, ya, 0, SWX, yb, zt + 0.45, "xXy", top="concrete")
        if i % 2 == 1:
            b.box("light", SWX, ya - 0.012, zt - 0.06, xa, ya, zt - 0.03, "y"); b.box("light", xa - 0.012, 5.0, zt - 0.06, xa, ya, zt - 0.03, "x")
        for ay in (8.3, 18.8, 29.3):   # red aisle steps up the bleachers
            b.box("red", xa - 0.4, ay, zt - RISE, xa, ay + 1.4, zt - RISE / 2, "xyYZ")
        for ax in (-9.0, 4.0, 25.0, 38.0):
            b.box("red", ax, ya - 0.45, zt - RISE, ax + 1.4, ya, zt - RISE / 2, "xXyZ")
    for ty in (13.6, 24.6):            # the two tunnel doors in the bleachers
        b.box("brick", EX0 - 0.06, ty - 1.1, 0, EX0 + 2.5, ty + 1.1, 2.5, "xyY", top="concrete")
        b.box("black", EX0 - 0.08, ty - 0.65, 0, EX0 - 0.06, ty + 0.65, 2.1, "x")
    for (a, c) in ((5.3, 8.3), (9.7, 18.8), (20.2, 29.3), (30.7, NY0 - 0.3)): mrail(b, [(EX0 - 0.5, a, 0), (EX0 - 0.5, c, 0)], h=0.95, bars=2)
    # south side: brick terrace wall with the pool deck on top
    b.push(RX1 - 1.0, 4.85, 0, 180)
    wall(b, "brick", 0, 34, 0, PD, [(3.0, 4.2, 0, 2.3, "door"), (11, 16, 0, 3.1, "slat"), (24, 25.2, 0, 2.3, "door")], t=0.35)
    b.box("concrete", 0, -0.03, PD - 0.35, 34, 0, PD, "yzZ")
    b.pop()
    b.push(19, 4.85, 0, -90); wall(b, "brick", 0, 11.85, 0, PD, [(3.5, 9.5, 0.12, 3.3, "shop")], t=0.35); b.box("concrete", 0, -0.03, PD - 0.35, 11.85, 0, PD, "yzZ"); b.pop()
    b.poly("deck", [(19, PYN, PD), (PX1, PYN, PD), (PX1, 4.85, PD), (19, 4.85, PD)])
    grail(b, [(19.05, PYN, PD), (19.05, 4.8, PD), (RX1 - 1.0, 4.8, PD)])
    rnd = random.Random(31)
    for (x, y) in ((23, -3), (28, 0.5), (33, -3.5), (39, 0.8), (45, -2.5), (51, 1.0)): table_set(b, x, y, PD, rnd.uniform(0, 90), chairs=4, top="timber_slat")
    for (x, y) in ((25.5, -1.2), (36, -1.4), (48, -0.8)): umbrella(b, x, y, PD, 1.7)


def fence(b, pts, h, post=3.0, gap=None):
    for p, q in zip(pts, pts[1:]):
        p = Vector((p[0], p[1], 0)); q = Vector((q[0], q[1], 0)); up = Vector((0, 0, h)); L = (q - p).length
        b.poly("fence", [p[:], q[:], (q + up)[:], (p + up)[:]], [(0, 0), (L / 2, 0), (L / 2, h / 2), (0, h / 2)])
        b.tube("m_dark", p + up, q + up, 0.035, 4); b.tube("m_dark", p + up * 0.02, q + up * 0.02, 0.03, 4)
        k = max(1, round(L / post))
        for i in range(k + 1):
            c = p.lerp(q, i / k); b.tube("m_dark", c, c + up, 0.045, 5)


def build_east(b):
    """The raised east and north side: plaza at the top of the bleachers, the two fenced pitches, the upper
    entrance plaza beside the car park, and grass banks back down to street level."""
    for q in ([(SWX, 43), (118.36, 43), (110, 52), (SWX, 52)], [(53, 4.85), (136, 4.85), (136, 24), (118.36, 43), (53, 43)],
              [(59, -8), (136, -8), (136, 4.85), (59, 4.85)], [(76, -8), (82, -28), (136, -28), (136, -8)]):
        b.poly("pave_red", [(x, y, PD) for x, y in q])
    edge = [(62, -8), (76, -8), (82, -28), (136, -28), (136, 24), (110, 52), (SWX, 52), (SWX, 43)]; W = 7.0
    nrm = []
    for p, q in zip(edge, edge[1:]):
        d = Vector((q[0] - p[0], q[1] - p[1])).normalized(); nrm.append(Vector((d.y, -d.x)))
    foot = []
    for i, p in enumerate(edge):
        if i == 0: o = nrm[0] * W
        elif i == len(edge) - 1: o = nrm[-1] * W
        else: o = (nrm[i - 1] + nrm[i]) * (W / (1 + nrm[i - 1].dot(nrm[i])))
        foot.append((p[0] + o.x, p[1] + o.y))
    for i in range(len(edge) - 1):
        b.poly("lawn", [(edge[i][0], edge[i][1], PD), (foot[i][0], foot[i][1], 0), (foot[i + 1][0], foot[i + 1][1], 0), (edge[i + 1][0], edge[i + 1][1], PD)])
    b.poly("brick", [(62, -8, PD), (62, -8, 0), (62, -8 - W, 0)]); b.poly("brick", [(SWX, 43, PD), (SWX - W, 43, 0), (SWX, 43, 0)])
    b.box("brick", 59, -8.3, 0, 62, -8, PD, "y")
    # the two five-a-side pitches in their cage
    b.push(107.5, 0.2, PD, -11.5)
    b.poly("pave_buff", [(-25, -17.5, 0.02), (25, -17.5, 0.02), (25, 17.5, 0.02), (-25, 17.5, 0.02)])
    for cx in (-12.0, 12.0):
        b.poly("pitch5", [(cx - 10, -14.75, 0.05), (cx + 10, -14.75, 0.05), (cx + 10, 14.75, 0.05), (cx - 10, 14.75, 0.05)], [(0, 0), (0, 1), (1, 1), (1, 0)])
        for sg in (-1, 1):
            y = sg * 14.6
            for gx in (cx - 1.5, cx + 1.5): b.tube("white", (gx, y, 0), (gx, y, 2.0), 0.05, 5)
            b.tube("white", (cx - 1.5, y, 2.0), (cx + 1.5, y, 2.0), 0.05, 5)
    fence(b, [(-23.5, -2), (-23.5, -16.5), (23.5, -16.5), (23.5, 16.5), (-23.5, 16.5), (-23.5, 2)], 5.0)
    fence(b, [(0, -16.5), (0, 16.5)], 5.0)
    for (x, y) in ((-24.2, -9), (-24.2, 9), (24.2, -9), (24.2, 9), (0, -17.2), (0, 17.2)):
        b.tube("m_steel", (x, y, 0), (x, y, 9.0), 0.11, 6, r1=0.07); b.box("light", x - 0.5, y - 0.25, 8.9, x + 0.5, y + 0.25, 9.15, "xXyYzZ")
    b.pop()
    # solar shade along the north of the pitches
    b.push(110, 18.5, PD, -11.5)
    b.box("m_dark", -22, -3.3, 3.2, 22, 3.3, 3.34, "xXyYz", top="black")
    for i in range(9):
        for y in (-2.6, 2.6): b.tube("m_steel", (-21 + i * 5.25, y, 0), (-21 + i * 5.25, y, 3.2), 0.06, 5)
    for i in range(4): bench(b, -15 + i * 10, 0, 0, 2.4)
    b.pop()
    # boundary fences: from the pitches round to the car park side, closed except for the gate on the upper plaza
    b.push(0, 0, PD)
    fence(b, [(62.3, -7.6), (76.4, -7.6), (82.4, -27.6), (135.6, -27.6), (135.6, 23.8), (109.8, 51.6), (16.0, 51.6)], 2.4)
    fence(b, [(-10.0, 51.6), (SWX + 0.4, 51.6), (SWX + 0.4, 43.4)], 2.4)
    b.pop()
    for q in ([(88, 28), (130, 28), (112, 48), (88, 48)], [(84, -27), (134, -27), (134, -21), (86, -21)]): b.poly("lawn", [(x, y, PD + 0.02) for x, y in q])
    shrubs(b, 90, 30, 112, 46, PD, 22, 93, r=(0.4, 0.9)); shrubs(b, 87, -26.5, 133, -21.5, PD, 30, 94, r=(0.4, 0.8)); tufts(b, 87, -26.5, 133, -21.5, PD, 60, 95, h=0.8)
    for gx in (-10.6, 16.0):
        b.box("brick", gx, 51.2, PD, gx + 0.6, 51.9, PD + 2.9, "xXyY", top="concrete")
    b.poly("pave_buff", [(-10, 50.5, PD + 0.02), (16, 50.5, PD + 0.02), (16, 52, PD + 0.02), (-10, 52, PD + 0.02)])
    b.poly("pave_buff", [(-10, 52, PD), (16, 52, PD), (16, 52 + W, 0), (-10, 52 + W, 0)])   # ramp down to the car park
    # two small brick kiosks on the upper plaza
    for kx in (22.0, 36.0):
        b.push(kx, 45.6, PD); wall(b, "brick", 0, 8, 0, 3.2, [(0.8, 7.2, 0.1, 2.7, "shop")], t=0.3); b.pop()
        b.push(kx + 8, 50.4, PD, 180); wall(b, "brick", 0, 8, 0, 3.2, [(3.4, 4.5, 0, 2.2, "door")], t=0.3); b.pop()
        b.push(kx, 50.4, PD, -90); wall(b, "brick", 0, 4.8, 0, 3.2, [], t=0.3); b.pop()
        b.push(kx + 8, 45.6, PD, 90); wall(b, "brick", 0, 4.8, 0, 3.2, [], t=0.3); b.pop()
        b.box("teal", kx - 0.8, 44.2, PD + 3.2, kx + 8.8, 50.9, PD + 3.45, "xXyYz", top="roof_green")
        for px in (kx - 0.5, kx + 8.5): b.tube("m_dark", (px, 44.5, PD), (px, 44.5, PD + 3.2), 0.06, 5)
    # planting on the raised side
    b.poly("lawn", [(62, 27, PD + 0.02), (84, 27, PD + 0.02), (84, 42, PD + 0.02), (62, 42, PD + 0.02)])
    b.cyl("pave_buff", 72, 34.5, PD + 0.02, PD + 0.04, 6.0, n=24, cap="t")
    tree(b, "broad", 72, 34.5, 1.1, 311, z=PD)
    for i, (k, x, y, s) in enumerate((("palm", 64, 29, 0.7), ("palm", 82, 40, 0.7), ("small", 66, 41, 1.2), ("palm", 90, 46, 0.65), ("broad", 100, 47, 0.8), ("palm", 60, 47, 0.65),
                                      ("small", 56.5, 30, 1.1), ("small", 56.5, 12, 1.1), ("palm", 66, -3, 0.6), ("small", 80, -2, 1.1), ("broad", 2, 47.5, 0.8), ("palm", -13, 47, 0.6), ("small", 50, 47.5, 1.1))):
        tree(b, k, x, y, s, 400 + i, z=PD)
    for i, (x, y) in enumerate(((58, 20), (70, 14), (60, 38), (88, 26), (30, 44.3), (8, 45))):
        b.push(0, 0, PD); lamp_tree(b, x, y, 4.6, 40 + i); b.pop()
    for (x, y, r) in ((57, 24, 90), (57, 8, 90), (76, 24.5, 0), (12, 49.5, 0), (-6, 46, 0)):
        b.push(0, 0, PD); bench(b, x, y, r); b.pop()
    shrubs(b, 63, 28, 83, 41, PD, 26, 91, r=(0.4, 0.8)); tufts(b, 62.5, 27.5, 83.5, 41.5, PD, 60, 92, h=0.8)


def build_octagon(b):
    # the open pavilion: a wide, low eight-sided roof with a timber soffit on leaning steel columns, a glazed green bar in the middle
    cx, cy = OCT; R = 13.0; apex = 5.5; ev = 3.7; KR = 5.2
    hz = lambda r: apex + (ev - apex) * r / R
    P = [(cx + R * cos(radians(k * 45 + 22.5)), cy + R * sin(radians(k * 45 + 22.5))) for k in range(8)]
    for k in range(8):
        k2 = (k + 1) % 8; a = (P[k][0], P[k][1], ev); c = (P[k2][0], P[k2][1], ev); ap = (cx, cy, apex); dz = Vector((0, 0, -0.3))
        horiz = k in (0, 3, 4, 7)
        b.poly("roof_green", [a, c, ap], rot=horiz)
        b.poly("timber_slat", [(Vector(c) + dz)[:], (Vector(a) + dz)[:], (Vector(ap) + dz)[:]], rot=horiz)
        b.poly("m_dark", [(a[0], a[1], ev - 0.34), (c[0], c[1], ev - 0.34), (c[0], c[1], ev + 0.04), (a[0], a[1], ev + 0.04)])
        ca = Vector((cx, cy, apex - 0.36)); va = Vector((a[0], a[1], ev - 0.36))
        b.tube("light", ca.lerp(va, 0.3), ca.lerp(va, 0.97), 0.035, 4)   # light line along each fold
        ang = radians(k * 45 + 22.5); t = Vector((-sin(ang), cos(ang), 0)); rad = Vector((cos(ang), sin(ang), 0))
        for sg in (-1, 1):  # steel columns leaning out from the foot, in pairs that spread apart
            b.tube("m_steel", Vector((cx, cy, 0)) + rad * 8.6 + t * sg * 0.2, Vector((cx, cy, hz(11.2) - 0.32)) + rad * 11.2 + t * sg * 1.5, 0.09, 6)
    b.cyl("roof_green", cx, cy, apex - 0.25, apex + 1.5, 2.6, 0.0, n=8, cap="", a0=22.5, a1=382.5)   # small raised cap over the middle
    b.cyl("m_dark", cx, cy, apex - 0.6, apex - 0.25, 2.6, n=8, cap="", a0=22.5, a1=382.5)
    K = [(cx + KR * cos(radians(k * 45 + 22.5)), cy + KR * sin(radians(k * 45 + 22.5))) for k in range(8)]
    for k in range(8):  # central glazed bar
        p, q = K[k], K[(k + 1) % 8]; L = sqrt((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2); ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        b.push(q[0], q[1], 0, ang + 180)
        if k in (1, 5): wall(b, "teal", 0, L, 0, 3.3, [(0.25, L - 0.25, 0.0, 2.4, "glass")], t=0.12)
        else:
            wall(b, "teal", 0, L, 0, 3.3, [(0.12, L - 0.12, 1.08, 2.9, "glass")], t=0.12)
            b.box("timber_slat", 0.05, -0.38, 1.04, L - 0.05, 0.05, 1.1, "xXyYZz"); b.poly("timber_slat", [(0.1, -0.02, 0.02), (L - 0.1, -0.02, 0.02), (L - 0.1, -0.02, 1.04), (0.1, -0.02, 1.04)])
        b.pop()
    b.cyl("teal", cx, cy, 3.3, 3.5, KR + 0.4, n=8, cap="tb", a0=22.5, a1=382.5)
    b.cyl("glazing", cx, cy, 3.5, hz(KR - 0.4) - 0.3, KR - 0.4, n=8, cap="", a0=22.5, a1=382.5)
    b.cyl("interior", cx, cy, 0, 3.3, 3.2, n=8, cap="", a0=22.5, a1=382.5)
    for k in range(8):
        a = radians(k * 45 + 22.5); b.tube("light", (cx + (KR + 0.3) * cos(a), cy + (KR + 0.3) * sin(a), 3.27), (cx + (KR + 0.3) * cos(a + pi / 4), cy + (KR + 0.3) * sin(a + pi / 4), 3.27), 0.03, 3)
    rnd = random.Random(4)
    for k in range(8):
        a = radians(k * 45); rr = 7.9 if k % 2 else 7.3
        table_set(b, cx + rr * cos(a), cy + rr * sin(a), 0, rnd.uniform(0, 90), chairs=4, top="timber_slat", seat="teal" if k % 2 else "m_dark")
    for k in range(8):
        a = radians(k * 45 + 12); table_set(b, cx + 15.6 * cos(a), cy + 15.6 * sin(a), 0, rnd.uniform(0, 90), chairs=rnd.choice((2, 4)), top="timber_slat")


def arc_bed(b, cx, cy, r0, r1, a0, a1, h=0.55, seed=0):
    """A raised brick planter that follows a curve, like the ones on the forecourt."""
    n = max(6, int((a1 - a0) / 8)); A = [radians(a0 + (a1 - a0) * i / n) for i in range(n + 1)]
    P = lambda r, a, z: (cx + r * cos(a), cy + r * sin(a), z)
    for i in range(n):
        a, c = A[i], A[i + 1]
        b.poly("brick", [P(r1, a, 0), P(r1, c, 0), P(r1, c, h), P(r1, a, h)]); b.poly("brick", [P(r0, c, 0), P(r0, a, 0), P(r0, a, h), P(r0, c, h)])
        for (ra, rb, m, z) in ((r0, r0 + 0.3, "concrete", h), (r1 - 0.3, r1, "concrete", h), (r0 + 0.3, r1 - 0.3, "planting", h - 0.04)):
            b.poly(m, [P(ra, a, z), P(rb, a, z), P(rb, c, z), P(ra, c, z)])
        m = (a + c) / 2; rm = (r0 + r1) / 2; w = (r1 - r0) / 2 - 0.6; x, y = cx + rm * cos(m), cy + rm * sin(m)
        shrubs(b, x - w, y - w, x + w, y + w, h - 0.04, 2, seed * 40 + i, r=(0.35, 0.7)); tufts(b, x - w, y - w, x + w, y + w, h - 0.04, 5, seed * 60 + i, h=0.8)
    b.poly("brick", [P(r0, A[0], 0), P(r1, A[0], 0), P(r1, A[0], h), P(r0, A[0], h)]); b.poly("brick", [P(r1, A[-1], 0), P(r0, A[-1], 0), P(r0, A[-1], h), P(r1, A[-1], h)])


def build_ground(b):
    # two-tone herringbone bands across the whole site
    x = -65.0; i = 0
    while x < 65.0:
        w = 9.4 if i % 2 == 0 else 1.4; x2 = min(65.0, x + w); m = "pave_red" if i % 2 == 0 else "pave_buff"
        b.poly(m, [(x, PYS, 0), (x2, PYS, 0), (x2, 38, 0), (x, 38, 0)]); x = x2; i += 1
    for (ya, yb) in ((-15.2, -14.0), (23.6, 24.6)): b.poly("pave_buff", [(-65, ya, 0.02), (16 if ya < 0 else 22, ya, 0.02), (16 if ya < 0 else 22, yb, 0.02), (-65, yb, 0.02)])
        # avenue verge: pavement, kerb, lawn between the gate crossings
    b.poly("pave_buff", [(-65, -38, 0.0), (146, -38, 0.0), (146, PYS, 0.0), (-65, PYS, 0.0)])
    b.poly("lawn", [(65, PYS, 0.0), (146, PYS, 0.0), (146, 38, 0.0), (65, 38, 0.0)]); b.poly("lawn", [(-65, 38, 0.0), (146, 38, 0.0), (146, 60, 0.0), (-65, 60, 0.0)])
    b.box("concrete", -65, -38, -0.12, 146, -37.82, 0.05, "xXyYZ")
    cuts = [(-65, -51.6), (-46.4, -25.6), (-20.4, 6.4), (11.6, 15.5), (56, 146)]
    for (a, c) in cuts:
        b.box("concrete", a, -37.5, 0, c, -36.1, 0.14, "xXyY", top="lawn")
    # north and west boundary: lawn strip, hedge on a low brick wall
    b.box("concrete", -65, 33.4, 0, -24, 38, 0.12, "xXy", top="lawn")
    b.box("brick", -65, 37.4, 0.12, -24, 37.7, 0.9); b.box("leaves_b", -65, 36.5, 0.12, -24, 37.4, 1.7, "xXyZ")
    b.box("leaves_b", -64.9, 2.7, 0, -64.2, 33.4, 1.2, "xXyYZ")
    # forecourt at the street corner on the west, beside the hotel: brick paving, curved raised planters, the big tree,
    # the name in white letters in front of a black railing, and brick piers where the way in meets the plaza
    b.poly("pave_red", [(-113, -36, 0), (-65, -36, 0), (-65, 14, 0), (-98, 14, 0), (-113, 2, 0)])
    for y in (-13.5, 0.9): b.poly("pave_buff", [(-113, y, 0.02), (-65, y, 0.02), (-65, y + 0.6, 0.02), (-113, y + 0.6, 0.02)])
    for (ya, yb) in ((-14.6, -13.7), (1.7, 2.6)):
        b.box("brick", -65.9, ya, 0, -65.0, yb, 3.2, "xXyY", top="concrete"); b.box("light", -65.92, ya + 0.25, 2.5, -65.9, yb - 0.25, 2.7, "x")
    for k in range(6): b.cyl("m_steel", -66.5, -11.0 + k * 2.1, 0, 0.9, 0.08, n=6)
    arc_bed(b, -88, -10, 8.5, 13, 200, 330, seed=1); arc_bed(b, -84, -35, 5, 9, 28, 152, seed=2); arc_bed(b, -92, 16, 6, 10, 215, 325, seed=3)
    b.cyl("brick", -73, -23, 0, 0.6, 3.2, n=20, cap="t", capmat="planting")
    tree(b, "broad", -73, -23, 2.1, 77, z=0.55); tree(b, "palm", -86.5, 8.2, 0.6, 501, z=0.5); tree(b, "small", -89, -21, 1.2, 502, z=0.5)
    mrail(b, [(-65.35, 2.7, 0), (-65.35, 33.4, 0)], h=1.7, post=0.24, mat="black", bars=0); mrail(b, [(-65.35, -14.7, 0), (-65.35, -36, 0)], h=1.7, post=0.24, mat="black", bars=0)
    b.push(-66.3, 19.5, 0, -90)
    for y in (0.0, -0.22):
        b.poly("sign", [(0, y, 0.3), (14, y, 0.3), (14, y, 2.1), (0, y, 2.1)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    b.box("concrete", -0.2, -0.45, 0, 14.2, 0.2, 0.3, "xXyYZ")
    b.pop()
    # raised planting beds on the west plaza
    for (a, c, d, e, s) in ((-60, 20, -46, 31, 1), (-40, 22, -26, 31, 2), (-60, 2, -50, 12, 3), (-42, -4, -36, 8, 4), (-28, -6, -22, 0, 5)):
        bed(b, a, c, d, e); shrubs(b, a + 1, c + 1, d - 1, e - 1, 0.45, int((d - a) * (e - c) / 9), 30 + s, r=(0.4, 0.8)); tufts(b, a + 0.6, c + 0.6, d - 0.6, e - 0.6, 0.45, int((d - a) * (e - c) / 5), 60 + s, h=0.8)
    bed(b, 62.8, -34.5, 64.6, -22.0); shrubs(b, 63.2, -34, 64.2, -22.6, 0.45, 8, 51, r=(0.35, 0.55))
    bed(b, 4, 25, 14, 31); shrubs(b, 5, 26, 13, 30, 0.45, 9, 53, r=(0.4, 0.8))
    for (x, y) in ((-58, -12.8), (-50, -12.8), (-20, -12.8), (-12, -12.8), (-5.5, -12.8)):
        b.box("concrete", x - 0.9, y - 0.9, 0, x + 0.9, y + 0.9, 0.5, "xXyY"); b.poly("planting", [(x - 0.8, y - 0.8, 0.45), (x + 0.8, y - 0.8, 0.45), (x + 0.8, y + 0.8, 0.45), (x - 0.8, y + 0.8, 0.45)])
        for (a, c, d, e) in ((-0.9, -0.9, 0.9, -0.8), (-0.9, 0.8, 0.9, 0.9), (-0.9, -0.8, -0.8, 0.8), (0.8, -0.8, 0.9, 0.8)): b.poly("concrete", [(x + a, y + c, 0.5), (x + d, y + c, 0.5), (x + d, y + e, 0.5), (x + a, y + e, 0.5)])
        tree(b, "small", x, y, 1.15, int(x * 7) % 97, z=0.45)
    # trees
    rnd = random.Random(2)
    for i, x in enumerate((-58.5, -36, -14, 13.5, 60)): tree(b, "conifer", x, -36.6, rnd.uniform(0.9, 1.05), 100 + i, z=0.14)
    for i, x in enumerate((-61, -42, -29, -5, 2)): tree(b, "flat" if i == 2 else "broad", x, -36.5, rnd.uniform(0.8, 0.95), 120 + i, z=0.14)
    for (x, s2) in ((30.2, 1.1), (38.7, 0.95), (53.4, 0.85), (20.8, 0.8)):
        b.box("concrete", x - 0.8, -37.6, 0, x + 0.8, -36.0, 0.14, "xXyY", top="lawn"); tree(b, "broad", x, -36.5, s2, int(x * 3), z=0.14)
    for (k, x, y, s) in (("broad", -54, 26, 1.1), ("flat", -49, 23.5, 1.0), ("broad", -36, 27, 1.1), ("flat", -30, 25, 0.9), ("broad", -55, 7, 1.0), ("small", -39, 5, 1.3), ("small", -39, -1, 1.2),
                         ("small", -25, -3, 1.2), ("palm", 63.4, -31, 0.6), ("palm", 63.4, -25, 0.55), ("broad", 9, 28, 0.9)):
        tree(b, k, x, y, s, int(x * 13 + y * 7) % 991, z=0.45)
    for i in range(3):
        x = -57 + i * 14.2; tree(b, ("broad", "conifer", "flat")[i % 3], x + rnd.uniform(-1.5, 1.5), 34.6, rnd.uniform(0.6, 0.75), 200 + i, z=0.12)
    # lamps, benches, loose tables
    for i, (x, y) in enumerate(((7.5, 3.5), (12.5, 15.5), (-22, 4), (-22, 22), (-44, 14), (-58, -4), (-33, -9), (-8, 30), (17, 28), (-62, 16), (-2, -3.5))): lamp_tree(b, x, y, 4.6, i)
    for (x, y, r) in ((-53, 19.2, 0), (-33, 21.2, 0), (-45.2, 26, 90), (-55, 1.2, 0), (-35.2, 2, 90), (9, 24.2, 0), (-23, 14, 90), (-23, 8, 90), (61, -27, 90)): bench(b, x, y, r)
    rnd = random.Random(6)
    for (x, y) in ((8, -3.5), (11.5, -2.5), (4.8, -2.2), (-16, -9), (-12, -6.5), (-46, -9), (-49.5, -7)): table_set(b, x, y, 0, rnd.uniform(0, 90), chairs=4, top="m_dark")
    for (x, y) in ((-51.4, 19.2), (-31.4, 21.2), (-53.4, 1.2), (10.6, 24.2), (-23, 11), (61, -25.2), (17, -5.6), (-3.6, 3.4), (-36, -13.4)): bin_(b, x, y)
    for (x, y) in ((16.5, -9.2), (41, -23.2), (58.2, -8)): bin_(b, x, y, PD)
    tufts(b, -64.5, 33.8, -25, 36.3, 0.12, 50, 77, h=0.8); tufts(b, 63.2, -34, 64.2, -22.6, 0.45, 12, 78, h=0.8)
    umbrella(b, 6.4, -3.6, 0, 1.8); umbrella(b, -14, -8, 0, 1.8); umbrella(b, -47.8, -8.2, 0, 1.8)
    for x in (-52, -47, -24, -21, 7, 11): b.cyl("m_steel", x, -35.6, 0, 0.9, 0.08, n=6)


# ============================================================ scene, materials, export
def material(name, img, rough=0.8, metal=0.0, alpha=None, emit=0.0, normal=None, cull=True):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(os.path.join(TEX, img)); tex.location = (-400, 300)
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough; bs.inputs["Metallic"].default_value = metal
    if alpha == "mask":
        r = nt.nodes.new("ShaderNodeMath"); r.operation = "ROUND"; r.location = (-200, 0)
        nt.links.new(tex.outputs["Alpha"], r.inputs[0]); nt.links.new(r.outputs[0], bs.inputs["Alpha"])
    elif alpha is not None:
        bs.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    if emit:
        nt.links.new(tex.outputs["Color"], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = emit
    if normal:
        nt2 = nt.nodes.new("ShaderNodeTexImage"); nt2.image = bpy.data.images.load(os.path.join(TEX, normal)); nt2.image.colorspace_settings.name = "Non-Color"; nt2.location = (-700, -200)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-300, -200); nm.inputs["Strength"].default_value = 1.0
        nt.links.new(nt2.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    m.use_backface_culling = cull
    return m


MATS = {  # name: (image, roughness, metallic, alpha, emission, normal map, backface culling)
    "brick": ("brick.jpg", 0.9, 0, None, 0, "brick_n.jpg", True), "pave_red": ("pave_red.jpg", 0.9, 0, None, 0, None, True), "pave_buff": ("pave_buff.jpg", 0.9, 0, None, 0, None, True),
    "concrete": ("concrete.jpg", 0.85, 0, None, 0, None, True), "render": ("render.jpg", 0.9, 0, None, 0, None, True), "stone": ("stone.jpg", 0.8, 0, None, 0, None, True),
    "timber_slat": ("timber_slat.jpg", 0.6, 0, None, 0, None, True), "slat_alpha": ("slat_alpha.png", 0.65, 0, "mask", 0, None, False), "deck": ("deck.jpg", 0.75, 0, None, 0, None, True),
    "timber_red": ("timber_red.jpg", 0.6, 0, None, 0, None, True), "bark": ("bark.jpg", 0.95, 0, None, 0, None, True),
    "roof_green": ("roof_green.jpg", 0.55, 0.0, None, 0, None, True), "roof_under": ("roof_under.jpg", 0.7, 0, None, 0.35, None, True),
    "steel_red": ("steel_red.png", 0.5, 0.2, "mask", 0, None, False), "court": ("court.jpg", 0.45, 0, None, 0, None, True),
    "leaves_a": ("leaves_a.jpg", 0.9, 0, None, 0, None, True), "leaves_b": ("leaves_b.jpg", 0.9, 0, None, 0, None, True), "foliage": ("foliage.png", 0.85, 0, "mask", 0, None, False),
    "planting": ("planting.jpg", 0.95, 0, None, 0, None, True), "lawn": ("lawn.jpg", 0.95, 0, None, 0, None, True),
    "glazing": ("glazing.jpg", 0.12, 0.3, None, 0, None, True), "glass": ("glass.jpg", 0.06, 0, 0.3, 0, None, False),
    "interior": ("interior.jpg", 0.8, 0, None, 0.9, None, True), "solids": ("solids.jpg", 0.55, 0.15, None, 0, None, True), "light": ("light.jpg", 0.5, 0, None, 2.0, None, True),
    "fence": ("fence.png", 0.6, 0.3, "mask", 0, None, False), "pitch5": ("pitch5.jpg", 0.9, 0, None, 0, None, True),
    "sign": ("sign.png", 0.55, 0, "mask", 0, None, False),
}


def main():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    b = Builder()
    build_ground(b); build_hotel(b); build_tower(b); build_podium(b); build_court(b); build_east(b); build_octagon(b)
    col = bpy.data.collections.new("Zaria"); bpy.context.scene.collection.children.link(col)
    tris = 0; objs = []
    for name, (V, F, U) in b.m.items():
        me = bpy.data.meshes.new("zaria_" + name); me.from_pydata([(x - OX, y - OY, z) for (x, y, z) in V], [], F)
        uvl = me.uv_layers.new(name="UVMap"); uvl.data.foreach_set("uv", [c for uv in U for c in uv])
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008); bm.to_mesh(me); bm.free()
        me.shade_smooth()
        if SMOOTH.get(name, 40) < 180: me.set_sharp_from_angle(angle=radians(SMOOTH.get(name, 40)))
        me.materials.append(material(name, *MATS[name])); me.update()
        o = bpy.data.objects.new("zaria_" + name, me); col.objects.link(o); objs.append(o)
        t = sum(len(p.vertices) - 2 for p in me.polygons); tris += t
        print("ZARIA  %-12s %7d tris" % (name, t))
    print("ZARIA total triangles:", tris, " meshes:", len(objs))
    # ---- export
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_texcoords=True, export_normals=True,
                              export_materials="EXPORT", export_image_format="AUTO", export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                              export_draco_position_quantization=16, export_draco_normal_quantization=8, export_draco_texcoord_quantization=12, export_cameras=False, export_lights=False)
    print("ZARIA glb: %.2f MB" % (os.path.getsize(OUT) / 1e6))
    if "render" in ARGS: render()


VIEWS = {  # name: (camera position, look-at point, lens mm)
    "top": ((36, 10.5, 230), (36, 11, 0), 24),
    "court_west": ((3, 21, 1.7), (40, 21, 7.5), 17),
    "from_octagon": ((-16, 15, 15), (36, 21, 6), 22),
    "pitches": ((152, -52, 40), (92, 8, 4), 24),
    "entrance": ((-93, -6, 1.7), (-40, -6, 4), 20),
    "forecourt": ((-125, -48, 16), (-70, -6, 2), 22),
    "sign": ((-84, 6, 1.7), (-62, 12, 2.5), 22),
    "pavilion": ((-36, -6, 1.7), (-10, 11, 3.5), 20),
    "bleachers": ((27, 14, 1.7), (53, 22, 4.5), 16),
    "upper": ((60, 20, PD + 1.7), (100, 5, PD + 2), 20),
    "aerial_85": ((92, -60, 40), (14, -9, 2), 30),
    "terrace_91": ((13.2, -21.6, 16.3), (46, -9, 3.5), 18),
    "tower_88": ((7.5, 17.5, 1.7), (6.8, -7, 9.0), 20),
    "court_86": ((64.6, 5.5, 1.7), (40, 11, 6.5), 17),
    "street_90": ((-34, -56.5, 1.7), (-10, -30, 6.5), 24),
    "hotel_89": ((-44, 2, 1.7), (-30, -16, 6), 20),
    "octagon_92": ((-10, 37, 1.7), (-10, 11, 3.2), 26),
    "deck": ((17, -12, PD + 1.7), (44, -15, PD + 1.5), 20),
    "court_in": ((24, 3, 4.0), (48, 13, 4), 16),
    "plaza_nw": ((-56, 33, 1.7), (-12, 2, 5), 20),
    "deck_tower": ((47, -14, PD + 1.7), (8, -15, 9), 20),
    "stair_w": ((6, 14, 1.7), (19, 3, 3.5), 20),
    "east": ((64.5, -28, 1.7), (55, -8, 4), 18),
}


def render():
    sc = bpy.context.scene; os.makedirs(REN, exist_ok=True)
    only = [a for a in ARGS if a in VIEWS]
    sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1360; sc.render.resolution_y = 900
    try: sc.eevee.taa_render_samples = 24
    except Exception: pass
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 88
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.66, 0.8, 1.0, 1); bg.inputs[1].default_value = 0.9
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.6; sun.angle = radians(3); so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    so.rotation_euler = Vector((0.42, -0.36, -0.83)).to_track_quat("-Z", "Y").to_euler()
    gm = bpy.data.materials.new("render_ground"); gm.use_nodes = True; gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.3, 0.13, 1)
    bpy.ops.mesh.primitive_plane_add(size=900, location=(0, 0, -0.06)); bpy.context.object.data.materials.append(gm)
    rm = bpy.data.materials.new("render_road"); rm.use_nodes = True; rm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.11, 1)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -50, -0.04)); bpy.context.object.scale = (700, 8, 1); bpy.context.object.data.materials.append(rm)
    cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co; cam.clip_end = 1000; cam.clip_start = 0.05
    for name, (loc, tgt, lens) in VIEWS.items():
        if only and name not in only: continue
        loc = (loc[0] - OX, loc[1] - OY, loc[2]); tgt = (tgt[0] - OX, tgt[1] - OY, tgt[2]); co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); cam.lens = lens
        sc.render.filepath = os.path.join(REN, name + ".jpg"); bpy.ops.render.render(write_still=True); print("rendered", sc.render.filepath)


main()
