"""Generates every surface texture the arena uses, into public/textures. All of them tile seamlessly.
Each material gets a colour map, a normal map (surface relief) and a roughness map (where it is shiny or dull).
Colour maps are near-neutral so the same texture can be tinted to any colour by the material that uses it.
Run with: ~/.blender-mcp/venv/bin/python scripts/make_textures.py
"""
import os, numpy as np
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "..", "public", "textures")
os.makedirs(OUT, exist_ok=True)

def noise(n, beta, seed, sx=1.0, sy=1.0, m=None):
    """Seamless noise in 0..1. Higher beta = smoother, larger blotches. sx/sy > 1 stretch features along that axis."""
    m = m or n
    w = np.random.default_rng(seed).standard_normal((m, n))
    fy = np.fft.fftfreq(m)[:, None] * sy * m; fx = np.fft.fftfreq(n)[None, :] * sx * n
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    out = np.real(np.fft.ifft2(np.fft.fft2(w) / f ** (beta / 2)))
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / (hi - lo), 0, 1)

def normal_map(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength; dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h); l = np.sqrt(dx * dx + dy * dy + nz * nz)
    return np.dstack([(-dx / l) * 0.5 + 0.5, (dy / l) * 0.5 + 0.5, (nz / l) * 0.5 + 0.5])

def save(name, color, height=None, rough=None, strength=4.0, q=80, aux=1.0):
    # File size matters: these are downloaded before the arena can be shown. Relief and shine maps tolerate more
    # compression than colour, and `aux` shrinks them further for large textures.
    def img(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    def small(im): return im if aux == 1.0 else im.resize((int(im.width * aux), int(im.height * aux)), Image.LANCZOS)
    if color.ndim == 2: color = np.dstack([color] * 3)
    img(color).save(os.path.join(OUT, name + "_color.jpg"), quality=q, optimize=True)
    if height is not None: small(img(normal_map(height, strength))).save(os.path.join(OUT, name + "_normal.jpg"), quality=76, optimize=True)
    if rough is not None: small(img(rough)).save(os.path.join(OUT, name + "_rough.jpg"), quality=68, optimize=True)
    print(" ", name, color.shape[1], "x", color.shape[0])

N = 512
# ---- concrete (4 m): mottled, with pores and faint formwork lines. Neutral, tinted by the material.
a, b = noise(N, 2.4, 1), noise(N, 1.0, 2)
pores = noise(N, 0.1, 3) > 0.988
c = 0.84 + 0.13 * (a - 0.5) + 0.07 * (b - 0.5); c[pores] *= 0.55
c[:, ::N // 4] *= 0.93
save("concrete", c, c - pores * 0.4, 0.72 + 0.2 * (b - 0.5), 3.0)

# ---- arena floor (6 m): polished black concrete. Dark, with trowel marks, fine aggregate and joints; shine varies.
F = 1024
a, b, s = noise(F, 2.8, 4), noise(F, 1.2, 5), noise(F, 0.0, 6)
v = 0.030 + 0.045 * a + 0.02 * b + (s > 0.992) * 0.07
for k in (0, F // 2): v[k:k + 2, :] *= 0.4; v[:, k:k + 2] *= 0.4
save("floor", np.dstack([v * 0.96, v, v * 1.03]), a * 0.3 + (s > 0.992) * 0.1, 0.16 + 0.34 * noise(F, 2.2, 7) + 0.06 * b, 1.2, q=84, aux=0.5)

# ---- paving (2.4 m): stone pavers 60 x 30 cm in running bond, each slightly different, dark joints.
P = 1024; rows, cols = 8, 4
yy, xx = np.mgrid[0:P, 0:P]
row = yy // (P // rows); xo = (xx + (row % 2) * (P // cols // 2)) % P; col = xo // (P // cols)
tone = np.random.default_rng(8).uniform(-0.07, 0.07, (rows, cols))[row, col]
joint = ((yy % (P // rows)) < 4) | ((xo % (P // cols)) < 4)
g = noise(P, 1.4, 9)
c = 0.84 + tone + 0.08 * (g - 0.5); c[joint] = 0.52
save("paving", c, np.where(joint, 0.0, 0.6 + 0.2 * g), 0.8 + 0.12 * (g - 0.5), 5.0, aux=0.5)

# ---- asphalt (3 m): coarse grain with pale aggregate
a, b = noise(N, 0.5, 10), noise(N, 2.2, 11)
c = 0.62 + 0.3 * (a - 0.5) + 0.12 * (b - 0.5) + (noise(N, 0.0, 12) > 0.985) * 0.2
save("asphalt", c, a, 0.9 + 0 * a, 5.0)

# ---- brushed metal (1 m): fine streaks along one direction
s = noise(N, 1.6, 13, sx=60.0)
save("metal", 0.82 + 0.16 * (s - 0.5), s, 0.3 + 0.25 * s, 2.0)

# ---- wood (2 m): planks 12.5 cm wide with end joints, grain and soft growth figure. Neutral: tinted by the material.
W = 1024; pw = W // 16
yy, xx = np.mgrid[0:W, 0:W]; plank = yy // pw
r = np.random.default_rng(14)
tone = r.uniform(-0.09, 0.09, 16)[plank]; shift = r.integers(0, W, 16)[plank]
grain = noise(W, 1.8, 15, sx=28.0); fig = noise(W, 2.6, 16, sx=6.0)
gx = np.take_along_axis(grain, (xx + shift) % W, axis=1)
rings = 0.5 + 0.5 * np.sin((fig * 9 + yy / pw * 0.6) * 6.283)
c = 0.86 + tone + 0.12 * (gx - 0.5) + 0.05 * (rings - 0.5)
seam = (yy % pw) < 2; ends = ((xx + shift) % (W // 2)) < 2
c[seam | ends] *= 0.6
save("wood", np.dstack([c, c * 0.97, c * 0.93]), np.where(seam | ends, 0.0, 0.7 + 0.3 * gx), 0.42 + 0.2 * (gx - 0.5), 3.0, aux=0.5)

# ---- moulded plastic (30 cm): nearly flat with a fine orange-peel surface
p = noise(256, 0.8, 17)
save("plastic", 0.97 + 0.03 * p, p, 0.36 + 0.1 * p, 1.0)

# ---- woven fabric / carpet (50 cm)
n = 256; yy, xx = np.mgrid[0:n, 0:n]
weave = 0.5 + 0.25 * np.sin(xx * 6.283 * 32 / n) + 0.25 * np.sin(yy * 6.283 * 32 / n)
f = noise(n, 1.0, 18)
save("fabric", 0.78 + 0.2 * (weave - 0.5) + 0.1 * (f - 0.5), weave, 0.92 + 0 * f, 3.0)

# ---- leather (40 cm): fine creased grain
l = noise(N, 1.3, 19); crease = 1 - np.abs(2 * l - 1) ** 0.6
save("leather", 0.9 + 0.1 * (1 - crease), 1 - crease, 0.45 + 0.2 * crease, 3.5)

# ---- roof membrane (6 m): panels 3 x 1.5 m with seams and fixings, light weathering
R = 1024; yy, xx = np.mgrid[0:R, 0:R]
rw = R // 4; cw = R // 2; rrow = yy // rw; xo = (xx + (rrow % 2) * (cw // 2)) % R
seam = ((yy % rw) < 3) | ((xo % cw) < 3)
dots = (((yy % rw) - rw // 2) ** 2 + ((xo % (cw // 4)) - cw // 8) ** 2) < 14
w = noise(R, 2.4, 20)
c = 0.93 + 0.07 * (w - 0.5); c[seam] = 0.74; c[dots] = 0.55
save("roof", c, np.where(seam | dots, 0.0, 1.0), 0.8 + 0.1 * w, 4.0, aux=0.5)

# ---- grass (8 m)
a, b = noise(N, 1.0, 21), noise(N, 2.6, 22)
save("grass", 0.74 + 0.3 * (a - 0.5) + 0.2 * (b - 0.5), a, 0.95 + 0 * a, 4.0)

# ---- LED screen (50 cm): the dark grid between the pixels
n = 256; yy, xx = np.mgrid[0:n, 0:n]; cell = 8
led = np.where(((xx % cell) < 2) | ((yy % cell) < 2), 0.25, 1.0)
save("led", led, None, None)

# ---- basketball courts, 32 x 19 m at 64 px per metre: FIBA markings on maple strip flooring, in two paint schemes
PX = 64; CW, CH = 32 * PX, 19 * PX
m = lambda v: int(round(v * PX))
def make_court(name, WOOD, KEY, SURROUND, LINE, circle, emblem, lettering=False):
    im = Image.new("RGB", (CW, CH), SURROUND); d = ImageDraw.Draw(im)
    ox, oz, cw, ch = m(2), m(2), m(28), m(15); cy = oz + ch // 2; lw = max(3, round(0.05 * PX))
    d.rectangle([ox, oz, ox + cw, oz + ch], fill=WOOD)
    def arc(cx, cyy, rad, a0, a1): d.arc([cx - rad, cyy - rad, cx + rad, cyy + rad], a0, a1, fill=LINE, width=lw)
    for side in (0, 1):
        dr = -1 if side else 1; base = ox + cw if side else ox; hoop = base + dr * m(1.575)
        kx0, kx1 = sorted([base, base + dr * m(5.8)])
        d.rectangle([kx0, cy - m(2.45), kx1, cy + m(2.45)], fill=KEY, outline=LINE, width=lw)
        arc(base + dr * m(5.8), cy, m(1.8), *((90, 270) if side else (-90, 90)))
        dz = m(7.5 - 0.9); dxa = int(np.sqrt(m(6.75) ** 2 - dz ** 2)); ang = np.degrees(np.arcsin(dz / m(6.75)))
        for s2 in (-1, 1): d.line([base, cy + s2 * dz, hoop + dr * dxa, cy + s2 * dz], fill=LINE, width=lw)
        arc(hoop, cy, m(6.75), *((180 - ang, 180 + ang) if side else (-ang, ang)))
        arc(hoop, cy, m(1.25), *((90, 270) if side else (-90, 90)))
        for s2 in (-1, 1):
            d.line([hoop, cy + s2 * m(1.25), hoop - dr * m(0.375), cy + s2 * m(1.25)], fill=LINE, width=lw)
            for q in (1.75, 2.6, 3.0, 3.85, 4.7): d.line([base + dr * m(q), cy + s2 * m(2.45), base + dr * m(q), cy + s2 * m(2.57)], fill=LINE, width=lw)
            d.line([base + dr * m(8.325), cy + s2 * m(7.5), base + dr * m(8.325), cy + s2 * m(7.66)], fill=LINE, width=lw)
    d.rectangle([ox, oz, ox + cw, oz + ch], outline=LINE, width=lw)
    d.line([ox + cw // 2, oz, ox + cw // 2, oz + ch], fill=LINE, width=lw)
    if circle: arc(ox + cw // 2, cy, m(1.8), 0, 360)
    painted = np.zeros((CH, CW), dtype=bool)
    if emblem:   # a neutral BK Arena roundel in the centre (a league's own logo can be laid over it: see center_logo.png)
        cx0 = ox + cw // 2; R0 = m(2.6)
        d.ellipse([cx0 - R0, cy - R0, cx0 + R0, cy + R0], fill=(0xf4, 0xf1, 0xe6), outline=LINE, width=lw * 2)
        for (a0, a1, colr) in ((200, 340, (0x00, 0xa1, 0xde)), (20, 90, (0xfa, 0xd2, 0x01)), (90, 160, (0x20, 0x60, 0x3d))):
            d.arc([cx0 - R0 + m(0.25), cy - R0 + m(0.25), cx0 + R0 - m(0.25), cy + R0 - m(0.25)], a0, a1, fill=colr, width=m(0.38))
        try:
            from PIL import ImageFont
            f1 = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", m(1.25)); f2 = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", m(0.5))
        except Exception:
            f1 = f2 = None
        if f1:
            d.text((cx0, cy - m(0.25)), "BK", font=f1, fill=(0x12, 0x14, 0x18), anchor="mm"); d.text((cx0, cy + m(0.85)), "ARENA", font=f2, fill=(0x12, 0x14, 0x18), anchor="mm")
        yy, xx = np.mgrid[0:CH, 0:CW]; painted = (xx - cx0) ** 2 + (yy - cy) ** 2 < R0 ** 2
    if lettering:                                                     # venue name along both sidelines
        try:
            from PIL import ImageFont
            cx0 = ox + cw // 2; fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", m(0.8))
        except Exception:
            fb = None
        if fb:
            for (txt, yy0, rot) in (("BK ARENA  ·  KIGALI", oz - m(1.0), 0), ("BK ARENA  ·  KIGALI", oz + ch + m(1.0), 180)):
                band = Image.new("RGBA", (m(14), m(1.2)), (0, 0, 0, 0)); ImageDraw.Draw(band).text((m(7), m(0.6)), txt, font=fb, fill=(255, 255, 255, 255), anchor="mm")
                band = band.rotate(rot); im.paste(band, (cx0 - m(7), yy0 - m(0.6)), band)
    base_rgb = np.asarray(im).astype(int)
    court = base_rgb.astype(np.float64) / 255
    yy, xx = np.mgrid[0:CH, 0:CW]; sw = 6; strip = yy // sw
    r = np.random.default_rng(23); nstrip = CH // sw + 1
    tone = r.uniform(-0.06, 0.06, nstrip)[strip]; shift = r.integers(0, 4096, nstrip)[strip]
    g = noise(4096, 1.8, 24, sx=30.0, m=64); gx = g[yy % 64, (xx + shift) % 4096]
    seam = ((yy % sw) == 0) | (((xx + shift) % m(1.6)) < 2)
    is_wood = np.all(np.abs(base_rgb - np.array(WOOD)) < 4, axis=2)
    shade = 1 + tone + 0.1 * (gx - 0.5); shade[seam] *= 0.82
    shade = np.where(is_wood, shade, 1 + (shade - 1) * 0.45)          # paint lets a little of the boards show through
    save(name, court * shade[..., None], np.where(seam, 0.0, 1.0), np.where(is_wood, 0.24 + 0.08 * gx, 0.36), 1.5, q=82, aux=0.5)
make_court("court", (0xd3, 0xb0, 0x5c), (0x1b, 0x98, 0xa8), (0x1b, 0x98, 0xa8), (0xf4, 0xf6, 0xf2), True, False)       # teal scheme
make_court("courtb", (0xdc, 0xbd, 0x8c), (0xf0, 0xc2, 0x1e), (0x1a, 0x8a, 0x4a), (0x1c, 0x1c, 0x1e), True, False, lettering=True)   # league scheme: plain centre circle, no logo

# ---- road (12 m of a 10 m wide two-way road): asphalt with solid edge lines and a dashed centre line. u runs along the road.
RW = 512; yy, xx = np.mgrid[0:RW, 0:RW]
a = noise(RW, 0.5, 30); bq = noise(RW, 2.2, 31)
road = 0.34 + 0.16 * (a - 0.5) + 0.07 * (bq - 0.5)
v = yy / RW; u = xx / RW
edge = (np.abs(v - 0.045) < 0.008) | (np.abs(v - 0.955) < 0.008)
dash = (np.abs(v - 0.5) < 0.008) & ((u % 0.5) < 0.25)
tracks = np.exp(-((v - 0.27) / 0.05) ** 2) + np.exp(-((v - 0.73) / 0.05) ** 2)
road = road * (1 - 0.1 * tracks); line = edge | dash
rc = np.dstack([road, road, road * 1.02]); rc[line] = 0.9 - 0.12 * a[line, None]
save("road", rc, a * 0.7 + line * 0.3, np.where(line, 0.6, 0.92), 4.0)

# ---- car park (one bay wide = 2.75 m, one row pitch = 16 m): bays either side of a centre line, driving aisle between rows
PW, PH = 128, 1024; yy, xx = np.mgrid[0:PH, 0:PW]
a = noise(PH, 0.5, 32)[:, :PW]
lot = 0.42 + 0.14 * (a - 0.5)
v = yy / PH; u = xx / PW
row_line = np.abs(v - 0.5) < 0.0045
divider = ((u < 0.03) | (u > 0.97)) & (np.abs(v - 0.5) < 0.325)
line = row_line | divider
pc = np.dstack([lot, lot, lot]); pc[line] = 0.88
stain = np.exp(-(((v - 0.5 - 0.17) / 0.06) ** 2)) + np.exp(-(((v - 0.5 + 0.17) / 0.06) ** 2))
pc *= (1 - 0.08 * stain * (np.abs(u - 0.5) < 0.2))[..., None]
save("parking", pc, a, np.where(line, 0.6, 0.92), 4.0)

# ---- sky (360 degree panorama, 2048 x 1024): hazy blue with broken cumulus, paler towards the horizon
SW, SH = 2048, 1024
n1 = noise(SW, 2.7, 25); n2 = noise(SW, 1.6, 26)
yy = np.arange(SH)[:, None]; e = np.clip(1 - yy / (SH / 2), 0, 1)                 # elevation: 1 at the top, 0 at the horizon
rows = np.clip((1 - e[:, 0] ** 0.55) * (SW // 2 - 1), 0, SW - 1).astype(int)       # flatten the clouds towards the horizon
field = (0.72 * n1 + 0.28 * n2)[rows, :]
cover = np.clip((field - 0.5) / 0.2, 0, 1) ** 1.3 * np.clip(e * 6, 0, 1) * (1 - 0.45 * e)
under = np.clip((np.roll(field, 10, 0) - field) * 5, -0.25, 0.25)
zen, hor = np.array([0x5c, 0x92, 0xb8]) / 255, np.array([0xcf, 0xde, 0xe1]) / 255
sky = hor + (zen - hor) * (e ** 0.7)[..., None]
cloud = np.clip(0.97 - 0.3 * np.clip(under, 0, 1)[..., None] + np.zeros(3), 0, 1) * np.array([1.0, 1.0, 0.99])
img = sky * (1 - cover[..., None]) + cloud * cover[..., None]
ground = np.array([0xb4, 0xbd, 0xa6]) / 255
below = (yy >= SH // 2)[:, 0]
img[below] = hor + (ground - hor) * np.clip((yy[below] - SH / 2) / 60, 0, 1)[..., None]
Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, "sky.jpg"), quality=80, optimize=True)
print("  sky 2048 x 1024")

lat = os.path.join(os.path.dirname(__file__), "..", "blender", "tex", "lattice.png")
if os.path.exists(lat): Image.open(lat).convert("RGB").save(os.path.join(OUT, "lattice_color.jpg"), quality=82, optimize=True); print("  lattice")
