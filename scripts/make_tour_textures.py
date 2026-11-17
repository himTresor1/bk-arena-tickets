"""Textures for the district in the sports-complex tour, into public/textures/tour.
House and office fronts are sheets of four pictures side by side (each one wall module wide and one floor high);
the rest tile or cover one pitch each. Colours are light so each building can be tinted.
Run with: ~/.blender-mcp/venv/bin/python scripts/make_tour_textures.py
"""
import math, os, numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "textures", "tour")
os.makedirs(OUT, exist_ok=True)


def noise(n, beta, seed, m=None, sx=1.0, sy=1.0):
    m = m or n
    w = np.random.default_rng(seed).standard_normal((m, n))
    fy = np.fft.fftfreq(m)[:, None] * sy * m; fx = np.fft.fftfreq(n)[None, :] * sx * n
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    out = np.real(np.fft.ifft2(np.fft.fft2(w) / f ** (beta / 2)))
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / (hi - lo), 0, 1)

def arr(img): return np.asarray(img).astype(np.float32) / 255
def img(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
def save(name, a, q=84): (a if isinstance(a, Image.Image) else img(a)).convert("RGB").save(os.path.join(OUT, name), quality=q)


# ------------------------------------------------------------------ house fronts: window, plain wall, door, wide window
T = 512
def plaster(seed, w=T, h=T):
    base = 0.90 + (noise(w, 2.2, seed, h) - 0.5) * 0.10 + (noise(w, 0.6, seed + 1, h) - 0.5) * 0.05
    streak = noise(w, 1.6, seed + 2, h, sx=6.0, sy=0.25)                     # rain streaks run down the wall
    y = np.linspace(0, 1, h)[:, None]
    base -= np.clip(streak - 0.55, 0, 1) * 0.25 * (1 - y) ** 0.6
    base *= 1 - 0.22 * np.clip(1 - y / 0.07, 0, 1)                            # shadow under the eave
    return np.dstack([base, base * 0.985, base * 0.96])

def glass(d, box, seed, lit=False):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    n = noise(64, 2.5, seed); g = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    refl = np.asarray(img(n).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
    r = 0.16 + 0.22 * (1 - g) * refl + (0.25 if lit else 0); gch = 0.22 + 0.26 * (1 - g) * refl + (0.2 if lit else 0); b = 0.29 + 0.30 * (1 - g) * refl + (0.1 if lit else 0)
    d.paste(img(np.dstack([r, gch, b])), (x0, y0))

def house_sheet():
    sheet = Image.new("RGB", (T * 4, T))
    for k in range(4):
        tile = img(plaster(20 + k * 5)); d = ImageDraw.Draw(tile); px = T / 3.2; py = T / 3.0; Y = lambda m: int(T - m * py)
        # painted plinth along the foot of the wall
        a = arr(tile); a[Y(0.5):, :, :] *= np.array([0.66, 0.62, 0.6]); a[Y(0.5) - 2:Y(0.5), :, :] *= 0.8; tile = img(a); d = ImageDraw.Draw(tile)
        if k in (0, 3):
            ww, wh, sill = (1.25, 1.25, 0.95) if k == 0 else (1.9, 1.15, 1.0)
            x0, x1 = int((1.6 - ww / 2) * px), int((1.6 + ww / 2) * px); y0, y1 = Y(sill + wh), Y(sill)
            d.rectangle([x0 - 9, y0 - 9, x1 + 9, y1 + 5], fill=(214, 208, 196))            # painted surround
            d.rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], fill=(58, 52, 48))               # steel frame
            glass(tile, (x0, y0, x1, y1), 40 + k); d = ImageDraw.Draw(tile)
            panes = 2 if k == 0 else 3
            for i in range(1, panes): d.line([(x0 + (x1 - x0) * i / panes, y0), (x0 + (x1 - x0) * i / panes, y1)], fill=(58, 52, 48), width=4)
            d.line([(x0, y0 + (y1 - y0) * 0.28), (x1, y0 + (y1 - y0) * 0.28)], fill=(58, 52, 48), width=3)
            for i in range(1, 7): d.line([(x0, y0 + (y1 - y0) * i / 7), (x1, y0 + (y1 - y0) * i / 7)], fill=(96, 90, 84), width=1)  # burglar bars
            d.rectangle([x0 - 14, y1 + 5, x1 + 14, y1 + 12], fill=(226, 221, 210)); d.rectangle([x0 - 14, y1 + 12, x1 + 14, y1 + 20], fill=(150, 142, 130))  # sill and its shadow
        elif k == 2:
            x0, x1 = int((1.6 - 0.5) * px), int((1.6 + 0.5) * px); y0, y1 = Y(2.2), Y(0.12)
            d.rectangle([x0 - 10, y0 - 10, x1 + 10, y1], fill=(210, 204, 192))
            d.rectangle([x0, y0, x1, y1], fill=(92, 70, 56))
            for (a0, b0, a1, b1) in ((0.1, 0.06, 0.9, 0.3), (0.1, 0.36, 0.9, 0.62), (0.1, 0.68, 0.9, 0.95)):
                d.rectangle([x0 + (x1 - x0) * a0, y0 + (y1 - y0) * b0, x0 + (x1 - x0) * a1, y0 + (y1 - y0) * b1], outline=(64, 48, 38), width=3)
            d.ellipse([x1 - 22, (y0 + y1) / 2 - 6, x1 - 10, (y0 + y1) / 2 + 6], fill=(190, 170, 110))
            d.rectangle([x0 - 26, y1, x1 + 26, T], fill=(150, 146, 138)); d.line([(x0 - 26, y1), (x1 + 26, y1)], fill=(190, 186, 178), width=3)   # step
            d.rectangle([x0 - 30, y0 - 34, x1 + 30, y0 - 22], fill=(120, 74, 58)); d.rectangle([x0 - 30, y0 - 22, x1 + 30, y0 - 10], fill=(140, 134, 124))  # small canopy and shadow
        else:
            x0 = int(1.35 * px); y0 = Y(2.6)
            for i in range(4):
                for j in range(2): d.rectangle([x0 + i * 20, y0 + j * 20, x0 + i * 20 + 13, y0 + j * 20 + 13], fill=(92, 86, 80))   # air brick
        sheet.paste(tile, (k * T, 0))
    save("house.jpg", sheet, 86)

def office_sheet():
    sheet = Image.new("RGB", (T * 4, T))
    for k in range(4):
        tile = img(plaster(60 + k * 3)); d = ImageDraw.Draw(tile); py = T / 3.4; Y = lambda m: int(T - m * py)
        d.rectangle([0, 0, T, 16], fill=(196, 192, 184)); d.rectangle([0, 16, T, 20], fill=(150, 146, 140))      # slab edge
        if k == 0:    # ribbon glazing over a panel
            glass(tile, (0, Y(2.95), T, Y(0.95)), 71); d = ImageDraw.Draw(tile)
            for x in (0, T // 2, T - 5): d.rectangle([x, Y(2.95), x + 5, Y(0.95)], fill=(70, 74, 78))
            d.rectangle([0, Y(0.95), T, Y(0.9)], fill=(70, 74, 78)); d.rectangle([0, Y(2.0), T, Y(1.96)], fill=(70, 74, 78))
        elif k == 1:  # shopfront
            d.rectangle([0, Y(3.2), T, Y(2.6)], fill=(198, 186, 160)); d.rectangle([0, Y(2.6), T, Y(2.55)], fill=(120, 112, 100))
            glass(tile, (14, Y(2.5), T - 14, Y(0.1)), 72, lit=True); d = ImageDraw.Draw(tile)
            for x in (14, T // 3, 2 * T // 3, T - 20): d.rectangle([x, Y(2.5), x + 6, Y(0.1)], fill=(52, 54, 58))
            d.rectangle([14, Y(2.05), T - 14, Y(2.0)], fill=(52, 54, 58)); d.rectangle([0, Y(0.1), T, T], fill=(132, 128, 122))
        elif k == 3:  # two separate windows
            for cx in (0.27, 0.73):
                x0, x1 = int(T * cx - 78), int(T * cx + 78); y0, y1 = Y(2.5), Y(1.0)
                d.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], fill=(70, 74, 78)); glass(tile, (x0, y0, x1, y1), 73 + int(cx * 10)); d = ImageDraw.Draw(tile)
                d.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=(70, 74, 78), width=4)
                d.rectangle([x0 - 10, y1 + 4, x1 + 10, y1 + 12], fill=(222, 218, 208))
        else:
            for x in (T // 2,): d.line([(x, 20), (x, T)], fill=(206, 200, 190), width=2)
        sheet.paste(tile, (k * T, 0))
    save("office.jpg", sheet, 86)


# ------------------------------------------------------------------ corrugated iron roofing, 1.2 m wide by 2.4 m up the slope
def sheet_roof():
    w, h = 256, 512; x = np.arange(w)[None, :]; ridge = np.cos(x / w * math.tau * 16)
    base = 0.80 + 0.10 * ridge + (noise(w, 2.0, 3, h, sx=0.3, sy=3.0) - 0.5) * 0.16 + (noise(w, 0.8, 4, h) - 0.5) * 0.05
    base = base * np.ones((h, 1)); base[-10:, :] *= 0.78; base[:4, :] *= 0.9                                    # where one sheet laps the next
    rust = np.clip(noise(w, 2.6, 5, h) - 0.72, 0, 1) * 2.2
    col = np.dstack([base, base - rust * 0.10, base - rust * 0.22])
    save("sheet.jpg", col, 84)
    hgt = (ridge * 0.5 + 0.5) * np.ones((h, 1)); dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 3.0
    l = np.sqrt(dx * dx + 1); save("sheet_normal.jpg", np.dstack([-dx / l * 0.5 + 0.5, np.full_like(dx, 0.5), 1 / l * 0.5 + 0.5]), 84)


# ------------------------------------------------------------------ open ground between the houses: red earth with grass
def ground():
    n = 1024
    patch = noise(n, 2.4, 9) * 0.65 + noise(n, 1.4, 10) * 0.35; g = np.clip((patch - 0.40) * 5, 0, 1)[..., None]
    fine = (noise(n, 0.7, 11) - 0.5)[..., None]; mid = (noise(n, 1.8, 12) - 0.5)[..., None]
    earth = np.array([0.62, 0.46, 0.35]) * (1 + mid * 0.22 + fine * 0.16)
    grass = np.array([0.40, 0.49, 0.26]) * (1 + mid * 0.35 + fine * 0.3)
    save("ground.jpg", earth * (1 - g) + grass * g, 80)


def kerb():
    a = np.ones((32, 128, 3)) * 0.9; a[:, :64] = 0.13
    a *= (0.9 + (noise(128, 1.2, 14, 32) - 0.5)[..., None] * 0.25)
    save("kerb.jpg", a, 85)

def track():
    a = np.ones((256, 256, 3)) * np.array([0.66, 0.26, 0.2]) * (0.92 + (noise(256, 0.6, 15) - 0.5)[..., None] * 0.2)
    for k in range(7):
        y = min(253, int(k / 6 * 255)); a[y:y + 3] = 0.93
    save("track.jpg", a, 85)

def turf(w, h, m_per_px_stripe, seed):
    x = np.arange(w)[None, :]; stripe = ((x // m_per_px_stripe) % 2) * 0.09
    g = 0.86 + stripe + (noise(w, 1.0, seed, h) - 0.5) * 0.12
    return np.dstack([g * 0.30, g * 0.56, g * 0.20])

def lines(size, draw, width=3):
    im = Image.new("L", size, 0); draw(ImageDraw.Draw(im), width); return (np.asarray(im.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255)[..., None]

def soccer():
    w, h = 1024, 662; s = w / 111.3; cx, cy = w / 2, h / 2; X = lambda m: cx + m * s; Yc = lambda m: cy + m * s
    def draw(d, lw):
        d.rectangle([X(-52.5), Yc(-34), X(52.5), Yc(34)], outline=255, width=lw); d.line([(cx, Yc(-34)), (cx, Yc(34))], fill=255, width=lw)
        d.ellipse([X(-9.15), Yc(-9.15), X(9.15), Yc(9.15)], outline=255, width=lw); d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=255)
        for sg in (-1, 1):
            e = X(sg * 52.5); a, b = sorted((e, X(sg * 36))); d.rectangle([a, Yc(-20.16), b, Yc(20.16)], outline=255, width=lw)
            a, b = sorted((e, X(sg * 47))); d.rectangle([a, Yc(-9.16), b, Yc(9.16)], outline=255, width=lw)
            px_ = X(sg * 41.5); d.ellipse([px_ - 2, cy - 2, px_ + 2, cy + 2], fill=255)
            d.arc([px_ - 9.15 * s, cy - 9.15 * s, px_ + 9.15 * s, cy + 9.15 * s], 127 if sg < 0 else 307, 233 if sg < 0 else 53, fill=255, width=lw) if False else None
    L = lines((w, h), draw); a = turf(w, h, int(5.5 * s), 16)
    save("soccer.jpg", a * (1 - L) + L * 0.95, 84)

def five():
    w, h = 512, 264; s = w / 34.0; cx, cy = w / 2, h / 2
    def draw(d, lw):
        d.rectangle([cx - 15 * s, cy - 7.6 * s, cx + 15 * s, cy + 7.6 * s], outline=255, width=lw); d.line([(cx, cy - 7.6 * s), (cx, cy + 7.6 * s)], fill=255, width=lw)
        d.ellipse([cx - 2.5 * s, cy - 2.5 * s, cx + 2.5 * s, cy + 2.5 * s], outline=255, width=lw)
        for sg in (-1, 1):
            e = cx + sg * 15 * s; d.pieslice([e - 5 * s, cy - 5 * s, e + 5 * s, cy + 5 * s], 270 if sg < 0 else 90, 90 if sg < 0 else 270, outline=255, width=lw)
    L = lines((w, h), draw, 3); a = turf(w, h, int(3 * s), 17) * np.array([0.9, 1.0, 0.9])
    save("pitch5.jpg", a * (1 - L) + L * 0.95, 84)

def hard_court(name, size, metres, court, colour, surround, draw):
    w, h = size; s = w / metres; cx, cy = w / 2, h / 2
    a = np.ones((h, w, 3)) * np.array(surround) * (0.94 + (noise(w, 0.8, 18, h) - 0.5)[..., None] * 0.14)
    x0, x1, y0, y1 = int(cx - court[0] / 2 * s), int(cx + court[0] / 2 * s), int(cy - court[1] / 2 * s), int(cy + court[1] / 2 * s)
    a[y0:y1, x0:x1] = np.array(colour) * (0.94 + (noise(w, 0.8, 19, h) - 0.5)[y0:y1, x0:x1, None] * 0.14)
    extra = Image.new("RGB", size, 0); mask = Image.new("L", size, 0); L = lines(size, lambda d, lw: draw(d, lw, s, cx, cy, ImageDraw.Draw(extra), ImageDraw.Draw(mask)))
    m = (np.asarray(mask).astype(np.float32) / 255)[..., None]; a = a * (1 - m) + arr(extra) * m
    save(name, a * (1 - L) + L * 0.95, 84)

def tennis_lines(d, lw, s, cx, cy, e, m):
    hw, hh = 23.77 / 2 * s, 10.97 / 2 * s; sh = 8.23 / 2 * s; sv = 6.4 * s
    d.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], outline=255, width=lw); d.line([(cx - hw, cy - sh), (cx + hw, cy - sh)], fill=255, width=lw); d.line([(cx - hw, cy + sh), (cx + hw, cy + sh)], fill=255, width=lw)
    for sg in (-1, 1): d.line([(cx + sg * sv, cy - sh), (cx + sg * sv, cy + sh)], fill=255, width=lw)
    d.line([(cx - sv, cy), (cx + sv, cy)], fill=255, width=lw); d.line([(cx, cy - hh - 6), (cx, cy + hh + 6)], fill=200, width=lw)

def basket_lines(d, lw, s, cx, cy, e, m):
    hw, hh = 14 * s, 7.5 * s
    for sg in (-1, 1):   # painted keys and the circle at the free-throw line
        x_end = cx + sg * hw; a, b = sorted((x_end, x_end - sg * 5.8 * s))
        for dr, fill in ((e, (196, 52, 44)), (m, 255)): dr.rectangle([a, cy - 2.45 * s, b, cy + 2.45 * s], fill=fill)
        d.rectangle([a, cy - 2.45 * s, b, cy + 2.45 * s], outline=255, width=lw)
        fx = x_end - sg * 5.8 * s; d.ellipse([fx - 1.8 * s, cy - 1.8 * s, fx + 1.8 * s, cy + 1.8 * s], outline=255, width=lw)
        hx = x_end - sg * 1.575 * s; d.arc([hx - 6.75 * s, cy - 6.75 * s, hx + 6.75 * s, cy + 6.75 * s], 270 if sg < 0 else 90, 90 if sg < 0 else 270, fill=255, width=lw)
        d.line([(x_end, cy - 6.6 * s), (hx, cy - 6.6 * s)], fill=255, width=lw); d.line([(x_end, cy + 6.6 * s), (hx, cy + 6.6 * s)], fill=255, width=lw)
    for dr, fill in ((e, (232, 190, 52)), (m, 255)): dr.ellipse([cx - 1.8 * s, cy - 1.8 * s, cx + 1.8 * s, cy + 1.8 * s], fill=fill)
    d.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], outline=255, width=lw); d.line([(cx, cy - hh), (cx, cy + hh)], fill=255, width=lw)
    d.ellipse([cx - 1.8 * s, cy - 1.8 * s, cx + 1.8 * s, cy + 1.8 * s], outline=255, width=lw)

def fence():
    n = 128; im = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(-8, 16):
        d.line([(k * 16, 0), (k * 16 + n, n)], fill=(150, 156, 160, 235), width=2); d.line([(k * 16, n), (k * 16 + n, 0)], fill=(150, 156, 160, 235), width=2)
    im.save(os.path.join(OUT, "fence.png"))


house_sheet(); office_sheet(); sheet_roof(); ground(); kerb(); track(); soccer(); five(); fence()
hard_court("tennis.jpg", (512, 354), 24.0, (23.77, 10.97), (0.2, 0.38, 0.62), (0.26, 0.47, 0.33), tennis_lines)
hard_court("basket.jpg", (1024, 534), 46.0, (28.0, 15.0), (0.18, 0.36, 0.66), (0.24, 0.48, 0.42), basket_lines)
print(sorted((f, os.path.getsize(os.path.join(OUT, f)) // 1024) for f in os.listdir(OUT)))
