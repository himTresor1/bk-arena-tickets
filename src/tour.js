// A tour of the Kigali sports complex: BK Arena, Amahoro Stadium, Zaria Court, Petit Stade and the outdoor courts,
// standing in the real street plan of Remera (from OpenStreetMap). Fly over it, or drop down and walk.
// Axes: x = east, y = up, z = south, origin at the centre of BK Arena. The district comes from blender/py/130_city.py.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MapControls } from 'three/addons/controls/MapControls.js';
import { preload, texture, dress, dressModel, setEnvironment, reflect } from './textures.js';
import { addAmahoroSeats } from './tour-seats.js';

const $ = (id) => document.getElementById(id);
const V = '?v=' + __BUILD__;
const UP = new THREE.Vector3(0, 1, 0), deg = Math.PI / 180;
const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const coarse = matchMedia('(pointer: coarse)').matches;
document.body.dataset.touch = coarse;
const progress = (f) => { if (window.__loading) window.__loading(f); };

// ---------------------------------------------------------------- the places
// pos = where the model's own origin stands; rot = turn about the vertical; air/ground = where the camera goes
const local = (v, x, north) => { const c = Math.cos(v.rot), s = Math.sin(v.rot); return [v.pos[0] + x * c - north * s, v.pos[1] - x * s - north * c]; };
const VENUES = [
  { id: 'bk', name: 'BK Arena', kind: 'Indoor arena · 10,000 seats', file: 'exterior.glb', pos: [0, 0], rot: -135 * deg, top: 34,
    text: 'The round arena with the patterned band under its cream roof. Home of the Basketball Africa League finals, concerts and conferences.',
    link: ['Choose a seat', '/'], air: { dist: 250, az: -40, el: 30 }, walk: [0, 104, 0, 0], reach: 135 },
  { id: 'amahoro', name: 'Amahoro Stadium', kind: 'National stadium · 45,000 seats', file: 'amahoro.glb', pos: [-135.3, 205.2], rot: 9.9 * deg, top: 48,
    text: 'Rebuilt and reopened in 2024: a full roof of scalloped vaults over a bowl wrapped in a leaning screen of imigongo patterns.',
    air: { dist: 430, az: -70, el: 34 }, walk: [-170, 0, 0, 0], reach: 185, inside: { label: 'Stand on the pitch', at: [44, -70], look: [-10, 30] } },
  { id: 'zaria', name: 'Zaria Court', kind: 'Sports, hotel and events', file: 'zaria.glb', pos: [-410.7, 463.3], rot: 23 * deg, top: 26,
    text: 'Brick and timber around a covered public court, with a hotel, pool terrace, cafes and five-a-side pitches. Opened in 2025.',
    air: { dist: 250, az: 200, el: 36 }, walk: [-24, 10, 15, 10], reach: 95 },
  { id: 'petit', name: 'Petit Stade', kind: 'Indoor halls', file: 'petitstade.glb', pos: [-238.6, 380.9], rot: 5.8 * deg, top: 22,
    text: 'Two halls for basketball, volleyball and para sport beside the stadium, wearing the same patterned screen.',
    air: { dist: 170, az: 30, el: 34, at: [26, 0] }, walk: [26, 58, 26, 0], reach: 85 },
  { id: 'courts', name: 'Outdoor courts', kind: 'Courts and training track', pos: [52, 175], rot: 0, top: 14,
    text: 'Open basketball and tennis courts, and the training pitch with its running track, between the arena and the stadium.',
    air: { dist: 240, az: 60, el: 38 }, walk: [0, 75, 0, 40], reach: 90 },
];

// ---------------------------------------------------------------- scene
const canvas = $('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, logarithmicDepthBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, coarse ? 1.5 : 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = !coarse; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xcfdadc, 500, 3200);
const camera = new THREE.PerspectiveCamera(46, 1, 0.3, 9000);
camera.position.set(330, 300, -260);

await preload((f) => progress(f * 0.45));
{
  const sky = texture('sky.jpg', { srgb: true });
  if (sky) { sky.mapping = THREE.EquirectangularReflectionMapping; scene.background = sky; const pm = new THREE.PMREMGenerator(renderer); setEnvironment(pm.fromEquirectangular(sky).texture); pm.dispose(); }
  else scene.background = new THREE.Color(0xa4c2ca);
}
scene.add(new THREE.HemisphereLight(0xe4eefb, 0x8d7c66, 1.25));
const sun = new THREE.DirectionalLight(0xfff0d8, 2.5); const SUN_DIR = new THREE.Vector3(-0.55, 0.74, 0.38).normalize();
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.6;
scene.add(sun, sun.target);
function aimSun(focus, span) { // keep the shadow map over the part of the site being looked at
  sun.position.copy(focus).addScaledVector(SUN_DIR, 900); sun.target.position.copy(focus);
  const c = sun.shadow.camera; c.left = c.bottom = -span; c.right = c.top = span; c.near = 100; c.far = 1900; c.updateProjectionMatrix();
}

// textures of the district (public/textures/tour, made by scripts/make_tour_textures.py)
const tl = new THREE.TextureLoader();
async function tex(file, { srgb = true, repeat = null } = {}) {
  const t = await tl.loadAsync('/textures/tour/' + file + V); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; t.flipY = false;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace; if (repeat) t.repeat.set(repeat[0], repeat[1]); return t;
}
const T = {};
await Promise.all(Object.entries({ house: 'house.jpg', office: 'office.jpg', sheet: 'sheet.jpg', ground: 'ground.jpg', kerb: 'kerb.jpg', track: 'track.jpg',
  soccer: 'soccer.jpg', pitch5: 'pitch5.jpg', tennis: 'tennis.jpg', basket: 'basket.jpg', fence: 'fence.png' }).map(async ([k, f]) => { T[k] = await tex(f); }));
T.sheetN = await tex('sheet_normal.jpg', { srgb: false });
progress(0.55);

// UVs in metres straight from the ground position, so flat surfaces keep their texture at real size wherever they are
function groundUV(geo) { const p = geo.attributes.position, uv = new Float32Array(p.count * 2); for (let i = 0; i < p.count; i++) { uv[i * 2] = p.getX(i); uv[i * 2 + 1] = p.getZ(i); } geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); }
const std = (o = {}) => new THREE.MeshStandardMaterial({ roughness: 0.95, side: THREE.DoubleSide, ...o });
// break up the visible repeat of a tiled texture by mixing it with two larger, turned copies of itself
function untile(m) {
  m.onBeforeCompile = (sh) => { sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', `
    #ifdef USE_MAP
      vec4 tA = texture2D(map, vMapUv);
      vec4 tB = texture2D(map, mat2(0.8, -0.6, 0.6, 0.8) * vMapUv * 0.217 + 0.37);
      vec4 tC = texture2D(map, mat2(0.6, 0.8, -0.8, 0.6) * vMapUv * 0.043 + 0.11);
      diffuseColor *= vec4(mix(mix(tA.rgb, tB.rgb, 0.5), tC.rgb, 0.42), 1.0);
    #endif`); };
  return m;
}
const lift = (m, n) => { m.polygonOffset = true; m.polygonOffsetFactor = -n; m.polygonOffsetUnits = -n; return m; };

{ // open ground: red earth and grass, out to the hills
  const g = new THREE.CircleGeometry(5200, 72).rotateX(-Math.PI / 2); groundUV(g);
  const map = T.ground.clone(); map.repeat.set(1 / 70, 1 / 70); map.needsUpdate = true;
  const m = new THREE.Mesh(g, untile(std({ map, color: 0xd6d4c6 }))); m.receiveShadow = true; scene.add(m);
  const hill = std({ color: 0x748a6c, side: THREE.FrontSide }), rnd = (() => { let r = 5; return () => ((r = (r * 16807) % 2147483647) / 2147483647); })();
  for (let i = 0; i < 26; i++) {
    const a = i / 26 * Math.PI * 2 + rnd() * 0.2, d = 2300 + rnd() * 1500, h = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), hill);
    h.scale.set(500 + rnd() * 700, 90 + rnd() * 190, 500 + rnd() * 600); h.position.set(Math.cos(a) * d, -4, Math.sin(a) * d); scene.add(h);
  }
}

{ // beyond the mapped streets the city carries on: simple houses and trees, only ever seen from far away
  let r = 91; const rnd = () => ((r = (r * 16807) % 2147483647) / 2147483647), o = new THREE.Object3D(), c = new THREE.Color(), N = coarse ? 1400 : 3200;
  const wallsI = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0), std({ side: THREE.FrontSide }), N);
  const roofsI = new THREE.InstancedMesh(new THREE.ConeGeometry(0.76, 1, 4).rotateY(Math.PI / 4).translate(0, 0.5, 0), std({ side: THREE.FrontSide, roughness: 0.6, flatShading: true }), N);
  const treesI = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1).translate(0, 1.6, 0), std({ side: THREE.FrontSide, flatShading: true }), N);
  const ROOF = [0x9a4a35, 0xa5533a, 0x8c4433, 0xb05e44, 0x6f7f96, 0x8f9499, 0x9a4a35], WALL = [0xe9dfc8, 0xe4d3b0, 0xd9c7a3, 0xdcd6c8];
  let n = 0, guard = 0;
  while (n < N && guard++ < 60000) {
    const a = rnd() * Math.PI * 2, d = 600 + Math.sqrt(rnd()) * 2100, x = -110 + Math.cos(a) * d, z = 190 + Math.sin(a) * d;
    if (x > -800 && x < 680 && z > -430 && z < 840) continue;
    if (Math.sin(x * 0.0041) + Math.sin(z * 0.0052 + 1.3) + Math.sin((x + z) * 0.0029) < -0.5) continue;
    const w = 8 + rnd() * 9, dpt = 7 + rnd() * 6, h = 3 + (rnd() < 0.15 ? 3 + rnd() * 6 : 0), ry = Math.floor(rnd() * 4) * 0.4 + Math.sin(x * 0.002) * 0.8;
    o.position.set(x, 0, z); o.rotation.set(0, ry, 0); o.scale.set(w, h, dpt); o.updateMatrix(); wallsI.setMatrixAt(n, o.matrix); wallsI.setColorAt(n, c.setHex(WALL[n % WALL.length]));
    o.position.y = h; o.scale.set(w * 1.05, 1.6 + rnd(), dpt * 1.05); o.updateMatrix(); roofsI.setMatrixAt(n, o.matrix); roofsI.setColorAt(n, c.setHex(ROOF[n % ROOF.length]));
    const s = 2.4 + rnd() * 2.2; o.position.set(x + (rnd() - 0.5) * 30, 0, z + (rnd() - 0.5) * 30); o.scale.set(s, s * 1.2, s); o.updateMatrix(); treesI.setMatrixAt(n, o.matrix); treesI.setColorAt(n, c.setHSL(0.27 + rnd() * 0.05, 0.4, 0.24 + rnd() * 0.1));
    n++;
  }
  [wallsI, roofsI, treesI].forEach((m) => { m.count = n; m.frustumCulled = false; scene.add(m); });
}

const loader = new GLTFLoader(); loader.setDRACOLoader(new DRACOLoader().setDecoderPath('/draco/'));
const shade = (root, cast = true) => root.traverse((o) => { if (o.isMesh) { o.castShadow = cast; o.receiveShadow = true; } });

// ---------------------------------------------------------------- the district
try {
  const g = await loader.loadAsync('/models/city.glb' + V);
  const flatUV = new Set(['C_Road', 'C_Parking', 'C_Sidewalk', 'C_Paving', 'C_PavingB', 'C_Path', 'C_Lawn', 'C_Turf', 'C_RoofFlat']);
  const MAT = {
    C_Road: () => lift(untile(dress(std({ color: 0x84878a }), 'asphalt')), 3),
    C_Parking: () => lift(untile(dress(std({ color: 0x8e9194 }), 'asphalt')), 2),
    C_Marking: () => lift(std({ color: 0xe9e9e2, roughness: 0.7 }), 5),
    C_Kerb: () => std({ map: T.kerb, roughness: 0.8 }),
    C_Sidewalk: () => dress(std({ color: 0xb9ad98 }), 'paving'),
    C_Paving: () => lift(untile(dress(std({ color: 0xc2b59d }), 'paving')), 1),
    C_PavingB: () => lift(untile(dress(std({ color: 0xab9c86 }), 'paving')), 1),
    C_Path: () => lift(dress(std({ color: 0xa89c88 }), 'paving'), 2),
    C_Lawn: () => untile(dress(std({ color: 0x8a9a5c }), 'grass')),
    C_Turf: () => lift(dress(std({ color: 0x7fa850 }), 'grass'), 3),
    C_Track: () => lift(std({ map: T.track, roughness: 0.9 }), 3),
    C_Soccer: () => lift(std({ map: T.soccer }), 4), C_Pitch5: () => lift(std({ map: T.pitch5 }), 3),
    C_Tennis: () => lift(std({ map: T.tennis, roughness: 0.8 }), 3), C_Basket: () => lift(std({ map: T.basket, roughness: 0.8 }), 3),
    C_Fence: () => std({ map: T.fence, alphaTest: 0.35, roughness: 0.6, metalness: 0.4 }),
    C_House: () => std({ map: T.house, vertexColors: true }),
    C_Office: () => reflect(std({ map: T.office, vertexColors: true, roughness: 0.55 }), 0.5),
    C_Sheet: () => { const map = T.sheet.clone(), n = T.sheetN.clone(); [map, n].forEach((t) => { t.repeat.set(1 / 1.2, 1 / 2.4); t.needsUpdate = true; });
      return reflect(std({ map, normalMap: n, vertexColors: true, roughness: 0.5, metalness: 0.25 }), 0.5); },
    C_RoofFlat: () => dress(std({ vertexColors: true }), 'concrete'),
  };
  g.scene.traverse((o) => {
    if (!o.isMesh) return;
    const name = o.material.name; if (flatUV.has(name)) groundUV(o.geometry);
    if (MAT[name]) o.material = MAT[name]();
    o.receiveShadow = true; o.castShadow = ['C_House', 'C_Office', 'C_Sheet', 'C_RoofFlat', 'C_Fence'].includes(name);
  });
  scene.add(g.scene);
} catch (err) { console.error('district not loaded:', err); }
progress(0.68);

// ---------------------------------------------------------------- the venues
const venueRoots = {};
let step = 0;
await Promise.all(VENUES.filter((v) => v.file).map(async (v) => {
  try {
    const g = await loader.loadAsync('/models/' + v.file + V), root = g.scene;
    root.traverse((o) => {
      if (!o.isMesh) return;
      const m = o.material, n = m.name || '';
      if (v.id === 'bk') {
        m.side = THREE.DoubleSide;
        if (n === 'E_Lattice') { const t = texture('lattice_color.jpg', { srgb: true }); if (t) { t.flipY = false; m.map = t; m.emissiveMap = t; m.emissive.set(0xffffff); m.emissiveIntensity = 0.25; } }
        if (n === 'E_Glass' || n === 'E_GlassDark' || n === 'E_Door') { m.metalness = 0.9; m.roughness = 0.08; reflect(m, 1.3); }
      } else if (/glass|glaz|window|water|pool/i.test(n) || m.metalness > 0.5) reflect(m, 1.1);
      else reflect(m, 0.25);
      if (n === 'Kerb') { m.map = null; m.color.set(0xb4ada0); } // plaza edges are plain stone; only street kerbs are painted black and white
      if (m.map) m.map.anisotropy = 8;
      if (m.transparent) { m.depthWrite = false; o.renderOrder = 3; }
    });
    if (v.id === 'bk') dressModel(root, 1);
    shade(root); root.position.set(v.pos[0], v.id === 'bk' ? 0 : 0.13, v.pos[1]); root.rotation.y = v.rot; scene.add(root); venueRoots[v.id] = root;
  } catch (err) { console.warn(v.name + ' model not loaded:', err.message); }
  progress(0.68 + ++step * 0.06);
}));

let seats = null;
if (venueRoots.amahoro) seats = await addAmahoroSeats({ THREE, scene, root: venueRoots.amahoro, loader, V, coarse }).catch((e) => (console.warn('stadium seats not loaded:', e), null));

// ---------------------------------------------------------------- trees, parked cars, street lamps, traffic
const site = await fetch('/tour/site.json' + V).then((r) => r.json()).catch(() => ({ trees: [], cars: [], lamps: [], traffic: [] }));
const o3 = new THREE.Object3D(), col = new THREE.Color();
const PAINT = [0xf2f2f2, 0xd9d9d6, 0x1b1b1d, 0x8b8f96, 0x8f1a1a, 0x1d3f7a, 0xc9c2b2, 0x2b2d31];
let drivers = [];
try {
  const g = await loader.loadAsync('/models/world.glb' + V), geo = (n) => { const o = g.scene.getObjectByName(n); return o && o.geometry; };
  const leaf = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide });
  ['Tree1', 'Tree2', 'Tree3'].map(geo).forEach((tg, k) => {
    const list = site.trees.filter((t) => t[4] === k); if (!tg || !list.length) return;
    const m = new THREE.InstancedMesh(tg, leaf, list.length); m.castShadow = true; m.receiveShadow = true;
    list.forEach(([x, z, s, r], i) => { o3.position.set(x, 0, z); o3.rotation.set(0, r, 0); o3.scale.set(s, s * (0.9 + (i % 7) * 0.04), s); o3.updateMatrix(); m.setMatrixAt(i, o3.matrix);
      m.setColorAt(i, col.setHSL(0.27, 0.0, 0.78 + (i % 5) * 0.05)); });
    scene.add(m);
  });
  const paintMat = reflect(new THREE.MeshStandardMaterial({ roughness: 0.3, metalness: 0.55 }), 0.8), glassMat = reflect(new THREE.MeshStandardMaterial({ color: 0x141c20, roughness: 0.06, metalness: 0.7 }), 1.2);
  const trimMat = new THREE.MeshStandardMaterial({ color: 0x0c0d0e, roughness: 0.7 }), lightMat = new THREE.MeshBasicMaterial({ color: 0xf6f3e6 });
  const MOVING = coarse ? 24 : 54;
  const fleets = [1, 2, 3].map((n, k) => {
    const parked = site.cars.filter((c) => c[3] === k), count = parked.length + MOVING / 3;
    const parts = [[`Car${n}_Body`, paintMat], [`Car${n}_Glass`, glassMat], [`Car${n}_Trim`, trimMat], [`Car${n}_Lights`, lightMat]].filter(([nm]) => geo(nm)).map(([nm, mat]) => new THREE.InstancedMesh(geo(nm), mat, count));
    parts.forEach((p) => { p.castShadow = true; p.frustumCulled = false; scene.add(p); });
    const put = (i, x, z, ry) => { o3.position.set(x, 0.07, z); o3.rotation.set(0, ry, 0); o3.scale.setScalar(1); o3.updateMatrix(); parts.forEach((p) => p.setMatrixAt(i, o3.matrix)); };
    parked.forEach(([x, z, ry, , c], i) => { put(i, x, z, ry); parts[0].setColorAt(i, col.setHex(PAINT[c])); });
    return { parts, put, base: parked.length };
  });
  // traffic: cars follow the main roads, keeping to the right
  const paths = site.traffic.map((t) => { const p = t.pts.map(([x, z]) => new THREE.Vector2(x, z)), cum = [0]; for (let i = 1; i < p.length; i++) cum.push(cum[i - 1] + p[i].distanceTo(p[i - 1])); return { p, cum, len: cum[cum.length - 1], w: t.w, oneway: t.oneway }; }).filter((t) => t.len > 120);
  const total = paths.reduce((s, t) => s + t.len, 0); let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < MOVING && paths.length; i++) {
    let pick = rnd() * total, path = paths[0]; for (const t of paths) { if ((pick -= t.len) <= 0) { path = t; break; } }
    const f = fleets[i % 3], slot = f.base + Math.floor(i / 3); f.parts[0].setColorAt(slot, col.setHex(PAINT[i % PAINT.length]));
    drivers.push({ f, slot, path, s: rnd() * path.len, dir: path.oneway || rnd() < 0.5 ? 1 : -1, speed: 8 + rnd() * 6 });
  }
  fleets.forEach((f) => f.parts.forEach((p) => { p.instanceMatrix.needsUpdate = true; if (p.instanceColor) p.instanceColor.needsUpdate = true; }));
} catch (err) { console.warn('trees and cars not loaded:', err.message); }
function drive(dt) {
  for (const d of drivers) {
    d.s += d.speed * dt * d.dir; if (d.s > d.path.len) d.s -= d.path.len; if (d.s < 0) d.s += d.path.len;
    const { p, cum } = d.path; let i = 1; while (i < cum.length - 1 && cum[i] < d.s) i++;
    const a = p[i - 1], b = p[i], k = (d.s - cum[i - 1]) / Math.max(0.001, cum[i] - cum[i - 1]), dx = (b.x - a.x) * d.dir, dz = (b.y - a.y) * d.dir, l = Math.hypot(dx, dz) || 1;
    const off = d.path.oneway ? 0 : d.path.w / 4; // to the right of the direction of travel
    d.f.put(d.slot, a.x + (b.x - a.x) * k - dz / l * off, a.y + (b.y - a.y) * k + dx / l * off, Math.atan2(dx, dz));
  }
  const seen = new Set(drivers.map((d) => d.f)); seen.forEach((f) => f.parts.forEach((p) => (p.instanceMatrix.needsUpdate = true)));
}
{ // street lamps
  const n = site.lamps.length; if (n) {
    const pole = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.08, 0.12, 9, 8).translate(0, 4.5, 0), dress(new THREE.MeshStandardMaterial({ color: 0x8c9296, metalness: 0.6, roughness: 0.5 }), 'metal'), n);
    const head = new THREE.InstancedMesh(new THREE.BoxGeometry(0.34, 0.12, 1.5).translate(0, 9, 0.7), new THREE.MeshStandardMaterial({ color: 0x9a9fa3, metalness: 0.5, roughness: 0.5 }), n);
    site.lamps.forEach(([x, z, ry], i) => { o3.position.set(x, 0, z); o3.rotation.set(0, ry, 0); o3.scale.setScalar(1); o3.updateMatrix(); pole.setMatrixAt(i, o3.matrix); head.setMatrixAt(i, o3.matrix); });
    pole.castShadow = true; scene.add(pole, head);
  }
}
progress(0.97);

// ---------------------------------------------------------------- moving about
const controls = new MapControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.screenSpacePanning = false; controls.zoomToCursor = true;
controls.minDistance = 30; controls.maxDistance = 1500; controls.maxPolarAngle = 84 * deg; controls.target.set(-90, 0, 170);
controls.autoRotateSpeed = 0.45;
let mode = 'fly', tween = null, place = null, menu = true;
const walk = { yaw: 0, pitch: 0, goal: null, look: null };
// everything that can steer: the two on-screen sticks, the keyboard and a game controller all end up here
const input = { keys: new Set(), L: new THREE.Vector2(), R: new THREE.Vector2(), padL: new THREE.Vector2(), padR: new THREE.Vector2(), run: false, padRun: false, zoom: 0, padZoom: 0 };
const EYE = 1.7, HOME = new THREE.Vector2(-110, 190);
// Zaria Court's north and east sides stand 4.5 m above the court: steps, bleachers and grass banks lead up to them.
// Numbers are in the model's own metres and must match blender/py/120_zaria.py (OX, OY, the plateau outline, the steps).
const ZPLAT = [[53, 4.85], [59, 4.85], [59, -8], [76, -8], [82, -28], [136, -28], [136, 24], [110, 52], [-16, 52], [-16, 43], [53, 43]];
const ZEDGE = [[62, -8], [76, -8], [82, -28], [136, -28], [136, 24], [110, 52], [-16, 52], [-16, 43]];
function heightAt(x, z) {
  const v = VENUES[2], dx = x - v.pos[0], dz = z - v.pos[1], c = Math.cos(v.rot), s = Math.sin(v.rot);
  const X = dx * c - dz * s + 25, Y = -dx * s - dz * c + 11;
  if (X < -30 || X > 150 || Y < -40 || Y > 66) return 0;
  let inside = false;
  for (let i = 0, j = ZPLAT.length - 1; i < ZPLAT.length; j = i++) {
    const a = ZPLAT[i], b = ZPLAT[j];
    if ((a[1] > Y) !== (b[1] > Y) && X < (b[0] - a[0]) * (Y - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  if (inside) return 4.5;
  let h = 0;
  if (Y >= 34 && Y < 43 && X >= -16 && X < 53) h = Math.ceil((Y - 34) / 0.9) * 0.45;
  if (X >= 45 && X < 53 && Y >= 5 && Y < 43) h = Math.max(h, Math.ceil((X - 45) / 0.8) * 0.45);
  let d = 1e9;
  for (let i = 0; i < ZEDGE.length - 1; i++) {
    const a = ZEDGE[i], b = ZEDGE[i + 1], ex = b[0] - a[0], ey = b[1] - a[1];
    const k = Math.max(0, Math.min(1, ((X - a[0]) * ex + (Y - a[1]) * ey) / (ex * ex + ey * ey)));
    d = Math.min(d, Math.hypot(X - a[0] - ex * k, Y - a[1] - ey * k));
  }
  if (d < 7) h = Math.max(h, 4.5 * (1 - d / 7));
  return h;
}

function airPose(v) {
  const a = v.air, at = a.at ? local(v, a.at[0], a.at[1]) : v.pos, target = new THREE.Vector3(at[0], 0, at[1]), az = a.az * deg, el = a.el * deg;
  return { pos: new THREE.Vector3(target.x + Math.sin(az) * Math.cos(el) * a.dist, Math.sin(el) * a.dist, target.z + Math.cos(az) * Math.cos(el) * a.dist), look: target };
}
function groundPose(v) {
  const p = local(v, v.walk[0], v.walk[1]), l = local(v, v.walk[2], v.walk[3]);
  return { pos: new THREE.Vector3(p[0], EYE, p[1]), look: new THREE.Vector3(l[0], Math.min(v.top * 0.35, 9), l[1]) };
}
// one straight move of the camera from where it is to a new position, turning as it goes
function moveTo(pos, look, ms, after) {
  const q1 = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(pos, look, UP));
  tween = { p0: camera.position.clone(), q0: camera.quaternion.clone(), p1: pos.clone(), q1, look: look.clone(), t0: performance.now(), ms, after };
  controls.enabled = false; walk.goal = null;
}
const syncWalk = () => { const e = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ'); walk.yaw = e.y; walk.pitch = e.x; };
const syncFly = (look) => () => { controls.target.copy(look); controls.enabled = true; controls.update(); };
let hintTimer = 0;
function hint(text) { const h = $('hint'); h.textContent = text; h.classList.remove('gone'); clearTimeout(hintTimer); hintTimer = setTimeout(() => h.classList.add('gone'), 9000); }
function setMode(m) {
  mode = m; document.body.dataset.mode = m; input.run = false; $('a-run').classList.remove('on'); $('places').hidden = true;
  $('fly-txt').textContent = m === 'fly' ? 'Land' : 'Fly';
  $('fly-ico').setAttribute('d', m === 'fly' ? 'M12 3v14M6 11l6 6 6-6M5 21h14' : 'M12 21V7M6 13l6-6 6 6M5 3h14');
  hint(m === 'fly' ? 'Left stick flies you over the map · right stick turns · Land drops you where you are looking'
    : 'Left stick walks · right stick looks · walk into the gold coins · Fly lifts you back up');
}
function landAt(x, z, lookAt) { // come down to eye level at a spot on the ground
  const pos = new THREE.Vector3(x, EYE + heightAt(x, z), z);
  let look = lookAt; if (!look) { const d = new THREE.Vector3(x - camera.position.x, 0, z - camera.position.z).normalize(); look = pos.clone().addScaledVector(d, 30); look.y = pos.y + 1; }
  setMode('walk'); $('card').hidden = true;
  moveTo(pos, look, 1800, syncWalk);
}
function takeOff() { // rise straight back and up from where you stand
  const f = new THREE.Vector3(); camera.getWorldDirection(f); f.y = 0; f.normalize();
  const look = camera.position.clone().addScaledVector(f, 40); look.y = 0;
  const pos = look.clone().addScaledVector(f, -190); pos.y = 150;
  setMode('fly'); moveTo(pos, look, 1600, syncFly(look));
}
function visit(v) {
  place = v; if (mode === 'fly') showCard(v); else $('card').hidden = true; $('places').hidden = true;
  document.querySelectorAll('#places button').forEach((b) => b.classList.toggle('on', b.dataset.id === v.id));
  if (mode === 'walk') { const g = groundPose(v); moveTo(g.pos, g.look, 2200, syncWalk); }
  else { const a = airPose(v); moveTo(a.pos, a.look, 2000, syncFly(a.look)); }
}
function showCard(v) {
  const c = $('card'); c.hidden = false;
  c.innerHTML = `<button class="x" data-act="close" aria-label="Close">×</button><small>${v.kind}</small><h2>${v.name}</h2><p>${v.text}</p>
    <div class="row"><button class="primary" data-act="ground">Walk here</button>${v.inside ? '<button data-act="inside">' + v.inside.label + '</button>' : ''}${v.link ? `<a href="${v.link[1]}">${v.link[0]}</a>` : ''}</div>`;
}
function goInside(v) { const p = local(v, v.inside.at[0], v.inside.at[1]), l = local(v, v.inside.look[0], v.inside.look[1]); $('card').hidden = true; landAt(p[0], p[1], new THREE.Vector3(l[0], 6, l[1])); }
$('card').addEventListener('click', (e) => {
  const act = e.target.dataset.act; if (!act) return;
  if (act === 'close') { $('card').hidden = true; return; }
  if (act === 'ground') { const g = groundPose(place); landAt(g.pos.x, g.pos.z, g.look); }
  if (act === 'inside') goInside(place);
});

// ---------------------------------------------------------------- the game layer: places to discover, coins to collect
let save = {}; try { save = JSON.parse(localStorage.getItem('ksc-tour') || '{}'); } catch { save = {}; }
const found = new Set(save.places || []), got = new Set(save.coins || []);
const keep = () => { try { localStorage.setItem('ksc-tour', JSON.stringify({ places: [...found], coins: [...got] })); } catch { /* private window: play on without saving */ } };
let toastTimer = 0;
function toast(text) { const t = $('toast'); t.textContent = text; t.hidden = false; t.style.animation = 'none'; void t.offsetWidth; t.style.animation = ''; clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 2800); }
// [place, metres east, metres north] in that place's own frame
const COIN_AT = [[0, 0, 112], [0, -70, 80], [0, 78, 62], [1, 0, 0], [1, -112, 0], [1, 0, 150], [1, 104, -30], [2, 7.5, 8.5], [2, 82, -11], [2, -100, -17], [2, -35, 9], [3, 26, 52], [3, -34, -40], [4, 0, 40], [4, 30, 78]];
const coinGeo = new THREE.CylinderGeometry(0.55, 0.55, 0.1, 28).rotateX(Math.PI / 2), beamGeo = new THREE.CylinderGeometry(0.5, 0.5, 60, 10, 1, true).translate(0, 30, 0);
const coinMat = new THREE.MeshStandardMaterial({ color: 0xfad201, metalness: 1, roughness: 0.25, emissive: 0x8a6400, emissiveIntensity: 0.9 });
const beamMat = new THREE.MeshBasicMaterial({ color: 0xffe45a, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, fog: false });
const coins = COIN_AT.map(([vi, x, n], i) => {
  const p = local(VENUES[vi], x, n), g = new THREE.Group(), c = new THREE.Mesh(coinGeo, coinMat), b = new THREE.Mesh(beamGeo, beamMat);
  c.position.y = 1.25; g.add(c, b); g.position.set(p[0], heightAt(p[0], p[1]), p[1]); g.visible = !got.has(i); scene.add(g);
  return { g, c, i };
});
function score() { $('n-places').textContent = found.size; $('n-coins').textContent = got.size; }
function play(dt, now) {
  for (const k of coins) if (k.g.visible) { k.c.rotation.y = now * 0.003 + k.i; k.c.position.y = 1.25 + Math.sin(now * 0.004 + k.i) * 0.12; }
  if (mode !== 'walk' || tween) return;
  const p = camera.position;
  for (const k of coins) if (k.g.visible && Math.hypot(p.x - k.g.position.x, p.z - k.g.position.z) < 2.6) {
    k.g.visible = false; got.add(k.i); keep(); score();
    toast(got.size === coins.length ? 'All 15 coins found. You know the complex better than most!' : `Coin ${got.size} of ${coins.length}`);
  }
  for (const v of VENUES) if (!found.has(v.id) && Math.hypot(p.x - v.pos[0], p.z - v.pos[1]) < v.reach) { found.add(v.id); keep(); score(); toast(`Discovered: ${v.name}  ·  ${found.size} of ${VENUES.length}`); refreshPlaces(); }
}
// what the action in front of you is, if any
let offer = null;
function lookForOffer() {
  let o = null; const p = camera.position;
  if (mode === 'walk' && !tween) {
    const bk = VENUES[0], am = VENUES[1], e = local(bk, 0, 104);
    if (Math.hypot(p.x - e[0], p.z - e[1]) < 55) o = { text: 'Go inside and choose your seat', run: () => { location.href = '/'; } };
    else {
      const dx = p.x - am.pos[0], dz = p.z - am.pos[1], c = Math.cos(am.rot), s = Math.sin(am.rot), X = dx * c - dz * s, N = -dx * s - dz * c, k = (X / 92) ** 2 + (N / 125) ** 2;
      if (k < 0.85) o = { text: 'Leave the stadium', run: () => { const g = groundPose(am); landAt(g.pos.x, g.pos.z, g.look); } };
      else if (k < 2.3) o = { text: 'Step onto the pitch', run: () => goInside(am) };
    }
  }
  if ((o && o.text) !== (offer && offer.text)) { offer = o; const el = $('prompt'); el.hidden = !o; if (o) el.innerHTML = `${coarse ? '' : '<kbd>E</kbd>'}${o.text}`; }
}
$('prompt').onclick = () => offer && offer.run();

// mini-map: you in the middle, your heading up, the places and the coins still to find
const mapC = $('map'), mctx = mapC.getContext('2d'), fwd = new THREE.Vector3();
function drawMap() {
  const W = mapC.width, R = W / 2, me = mode === 'walk' || tween ? camera.position : controls.target, span = mode === 'walk' ? 170 : 520, k = R / span;
  camera.getWorldDirection(fwd); const a = Math.atan2(fwd.x, -fwd.z), ca = Math.cos(-a), sa = Math.sin(-a);
  const at = (x, z) => { const dx = (x - me.x) * k, dz = (z - me.z) * k; return [R + dx * ca - dz * sa, R + dx * sa + dz * ca]; };
  mctx.clearRect(0, 0, W, W); mctx.save(); mctx.beginPath(); mctx.arc(R, R, R - 3, 0, 7); mctx.clip();
  mctx.strokeStyle = 'rgba(255,255,255,.22)'; mctx.lineWidth = 1.5; for (const r of [0.33, 0.66]) { mctx.beginPath(); mctx.arc(R, R, R * r, 0, 7); mctx.stroke(); }
  for (const v of VENUES) {
    let [x, y] = at(v.pos[0], v.pos[1]); const d = Math.hypot(x - R, y - R), edge = R - 14; if (d > edge) { x = R + (x - R) * edge / d; y = R + (y - R) * edge / d; }
    mctx.fillStyle = found.has(v.id) ? '#ffffff' : 'rgba(255,255,255,.45)'; mctx.beginPath(); mctx.arc(x, y, d > edge ? 5 : 8, 0, 7); mctx.fill();
    mctx.fillStyle = '#0b0f16'; mctx.font = '700 11px -apple-system, system-ui, sans-serif'; mctx.textAlign = 'center'; mctx.textBaseline = 'middle'; if (d <= edge) mctx.fillText(v.name[0], x, y + 0.5);
  }
  mctx.fillStyle = '#fad201';
  for (const c of coins) if (c.g.visible) { const [x, y] = at(c.g.position.x, c.g.position.z); if (Math.hypot(x - R, y - R) < R - 8) { mctx.beginPath(); mctx.arc(x, y, 4, 0, 7); mctx.fill(); } }
  mctx.restore();
  mctx.fillStyle = '#fff'; mctx.strokeStyle = '#0b0f16'; mctx.lineWidth = 2; mctx.beginPath(); mctx.moveTo(R, R - 13); mctx.lineTo(R + 9, R + 10); mctx.lineTo(R, R + 5); mctx.lineTo(R - 9, R + 10); mctx.closePath(); mctx.stroke(); mctx.fill();
  const n = [R + Math.sin(-a) * (R - 12), R - Math.cos(-a) * (R - 12)]; mctx.fillStyle = '#fad201'; mctx.font = '800 15px -apple-system, system-ui, sans-serif'; mctx.textAlign = 'center'; mctx.textBaseline = 'middle'; mctx.fillText('N', n[0], n[1]);
}

// travel list, and a name tag floating over each place
function refreshPlaces() { document.querySelectorAll('#places button').forEach((b) => { b.lastElementChild.textContent = found.has(b.dataset.id) ? '' : 'NEW'; }); }
const tags = VENUES.map((v) => {
  const b = document.createElement('button'); b.innerHTML = `<span>${v.name}</span><i></i>`; b.dataset.id = v.id; b.onclick = () => visit(v); $('places').append(b);
  const t = document.createElement('button'); t.className = 'tag'; t.textContent = v.name; t.onclick = () => visit(v); $('tags').append(t);
  return { el: t, at: new THREE.Vector3(v.pos[0], v.top, v.pos[1]) };
});
refreshPlaces(); score();
const scr = new THREE.Vector3();
function placeTags() {
  for (const t of tags) {
    const d = camera.position.distanceTo(t.at), ahead = scr.copy(t.at).applyMatrix4(camera.matrixWorldInverse).z < 0; scr.copy(t.at).project(camera);
    const show = ahead && Math.abs(scr.x) < 1.05 && Math.abs(scr.y) < 1.05 && mode === 'fly' && d > 90 && !tween;
    t.el.style.display = show ? '' : 'none';
    if (show) { t.el.style.left = ((scr.x + 1) / 2 * innerWidth) + 'px'; t.el.style.top = ((1 - scr.y) / 2 * innerHeight - 14) + 'px'; }
  }
}

// ---------------------------------------------------------------- controls: sticks, buttons, keys, controller, and the screen itself
function stick(el, out) { // a thumb stick that works with a finger or the mouse; out.x = right, out.y = forward/up
  const knob = el.querySelector('b'); let id = null;
  const set = (e) => { const r = el.getBoundingClientRect(), reach = r.width * 0.3; let x = (e.clientX - r.left - r.width / 2) / reach, y = (e.clientY - r.top - r.height / 2) / reach; const l = Math.max(1, Math.hypot(x, y)); x /= l; y /= l;
    out.set(x, -y); knob.style.transform = `translate(${x * reach}px, ${y * reach}px)`; };
  el.addEventListener('pointerdown', (e) => { id = e.pointerId; el.setPointerCapture(id); el.classList.add('held'); set(e); walk.goal = null; e.preventDefault(); });
  el.addEventListener('pointermove', (e) => { if (e.pointerId === id) set(e); });
  const end = (e) => { if (e.pointerId === id) { id = null; out.set(0, 0); knob.style.transform = ''; el.classList.remove('held'); } };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end); el.addEventListener('lostpointercapture', end);
}
stick($('padL'), input.L); stick($('padR'), input.R);
const toggleFly = () => { if (tween) return; if (mode === 'walk') takeOff(); else landAt(controls.target.x, controls.target.z); };
$('a-fly').onclick = toggleFly;
$('a-run').onclick = () => { input.run = !input.run; $('a-run').classList.toggle('on', input.run); };
$('a-go').onclick = () => { $('places').hidden = !$('places').hidden; };
for (const [id, dir] of [['a-zin', -1], ['a-zout', 1]]) {
  const b = $(id); b.addEventListener('pointerdown', (e) => { input.zoom = dir; b.setPointerCapture(e.pointerId); });
  for (const ev of ['pointerup', 'pointercancel', 'lostpointercapture']) b.addEventListener(ev, () => { input.zoom = 0; });
}
function startGame() { menu = false; delete document.body.dataset.menu; controls.autoRotate = false; setMode(mode); try { history.replaceState(null, '', '#explore'); } catch { /* no history: fine */ } }
$('start').onclick = startGame;

// pointing at the ground
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), floor = new THREE.Plane(UP, 0), hit = new THREE.Vector3();
function groundAt(e) { ndc.set(e.clientX / innerWidth * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); ray.setFromCamera(ndc, camera); return ray.ray.intersectPlane(floor, hit) && hit.distanceTo(camera.position) < 2500 ? hit : null; }
let lastTap = 0, lastTapAt = [0, 0];
canvas.addEventListener('pointerdown', (e) => {
  $('places').hidden = true; if (tween) return;
  if (mode === 'walk') { walk.look = { id: e.pointerId, x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, moved: false }; canvas.setPointerCapture(e.pointerId); }
  else walk.look = { id: e.pointerId, sx: e.clientX, sy: e.clientY, moved: false, fly: true };
});
canvas.addEventListener('pointermove', (e) => {
  const L = walk.look; if (!L || L.id !== e.pointerId) return;
  if (Math.hypot(e.clientX - L.sx, e.clientY - L.sy) > 7) L.moved = true;
  if (L.fly) return;
  walk.yaw -= (e.clientX - L.x) * 0.0042; walk.pitch = Math.max(-1.1, Math.min(1.25, walk.pitch - (e.clientY - L.y) * 0.0042)); L.x = e.clientX; L.y = e.clientY;
});
canvas.addEventListener('pointerup', (e) => {
  const L = walk.look; if (!L || L.id !== e.pointerId) return; walk.look = null;
  if (L.moved || tween) return;
  const g = groundAt(e); if (!g) return;
  if (L.fly) { // double click or double tap in the air: come down there
    const now = performance.now(), dbl = now - lastTap < 380 && Math.hypot(e.clientX - lastTapAt[0], e.clientY - lastTapAt[1]) < 30; lastTap = now; lastTapAt = [e.clientX, e.clientY];
    if (dbl) landAt(g.x, g.z);
  } else if (g.distanceTo(camera.position) < 260 && heightAt(camera.position.x, camera.position.z) < 0.5) walk.goal = new THREE.Vector2(g.x, g.z);
});
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.repeat) return; const k = e.key.toLowerCase(); input.keys.add(k);
  if (menu) { if (k === 'enter' || k === ' ') startGame(); return; }
  if (e.key.startsWith('Arrow') || k === ' ') e.preventDefault();
  if (k === 'f' || k === ' ' || (k === 'escape' && mode === 'walk')) toggleFly();
  if (k === 'e' || k === 'enter') offer && offer.run();
  if (k === 'm') $('places').hidden = !$('places').hidden;
});
addEventListener('keyup', (e) => input.keys.delete(e.key.toLowerCase()));
addEventListener('blur', () => input.keys.clear());
// a game controller, if one is plugged in: left stick moves, right stick looks, A = action, B = run, Y = fly or land, triggers zoom
const padWas = [];
function pollPad() {
  const gp = (navigator.getGamepads ? [...navigator.getGamepads()] : []).find((g) => g && g.connected);
  if (!gp) { input.padL.set(0, 0); input.padR.set(0, 0); input.padRun = false; input.padZoom = 0; return; }
  const dz = (v) => (Math.abs(v) < 0.16 ? 0 : v), down = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed), hit = (i) => { const d = down(i), was = padWas[i]; padWas[i] = d; return d && !was; };
  input.padL.set(dz(gp.axes[0] || 0), -dz(gp.axes[1] || 0)); input.padR.set(dz(gp.axes[2] || 0), -dz(gp.axes[3] || 0));
  input.padRun = down(1) || down(10); input.padZoom = (down(6) ? 1 : 0) - (down(7) ? 1 : 0);
  if (hit(0)) { if (menu) startGame(); else if (offer) offer.run(); }
  if (hit(3) && !menu) toggleFly();
  if (hit(2) && !menu) $('places').hidden = !$('places').hidden;
}
const mv = new THREE.Vector2(), lk = new THREE.Vector2();
function readInput() {
  const k = input.keys;
  mv.set((k.has('d') || k.has('arrowright') ? 1 : 0) - (k.has('a') || k.has('arrowleft') ? 1 : 0), (k.has('w') || k.has('arrowup') ? 1 : 0) - (k.has('s') || k.has('arrowdown') ? 1 : 0)).add(input.L).add(input.padL);
  if (mv.lengthSq() > 1) mv.normalize();
  lk.copy(input.R).add(input.padR);
}

// house outlines, sorted into 40 m squares, so walking stops at walls
const cells = new Map();
for (const ring of site.blocks || []) {
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const [x, z] of ring) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  const b = { ring, x0: x0 - 0.5, x1: x1 + 0.5, z0: z0 - 0.5, z1: z1 + 0.5 };
  for (let gx = Math.floor(b.x0 / 40); gx <= Math.floor(b.x1 / 40); gx++) for (let gz = Math.floor(b.z0 / 40); gz <= Math.floor(b.z1 / 40); gz++) { const k = gx + ',' + gz; if (!cells.has(k)) cells.set(k, []); cells.get(k).push(b); }
}
function blocked(x, z) {
  for (const b of cells.get(Math.floor(x / 40) + ',' + Math.floor(z / 40)) || []) {
    if (x < b.x0 || x > b.x1 || z < b.z0 || z > b.z1) continue;
    let inside = false; const r = b.ring;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) if ((r[i][1] > z) !== (r[j][1] > z) && x < (r[j][0] - r[i][0]) * (z - r[i][1]) / (r[j][1] - r[i][1]) + r[i][0]) inside = !inside;
    if (inside) return true;
  }
  return false;
}
const tether = (p) => { const far = Math.hypot(p.x - HOME.x, p.z - HOME.y); if (far > 950) { p.x = HOME.x + (p.x - HOME.x) * 950 / far; p.z = HOME.y + (p.z - HOME.y) * 950 / far; } };
function stepWalk(dt) {
  const run = input.run || input.padRun || input.keys.has('shift');
  const speed = (run ? 15 : 5.5) * dt, sin = Math.sin(walk.yaw), cos = Math.cos(walk.yaw), p = camera.position, ox = p.x, oz = p.z;
  walk.yaw -= lk.x * 2.3 * dt; walk.pitch = Math.max(-1.1, Math.min(1.25, walk.pitch + lk.y * 1.5 * dt));
  if (mv.x || mv.y) { walk.goal = null; p.x += (-sin * mv.y + cos * mv.x) * speed; p.z += (-cos * mv.y - sin * mv.x) * speed; }
  else if (walk.goal) { const dx = walk.goal.x - p.x, dz = walk.goal.y - p.z, d = Math.hypot(dx, dz), s = Math.min(d, Math.max(6, d * 1.2) * dt); if (d < 0.4) walk.goal = null; else { p.x += dx / d * s; p.z += dz / d * s; } }
  tether(p);
  if (blocked(p.x, p.z) && !blocked(ox, oz)) { // slide along the wall if one direction is still free, otherwise stop
    if (!blocked(p.x, oz)) p.z = oz; else if (!blocked(ox, p.z)) p.x = ox; else { p.x = ox; p.z = oz; } walk.goal = null;
  }
  p.y += (EYE + heightAt(p.x, p.z) - p.y) * Math.min(1, dt * 9); camera.rotation.set(walk.pitch, walk.yaw, 0, 'YXZ');
}
const off = new THREE.Vector3(), sph = new THREE.Spherical(), slide = new THREE.Vector3();
function stepFly(dt) { // the sticks fly the camera: left slides over the ground, right turns and tilts, the two buttons move in and out
  const zoom = input.zoom + input.padZoom + (input.keys.has('q') ? 1 : 0) - (input.keys.has('z') ? 1 : 0);
  if (!mv.x && !mv.y && !lk.x && !lk.y && !zoom) return;
  const t = controls.target; off.copy(camera.position).sub(t); sph.setFromVector3(off);
  sph.theta -= lk.x * 1.5 * dt; sph.phi = Math.max(0.12, Math.min(controls.maxPolarAngle, sph.phi - lk.y * 1.0 * dt));
  sph.radius = Math.max(controls.minDistance, Math.min(controls.maxDistance, sph.radius * (1 + zoom * 1.3 * dt)));
  const sp = Math.max(40, sph.radius * 0.9) * (input.keys.has('shift') || input.padRun ? 2 : 1) * dt, s = Math.sin(sph.theta), c = Math.cos(sph.theta);
  slide.set((-s * mv.y + c * mv.x) * sp, 0, (-c * mv.y - s * mv.x) * sp); t.add(slide); tether(t);
  camera.position.setFromSpherical(sph).add(t); camera.lookAt(t);
}

// ---------------------------------------------------------------- run
function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
setMode('fly'); controls.autoRotate = true; controls.update();
if (location.hash === '#explore') startGame();
let last = performance.now(), slow = 0;
const focus = new THREE.Vector3();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  pollPad(); readInput();
  if (tween) {
    const k = Math.min(1, (now - tween.t0) / tween.ms), e = ease(k);
    camera.position.lerpVectors(tween.p0, tween.p1, e); camera.quaternion.slerpQuaternions(tween.q0, tween.q1, e);
    if (k >= 1) { const after = tween.after; tween = null; if (after) after(); }
  } else if (mode === 'walk') stepWalk(dt);
  else { if (!menu) stepFly(dt); controls.update(); }
  drive(dt); play(dt, now);
  if ((slow += dt) > 0.2) { slow = 0; lookForOffer(); }
  if (mode === 'walk') { focus.copy(camera.position); focus.y = 0; aimSun(focus, 150); }
  else { focus.copy(tween ? tween.look : controls.target); aimSun(focus, Math.max(160, Math.min(520, camera.position.distanceTo(focus) * 0.7))); }
  if (seats) seats.update(camera);
  placeTags(); if (!menu) drawMap();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
progress(1);
document.body.dataset.mode = 'fly';
requestAnimationFrame(frame);
window.__tour = { stand: (x, z, lx, lz, ly = 8) => landAt(x, z, new THREE.Vector3(lx, ly, lz)), scene, camera, controls, VENUES, visit, landAt, takeOff, renderer, input, startGame, coins, get mode() { return mode; } };
