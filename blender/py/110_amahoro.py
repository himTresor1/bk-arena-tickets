"""Amahoro Stadium (Kigali) exterior + visible bowl -> public/models/amahoro.glb

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/py/110_amahoro.py
Env:  TOUR_RENDER=0   skip preview renders
      TOUR_VIEWS=aerial,top,ground,close,bowl   choose views

Units metres, Z up. Origin = centre of pitch at ground level. +Y = long axis, +X = east.
Textures come from blender/py/109_tour_textures.py (blender/tex/tour/).
"""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
TEX = os.path.join(ROOT, 'blender', 'tex', 'tour')
RENDERS = os.path.join(ROOT, 'blender', 'renders', 'tour')
MODELS = os.path.join(ROOT, 'public', 'models')

# ------------------------------------------------------------------ dimensions
FAC_A, FAC_B, FAC_N = 184.5 / 2, 249.6 / 2, 2.5     # facade footprint superellipse
NP = 180                                             # facade panel columns (2 per bay)
Z_SCREEN0, Z_SCREEN1 = 7.0, 33.0                     # pierced screen
Z_SOFFIT = 6.3
ROWS = 7
OPEN_A, OPEN_B, OPEN_N = 49.0, 83.0, 2.6             # roof opening
Z_ROOF_OUT, Z_ROOF_IN = 33.7, 39.0                   # valley (base) heights
RISE_OUT, RISE_IN = 1.8, 0.9                         # barrel vault rise
FRONT_A, FRONT_B, FRONT_N = 62.0, 97.0, 2.8          # front of lower tier (just outside the track oval)
APRON = 12.0
LEAN = math.tan(math.radians(12.0))                  # the screen leans outward: metres out per metre up
TOPD = (Z_SCREEN1 - Z_SCREEN0) * LEAN                # how far the top of the screen stands outside its foot
NL, NU = 12, 24                                      # seat rows, lower and upper tier
LOW = (0.02, 1.3, 0.36, 6.4)                         # tier: s0, z0, s1, z1 (s = fraction from tier front to back wall)
UPP = (0.325, 9.8, 1.0, 26.0)
AISLE_EVERY, VOM_EVERY, VOM_ROWS, VOM_W = 5, 10, (1, 4), 0.47


def lean(z):
    return (z - Z_SCREEN0) * LEAN


# ------------------------------------------------------------------ helpers
def V3(p, z=0.0):
    return np.array([p[0], p[1], z], float)


def oval(a, b, n, N, M=40000):
    """Superellipse resampled to N points equally spaced by arc length.
    Point i sits at arc fraction (i+1)/N measured CCW from +X, so i = N/2-1 is due west."""
    t = np.linspace(0, 2 * np.pi, M + 1)
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2 / n)
    y = b * np.sign(s) * np.abs(s) ** (2 / n)
    cum = np.concatenate([[0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    L = cum[-1]
    tg = (np.arange(N) + 1) / N * L
    P = np.stack([np.interp(tg, cum, x), np.interp(tg, cum, y)], 1)
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    Nn = np.stack([T[:, 1], -T[:, 0]], 1)
    return P, Nn, L


class Mesh:
    """Accumulates faces for one material."""
    all = {}

    def __init__(self, name, mat, smooth=False, angle=40, tile=4.0):
        self.name, self.mat, self.smooth, self.angle, self.tile = name, mat, smooth, angle, tile
        self.v, self.f, self.uv = [], [], []
        Mesh.all[name] = self

    def poly(self, pts, uvs=None, hint=None):
        pts = [np.asarray(p, float) for p in pts]
        if uvs is None:
            uvs = [(0, 0)] * len(pts)
        if hint is not None:
            n = np.zeros(3)
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                n += np.cross(a, b)
            if np.dot(n, hint) < 0:
                pts, uvs = pts[::-1], list(uvs)[::-1]
        i0 = len(self.v)
        self.v.extend(pts)
        self.f.append(list(range(i0, i0 + len(pts))))
        self.uv.extend(uvs)

    def quad(self, a, b, c, d, uv=None, hint=None, tile=None):
        if uv is None:
            t = tile or self.tile
            w = np.linalg.norm(np.asarray(b) - np.asarray(a)) / t
            h = np.linalg.norm(np.asarray(d) - np.asarray(a)) / t
            uv = [(0, 0), (w, 0), (w, h), (0, h)]
        self.poly([a, b, c, d], uv, hint)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def build(self, coll):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        uvl = me.uv_layers.new(name='UVMap')
        for i, uv in enumerate(self.uv):
            uvl.data[i].uv = uv
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bm.to_mesh(me)
        bm.free()
        if self.smooth:
            me.shade_smooth()
            me.set_sharp_from_angle(angle=math.radians(self.angle))
        else:
            me.shade_flat()
        me.materials.append(self.mat)
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        return ob


def band(m, A, B, hint, nrm=None, closed=True, tile=None, u_fn=None, v=None):
    """Quads between two point lists A (first/bottom) and B (second/top)."""
    n = len(A)
    cnt = n if closed else n - 1
    cum = 0.0
    for i in range(cnt):
        j = (i + 1) % n
        a0, a1, b0, b1 = A[i], A[j], B[i], B[j]
        if hint == 'up':
            h = np.array([0, 0, 1.])
        elif hint == 'down':
            h = np.array([0, 0, -1.])
        else:
            nn = nrm[i] + nrm[j]
            h = np.array([nn[0], nn[1], 0.]) * (1 if hint == 'out' else -1)
        seg = np.linalg.norm(a1 - a0)
        t = tile or m.tile
        if u_fn:
            u0, u1 = u_fn(i)
        else:
            u0 = cum / t
            u0 -= math.floor(u0)
            u1 = u0 + seg / t
        cum += seg
        if v is None:
            v0, v1 = 0.0, np.linalg.norm(b0 - a0) / t
        else:
            v0, v1 = v
        m.poly([a0, a1, b1, b0], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], h)


def obox(m, o, ex, ey, ez, tile=None, skip=()):
    """Box from corner o with edge vectors ex, ey, ez. skip: face names to omit (x0,x1,y0,y1,z0,z1)."""
    o, ex, ey, ez = (np.asarray(k, float) for k in (o, ex, ey, ez))
    c = o + (ex + ey + ez) / 2
    faces = {
        'x0': (o, ey, ez), 'x1': (o + ex, ey, ez),
        'y0': (o, ex, ez), 'y1': (o + ey, ex, ez),
        'z0': (o, ex, ey), 'z1': (o + ez, ex, ey)}
    for k, (p, e1, e2) in faces.items():
        if k in skip:
            continue
        fc = p + (e1 + e2) / 2
        m.quad(p, p + e1, p + e1 + e2, p + e2, hint=fc - c, tile=tile)


def cyl(m, base, r, h, n=10, r2=None, cap=True, tile=None):
    base = np.asarray(base, float)
    r2 = r if r2 is None else r2
    t = tile or m.tile
    circ = 2 * math.pi * r / t
    top = []
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        d0 = np.array([math.cos(a0), math.sin(a0), 0])
        d1 = np.array([math.cos(a1), math.sin(a1), 0])
        p0, p1 = base + d0 * r, base + d1 * r
        q0, q1 = base + d0 * r2 + [0, 0, h], base + d1 * r2 + [0, 0, h]
        m.poly([p0, p1, q1, q0], [(circ * k / n, 0), (circ * (k + 1) / n, 0), (circ * (k + 1) / n, h / t),
                                  (circ * k / n, h / t)], d0 + d1)
        top.append(q0)
    if cap:
        m.poly(top, [(0.5 + 0.1 * math.cos(2 * math.pi * k / n), 0.5 + 0.1 * math.sin(2 * math.pi * k / n))
                     for k in range(n)], np.array([0, 0, 1.]))


# ------------------------------------------------------------------ materials
def make_mat(name, tex=None, normal=None, rough=0.8, metal=0.0, alpha=None, double=False,
             emission=None, color=(0.8, 0.8, 0.8), normal_strength=1.0, emission_tex=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    if tex:
        img = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = img
        nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha == 'BLEND':
            nt.links.new(tn.outputs['Alpha'], bsdf.inputs['Alpha'])
        elif alpha == 'MASK':
            mn = nt.nodes.new('ShaderNodeMath')
            mn.operation = 'ROUND'
            nt.links.new(tn.outputs['Alpha'], mn.inputs[0])
            nt.links.new(mn.outputs[0], bsdf.inputs['Alpha'])
        if emission_tex:
            nt.links.new(tn.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = emission or 1.0
    if normal:
        img = bpy.data.images.load(os.path.join(TEX, normal), check_existing=True)
        img.colorspace_settings.name = 'Non-Color'
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = img
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if emission and not emission_tex:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = emission
    mat.use_backface_culling = not double
    if alpha:
        try:
            mat.surface_render_method = 'DITHERED'
        except Exception:
            pass
        try:
            mat.blend_method = 'BLEND' if alpha == 'BLEND' else 'CLIP'
        except Exception:
            pass
    return mat


def shared_materials(small=False):
    M = {}
    M['screen'] = make_mat('Facade_Screen', 'screen_512.png' if small else 'screen.png',
                           'screen_n_512.jpg' if small else 'screen_n.jpg', rough=0.45, metal=0.35, alpha='BLEND',
                           normal_strength=1.0)
    M['inner'] = make_mat('Facade_Inner', 'innerwall.jpg', rough=0.85)
    M['stone'] = make_mat('Stone', 'stone.jpg', rough=0.85)
    M['concrete'] = make_mat('Concrete', 'concrete.jpg', rough=0.9)
    M['glazing'] = make_mat('Entrance_Glazing', 'glazing.jpg', rough=0.25, metal=0.2)
    M['paving'] = make_mat('Paving', 'paving.jpg', rough=0.9)
    M['kerb'] = make_mat('Kerb', 'kerb.jpg', rough=0.8)
    M['metal_dark'] = make_mat('Metal_Dark', 'metal.jpg', rough=0.5, metal=0.6)
    M['metal_light'] = make_mat('Metal_Light', 'metal_light.jpg', rough=0.45, metal=0.5)
    return M


# ------------------------------------------------------------------ scene utils
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    Mesh.all = {}
    coll = bpy.data.collections.new('Model')
    bpy.context.scene.collection.children.link(coll)
    return coll


def export_glb(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_draco_position_quantization=16, export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=16, export_image_format='AUTO', export_materials='EXPORT',
        export_cameras=False, export_lights=False, export_animations=False)
    # report
    import json, struct
    with open(path, 'rb') as f:
        data = f.read()
    jl = struct.unpack('<I', data[12:16])[0]
    js = json.loads(data[20:20 + jl])
    print('GLB', path, '%.2f MB' % (len(data) / 1e6))
    print('  meshes', len(js.get('meshes', [])), 'primitives',
          sum(len(m['primitives']) for m in js.get('meshes', [])), 'images', len(js.get('images', [])))
    for m in js.get('materials', []):
        print('  material', m['name'], m.get('alphaMode', 'OPAQUE'), 'doubleSided' if m.get('doubleSided') else '')
    tri = 0
    for me in js['meshes']:
        for p in me['primitives']:
            tri += js['accessors'][p['indices']]['count'] // 3
    print('  triangles', tri)
    return tri, len(data)


def setup_render(ground=True, sun_dir=(-0.55, -0.45, 0.7)):
    sc = bpy.context.scene
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = eng
            break
        except Exception:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 88
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    w = bpy.data.worlds.new('W')
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.72, 0.82, 0.97, 1)
    bg.inputs[1].default_value = 0.6
    sc.world = w
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 3.0
    sun.angle = math.radians(2)
    so = bpy.data.objects.new('Sun', sun)
    sc.collection.objects.link(so)
    d = Vector(sun_dir).normalized()
    so.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    if ground:
        me = bpy.data.meshes.new('ground')
        s = 900
        me.from_pydata([(-s, -s, -0.05), (s, -s, -0.05), (s, s, -0.05), (-s, s, -0.05)], [], [[0, 1, 2, 3]])
        gm = bpy.data.materials.new('ground')
        gm.use_nodes = True
        b = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = (0.09, 0.09, 0.095, 1)
        b.inputs['Roughness'].default_value = 0.9
        me.materials.append(gm)
        sc.collection.objects.link(bpy.data.objects.new('ground', me))
    try:
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = False
    except Exception:
        pass


def render_view(name, loc, target, lens=35, ortho=None, res=None, prefix=''):
    sc = bpy.context.scene
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start, cam.clip_end = 0.3, 3000
    if ortho:
        cam.type = 'ORTHO'
        cam.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = ob
    if res:
        sc.render.resolution_x, sc.render.resolution_y = res
    else:
        sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    os.makedirs(RENDERS, exist_ok=True)
    sc.render.filepath = os.path.join(RENDERS, prefix + name + '.jpg')
    bpy.ops.render.render(write_still=True)
    print('rendered', sc.render.filepath)


# ------------------------------------------------------------------ stadium
def build_stadium(coll):
    M = shared_materials()
    M['roof'] = make_mat('Roof_Membrane', 'roof.jpg', rough=0.7, double=True)
    M['truss'] = make_mat('Roof_Truss', 'truss.png', rough=0.6, metal=0.3, alpha='MASK', double=True)
    M['pitch'] = make_mat('Pitch', 'pitch.jpg', rough=0.95)
    M['track'] = make_mat('Track_Lanes', 'track.jpg', rough=0.9)
    M['rubber'] = make_mat('Track_Red', 'rubber.jpg', rough=0.9)
    M['flags'] = make_mat('Flags', 'flags.jpg', rough=0.8, double=True)
    M['board'] = make_mat('Scoreboard', 'board.jpg', rough=0.3, emission=0.15, emission_tex=True)
    M['white'] = make_mat('Letters_White', None, rough=0.5, color=(0.93, 0.93, 0.91), emission=0.25)

    screen = Mesh('Facade_Screen', M['screen'])
    inner = Mesh('Facade_Inner', M['inner'])
    stone = Mesh('Stone', M['stone'], smooth=True, tile=2.4)
    conc = Mesh('Concrete', M['concrete'], tile=4.0)
    glaz = Mesh('Entrance_Glazing', M['glazing'])
    pav = Mesh('Paving', M['paving'], tile=4.0)
    kerb = Mesh('Kerb', M['kerb'], tile=2.0)
    mdark = Mesh('Metal_Dark', M['metal_dark'], smooth=True, tile=1.0)
    mlight = Mesh('Metal_Light', M['metal_light'], smooth=True, tile=1.0)
    roof = Mesh('Roof_Membrane', M['roof'], smooth=True, angle=38)
    truss = Mesh('Roof_Truss', M['truss'])
    pitch = Mesh('Pitch', M['pitch'])
    track = Mesh('Track_Lanes', M['track'])
    rubber = Mesh('Track_Red', M['rubber'], tile=4.0)
    flags = Mesh('Flags', M['flags'], smooth=True, angle=80)
    board = Mesh('Scoreboard', M['board'])
    white = Mesh('Letters_White', M['white'])

    FAC, NRM, FAC_L = oval(FAC_A, FAC_B, FAC_N, NP)
    OPEN, ONRM, _ = oval(OPEN_A, OPEN_B, OPEN_N, NP)
    FRONT, FNRM, _ = oval(FRONT_A, FRONT_B, FRONT_N, NP)
    BACK = FAC - 2.0 * NRM
    TAN = np.stack([-NRM[:, 1], NRM[:, 0]], 1)        # CCW tangent
    print('facade perimeter %.1f m, panel column %.2f m, panel row %.2f m' %
          (FAC_L, FAC_L / NP, (Z_SCREEN1 - Z_SCREEN0) / ROWS))

    def R(d, z, idx=None):
        idx = range(NP) if idx is None else idx
        return [V3(FAC[i % NP] + d * NRM[i % NP], z) for i in idx]

    def BW(s, z):
        return [V3(FRONT[i] + (BACK[i] - FRONT[i]) * s, z) for i in range(NP)]

    def fpt(fi, d=0.0, z=0.0):
        """Point at fractional facade index fi."""
        i0 = int(math.floor(fi)) % NP
        i1 = (i0 + 1) % NP
        t = fi - math.floor(fi)
        p = FAC[i0] * (1 - t) + FAC[i1] * t
        n = NRM[i0] * (1 - t) + NRM[i1] * t
        n /= np.linalg.norm(n)
        return V3(p + d * n, z), V3(n), V3((-n[1], n[0]))

    # ---------------- facade screen, inner wall, mullions, fascias
    band(screen, R(0, Z_SCREEN0), R(TOPD, Z_SCREEN1), 'out', NRM,
         u_fn=lambda i: (0.0, 0.5) if i % 2 == 0 else (0.5, 1.0), v=(0, ROWS / 2))
    band(inner, R(-1.5 + lean(Z_SOFFIT), Z_SOFFIT), R(-1.5 + lean(Z_ROOF_OUT), Z_ROOF_OUT), 'out', NRM,
         u_fn=lambda i: (0.0, 0.5) if i % 2 == 0 else (0.5, 1.0), v=(0, 1))
    for i in range(NP):
        p, n, t = fpt(i, 0.0, Z_SCREEN0)
        w = 0.14 if i % 2 == 0 else 0.08
        obox(mlight, p - t * w / 2 - n * 0.05, t * w, n * (0.30 if i % 2 == 0 else 0.16),
             n * TOPD + [0, 0, Z_SCREEN1 - Z_SCREEN0], skip=('z0', 'z1', 'y0'))
    # bottom fascia beam under the screen (z 6.3 .. 7.0), slightly proud
    band(mlight, R(0.12, Z_SOFFIT), R(0.12, Z_SCREEN0 + 0.12), 'out', NRM, tile=1.0)
    band(mlight, R(-0.6, Z_SOFFIT), R(0.12, Z_SOFFIT), 'down', tile=1.0)
    band(mlight, R(0.0, Z_SCREEN0 + 0.12), R(0.12, Z_SCREEN0 + 0.12), 'up', tile=1.0)
    # top coping
    band(mlight, R(0.1 + lean(Z_SCREEN1 - 0.25), Z_SCREEN1 - 0.25), R(0.1 + TOPD, Z_SCREEN1 + 0.1), 'out', NRM, tile=1.0)
    band(mlight, R(-0.4 + TOPD, Z_SCREEN1 + 0.1), R(0.1 + TOPD, Z_SCREEN1 + 0.1), 'up', tile=1.0)

    # ---------------- ground level: soffit, base wall, columns
    band(conc, R(-5.0, Z_SOFFIT), R(-0.6, Z_SOFFIT), 'down')
    WEST = NP // 2 - 1                   # facade point index due west (89)

    def bay_type(b):
        if 42 <= b <= 46 or b in (88, 89, 0):
            return 'glass'
        if b in (20, 21, 22, 23, 65, 66, 67, 68):
            return 'gate'
        return 'gate' if b % 3 == 0 else ('glass' if b % 6 == 4 else 'stone')

    W0, W1 = R(-5.0, 0.0), R(-5.0, Z_SOFFIT)
    for b in range(NP // 2):
        ty = bay_type(b)
        for k in (0, 1):
            i = 2 * b + k
            j = (i + 1) % NP
            hn = V3(NRM[i] + NRM[j])
            if ty == 'stone':
                stone.quad(W0[i], W0[j], W1[j], W1[i], hint=hn)
            else:
                u0 = (0.0 if ty == 'glass' else 0.5) + 0.25 * k
                glaz.poly([W0[i], W0[j], W1[j], W1[i]],
                          [(u0, 0), (u0 + 0.25, 0), (u0 + 0.25, 1), (u0, 1)], hn)
        # stone pier at each bay boundary on the wall line (hides the texture joint)
        p, n, t = fpt(2 * b, -5.0, 0)
        obox(stone, p - t * 0.45, t * 0.9, n * 0.35, [0, 0, Z_SOFFIT], skip=('z0', 'z1', 'y0'))
    # round columns under the screen at every bay line + capital
    for b in range(NP // 2):
        p, n, t = fpt(2 * b, -0.75, 0)
        cyl(stone, p, 0.5, Z_SOFFIT, n=12, cap=False)
        cyl(stone, p, 0.62, 0.5, n=12, cap=True)

    # ---------------- paving apron, kerb
    band(pav, R(-5.0, 0.02), R(APRON, 0.02), 'up',
         u_fn=None, tile=4.0)
    band(kerb, R(APRON, 0.0), R(APRON, 0.17), 'out', NRM, tile=2.0, v=(0, 1))
    band(kerb, R(APRON - 0.3, 0.17), R(APRON, 0.17), 'up', tile=2.0, v=(0, 1))
    band(kerb, R(APRON - 0.3, 0.02), R(APRON - 0.3, 0.17), 'in', NRM, tile=2.0, v=(0, 1))

    # ---------------- west entrance canopy (bays 42..46)
    ci = list(range(84, 95))
    cn = [NRM[i] for i in ci]
    zc0, zc1 = 5.2, 5.9
    cin0, cout0 = R(-0.3, zc0, ci), R(9.0, zc0, ci)
    cin1, cout1 = R(-0.3, zc1, ci), R(9.0, zc1, ci)
    band(mdark, cin1, cout1, 'up', closed=False)
    band(mlight, cin0, cout0, 'down', closed=False)
    band(mdark, cout0, cout1, 'out', cn, closed=False)
    for e in (0, -1):
        mdark.quad(cin0[e], cout0[e], cout1[e], cin1[e], hint=V3(TAN[ci[e]]) * (-1 if e == 0 else 1))
    for i in ci[::2]:
        p, n, t = fpt(i, 8.2, 0)
        cyl(mdark, p, 0.22, zc0, n=10, cap=False)
    # low plinth steps under canopy edge
    band(stone, R(9.3, 0.02, ci), R(9.3, 0.20, ci), 'out', cn, closed=False)
    band(pav, R(-0.3, 0.20, ci), R(9.3, 0.20, ci), 'up', closed=False)

    # ---------------- roof: 90 barrel vault segments
    NS = NP // 2
    K = 8
    S = [0.0, 0.05, 0.12, 0.24, 0.38, 0.52, 0.66, 0.80, 0.92, 1.0]

    def zb(s):
        return Z_ROOF_OUT + (Z_ROOF_IN - Z_ROOF_OUT) * (1 - (1 - s) ** 1.5)

    def rise(s):
        return RISE_OUT + (RISE_IN - RISE_OUT) * s

    def shape(q):
        return math.sin(math.pi * q) ** 0.8

    def rl(b, s):
        i = (2 * b) % NP
        o = FAC[i] + (TOPD - 0.5) * NRM[i]
        return o + (OPEN[i] - o) * s

    def nose(b, d):
        i = (2 * b) % NP
        return FAC[i] + (d + TOPD) * NRM[i]

    for b in range(NS):
        rings = []
        # nose rings (outside the facade line), then the main stations
        for d, z, rf in ((0.75, Z_SCREEN1 + 0.1, 0.0), (0.62, Z_SCREEN1 + 0.55, 0.62), (0.2, Z_ROOF_OUT - 0.05, 0.9)):
            rings.append([V3(nose(b, d) * (1 - k / K) + nose(b + 1, d) * (k / K),
                             z + RISE_OUT * rf * shape(k / K)) for k in range(K + 1)])
        for s in S:
            rings.append([V3(rl(b, s) * (1 - k / K) + rl(b + 1, s) * (k / K),
                             zb(s) + rise(s) * shape(k / K)) for k in range(K + 1)])
        vv = 0.0
        for r in range(len(rings) - 1):
            dv = np.linalg.norm(rings[r + 1][K // 2] - rings[r][K // 2]) / 7.0
            for k in range(K):
                roof.poly([rings[r][k], rings[r][k + 1], rings[r + 1][k + 1], rings[r + 1][k]],
                          [(k / K, vv), ((k + 1) / K, vv), ((k + 1) / K, vv + dv), (k / K, vv + dv)],
                          np.array([0, 0, 1.]))
            vv += dv
            vv -= math.floor(vv)
        # lunette closing the inner end of the vault
        last = rings[-1]
        for k in range(K):
            a, c = last[k], last[k + 1]
            a0, c0 = a.copy(), c.copy()
            a0[2] = c0[2] = Z_ROOF_IN - 0.1
            roof.poly([a0, c0, c, a], [(k / K, 0), ((k + 1) / K, 0), ((k + 1) / K, 0.2), (k / K, 0.2)],
                      -V3(OPEN[(2 * b) % NP]))
    # nose underside back to the facade top
    band(mlight, R(0.1 + TOPD, Z_SCREEN1 + 0.1), R(0.75 + TOPD, Z_SCREEN1 + 0.1), 'down', tile=1.0)
    # inner edge ring beam
    def OR(d, z):
        return [V3(OPEN[i] + d * ONRM[i], z) for i in range(NP)]
    zr0, zr1 = Z_ROOF_IN - 1.5, Z_ROOF_IN - 0.05
    band(mlight, OR(-0.45, zr0), OR(-0.45, zr1), 'in', ONRM, tile=2.0)
    band(mlight, OR(0.45, zr0), OR(0.45, zr1), 'out', ONRM, tile=2.0)
    band(mlight, OR(-0.45, zr0), OR(0.45, zr0), 'down', tile=2.0)
    band(mlight, OR(-0.45, zr1), OR(0.45, zr1), 'up', tile=2.0)
    # radial trusses under every valley + two rings of purlin trusses
    TS = np.linspace(0, 1, 7)
    for b in range(NS):
        for a in range(len(TS) - 1):
            s0, s1 = TS[a], TS[a + 1]
            d0, d1 = 3.2 - 1.9 * s0, 3.2 - 1.9 * s1
            p0, p1 = rl(b, s0), rl(b, s1)
            truss.poly([V3(p0, zb(s0) - d0), V3(p1, zb(s1) - d1), V3(p1, zb(s1) - 0.05), V3(p0, zb(s0) - 0.05)],
                       [(a * 1.0, 0), (a * 1.0 + 1.0, 0), (a * 1.0 + 1.0, 1), (a * 1.0, 1)])
        for s in (0.3, 0.62, 0.97):
            p0, p1 = rl(b, s), rl(b + 1, s)
            dd = 1.3
            truss.poly([V3(p0, zb(s) - dd), V3(p1, zb(s) - dd), V3(p1, zb(s) - 0.05), V3(p0, zb(s) - 0.05)],
                       [(0, 0), (1, 0), (1, 1), (0, 1)])

    # ---------------- bowl
    # red surface under everything inside the tier front
    ctr = np.array([0, 0, 0.0])
    fr0 = BW(0.0, 0.0)
    for i in range(NP):
        j = (i + 1) % NP
        rubber.poly([ctr, fr0[i], fr0[j]], [(0, 0), (fr0[i][0] / 4, fr0[i][1] / 4), (fr0[j][0] / 4, fr0[j][1] / 4)],
                    np.array([0, 0, 1.]))
    band(conc, BW(0.0, 0.0), BW(0.0, 1.3), 'in', FNRM)
    band(conc, BW(0.0, 1.3), BW(0.02, 1.3), 'up')
    band(conc, BW(0.36, 6.4), BW(0.41, 6.4), 'up')
    band(glaz, BW(0.41, 6.4), BW(0.41, 8.8), 'in', FNRM,
         u_fn=lambda i: (0.0, 0.5), v=(0.42, 0.98))
    band(conc, BW(0.31, 8.8), BW(0.41, 8.8), 'down')
    band(conc, BW(0.31, 8.8), BW(0.31, 10.2), 'in', FNRM)
    band(conc, BW(0.31, 10.2), BW(0.325, 10.2), 'up')
    band(conc, BW(1.0, 26.0), BW(1.0, 27.1), 'in', NRM)
    band(inner, BW(1.0, 27.1), BW(1.0, Z_ROOF_OUT), 'in', NRM,
         u_fn=lambda i: (0.0, 0.5) if i % 2 == 0 else (0.5, 1.0), v=(0.62, 0.98))

    # stepped terraces: one tread per seat row. The chairs themselves are placed by the website
    # (src/tour-seats.js) from public/tour/amahoro_seats.json, written below.
    def TP(fi, s, z):
        i0 = int(math.floor(fi)) % NP
        i1 = (i0 + 1) % NP
        t = fi - math.floor(fi)
        a = FRONT[i0] + (BACK[i0] - FRONT[i0]) * s
        c = FRONT[i1] + (BACK[i1] - FRONT[i1]) * s
        return V3(a * (1 - t) + c * t, z)

    UPZ = np.array([0, 0, 1.])
    layout = {}
    for name, (s0, z0, s1, z1), N, voms in (('lower', LOW, NL, False), ('upper', UPP, NU, True)):
        se = [s0 + (s1 - s0) * r / N for r in range(N + 1)]
        zt = [z0 + (z1 - z0) * (r + 1) / N for r in range(N)]
        zbase = z0 if name == 'lower' else 10.2
        layout[name] = [[round(se[r] + (se[r + 1] - se[r]) * 0.56, 5), round(zt[r], 3)] for r in range(N)]
        for r in range(N):
            zlo = zbase if r == 0 else zt[r - 1]
            for i in range(NP):
                spans = [(0.0, 1.0)]
                if voms and VOM_ROWS[0] <= r <= VOM_ROWS[1]:
                    if i % VOM_EVERY == 0:
                        spans = [(VOM_W, 1.0)]
                    elif (i + 1) % VOM_EVERY == 0:
                        spans = [(0.0, 1 - VOM_W)]
                for (w0, w1) in spans:
                    a, c = i + w0, i + w1
                    hn = -V3(FRONT[i])
                    conc.quad(TP(a, se[r], zlo), TP(c, se[r], zlo), TP(c, se[r], zt[r]), TP(a, se[r], zt[r]), hint=hn)
                    conc.quad(TP(a, se[r], zt[r]), TP(c, se[r], zt[r]), TP(c, se[r + 1], zt[r]), TP(a, se[r + 1], zt[r]),
                              hint=UPZ)
        if voms:   # vomitories: a slot cut into the tier with a dark doorway at its back
            r0, r1 = VOM_ROWS
            zf, ztop = zt[r0 - 1], zt[r1] + 1.1
            sa, sb = se[r0], se[r1 + 1]
            for i in range(0, NP, VOM_EVERY):
                fa, fb = i - VOM_W, i + VOM_W
                conc.quad(TP(fa, sa, zf), TP(fb, sa, zf), TP(fb, sb, zf), TP(fa, sb, zf), hint=UPZ)
                for f, sg in ((fa, 1), (fb, -1)):
                    side = [TP(f, sa, zf), TP(f, sb, zf), TP(f, sb, ztop), TP(f, sa, ztop)]
                    tv = V3(TAN[i]) * sg
                    conc.quad(*side, hint=tv)
                    conc.quad(*[q - tv * 0.15 for q in side], hint=-tv)
                    conc.quad(side[3], side[2], side[2] - tv * 0.15, side[3] - tv * 0.15, hint=UPZ)
                    conc.quad(side[0] - tv * 0.15, side[0], side[3], side[3] - tv * 0.15, hint=-V3(FRONT[i]))
                hn = -V3(FRONT[i])
                zd = zf + 2.3
                mdark.quad(TP(fa, sb, zf), TP(fb, sb, zf), TP(fb, sb, zd), TP(fa, sb, zd), hint=hn)
                conc.quad(TP(fa, sb, zd), TP(fb, sb, zd), TP(fb, sb, ztop), TP(fa, sb, ztop), hint=hn)
    import json
    os.makedirs(os.path.join(ROOT, 'public', 'tour'), exist_ok=True)
    with open(os.path.join(ROOT, 'public', 'tour', 'amahoro_seats.json'), 'w') as f:
        json.dump({'front': [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in FRONT],
                   'back': [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in BACK],
                   'lower': layout['lower'], 'upper': layout['upper'], 'pitch': 0.5,
                   'aisleEvery': AISLE_EVERY, 'aisleHalf': 0.6,
                   'vomEvery': VOM_EVERY, 'vomRows': list(VOM_ROWS), 'vomFrac': VOM_W}, f, separators=(',', ':'))

    # pitch + lanes
    px, py = 36.2, 55.5
    du = (37 - px) / 74.0
    pitch.poly([(-px, -py, 0.03), (px, -py, 0.03), (px, py, 0.03), (-px, py, 0.03)],
               [(0, 1 - du), (0, du), (1, du), (1, 1 - du)], np.array([0, 0, 1.]))
    # (image x runs along the pitch length = model Y; image y across = model X)
    ri, ro, hs = 36.5, 36.5 + 8 * 1.22, 84.39 / 2
    pts_i, pts_o = [], []
    nseg = 32
    for a in np.linspace(0, math.pi, nseg + 1):          # north curve, from +X round to -X
        pts_i.append((ri * math.cos(a), hs + ri * math.sin(a)))
        pts_o.append((ro * math.cos(a), hs + ro * math.sin(a)))
    for a in np.linspace(math.pi, 2 * math.pi, nseg + 1):  # south curve
        pts_i.append((ri * math.cos(a), -hs + ri * math.sin(a)))
        pts_o.append((ro * math.cos(a), -hs + ro * math.sin(a)))
    n = len(pts_i)
    cum = 0.0
    for i in range(n):
        j = (i + 1) % n
        seg = math.hypot(pts_i[j][0] - pts_i[i][0], pts_i[j][1] - pts_i[i][1])
        nsub = max(1, int(round(seg / 12.0)))
        for q in range(nsub):
            t0, t1 = q / nsub, (q + 1) / nsub
            a0 = np.array(pts_i[i]) * (1 - t0) + np.array(pts_i[j]) * t0
            a1 = np.array(pts_i[i]) * (1 - t1) + np.array(pts_i[j]) * t1
            b0 = np.array(pts_o[i]) * (1 - t0) + np.array(pts_o[j]) * t0
            b1 = np.array(pts_o[i]) * (1 - t1) + np.array(pts_o[j]) * t1
            u0 = cum / 10.0
            u0 -= math.floor(u0)
            u1 = u0 + seg / nsub / 10.0
            cum += seg / nsub
            track.poly([V3(a0, 0.02), V3(a1, 0.02), V3(b1, 0.02), V3(b0, 0.02)],
                       [(u0, 0), (u1, 0), (u1, 1), (u0, 1)], np.array([0, 0, 1.]))
    # goals
    for sgn in (-1, 1):
        y = sgn * 52.5
        for x in (-3.66, 3.66):
            obox(white, (x - 0.06, y - 0.06, 0.03), (0.12, 0, 0), (0, 0.12, 0), (0, 0, 2.44))
        obox(white, (-3.72, y - 0.06, 2.44), (7.44, 0, 0), (0, 0.12, 0), (0, 0, 0.12))
        for x in (-3.66, 3.66):
            obox(white, (x - 0.03, y, 0.03), (0.06, 0, 0), (0, sgn * 2.0, 0), (0, 0, 0.06))
            obox(white, (x - 0.03, y + sgn * 2.0, 0.03), (0.06, 0, 0), (0, sgn * 0.06, 0), (0, 0, 1.2))
    # dugouts (west side, beyond the lanes)
    for yc in (-16, 16):
        # curved shell: back wall, arched roof, open front with a bench
        prof = [(-51.2, 0.02), (-51.2, 1.5), (-50.9, 2.0), (-50.3, 2.25), (-49.4, 2.3)]
        for a in range(len(prof) - 1):
            (x0, z0), (x1, z1) = prof[a], prof[a + 1]
            white.quad((x0, yc - 5, z0), (x0, yc + 5, z0), (x1, yc + 5, z1), (x1, yc - 5, z1),
                       hint=np.array([-1, 0, 1.]))
            board.quad((x0 + .04, yc - 5, z0), (x0 + .04, yc + 5, z0), (x1 + .04, yc + 5, z1 - .04),
                       (x1 + .04, yc - 5, z1 - .04), hint=np.array([1, 0, -1.]), tile=2.0)
        for ye in (yc - 5, yc + 5):
            white.poly([(x, ye, z) for x, z in prof] + [(-49.4, ye, 0.02)], None, np.array([0, ye - yc, 0.]))
        obox(mdark, (-50.9, yc - 4.8, 0.02), (0.5, 0, 0), (0, 9.6, 0), (0, 0, 0.45))
    # scoreboards at both ends, hung under the roof edge
    for sgn in (-1, 1):
        y = sgn * 83.0
        obox(mdark, (-9.5, y, 29.5), (19, 0, 0), (0, sgn * 0.9, 0), (0, 0, 8.6))
        yf = y - sgn * 0.05
        board.poly([(-9, yf, 30.0), (9, yf, 30.0), (9, yf, 37.6), (-9, yf, 37.6)],
                   [(0, 0), (9, 0), (9, 4), (0, 4)], np.array([0, -sgn, 0.]))
        for x in (-7, 7):
            obox(mdark, (x - 0.15, y + sgn * 0.3, 38.1), (0.3, 0, 0), (0, sgn * 0.3, 0), (0, 0, 1.2))

    # ---------------- outside furniture
    # lamp posts
    for i in range(6, NP, 12):
        if 80 <= i <= 98:
            continue
        p, nrm, t = fpt(i, APRON - 1.6, 0.02)
        cyl(mdark, p, 0.16, 0.5, n=8, cap=True)
        cyl(mdark, p, 0.10, 11.0, n=8, r2=0.07, cap=True)
        top = p + [0, 0, 11.0]
        for sg in (-1, 1):
            obox(mdark, top + t * sg * 0.1 - nrm * 0.18, t * sg * 0.9 + np.array([0, 0, 0.25]), nrm * 0.36,
                 [0, 0, 0.08])
    # bollards along the west forecourt edge
    fi = 62.0
    while fi <= 116.0:
        p, nrm, t = fpt(fi, APRON - 0.9, 0.02)
        cyl(mdark, p, 0.11, 0.9, n=8, cap=True)
        fi += 0.5
    # flagpoles, north of the west entrance
    fcol = [0, 1, 2]
    for k, fi in enumerate(np.arange(72.0, 82.0, 1.0)):
        p, nrm, t = fpt(fi, APRON - 2.6, 0.02)
        H = 12.0
        cyl(mlight, p, 0.09, H, n=8, r2=0.05, cap=True)
        cyl(mlight, p, 0.2, 0.25, n=8, cap=True)
        c = fcol[k % 3]
        nx, ny = 8, 3
        fw, fh = 2.6, 1.6
        grid = []
        for iy in range(ny + 1):
            row = []
            for ix in range(nx + 1):
                fx = ix / nx
                wv = 0.28 * fx * math.sin(fx * 7.0 + k * 1.3) + 0.08 * fx * math.sin(iy * 1.4 + k)
                sag = -0.35 * fx * fx
                row.append(p + t * (-fw * fx) + nrm * wv + np.array([0, 0, H - 0.15 - fh + fh * iy / ny + sag]))
            grid.append(row)
        for iy in range(ny):
            for ix in range(nx):
                u0, u1 = c * 0.25 + 0.02 + 0.21 * ix / nx, c * 0.25 + 0.02 + 0.21 * (ix + 1) / nx
                flags.poly([grid[iy][ix], grid[iy][ix + 1], grid[iy + 1][ix + 1], grid[iy + 1][ix]],
                           [(u0, iy / ny), (u1, iy / ny), (u1, (iy + 1) / ny), (u0, (iy + 1) / ny)])

    # ---------------- lettering on the west face
    add_lettering(white, 'AMAHORO STADIUM', cap=3.4, zc=19.2, standoff=0.45)

    objs = [m.build(coll) for m in Mesh.all.values() if m.f]
    print('TRIS', {m.name: m.tris() for m in Mesh.all.values()}, 'total', sum(m.tris() for m in Mesh.all.values()))
    return objs


def add_lettering(mesh, text, cap, zc, standoff, a=FAC_A, b=FAC_B, n=FAC_N):
    """3D sans letters following the west face, readable from outside (-X side)."""
    font = None
    for fp in ('/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf'):
        if os.path.exists(fp):
            font = bpy.data.fonts.load(fp)
            break
    size = cap / 0.716
    ND = 7200
    D, DN, L = oval(a, b, n, ND)
    glyphs = {}
    tmpc = bpy.context.scene.collection
    for ch in set(text.replace(' ', '')):
        cu = bpy.data.curves.new('t', 'FONT')
        cu.body = ch
        if font:
            cu.font = font
        cu.size = size
        cu.extrude = 0.14
        cu.offset = 0.035
        cu.resolution_u = 3
        ob = bpy.data.objects.new('t', cu)
        tmpc.objects.link(ob)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        vs = np.array([v.co[:] for v in me.vertices])
        fs = [list(p.vertices) for p in me.polygons]
        glyphs[ch] = (vs, fs, vs[:, 0].min(), vs[:, 0].max())
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    gap, space = 0.20 * cap, 0.85 * cap
    widths = [space if ch == ' ' else glyphs[ch][3] - glyphs[ch][2] for ch in text]
    total = sum(widths) + gap * (len(text) - 1)
    x = -total / 2
    west = ND // 2 - 1
    for ch, w in zip(text, widths):
        if ch != ' ':
            vs, fs, x0, x1 = glyphs[ch]
            arc = x + w / 2
            fi = west + arc / L * ND
            i0 = int(math.floor(fi))
            tt = fi - i0
            p = D[i0] * (1 - tt) + D[i0 + 1] * tt
            nn = DN[i0] * (1 - tt) + DN[i0 + 1] * tt
            nn /= np.linalg.norm(nn)
            T3 = V3((-nn[1], nn[0]))
            k = 1 / math.hypot(1, LEAN)                    # the letters lie on the leaning screen
            Z3 = (np.array([0, 0, 1.]) + V3(nn) * LEAN) * k
            N3 = (V3(nn) - np.array([0, 0, 1.]) * LEAN) * k
            o = V3(p + nn * lean(zc - cap / 2), zc - cap / 2) + N3 * standoff
            loc = vs.copy()
            loc[:, 0] -= (x0 + x1) / 2
            wp = o[None, :] + loc[:, 0:1] * T3[None, :] + loc[:, 1:2] * Z3[None, :] + loc[:, 2:3] * N3[None, :]
            for f in fs:
                mesh.poly([wp[k] for k in f])
        x += w + gap
    print('lettering width %.1f m, cap height %.2f m, centre z %.1f' % (total, cap, zc))


def main():
    coll = reset_scene()
    objs = build_stadium(coll)
    os.makedirs(MODELS, exist_ok=True)
    export_glb(objs, os.path.join(MODELS, 'amahoro.glb'))
    if os.environ.get('TOUR_RENDER', '1') != '0':
        setup_render()
        views = os.environ.get('TOUR_VIEWS', 'aerial,top,ground,close,bowl,aerial2').split(',')
        if 'aerial' in views:
            render_view('aerial', (-330, -190, 210), (0, 0, 5), lens=32, prefix='amahoro_')
        if 'aerial2' in views:
            render_view('aerial2', (300, -330, 150), (0, 0, 5), lens=32, prefix='amahoro_')
        if 'top' in views:
            render_view('top', (0, 0, 600), (0, 0, 0), ortho=300, res=(1000, 1300), prefix='amahoro_')
        if 'ground' in views:
            render_view('ground', (-FAC_A - 90, -6, 1.7), (-FAC_A, -2, 15), lens=20, prefix='amahoro_')
        if 'close' in views:
            render_view('close', (-FAC_A - 17, -34, 1.7), (-FAC_A + 2, -6, 7.5), lens=22, prefix='amahoro_')
        if 'bowl' in views:
            render_view('bowl', (-38, -70, 19), (20, 40, 6), lens=18, prefix='amahoro_')


if __name__ == '__main__':
    main()
