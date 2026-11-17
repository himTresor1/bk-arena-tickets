"""Procedural textures for the Amahoro Stadium / Petit Stade tour models.
Run with:  ~/.blender-mcp/venv/bin/python blender/py/109_tour_textures.py
Writes tileable textures to blender/tex/tour/."""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tex', 'tour')
os.makedirs(OUT, exist_ok=True)


def tnoise(h, w, beta=1.5, seed=0):
    """Tileable fractal noise in 0..1 (FFT filtered)."""
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * h
    fx = np.fft.fftfreq(w)[None, :] * w
    r = np.sqrt(fx * fx + fy * fy)
    r[0, 0] = 1
    n = np.real(np.fft.ifft2(f / r ** beta))
    n -= n.min()
    return n / n.max()


def save_jpg(arr, name, q=88):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(
        os.path.join(OUT, name), quality=q, optimize=True)


def col(c, h, w):
    return np.ones((h, w, 3)) * np.array(c, float)[None, None, :]


def wrap_blur(a, r):
    """Gaussian blur with wrap-around via FFT (keeps tiles seamless)."""
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (math.pi * r) ** 2 * (fx * fx + fy * fy))
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * g))
    return np.stack([np.real(np.fft.ifft2(np.fft.fft2(a[..., i]) * g)) for i in range(a.shape[2])], -1)


def normal_from_height(hgt, strength):
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * strength
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * strength
    nz = np.ones_like(hgt)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    # image y runs down, glTF normal maps are +Y up
    return np.stack([(-dx / l) * .5 + .5, (dy / l) * .5 + .5, (nz / l) * .5 + .5], -1) * 255


# ---------------------------------------------------------------- facade screen
def screen():
    S = 1024
    SS = 2                      # supersample
    P = S * SS // 2             # one panel
    yy, xx = np.mgrid[0:P, 0:P]
    x = (xx + .5) / P * 2 - 1
    y = (yy + .5) / P * 2 - 1
    a, b = np.abs(x), np.abs(y)
    frame = (a > .945) | (b > .945)

    def stripes(d, k, duty=.5, ph=0.):
        return ((d * k + ph) % 1.0) < duty

    # A: concentric diamonds, solid centre, thin cross spokes
    d = a + b
    A = stripes(d, 5.0, .5, .5) | (d < .26) | (np.minimum(a, b) < .022)
    # B: chevrons pointing to the corners (X figure) with diagonal spokes
    d = np.abs(a - b)
    B = stripes(d, 5.0, .5, .0) | (np.abs(a - b) < .03) | ((a + b) < .2)
    # C: four small concentric diamonds, one per quadrant
    a2, b2 = np.abs(a - .46) / .46, np.abs(b - .46) / .46
    d = a2 + b2
    C = stripes(d, 3.0, .5, .5) | (d < .3) | (a < .03) | (b < .03)
    # D: big diamond whose inside is chevrons, outside concentric
    d1 = a + b
    D = np.where(d1 < 1.0, stripes(np.abs(a - b), 5.0, .5, .25), stripes(d1, 5.0, .5, .5)) \
        | (np.abs(d1 - 1.0) < .05) | (np.minimum(a, b) < .022)
    tiles = [[A, B], [C, D]]
    m = np.zeros((2 * P, 2 * P), bool)
    for r in range(2):
        for c in range(2):
            m[r * P:(r + 1) * P, c * P:(c + 1) * P] = tiles[r][c] | frame
    mask = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)) / 255.
    hgt = wrap_blur(mask, 1.6)
    # colour: champagne metal, slight panel-to-panel tone shift, edge highlight
    base = col((182, 157, 116), S, S)
    n = tnoise(S, S, 1.2, 1)
    brushed = wrap_blur(np.random.default_rng(2).random((S, S)), 0.6)
    base *= (0.94 + 0.10 * n)[..., None] * (0.97 + 0.06 * brushed)[..., None]
    tone = np.array([[1.0, 0.965], [0.975, 1.02]])
    tone = np.kron(tone, np.ones((S // 2, S // 2)))
    base *= tone[..., None]
    # bevel light from top-left, dark at lower-right edge
    gx = np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)
    gy = np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)
    base *= (1 + 0.9 * np.clip(gx + gy, -0.3, 0.3))[..., None]
    rgba = np.dstack([np.clip(base, 0, 255), mask * 255]).astype(np.uint8)
    # quantise colour a little so the PNG stays small
    rgba[..., :3] = (rgba[..., :3] // 4) * 4
    Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, 'screen.png'), optimize=True)
    save_jpg(normal_from_height(hgt, 2.2), 'screen_n.jpg', 90)
    # half-size copies for the small halls (keeps petitstade.glb under 1 MB)
    Image.fromarray(rgba, 'RGBA').resize((512, 512), Image.LANCZOS).save(
        os.path.join(OUT, 'screen_512.png'), optimize=True)
    Image.open(os.path.join(OUT, 'screen_n.jpg')).resize((512, 512), Image.LANCZOS).save(
        os.path.join(OUT, 'screen_n_512.jpg'), quality=88)
    # opaque version (dark infill) for distant / fallback use
    dark = col((30, 27, 24), S, S)
    save_jpg(base * mask[..., None] + dark * (1 - mask[..., None]), 'screen_opaque.jpg', 85)


# ---------------------------------------------------------------- inner wall
def innerwall():
    S = 512
    img = col((34, 32, 31), S, S) * (0.8 + 0.4 * tnoise(S, S, 1.6, 3))[..., None]
    yy, xx = np.mgrid[0:S, 0:S]
    v = yy / S
    u = xx / S
    # 5 floor slabs over the height, concrete edge beams
    slab = ((v * 5) % 1.0) < 0.12
    img[slab] = np.array((92, 88, 82)) * (0.85 + 0.3 * tnoise(S, S, 1.5, 4))[slab][:, None]
    # shadow under slab
    sh = (((v * 5) % 1.0) >= 0.12) & (((v * 5) % 1.0) < 0.2)
    img[sh] *= 0.6
    # columns at tile edges + mid
    colm = (np.abs(((u + .5) % 1.0) - .5) < 0.035) | (np.abs(u - .5) < 0.022)
    img[colm & ~slab] = np.array((70, 67, 63))
    # faint glazing glints between
    gl = (~slab) & (~colm) & ((((v * 5) % 1.0) > .55))
    img[gl] += np.array((6, 9, 12))
    save_jpg(img, 'innerwall.jpg', 85)


# ---------------------------------------------------------------- roof membrane
def roof():
    S = 512
    img = col((220, 201, 163), S, S)
    yy, xx = np.mgrid[0:S, 0:S]
    u = xx / S
    v = yy / S
    n = tnoise(S, S, 1.8, 5)
    img *= (0.93 + 0.12 * n)[..., None]
    # valley darkening (dust settles in the seams) and seam line
    edge = np.minimum(u, 1 - u)
    img *= (0.72 + 0.28 * np.clip(edge / 0.16, 0, 1) ** 0.7)[..., None]
    img[edge < 0.012] *= 0.55
    # crown highlight
    img *= (1 + 0.05 * np.exp(-((u - .5) / .18) ** 2))[..., None]
    # transverse weld lines every 1/4 tile, faint
    weld = np.abs(((v * 4) % 1.0) - .5) > 0.488
    img[weld] *= 0.93
    # faint weave
    img *= (0.985 + 0.03 * ((xx % 4 < 2) ^ (yy % 4 < 2)))[..., None]
    save_jpg(img, 'roof.jpg', 88)


# ---------------------------------------------------------------- truss (alpha)
def truss():
    W, H = 512, 128
    SS = 4
    im = Image.new('L', (W * SS, H * SS), 0)
    d = ImageDraw.Draw(im)
    t = 9 * SS
    d.rectangle([0, 0, W * SS, t], fill=255)
    d.rectangle([0, H * SS - t, W * SS, H * SS], fill=255)
    n = 4
    for i in range(n):
        x0 = i * W * SS / n
        x1 = (i + .5) * W * SS / n
        x2 = (i + 1) * W * SS / n
        d.line([x0, H * SS - t, x1, t], fill=255, width=6 * SS)
        d.line([x1, t, x2, H * SS - t], fill=255, width=6 * SS)
        d.line([x1, t, x1, H * SS - t], fill=255, width=4 * SS)
    d.line([0, 0, 0, H * SS], fill=255, width=4 * SS)
    d.line([W * SS - 1, 0, W * SS - 1, H * SS], fill=255, width=4 * SS)
    m = np.asarray(im.resize((W, H), Image.LANCZOS))
    c = col((112, 100, 84), H, W) * (0.85 + 0.3 * tnoise(H, W, 1.3, 6))[..., None]
    rgba = np.dstack([np.clip(c, 0, 255), m]).astype(np.uint8)
    rgba[..., :3] = (rgba[..., :3] // 8) * 8
    Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, 'truss.png'), optimize=True)


# ---------------------------------------------------------------- stone cladding
def stone():
    S = 512
    n = tnoise(S, S, 1.7, 7)
    fine = tnoise(S, S, 0.7, 8)
    img = col((203, 187, 158), S, S) * (0.88 + 0.16 * n + 0.08 * fine)[..., None]
    rng = np.random.default_rng(9)
    rows, cols = 4, 2            # blocks 1.2 x 0.6 m when tile = 2.4 m
    bh, bw = S // rows, S // cols
    for r in range(rows):
        off = (bw // 2) if r % 2 else 0
        for c in range(cols):
            t = 0.94 + 0.12 * rng.random()
            ys = slice(r * bh, (r + 1) * bh)
            xs = (np.arange(c * bw, (c + 1) * bw) + off) % S
            img[ys, xs[:, None].T.repeat(bh, 0)[0]] *= t
    yy, xx = np.mgrid[0:S, 0:S]
    jy = (yy % bh) < 3
    jx = (((xx - np.where((yy // bh) % 2 == 1, bw // 2, 0)) % bw) < 3)
    img[jy | jx] *= 0.70
    save_jpg(img, 'stone.jpg', 86)


def concrete():
    S = 512
    n = tnoise(S, S, 1.9, 10)
    f = tnoise(S, S, 0.8, 11)
    img = col((158, 154, 146), S, S) * (0.86 + 0.2 * n + 0.08 * f)[..., None]
    yy, xx = np.mgrid[0:S, 0:S]
    img[(yy % 128) < 2] *= 0.86
    img[(xx % 256) < 2] *= 0.88
    save_jpg(img, 'concrete.jpg', 84)


# ---------------------------------------------------------------- glazing / gates atlas
def glazing():
    W, H = 1024, 512            # left half: glazed entrance bay, right half: gate bay. v = 0..6.4 m
    SS = 2
    im = Image.new('RGB', (W * SS, H * SS), (0, 0, 0))
    d = ImageDraw.Draw(im)
    hw = W * SS // 2
    Hs = H * SS
    # ---- glazed bay
    for y in range(Hs):
        t = y / Hs
        c = (int(34 + 50 * (1 - t) ** 2), int(48 + 62 * (1 - t) ** 2), int(62 + 70 * (1 - t) ** 2))
        d.line([0, y, hw, y], fill=c)
    # reflections: soft diagonal bands
    alu = (64, 62, 60)
    nx = 6
    for i in range(nx + 1):
        x = i * hw / nx
        d.rectangle([x - 5, 0, x + 5, Hs], fill=alu)
    for fy in (0.0, 0.34, 0.60, 1.0):
        y = fy * Hs
        d.rectangle([0, y - 6, hw, y + 6], fill=alu)
    # doors: bottom 2.6 m (0.6..1.0 of height), middle four modules = 2 double doors
    dy0 = 0.60 * Hs
    for k in (1, 3):
        x0 = k * hw / nx
        x1 = (k + 2) * hw / nx
        d.rectangle([x0 + 5, dy0 + 6, x1 - 5, Hs], fill=(22, 30, 38))
        d.rectangle([x0 + 5, dy0 + 6, x1 - 5, Hs], outline=(96, 94, 90), width=8)
        xm = (x0 + x1) / 2
        d.rectangle([xm - 4, dy0 + 6, xm + 4, Hs], fill=(96, 94, 90))
        for s in (-1, 1):
            d.rectangle([xm + s * 22 - 4, dy0 + 0.35 * (Hs - dy0), xm + s * 22 + 4, dy0 + 0.7 * (Hs - dy0)],
                        fill=(190, 188, 180))
        d.rectangle([x0 + 5, Hs - 26, x1 - 5, Hs], fill=(70, 68, 66))
    # ---- gate bay: stone surround, deep dark opening with bar gate
    d.rectangle([hw, 0, 2 * hw, Hs], fill=(200, 184, 155))
    ox0, ox1 = hw + 0.12 * hw, hw + 0.88 * hw
    oy0 = 0.30 * Hs
    d.rectangle([ox0, oy0, ox1, Hs], fill=(26, 25, 25))
    d.rectangle([ox0 - 14, oy0 - 14, ox1 + 14, oy0], fill=(120, 110, 95))     # lintel shadow line
    # sign plate (blank)
    d.rectangle([hw + 0.36 * hw, 0.13 * Hs, hw + 0.64 * hw, 0.23 * Hs], fill=(52, 60, 68))
    # bars
    nb = 26
    for i in range(nb + 1):
        x = ox0 + i * (ox1 - ox0) / nb
        d.rectangle([x - 3, oy0 + 0.1 * (Hs - oy0), x + 3, Hs], fill=(98, 100, 100))
    for fy in (0.10, 0.5, 0.97):
        y = oy0 + fy * (Hs - oy0)
        d.rectangle([ox0, y - 6, ox1, y + 6], fill=(98, 100, 100))
    for fx in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = ox0 + fx * (ox1 - ox0)
        d.rectangle([x - 8, oy0, x + 8, Hs], fill=(78, 80, 80))
    # roller-shutter box
    d.rectangle([ox0, oy0, ox1, oy0 + 0.1 * (Hs - oy0)], fill=(60, 60, 60))
    im = im.resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    n = tnoise(H, W, 1.6, 12)
    a *= (0.92 + 0.16 * n)[..., None]
    # stone joints on the gate half surround
    yy, xx = np.mgrid[0:H, 0:W]
    st = (xx >= W // 2) & (a[..., 0] > 150)
    j = (((yy % 48) < 2) | ((xx + (yy // 48 % 2) * 48) % 96 < 2)) & st
    a[j] *= 0.75
    save_jpg(a, 'glazing.jpg', 88)


# ---------------------------------------------------------------- seats
def seats():
    S = 1024
    rng = np.random.default_rng(13)
    img = col((150, 148, 142), S, S) * (0.9 + 0.15 * tnoise(S, S, 1.5, 14))[..., None]
    yel, grn, blu = (236, 200, 38), (38, 150, 82), (32, 84, 172)
    ncol = 64
    cw = S // ncol
    lower_px = int(S * 0.4)
    rows_lo, rows_up = 14, 22
    rows = []       # (y0, y1, hfrac, tier)
    for r in range(rows_up):
        y0 = int(r * (S - lower_px) / rows_up)
        y1 = int((r + 1) * (S - lower_px) / rows_up)
        rows.append((y0, y1, 1 - r / rows_up, 1, rows_up - 1 - r))
    for r in range(rows_lo):
        y0 = S - lower_px + int(r * lower_px / rows_lo)
        y1 = S - lower_px + int((r + 1) * lower_px / rows_lo)
        rows.append((y0, y1, 1 - r / rows_lo, 0, rows_lo - 1 - r))
    for (y0, y1, hf, tier, rfrombot) in rows:
        rh = y1 - y0
        for c in range(ncol):
            aisle = (c % 16) == 0
            vom = False
            cc = c % 32
            if tier == 1 and rfrombot in (2, 3, 4, 5) and cc in (30, 31, 0, 1, 2):
                vom = True
            if tier == 0 and rfrombot in (rows_lo - 1, rows_lo - 2, rows_lo - 3) and (c % 32) in (15, 16, 17):
                vom = True
            x0 = c * cw
            if vom:
                edge = (cc in (30, 2)) if tier == 1 else ((c % 32) in (15, 17))
                img[y0:y1, x0:x0 + cw] = (38, 36, 36)
                if edge:
                    xs = x0 if (cc == 30 or (c % 32) == 15) else x0 + cw - 4
                    img[y0:y1, xs:xs + 4] = (178, 175, 168)
                continue
            if aisle:
                # stair treads
                img[y0:y1, x0:x0 + cw] = (170, 167, 160)
                img[y0 + rh // 2:y0 + rh // 2 + 2, x0:x0 + cw] = (120, 118, 112)
                img[y1 - 2:y1, x0:x0 + cw] = (120, 118, 112)
                continue
            if tier == 1:
                pb = np.clip((hf - 0.42) / 0.3, 0, 1) * 0.92 + 0.04
            else:
                pb = 0.06
            r_ = rng.random()
            if r_ < pb:
                cl = blu
            else:
                cl = yel if rng.random() < 0.55 else grn
            cl = np.array(cl) * (0.9 + 0.2 * rng.random())
            sy0 = y0 + 2
            sy1 = y0 + int(rh * 0.72)
            img[sy0:sy1, x0 + 2:x0 + cw - 2] = cl
            img[sy0:sy0 + max(2, rh // 6), x0 + 2:x0 + cw - 2] = np.clip(cl * 1.18 + 10, 0, 255)   # backrest top
            img[sy1 - 2:sy1, x0 + 2:x0 + cw - 2] = cl * 0.7
        img[y1 - 2:y1, :] *= 0.8
    # vomitory head walls above upper-tier openings
    save_jpg(img, 'seats.jpg', 86)


# ---------------------------------------------------------------- pitch
def pitch():
    # covers 111 x 74 m (3 m grass margin). Image x = along pitch length.
    ppm = 1024 / 111.0
    W, H = 1024, int(round(74 * ppm))
    SS = 3
    yy, xx = np.mgrid[0:H, 0:W]
    X = xx / ppm - 55.5
    Y = yy / ppm - 37
    band = np.floor((X + 52.5) / (105 / 18.)).astype(int)
    g1, g2 = np.array((62, 132, 52.)), np.array((84, 156, 62.))
    img = np.where((band % 2 == 0)[..., None], g1, g2)
    cross = np.floor((Y + 34) / (68 / 12.)).astype(int) % 2
    img = img * (0.97 + 0.06 * cross)[..., None]
    n = tnoise(H, W, 1.4, 15)
    img *= (0.9 + 0.2 * n)[..., None]
    fine = np.random.default_rng(16).random((H, W))
    img *= (0.95 + 0.1 * fine)[..., None]
    L = Image.new('L', (W * SS, H * SS), 0)
    d = ImageDraw.Draw(L)
    s = ppm * SS
    lw = max(2, int(round(0.14 * s)))

    def P(x, y):
        return ((x + 55.5) * s, (y + 37) * s)

    def rect(x0, y0, x1, y1):
        d.rectangle([P(x0, y0), P(x1, y1)], outline=255, width=lw)

    def circ(cx, cy, r, a0=0, a1=360):
        d.arc([P(cx - r, cy - r), P(cx + r, cy + r)], a0, a1, fill=255, width=lw)

    rect(-52.5, -34, 52.5, 34)
    d.line([P(0, -34), P(0, 34)], fill=255, width=lw)
    circ(0, 0, 9.15)
    d.ellipse([P(-.3, -.3), P(.3, .3)], fill=255)
    for sgn in (-1, 1):
        gx = sgn * 52.5
        rect(min(gx, gx - sgn * 16.5), -20.16, max(gx, gx - sgn * 16.5), 20.16)
        rect(min(gx, gx - sgn * 5.5), -9.16, max(gx, gx - sgn * 5.5), 9.16)
        px = gx - sgn * 11
        d.ellipse([P(px - .25, -.25), P(px + .25, .25)], fill=255)
        ang = math.degrees(math.acos(5.5 / 9.15))
        if sgn == 1:
            circ(px, 0, 9.15, 180 - ang, 180 + ang)
        else:
            circ(px, 0, 9.15, -ang, ang)
    for cx, cy, a0 in ((-52.5, -34, 0), (52.5, -34, 90), (52.5, 34, 180), (-52.5, 34, 270)):
        circ(cx, cy, 1, a0, a0 + 90)
    m = np.asarray(L.resize((W, H), Image.LANCZOS)) / 255.
    img = img * (1 - m[..., None]) + np.array((238, 240, 232.)) * m[..., None]
    save_jpg(img, 'pitch.jpg', 88)


def track():
    S = 512
    n = tnoise(S, S, 1.5, 17)
    f = np.random.default_rng(18).random((S, S))
    img = col((178, 78, 56), S, S) * (0.9 + 0.14 * n + 0.08 * f)[..., None]
    yy, xx = np.mgrid[0:S, 0:S]
    v = yy / S * 8
    line = np.abs(v - np.round(v)) < 0.028
    img[line] = (236, 232, 224)
    save_jpg(img, 'track.jpg', 88)
    S = 256
    n = tnoise(S, S, 1.5, 19)
    f = np.random.default_rng(20).random((S, S))
    save_jpg(col((178, 78, 56), S, S) * (0.9 + 0.14 * n + 0.08 * f)[..., None], 'rubber.jpg', 85)


def paving():
    S = 512
    n = tnoise(S, S, 1.7, 21)
    img = col((196, 186, 168), S, S) * (0.88 + 0.2 * n)[..., None]
    rng = np.random.default_rng(22)
    k = 8                      # 0.5 m pavers when tile = 4 m
    c = S // k
    t = 0.93 + 0.14 * rng.random((k, k))
    img *= np.kron(t, np.ones((c, c)))[..., None]
    yy, xx = np.mgrid[0:S, 0:S]
    img[((yy % c) < 2) | ((xx % c) < 2)] *= 0.78
    # darker banding course every tile
    img[(yy % S) < c] *= 0.86
    save_jpg(img, 'paving.jpg', 85)


def kerb():
    W, H = 128, 32
    img = col((236, 236, 230), H, W)
    img[:, W // 2:] = (30, 30, 32)
    img *= (0.9 + 0.2 * tnoise(H, W, 1.2, 23))[..., None]
    save_jpg(img, 'kerb.jpg', 85)


def metal():
    S = 256
    rng = np.random.default_rng(24)
    streak = wrap_blur(rng.random((S, S)), 0.5)
    streak = np.repeat(streak[:, :1], S, 1) * .5 + streak * .5
    img = col((74, 76, 80), S, S) * (0.85 + 0.3 * streak)[..., None] * (0.92 + 0.16 * tnoise(S, S, 1.6, 25))[..., None]
    save_jpg(img, 'metal.jpg', 84)
    # light champagne/steel metal for poles, mullions, fascias
    img = col((196, 178, 146), S, S) * (0.9 + 0.2 * streak)[..., None] * (0.94 + 0.12 * tnoise(S, S, 1.6, 26))[..., None]
    save_jpg(img, 'metal_light.jpg', 84)


def flags():
    W, H = 256, 64     # 4 swatches: blue, yellow, green, white
    img = np.zeros((H, W, 3))
    cols = [(0, 112, 200), (250, 210, 30), (32, 140, 70), (240, 240, 236)]
    for i, c in enumerate(cols):
        img[:, i * 64:(i + 1) * 64] = c
    yy, xx = np.mgrid[0:H, 0:W]
    img *= (0.9 + 0.1 * np.sin((xx % 64) / 64 * math.pi * 4 + yy / 20.))[..., None]
    save_jpg(img, 'flags.jpg', 88)


def seam():
    S = 512
    n = tnoise(S, S, 1.7, 27)
    img = col((172, 170, 164), S, S) * (0.9 + 0.16 * n)[..., None]
    yy, xx = np.mgrid[0:S, 0:S]
    u = (xx % 64) / 64.
    img[u < 0.06] *= 1.18
    img[(u >= 0.06) & (u < 0.14)] *= 0.72
    img[(yy % 256) < 2] *= 0.85
    save_jpg(img, 'seam.jpg', 85)
    h = np.where(u < 0.1, 1.0, 0.0)
    save_jpg(normal_from_height(wrap_blur(h, 1.5), 3.0), 'seam_n.jpg', 88)


def screenboard():
    S = 128
    yy, xx = np.mgrid[0:S, 0:S]
    img = col((16, 18, 24), S, S)
    img[((yy % 16) < 1) | ((xx % 16) < 1)] = (8, 9, 12)
    img *= (0.9 + 0.2 * tnoise(S, S, 1.5, 28))[..., None]
    save_jpg(img, 'board.jpg', 85)


if __name__ == '__main__':
    for f in (screen, innerwall, roof, truss, stone, concrete, glazing, seats, pitch, track,
              paving, kerb, metal, flags, seam, screenboard):
        f()
    for n in sorted(os.listdir(OUT)):
        print(n, os.path.getsize(os.path.join(OUT, n)) // 1024, 'KB')
