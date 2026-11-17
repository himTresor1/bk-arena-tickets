import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { buildArena, makeLabel, COLORS } from './arena.js';
import { preload, texture, dress, dressModel, setEnvironment, reflect } from './textures.js';
import { useDemoBackendIfNeeded } from './demo-backend.js';

await useDemoBackendIfNeeded(); // on a static host there is no server: run the seat database in the browser instead
// wait briefly for the typeface, so numbers painted onto signs and labels use it too
try { await Promise.race([document.fonts.load('700 72px Geist'), new Promise((r) => setTimeout(r, 1500))]); } catch { /* fall back to the system font */ }
import { buildSeats, seatId } from '../shared/layout.js';
import qrcode from 'qrcode-generator';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const $ = (id) => document.getElementById(id);
const UP = new THREE.Vector3(0, 1, 0);
const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const coarse = matchMedia('(pointer: coarse)').matches;
let touch = coarse; // switches to whatever the person last used
document.body.dataset.touch = touch;

let clientId;
try { clientId = sessionStorage.getItem('bk-client') || crypto.randomUUID(); sessionStorage.setItem('bk-client', clientId); }
catch { clientId = Math.random().toString(36).slice(2); }

// ---------------------------------------------------------------- scene
const canvas = $('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, coarse ? 1.5 : 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;
const scene = new THREE.Scene();
// loading screen: textures are the first 70% of the wait, the models the rest
const progress = (f) => { if (window.__loading) window.__loading(f); };
let loadStep = 0; const tick = () => progress(0.7 + ++loadStep * 0.04); // one tick per model file
await preload((f) => progress(f * 0.7)); // all surface textures and the sky
{ // a real sky with clouds: it is the backdrop, and it is also what glass and metal reflect
  const sky = texture('sky.jpg', { srgb: true });
  if (sky) {
    sky.mapping = THREE.EquirectangularReflectionMapping;
    scene.background = sky;
    const pm = new THREE.PMREMGenerator(renderer); setEnvironment(pm.fromEquirectangular(sky).texture); pm.dispose();
  } else scene.background = new THREE.Color(0xa4c2ca);
}
scene.fog = new THREE.Fog(0xc4d4d6, 500, 1700);
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 3000);
// cars, trees and shrubs modelled in Blender (public/models/world.glb); the surroundings fall back to simple shapes without them
const worldAssets = {};
try {
  const g = await new GLTFLoader().loadAsync('/models/world.glb?v=' + __BUILD__), geo = (n) => { const o = g.scene.getObjectByName(n); return o && o.geometry; };
  worldAssets.cars = [1, 2, 3].map((n) => ({ body: geo(`Car${n}_Body`), glass: geo(`Car${n}_Glass`), trim: geo(`Car${n}_Trim`), lights: geo(`Car${n}_Lights`) })).filter((c) => c.body && c.glass);
  worldAssets.trees = ['Tree1', 'Tree2', 'Tree3'].map(geo).filter(Boolean); worldAssets.bush = geo('Bush');
  if (!worldAssets.trees.length) delete worldAssets.trees;
} catch (err) { console.warn('Blender cars and trees not loaded, using simple shapes:', err.message); }
tick();
const arena = buildArena(scene, worldAssets);
arena.setInterior(false);

// ---- A tip-up stadium chair, as at BK Arena: tall plastic back with rounded corners, a seat that
// stands upright against it when empty, and a black steel frame with side arms.
function makeBack(curve) {
  const w = 0.225, h = 0.52, r = 0.07, sh = new THREE.Shape();
  sh.moveTo(-w + 0.03, 0); sh.lineTo(0, 0); sh.lineTo(w - 0.03, 0); sh.lineTo(w, 0.05);
  sh.lineTo(w, h - r); sh.quadraticCurveTo(w, h, w - r, h);
  sh.lineTo(0, h + 0.008); sh.lineTo(-(w - r), h);
  sh.quadraticCurveTo(-w, h, -w, h - r); sh.lineTo(-w, 0.05); sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, { depth: 0.035, bevelEnabled: false, curveSegments: curve });
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) p.setZ(i, p.getZ(i) + 0.9 * p.getX(i) ** 2); // slight wrap
  g.rotateX(-0.12); g.translate(0, 0.42, -0.2); g.computeVertexNormals();
  return g;
}
const frameGeo = (() => {
  const box = (w, h, d, x, y, z, rx = 0) => { const b = new THREE.BoxGeometry(w, h, d); b.rotateX(rx); b.translate(x, y, z); return b; };
  return mergeGeometries([
    box(0.07, 0.44, 0.08, 0, 0.22, -0.2),          // post
    box(0.54, 0.05, 0.05, 0, 0.43, -0.18),         // beam the seat hinges on
    box(0.03, 0.05, 0.34, -0.26, 0.62, -0.04, -0.25), box(0.03, 0.05, 0.34, 0.26, 0.62, -0.04, -0.25), // arms
    box(0.03, 0.22, 0.04, -0.26, 0.52, -0.17), box(0.03, 0.22, 0.04, 0.26, 0.52, -0.17),               // arm supports
  ]);
})();
function makePan(curve) {
  const w = 0.22, sh = new THREE.Shape();
  sh.moveTo(-w, 0); sh.lineTo(0, 0); sh.lineTo(w, 0); sh.lineTo(w, 0.3);
  sh.quadraticCurveTo(w, 0.4, w - 0.1, 0.4); sh.lineTo(0, 0.41); sh.lineTo(-(w - 0.1), 0.4);
  sh.quadraticCurveTo(-w, 0.4, -w, 0.3); sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, { depth: 0.06, bevelEnabled: false, curveSegments: curve });
  g.rotateX(Math.PI / 2); g.computeVertexNormals(); // lies flat, hinged along its back edge
  return g;
}
// Chairs come from the Blender model (public/models/chair.glb): a detailed one for the block being
// looked at ("near") and a simplified one with the same outline for every other seat ("far").
// If the file can't be loaded, the simple chairs built in code above are used instead.
const GEO = { far: { back: makeBack(1), pan: makePan(1), frame: frameGeo }, near: { back: makeBack(3), pan: makePan(3), frame: frameGeo } };
try {
  const gltf = await new GLTFLoader().loadAsync('/models/chair.glb?v=' + __BUILD__);
  const get = (name) => { const o = gltf.scene.getObjectByName(name); if (!o || !o.geometry) throw new Error('missing ' + name); return o.geometry; };
  GEO.near = { back: get('Back_near'), pan: get('Pan_near'), frame: get('Frame_near') };
  GEO.far = { back: get('Back_far'), pan: get('Pan_far'), frame: get('Frame_far') };
  // leather armchairs for the skyboxes (the cushion takes the place of the folding seat and never folds)
  GEO.vipNear = { back: get('Vip_Back_near'), pan: get('Vip_Pan_near'), frame: get('Vip_Frame_near') };
  GEO.vipFar = { back: get('Vip_Back_far'), pan: get('Vip_Pan_far'), frame: get('Vip_Frame_far') };
} catch (err) { console.warn('Blender chair not loaded, using the built-in one:', err.message); }
tick();
const SHARED = new Set(Object.values(GEO).flatMap((g) => Object.values(g)));

// The seating bowl from Blender (public/models/bowl.glb): stepped terraces with baked shading, aisle
// stairs, rails and tunnels. Each block is its own mesh, named Bowl_<section>, and is only shown while
// that section still has the rows and seats it was built for; otherwise the coded ramp and steps are used.
const bowl = new Map();
try {
  const loader = new GLTFLoader();
  loader.setDRACOLoader(new DRACOLoader().setDecoderPath('/draco/'));
  const gltf = await loader.loadAsync('/models/bowl.glb?v=' + __BUILD__);
  gltf.scene.traverse((o) => {
    if (o.isMesh && o.material) { o.material.side = THREE.DoubleSide; if (o.material.emissive && o.material.emissive.getHex()) o.material.emissiveIntensity = 0.3; } // tunnel doorways glow softly, not glare
    const id = o.userData && o.userData.section;
    if (id !== undefined && o.name.startsWith('Bowl_')) bowl.set(String(id), o);
  });
  dressModel(gltf.scene, 0);
  scene.add(gltf.scene);
  (arena.codedTunnels || []).forEach((m) => (m.visible = false));
} catch (err) { console.warn('Blender bowl not loaded, using the built-in terraces:', err.message); }
tick();
// The outside of the building from Blender (public/models/exterior.glb), matched to drone footage: round drum, cream roof,
// patterned screen over dark glass, terrace, colonnade and white letters. The roof fades away when you enter.
try {
  const loader = new GLTFLoader();
  loader.setDRACOLoader(new DRACOLoader().setDecoderPath('/draco/'));
  const gltf = await loader.loadAsync('/models/exterior.glb?v=' + __BUILD__);
  const roofMeshes = [];
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    o.material.side = THREE.DoubleSide;
    if (o.material.name === 'E_Lattice') { const t = texture('lattice_color.jpg', { srgb: true }); if (t) { t.flipY = false; o.material.map = t; o.material.emissiveMap = t; o.material.emissive.set(0xffffff); o.material.emissiveIntensity = 0.3; } } // the patterned screen
    if (o.material.name === 'E_Glass' || o.material.name === 'E_GlassDark' || o.material.name === 'E_Door') { o.material.metalness = 0.9; o.material.roughness = 0.08; reflect(o.material, 1.3); } // glass mirrors the sky
    let p = o, inRoof = false; while (p) { if (p.name === 'Ext_Roof') inRoof = true; p = p.parent; }
    if (inRoof) { o.material = o.material.clone(); o.material.transparent = true; roofMeshes.push(o); }
  });
  if (!roofMeshes.length) throw new Error('missing Ext_Roof');
  dressModel(gltf.scene, 1);
  scene.add(gltf.scene);
  arena.codedExterior.forEach((o) => (o.visible = false));
  arena.roofParts.length = 0; arena.roofParts.push(...roofMeshes);
} catch (err) { console.warn('Blender exterior not loaded, using the built-in one:', err.message); }
tick();
// The centre stage from Blender (public/models/stage.glb), shown when the floor layout is "Centre stage".
try {
  const loader = new GLTFLoader();
  loader.setDRACOLoader(new DRACOLoader().setDecoderPath('/draco/'));
  const gltf = await loader.loadAsync('/models/stage.glb?v=' + __BUILD__);
  gltf.scene.traverse((o) => { if (o.isMesh) o.material.side = THREE.DoubleSide; });
  dressModel(gltf.scene, 0);
  gltf.scene.visible = false; scene.add(gltf.scene); arena.stageModel = gltf.scene;
} catch (err) { console.warn('Blender stage not loaded, using the built-in one:', err.message); }
tick();
// The structure around the bowl from Blender (public/models/structure.glb): wall between the tiers, upper-tier
// supports, furnished skyboxes, corner pillars, and the roof with its trusses, floodlights and scoreboard.
// The roof is only shown from inside the arena, so the aerial view can still look in.
try {
  const loader = new GLTFLoader();
  loader.setDRACOLoader(new DRACOLoader().setDecoderPath('/draco/'));
  const gltf = await loader.loadAsync('/models/structure.glb?v=' + __BUILD__);
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    o.material.side = THREE.DoubleSide;
    if (o.material.transparent || o.material.opacity < 1) { o.material.transparent = true; o.material.depthWrite = false; o.renderOrder = 4; }
  });
  const roof = gltf.scene.getObjectByName('Roof');
  if (!roof) throw new Error('missing Roof');
  dressModel(gltf.scene, 0);
  scene.add(gltf.scene);
  arena.codedInside.visible = false;
  arena.interiorOnly.forEach((m) => (m.visible = false));
  arena.interiorOnly.length = 0; arena.interiorOnly.push(roof);
  arena.setInterior(false);
} catch (err) { console.warn('Blender structure not loaded, using the built-in interior:', err.message); }
tick();
// true when the Blender terrace for this section matches how the section is set up now
const builtTerrace = (cfg) => {
  const m = bowl.get(cfg.id);
  return !!m && cfg.enabled && m.userData.rows === cfg.rows && (cfg.shape === 'arc' || m.userData.seats === cfg.seats);
};
// Lighter drawing for phones that struggle: simpler chairs, and the steel frames only on the block
// you are looking at. Starts on for low-memory phones and switches on by itself if frames run slow.
let lite = coarse && ((navigator.deviceMemory || 8) <= 4 || (navigator.hardwareConcurrency || 8) <= 4);
const hinge = (angle) => new THREE.Matrix4().makeTranslation(0, 0.45, -0.15).multiply(new THREE.Matrix4().makeRotationX(angle));
const A_UP = -1.44, A_DOWN = -0.06, FOLD_MS = 650;
const PAN_UP = hinge(A_UP), PAN_DOWN = hinge(A_DOWN);
const folding = new Map(); // seats whose pan is mid-swing
const seatMat = dress(new THREE.MeshStandardMaterial({ side: THREE.DoubleSide }), 'plastic', { relief: 0.35 }); // moulded plastic; the far chair's back is a single sheet
const leatherMat = dress(new THREE.MeshStandardMaterial({ side: THREE.DoubleSide }), 'leather', { relief: 0.8 }); // skybox armchairs
const frameMat = dress(new THREE.MeshStandardMaterial({ color: 0x15171a, metalness: 0.7 }), 'metal');
const stairMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, side: THREE.DoubleSide });
const slabMat = new THREE.MeshStandardMaterial({ color: 0x191c21, roughness: 0.95, side: THREE.DoubleSide });
const C = Object.fromEntries(Object.entries(COLORS).map(([k, v]) => [k, new THREE.Color(v)]));
const tmp = new THREE.Matrix4();

// ---------------------------------------------------------------- state
let settings = {}, taken = {}, sections = new Map();
let mode = 'intro', active = null, hoverSec = null, hoverSeat = -1, selected = null, bought = null;
// One order can hold several seats. `basket` is every seat picked so far; `selected` is the one whose view is on screen.
let basket = [];
const MAX_SEATS = 8;
const inBasket = (id) => basket.some((b) => b.id === id);
const basketTotal = () => basket.reduce((n, b) => n + b.S.cfg.price, 0);
// after the stands are rebuilt, point each picked seat at its new section (or drop it if the section has gone)
function remapBasket() { basket = basket.filter((b) => { const S = sections.get(b.S.cfg.id); if (!S) return false; b.S = S; return true; }); if (selected && !basket.includes(selected)) selected = null; basket.forEach((b) => paint(b.S)); }
let preview = null;     // on touch: the section tapped once, shown with its price before zooming in
let ticketOff = false; // the buyer put the ticket away to look around
let nav = 0;   // increases on every navigation so stale camera moves can be ignored
let depth = 0; // 0 = whole arena, 1 = a section, 2 = a seat (mirrors the browser's back history)
const group = new THREE.Group(); scene.add(group);

const cur = () => settings.currency || 'RWF';
const price = (n) => Number(n).toLocaleString('en-US');
const tierLabel = (sec) => ({ lower: 'Lower Bowl', upper: 'Upper Bowl', vip: 'VIP Box', platform: 'Platform', floor: 'Floor' }[sec.tier] || 'Section');

const real = () => settings.seatColors !== 'green';
const pickC = () => (real() ? C.orange : C.yellow), holdC = () => (real() ? C.violet : C.blue);
// The colour a free seat has. 'real' copies the arena: green, yellow and blue in loose patches in the
// lower bowl, mostly blue upstairs, black armchairs in the boxes and black chairs on the floor.
function freeColor(cfg, seat, rows) {
  if (cfg.tier === 'vip') return C.black;
  if (!real()) return C.green;
  if (cfg.tier === 'floor' || cfg.tier === 'platform') return C.black;
  const hash = (str) => { let h = 2166136261; for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619); return ((h ^ (h >>> 13)) >>> 0) / 4294967296; };
  const own = hash(seat.id), patch = hash(`${cfg.id}/${Math.floor(seat.row / 2)}/${Math.floor(seat.num / 3)}`);
  const h = hash(seat.id + 'x') < 0.55 ? patch : own; // just over half the seats follow their patch
  if (cfg.tier === 'upper') return h < 0.7 ? C.rBlue : h < 0.9 ? C.rYellow : C.rGreen;
  const f = (seat.row - 1) / Math.max(1, rows - 1), g = 0.2 + (1 - f) * 0.6, y = 0.42, b = 0.14 + f * 0.3, t = h * (g + y + b);
  return t < g ? C.rGreen : t < g + y ? C.rYellow : C.rBlue;
}
function seatColor(S, i) {
  const seat = S.seats[i], st = taken[seat.id];
  if (inBasket(seat.id)) return pickC();
  if (st === 's' || st === 'b') return C.sold;
  if (st === 'h') return holdC();
  if (mode === 'section' && S === active) return i === hoverSeat ? pickC() : S.free[i];
  return S === hoverSec ? pickC() : S.free[i];
}
// a seat is folded down when someone has it, or while you're pointing at it
const isDown = (S, i) => S.armchair || !!taken[S.seats[i].id] || inBasket(S.seats[i].id) || (S === active && i === hoverSeat);
function paintSeat(S, i, animate = false) {
  if (!S || i < 0) return;
  const c = seatColor(S, i), target = isDown(S, i) ? A_DOWN : A_UP, key = S.cfg.id + ':' + i;
  S.mesh.setColorAt(i, c); S.pan.setColorAt(i, c);
  if (animate && Math.abs(S.ang[i] - target) > 0.01) folding.set(key, { S, i, from: S.ang[i], to: target, t0: performance.now() });
  else if (!folding.has(key) || !animate) {
    folding.delete(key); S.ang[i] = target;
    S.pan.setMatrixAt(i, tmp.multiplyMatrices(S.base[i], target === A_DOWN ? PAN_DOWN : PAN_UP));
  }
  S.mesh.instanceColor.needsUpdate = S.pan.instanceColor.needsUpdate = S.pan.instanceMatrix.needsUpdate = true;
}
// swing the seats that are folding or unfolding a little further each frame
function stepFolding(now) {
  folding.forEach((f, key) => {
    const k = Math.min(1, (now - f.t0) / FOLD_MS), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    f.S.ang[f.i] = f.from + (f.to - f.from) * e;
    f.S.pan.setMatrixAt(f.i, tmp.multiplyMatrices(f.S.base[f.i], hinge(f.S.ang[f.i])));
    f.S.pan.instanceMatrix.needsUpdate = true;
    if (k >= 1) folding.delete(key);
  });
}
function paint(S) { if (S) for (let i = 0; i < S.seats.length; i++) paintSeat(S, i); }
function recount(S) { S.left = S.seats.reduce((n, s) => n + (taken[s.id] ? 0 : 1), 0); }

// Ramp under the seats (also what the pointer hits when choosing a section).
function slabGeometry(rows, tier) {
  const K = 7, lines = [];
  const sample = (row, shift, dy) => {
    const line = [];
    for (let k = 0; k < K; k++) {
      const t = (k / (K - 1)) * (row.length - 1), i0 = Math.floor(t), i1 = Math.min(row.length - 1, i0 + 1), f = t - i0;
      const a = row[i0], b = row[i1];
      const fx = Math.sin(a.ry), fz = Math.cos(a.ry);
      const side = (k / (K - 1) - 0.5) * 0.7;
      line.push(new THREE.Vector3(a.x + (b.x - a.x) * f + fx * shift + fz * side, a.y + dy, a.z + (b.z - a.z) * f + fz * shift - fx * side));
    }
    return line;
  };
  const dy = tier === 'floor' ? 0.06 : -0.02;
  if (tier !== 'floor') lines.push(sample(rows[0], 0.5, tier === 'lower' ? -rows[0][0].y : -1.5));
  lines.push(sample(rows[0], 0.5, dy));
  rows.forEach((row) => lines.push(sample(row, -0.42, dy)));
  const pos = [], idx = [];
  lines.forEach((l) => l.forEach((p) => pos.push(p.x, p.y, p.z)));
  for (let r = 0; r < lines.length - 1; r++) for (let k = 0; k < K - 1; k++) {
    const a = r * K + k, b = a + 1, c = a + K, d = c + 1;
    idx.push(a, c, b, b, c, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// Things that belong to a section but aren't seats: the steps either side of it and its number on the wall.
function extras(cfg) {
  const out = [], D = Math.PI / 180;
  const raked = cfg.rise > 0 && (cfg.tier === 'lower' || cfg.tier === 'upper') && !builtTerrace(cfg);
  if (cfg.shape !== 'arc' && raked) {
    // Real steps: two per row of seats, each with a tread, a riser and a pale edge strip.
    const a = cfg.facing * D, ox = Math.cos(a), oz = Math.sin(a), tx = -oz, tz = ox;
    const W = cfg.seats * (cfg.spacing || 0.5) / 2, pos = [], col = [], idx = [];
    const TREAD = [0.42, 0.44, 0.47], RISER = [0.2, 0.21, 0.23], EDGE = [0.86, 0.87, 0.88];
    const quad = (pts, c) => { const k = pos.length / 3; pts.forEach((p) => { pos.push(p[0], p[1], p[2]); col.push(c[0], c[1], c[2]); }); idx.push(k, k + 1, k + 2, k, k + 2, k + 3); };
    for (const side of [-1, 1]) {
      const l0 = (W + 0.12) * side, l1 = (W + 0.4) * side;
      const P = (lat, d, y) => [cfg.x + ox * d + tx * lat, y, cfg.z + oz * d + tz * lat];
      const step = (d0, d1, yLow, y) => { // riser at d0 from yLow up to y, then a tread from d0 to d1
        quad([P(l0, d0, yLow), P(l1, d0, yLow), P(l1, d0, y), P(l0, d0, y)], RISER);
        quad([P(l0, d0, y + 0.012), P(l1, d0, y + 0.012), P(l1, d0 + 0.07, y + 0.012), P(l0, d0 + 0.07, y + 0.012)], EDGE);
        quad([P(l0, d0, y), P(l1, d0, y), P(l1, d1, y), P(l0, d1, y)], TREAD);
      };
      const half = cfg.rowDepth / 2, front = -0.4;
      if (cfg.baseY > 0.3 && cfg.baseY < 1.5) { // steps up from the arena floor to the first row
        const n = Math.round(cfg.baseY / 0.3), h = cfg.baseY / n;
        for (let k = n - 1; k >= 1; k--) step(front - k * 0.3, front - (k - 1) * 0.3, cfg.baseY - (k + 1) * h, cfg.baseY - k * h);
      }
      for (let r = 0; r < cfg.rows; r++) {
        const d = front + r * cfg.rowDepth, y = cfg.baseY + r * cfg.rise + 0.03;
        step(d, d + half, y - (r === 0 && cfg.baseY < 1.5 ? cfg.baseY / Math.round(cfg.baseY / 0.3) : cfg.rise / 2), y);
        step(d + half, d + cfg.rowDepth, y, y + cfg.rise / 2);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.setIndex(idx); g.computeVertexNormals();
    out.push(new THREE.Mesh(g, stairMat));
  }
  if (cfg.tier === 'lower') { // white number on the dark wall behind the block
    const c = document.createElement('canvas'); c.width = 256; c.height = 112;
    const g = c.getContext('2d'); g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = '700 86px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillText(cfg.name, 128, 60, 240);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 0.8), new THREE.MeshBasicMaterial({ map: t, transparent: true }));
    sign.userData.sign = true;
    if (cfg.shape === 'arc') {
      const mid = (cfg.a0 + cfg.a1) / 2 + (cfg.cut ? (Math.abs(cfg.a1 - cfg.cut.a) < Math.abs(cfg.a0 - cfg.cut.a) ? -6 : 6) : 0);
      const ox = Math.cos(mid * D), oz = Math.sin(mid * D);
      sign.position.set(cfg.cx + ox * 16.5, 6.95, cfg.cz + oz * 16.5); sign.rotation.y = Math.atan2(-ox, -oz);
    } else {
      const ox = Math.cos(cfg.facing * D), oz = Math.sin(cfg.facing * D);
      sign.position.set(cfg.x + ox * 11.5, 7.12, cfg.z + oz * 11.5); sign.rotation.y = Math.atan2(-ox, -oz);
    }
    out.push(sign);
  }
  return out;
}

let lastList = [];
function buildSections(list) {
  lastList = list;
  group.traverse((o) => {
    if (o.isMesh && !SHARED.has(o.geometry)) o.geometry.dispose();
    if (o.userData.sign) { o.material.map.dispose(); o.material.dispose(); }
    if (o.isSprite) { o.material.map.dispose(); o.material.dispose(); }
  });
  group.clear(); sections = new Map(); folding.clear();
  bowl.forEach((m, id) => { const cfg = list.find((c) => c.id === id); m.visible = !!cfg && builtTerrace(cfg); });
  const dummy = new THREE.Object3D();
  for (const cfg of list) {
    if (!cfg.enabled) continue;
    const rows = buildSeats(cfg), seats = [];
    rows.forEach((row, r) => row.forEach((p, i) => seats.push({ ...p, row: r + 1, num: i + 1, id: seatId(cfg.id, r + 1, i + 1) })));
    if (!seats.length) continue;
    const armchair = cfg.tier === 'vip' && !!GEO.vipFar;
    const G = armchair ? GEO.vipFar : GEO.far;
    const surface = armchair ? leatherMat : seatMat;
    const mesh = new THREE.InstancedMesh(G.back, surface, seats.length);
    const pan = new THREE.InstancedMesh(G.pan, surface, seats.length);
    const frame = new THREE.InstancedMesh(G.frame, frameMat, seats.length);
    const base = seats.map((s, i) => {
      dummy.position.set(s.x, s.y, s.z); dummy.rotation.set(0, s.ry, 0); dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix); pan.setMatrixAt(i, dummy.matrix); frame.setMatrixAt(i, dummy.matrix);
      return dummy.matrix.clone();
    });
    mesh.computeBoundingSphere(); pan.computeBoundingSphere();
    const slab = new THREE.Mesh(slabGeometry(rows, cfg.tier), slabMat);
    const pts = seats.map((s) => new THREE.Vector3(s.x, s.y, s.z));
    const centre = pts.reduce((v, p) => v.add(p), new THREE.Vector3()).divideScalar(pts.length);
    const label = makeLabel(cfg.name);
    label.position.copy(centre).add(new THREE.Vector3(0, cfg.tier === 'vip' ? 2.4 : 3.2, 0));
    if (cfg.tier === 'vip' || cfg.tier === 'platform') label.scale.multiplyScalar(0.62);
    const S = { cfg, rows, seats, base, mesh, pan, frame, slab, armchair, detail: 'far', free: seats.map((st) => freeColor(cfg, st, rows.length)), ang: new Float32Array(seats.length).fill(A_UP), centre, label, radius: Math.max(...pts.map((p) => p.distanceTo(centre))) + 0.6, left: 0 };
    slab.userData.S = S;
    if (builtTerrace(cfg)) slab.visible = false; // the Blender terrace is shown; the ramp stays only to catch clicks
    recount(S);
    group.add(mesh, pan, frame, slab, label);
    extras(cfg).forEach((m) => group.add(m));
    sections.set(cfg.id, S);
    paint(S);
  }
  showLabels(mode === 'overview');
}
const showLabels = (on) => sections.forEach((S) => (S.label.visible = on));
// Detail follows attention: the block being looked at gets the detailed chair, the rest the simple one.
// In lighter mode everything stays simple and the steel frames are drawn only on the active block.
const showFrames = () => sections.forEach((S) => {
  S.frame.visible = !lite || S === active;
  const want = S === active ? 'near' : 'far';
  if (S.detail === want) return;
  S.detail = want;
  const G = S.armchair ? (want === 'near' ? GEO.vipNear : GEO.vipFar) : GEO[want];
  S.mesh.geometry = G.back; S.pan.geometry = G.pan; S.frame.geometry = G.frame;
});
// Called when frames are running slow: first drop the sharpness, then switch to the lighter chairs.
function degrade() {
  if (renderer.getPixelRatio() > 1) { renderer.setPixelRatio(1); resize(); return; }
  if (lite) return;
  lite = true;
  const keep = active && active.cfg.id;
  buildSections(lastList);
  active = sections.get(keep) || null;
  remapBasket();
  hoverSec = null; hoverSeat = -1; paint(active); showFrames();
}

// ---------------------------------------------------------------- camera
const rig = { tween: null, zoom: 1.28, secZoom: 1, pan: new THREE.Vector3(), az: Math.PI, yaw: 0, pitch: 0, base: new THREE.Quaternion() };
function pose(pos, target) {
  return { pos: pos.clone(), quat: new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(pos, target, UP)) };
}
function fly(to, dur, onUpdate, fov = 42) {
  return new Promise((res) => { rig.tween = { p0: camera.position.clone(), q0: camera.quaternion.clone(), f0: camera.fov, f1: fov, ...to, t0: performance.now(), dur, onUpdate, res }; });
}
const portrait = () => camera.aspect < 0.8;
function aerialPose() {
  // upright phone: fit just the seating bowl across the screen; otherwise fit the whole building
  const k = (portrait() ? 0.98 / camera.aspect : Math.max(1, 1.55 / camera.aspect)) * rig.zoom;
  const p = new THREE.Vector3(Math.sin(rig.az) * 60 * k, 104 * k, Math.cos(rig.az) * 60 * k);
  return pose(p, new THREE.Vector3(0, 0, 0).addScaledVector(p, 0.04).setY(0));
}
// Section view: the camera keeps the heading it has in the aerial view and simply travels
// straight in, ending above the block. No turning round, so you never lose your bearings.
function sectionPose(S) {
  const pitch = THREE.MathUtils.degToRad(S.cfg.tier === 'vip' ? 24 : 66);
  const dir = new THREE.Vector3(-Math.sin(rig.az) * Math.cos(pitch), -Math.sin(pitch), -Math.cos(rig.az) * Math.cos(pitch));
  const half = Math.atan(Math.tan(THREE.MathUtils.degToRad(21)) * Math.min(1, camera.aspect));
  const dist = ((S.radius / Math.sin(half)) * 0.8 + 1.5) * rig.secZoom;
  const target = S.centre.clone().add(rig.pan);
  return pose(target.clone().addScaledVector(dir, -dist), target);
}
// On a narrow upright screen the whole block would be tiny, so start closer and let people drag.
const startSecZoom = () => (camera.aspect < 0.8 ? 0.55 : 1);
function snap(p) { camera.position.copy(p.pos); camera.quaternion.copy(p.quat); }
function zoomBy(f) {
  if (rig.tween) return;
  if (mode === 'overview') { rig.zoom = Math.max(0.9, Math.min(3.2, rig.zoom * f)); snap(aerialPose()); }
  if (mode === 'section' && active) { rig.secZoom = Math.max(0.3, Math.min(1.4, rig.secZoom * f)); snap(sectionPose(active)); }
}
function panBy(mx, my) { // drag the section under your finger
  if (!active) return;
  const dist = camera.position.distanceTo(active.centre.clone().add(rig.pan));
  const k = (2 * dist * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) / innerHeight;
  const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion), up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);
  rig.pan.addScaledVector(right, -mx * k).addScaledVector(up, my * k);
  if (rig.pan.length() > active.radius) rig.pan.setLength(active.radius);
  snap(sectionPose(active));
}
const courtTarget = () => new THREE.Vector3(0, settings.floor === 'stage' ? 2 : 1.4, 0);

// ---------------------------------------------------------------- navigation
const HINTS = {
  overview: ['Hover a section for price and seats left · click to zoom in · drag to turn · scroll to see the surroundings', 'Tap a section for its price · drag to turn · pinch to zoom out'],
  section: ['Click a free seat to sit down · drag to move · scroll to zoom', 'Tap a free seat · drag to move · pinch to zoom'],
  seat: ['This is your view · drag to look around', 'This is your view · drag to look around'],
};
function setMode(m) {
  mode = m;
  document.body.dataset.mode = m;
  showLabels(m === 'overview');
  arena.setInterior(false); // ceiling and scoreboard only appear once you sit down
  preview = null; showFrames();
  hideTip(); renderCrumbs(); renderPanel(); renderDock();
}
function renderDock() {
  $('hint').textContent = (HINTS[mode] || ['', ''])[touch ? 1 : 0];
  $('back').hidden = mode !== 'section';
  $('showticket').hidden = !(mode === 'seat' && ticketOff && selected);
  const bk = $('basket'); bk.hidden = !(basket.length && !bought && (mode === 'overview' || mode === 'section'));
  if (!bk.hidden) bk.textContent = `${basket.length} seat${basket.length > 1 ? 's' : ''} picked · ${cur()} ${price(basketTotal())} · View`;
  const pick = mode === 'section' && touch && active && hoverSeat >= 0 && (!taken[active.seats[hoverSeat].id] || inBasket(active.seats[hoverSeat].id)) ? active.seats[hoverSeat] : null;
  const sec = !pick && touch && preview && sections.get(preview.cfg.id) === preview && (mode === 'overview' || mode === 'section') ? preview : null;
  $('confirm').hidden = !pick && !sec;
  if (sec) $('confirm').innerHTML = `<div><small>${tierLabel(sec.cfg)}</small><b>${sec.cfg.name}</b><span>${cur()} ${price(sec.cfg.price)} · ${sec.left ? sec.left + ' seats left' : 'Sold out'}</span></div>${sec.left ? '<button data-act="zoom">Zoom in</button>' : ''}`;
  if (pick) $('confirm').innerHTML = `<div><small>${tierLabel(active.cfg)} ${active.cfg.name}</small><b>Row ${pick.row} · Seat ${pick.num}</b><span>${cur()} ${price(active.cfg.price)}</span></div><button data-act="sit">Sit here</button>`;
}

async function enterArena() {
  const n = ++nav;
  setMode('flying');
  rig.az = Math.PI; rig.zoom = portrait() ? 1 : 1.28;
  // circle round the building while rising, always looking at it
  const end = aerialPose(), a0 = Math.atan2(camera.position.x, camera.position.z);
  const r0 = Math.hypot(camera.position.x, camera.position.z), r1 = Math.hypot(end.pos.x, end.pos.z), y0 = camera.position.y;
  const t0 = INTRO_TARGET.clone(), t1 = new THREE.Vector3(0, 0, 0).addScaledVector(end.pos, 0.04).setY(0);
  await fly(end, 4200, (k, e) => {
    const a = a0 + (rig.az - a0) * e, r = r0 + (r1 - r0) * e;
    const p = pose(new THREE.Vector3(Math.sin(a) * r, y0 + (end.pos.y - y0) * e, Math.cos(a) * r), t0.clone().lerp(t1, e));
    camera.position.copy(p.pos); camera.quaternion.copy(p.quat);
    arena.setRoof(1 - Math.min(1, Math.max(0, (k - 0.3) / 0.35)));
  });
  if (n !== nav) return;
  arena.setRoof(0); setMode('overview');
}
async function toOverview() {
  ++nav;
  leaveSeat();
  const prev = active, hov = hoverSec; active = null; hoverSeat = -1; hoverSec = null;
  setMode('overview'); paint(prev); paint(hov);
  await fly(aerialPose(), 1100);
}
async function enterSection(S) {
  ++nav;
  leaveSeat();
  if (depth < 1) { history.pushState({ d: 1 }, ''); depth = 1; }
  const prev = active, hov = hoverSec; active = S; hoverSec = null; hoverSeat = -1;
  rig.secZoom = startSecZoom(); rig.pan.set(0, 0, 0);
  setMode('section'); paint(prev); paint(hov); paint(S);
  await fly(sectionPose(S), 1100);
}
// Pick a seat: hold it for this buyer, add it to the order, then sit in it. Picking one already in the order just sits in it.
async function chooseSeat(S, i) {
  const seat = S.seats[i];
  let entry = basket.find((b) => b.id === seat.id);
  if (!entry) {
    if (bought) { basket = []; bought = null; }                     // the last order is finished: this starts a new one
    if (basket.length >= MAX_SEATS) { toast(`You can pick up to ${MAX_SEATS} seats in one order`); return; }
    const r = await post('/api/hold', { seatId: seat.id, clientId });
    if (!r.ok) { toast(r.error && r.error.startsWith('You can') ? r.error : 'That seat was just taken. Pick another.'); return; }
    entry = { ...seat, S, i }; basket.push(entry); taken[seat.id] = 'h';
  }
  await sitAt(entry);
}
async function sitAt(entry) {
  const seat = entry, S = entry.S;
  const n = ++nav;
  if (depth < 1) { history.pushState({ d: 1 }, ''); depth = 1; }
  if (depth < 2) { history.pushState({ d: 2 }, ''); depth = 2; }
  const hov = hoverSec, prev = active; hoverSec = null; active = S;
  ticketOff = false; document.body.dataset.ticket = 'on';
  selected = entry; hoverSeat = -1; $('ticket').hidden = true;
  setMode('seat'); paint(prev); paint(S); paint(hov);
  const f = new THREE.Vector3(Math.sin(seat.ry), 0, Math.cos(seat.ry));
  const p = new THREE.Vector3(seat.x, seat.y, seat.z);
  // 1) travel straight to the chair, 2) sit in it and face the court
  const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
  await fly({ pos: p.clone().add(new THREE.Vector3(0, 0.6, 0)).addScaledVector(fwd, -4.2), quat: camera.quaternion.clone() }, 900);
  if (n !== nav) return;
  await new Promise((r2) => setTimeout(r2, 300));
  if (n !== nav) return;
  const sit = pose(p.clone().add(new THREE.Vector3(0, 1.22, 0)).addScaledVector(f, 0.1), courtTarget());
  arena.setInterior(true);
  await fly(sit, 1300, null, 64);
  if (n !== nav) return;
  rig.base.copy(sit.quat); rig.yaw = 0; rig.pitch = 0;
  // photograph the view for the ticket
  renderer.render(scene, camera);
  const shot = document.createElement('canvas'); shot.width = 360; shot.height = 440;
  const sc = Math.max(360 / canvas.width, 440 / canvas.height), sw = 360 / sc, sh = 440 / sc;
  shot.getContext('2d').drawImage(canvas, (canvas.width - sw) / 2, (canvas.height - sh) / 2, sw, sh, 0, 0, 360, 440);
  try { entry.shot = shot.toDataURL('image/jpeg', 0.8); } catch { /* no picture, ticket still works */ }
  renderTicket();
}
async function backToSection() {
  const S = selected ? selected.S : active;
  if (!S || !sections.has(S.cfg.id)) return toOverview();
  await enterSection(S);
}
// Stand up from the seat. The seats stay in the order; a finished (paid) order is cleared.
function leaveSeat() {
  if (!selected) return;
  selected = null; $('ticket').hidden = true;
  if (bought) { const done = basket; basket = []; bought = null; done.forEach((b) => { recount(b.S); paint(b.S); }); }
}
// Take one seat out of the order and give it back.
function removeSeat(entry) {
  basket = basket.filter((b) => b !== entry);
  if (taken[entry.id] === 'h') delete taken[entry.id];
  post('/api/release', { clientId, seatId: entry.id });
  if (selected === entry) selected = null;
  recount(entry.S); paint(entry.S);
}
// Going back: on-screen buttons, Esc, and the phone's own back button or swipe all end up here.
function show(d) {
  if (mode === 'intro' || mode === 'flying') return;
  if (d <= 0) toOverview(); else if (d === 1 && mode !== 'section') backToSection();
}
function goTo(d) { if (d < depth) history.go(d - depth); else show(d); }
addEventListener('popstate', (e) => { depth = (e.state && e.state.d) || 0; show(depth); });
history.replaceState({ d: 0 }, '');

// ---------------------------------------------------------------- overlay UI
function renderCrumbs() {
  const el = $('crumbs');
  if (mode === 'intro' || mode === 'flying' || mode === 'overview') { el.hidden = true; return; }
  el.hidden = false;
  const parts = [`<button data-d="0">Whole arena</button>`];
  if (active) parts.push(mode === 'seat' ? `<button data-d="1">${tierLabel(active.cfg)} ${active.cfg.name}</button>` : `<span>${tierLabel(active.cfg)} ${active.cfg.name}</span>`);
  if (mode === 'seat' && selected) parts.push(`<span>Row ${selected.row} · Seat ${selected.num}</span>`);
  el.innerHTML = parts.join('<i>/</i>');
}
function renderPanel() {
  const el = $('panel');
  if (mode !== 'section' || !active) { el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = `<small>${tierLabel(active.cfg)}</small><h2>${active.cfg.name}</h2>
    <dl><dt>Price</dt><dd>${cur()} ${price(active.cfg.price)}</dd><dt>Available seats</dt><dd>${active.left}</dd><dt>Gate</dt><dd>${active.cfg.gate || '—'}</dd></dl>
    <p class="mini">${cur()} ${price(active.cfg.price)} · ${active.left} seats left · Gate ${active.cfg.gate || '—'}</p>`;
}
function qrSvg(text) {
  const q = qrcode(0, 'M'); q.addData(text); q.make();
  return q.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
}
// The best free VIP seat, for the upgrade offer on the ticket.
function vipOffer() {
  let best = null;
  sections.forEach((S) => {
    if (S.cfg.tier !== 'vip' || !S.left) return;
    const i = S.seats.findIndex((s) => !taken[s.id]);
    const score = Math.abs(S.centre.x) + S.seats[i].row * 5; // closest to the halfway line, front row first
    if (i >= 0 && (!best || score < best.score)) best = { S, i, score };
  });
  return best;
}
async function upgrade() {
  const offer = vipOffer();
  if (!offer) return toast('The VIP boxes are sold out');
  if (selected) removeSeat(selected);                              // the upgrade replaces the seat you were looking at
  chooseSeat(offer.S, offer.i);
}
function renderTicket() {
  if (!selected) return;
  const { S } = selected, el = $('ticket'), n = basket.length, many = n > 1;
  document.body.dataset.ticket = ticketOff ? 'off' : 'on';
  renderDock();
  if (ticketOff) { el.hidden = true; return; }
  const offer = !bought && S.cfg.tier !== 'vip' ? vipOffer() : null;
  const block = S.cfg.tier === 'vip' || S.cfg.tier === 'platform' ? S.cfg.name : `Block ${S.cfg.name}`;
  el.hidden = false;
  el.innerHTML = `
    <button class="tk-hide" data-act="hide">Hide ticket</button>
    <div class="tk">
      ${selected.shot ? `<div class="tk-view" style="background-image:url(${selected.shot})"><span>View from your seat</span></div>` : ''}
      <div class="tk-main">
        <p class="tk-event">${settings.eventName || ''}</p>
        <p class="tk-date">${settings.eventDate || ''}<br>BK Arena, Kigali</p>
        <h2><small>${tierLabel(S.cfg)}</small>${block}</h2>
        <div class="tk-grid"><div><small>Row</small><b>${selected.row}</b></div><div><small>Seat</small><b>${selected.num}</b></div><div><small>Gate</small><b>${S.cfg.gate || '—'}</b></div></div>
      </div>
      <div class="tk-stub">
        <div class="tk-qr">${bought ? qrSvg(`BKARENA|${bought}|${basket.map((b) => b.id).join(',')}`) : '<span>QR code appears when the order is confirmed</span>'}</div>
        <p class="tk-code">${bought || 'Not paid yet'}</p>
        <p class="tk-price">${many ? `<small>${n} seats</small>` : ''}${cur()} ${price(basketTotal())}</p>
        <span class="tk-admit">Admit ${n}</span>
      </div>
    </div>
    ${many ? `<div class="tk-seats">${basket.map((b, k) => `<button data-seat="${k}" class="${b === selected ? 'on' : ''}">${b.S.cfg.name} · Row ${b.row} · Seat ${b.num}</button>`).join('')}</div>` : ''}
    <div class="tk-actions">
      ${bought
        ? `<button data-d="1">Choose more seats</button><button data-d="0">Whole arena</button>`
        : `<button class="primary" data-act="buy">${many ? `Get ${n} seats` : 'Get this seat'}</button><button data-d="1">Add another seat</button><button data-act="remove">Remove this seat</button>
           ${offer ? `<button class="wide" data-act="upgrade">Upgrade this seat to a VIP box · +${cur()} ${price(offer.S.cfg.price - S.cfg.price)}</button>` : ''}`}
    </div>
    <p class="tk-note">${bought ? 'Order confirmed. Demo only: no payment was taken.' : `Held for you for ${settings.holdMinutes || 10} minutes`}</p>`;
}
function showTip(html, x, y) {
  const el = $('tip'); el.innerHTML = html; el.hidden = false;
  const w = el.offsetWidth, h = el.offsetHeight;
  el.style.left = Math.min(innerWidth - w - 12, Math.max(12, x - w / 2)) + 'px';
  el.style.top = Math.max(12, y - h - 18) + 'px';
}
function hideTip() { $('tip').hidden = true; }
let toastTimer;
function toast(msg) { const el = $('toast'); el.textContent = msg; el.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => (el.hidden = true), 2600); }
function sectionTip(S) {
  const dot = S.left ? `<i class="dot ok"></i>${S.left} left` : '<i class="dot no"></i>Sold out';
  return `<div><small>${tierLabel(S.cfg)}</small><b>${S.cfg.name}</b><span>${dot}</span></div><div class="price"><small>${cur()}</small><b>${price(S.cfg.price)}</b></div>`;
}
function seatTip(S, i) {
  const s = S.seats[i], st = taken[s.id];
  const state = st === 'h' ? '<i class="dot hold"></i>On hold' : st ? '<i class="dot no"></i>Taken' : '<i class="dot ok"></i>Available';
  return `<div><small>${tierLabel(S.cfg)} ${S.cfg.name}</small><b>Row ${s.row} · Seat ${s.num}</b><span>${state}</span></div><div class="price"><small>${cur()}</small><b>${price(S.cfg.price)}</b></div>`;
}

// ---------------------------------------------------------------- picking
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
const pointer = { x: 0, y: 0, dirty: false, down: null, last: null, dragged: false };
function nearestSeat(S, point, max) {
  let best = -1, bd = max * max;
  S.seats.forEach((s, i) => { const d = (s.x - point.x) ** 2 + (s.z - point.z) ** 2 + (s.y - point.y) ** 2; if (d < bd) { bd = d; best = i; } });
  return best;
}
function pick() {
  if (rig.tween || (mode !== 'overview' && mode !== 'section')) return;
  ndc.set((pointer.x / innerWidth) * 2 - 1, -(pointer.y / innerHeight) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  let sec = null, seat = -1;
  if (mode === 'section' && active) {
    const hit = ray.intersectObjects([active.mesh, active.pan])[0];
    if (hit) seat = hit.instanceId;
    else { // a near miss still counts: fingers are wider than seats
      const near = ray.intersectObject(active.slab)[0];
      if (near) seat = nearestSeat(active, near.point, touch ? 0.9 : 0.45);
    }
  }
  if (seat < 0) {
    const slabs = [];
    sections.forEach((S) => { if (S !== active) slabs.push(S.slab); });
    const hit = ray.intersectObjects(slabs)[0];
    if (hit) sec = hit.object.userData.S;
  }
  if (seat !== hoverSeat) { const old = hoverSeat; hoverSeat = seat; paintSeat(active, old, true); paintSeat(active, seat, true); }
  if (sec !== hoverSec) { const old = hoverSec; hoverSec = sec; paint(old); paint(sec); }
  canvas.style.cursor = seat >= 0 || sec ? 'pointer' : mode === 'overview' ? 'grab' : 'default';
  if (touch) hideTip();
  else if (seat >= 0) showTip(seatTip(active, seat), pointer.x, pointer.y);
  else if (sec) showTip(sectionTip(sec), pointer.x, pointer.y);
  else hideTip();
}
function click() {
  pick();
  if (mode === 'section' && hoverSeat >= 0) {
    preview = null;
    const sid = active.seats[hoverSeat].id;
    if (taken[sid] && !inBasket(sid)) toast('That seat is taken. Pick a free one.');
    else if (!touch) chooseSeat(active, hoverSeat); // with a finger: preview first, confirm with “Sit here”
  } else if (hoverSec) {
    // with a finger there is no hover, so the first tap shows the price and the second one zooms in
    if (touch && preview !== hoverSec) preview = hoverSec;
    else if (!hoverSec.left) toast(`${tierLabel(hoverSec.cfg)} ${hoverSec.cfg.name} is sold out`);
    else enterSection(hoverSec);
  } else preview = null;
  renderDock();
}
// ---- pointers: one finger or the mouse drags, two fingers pinch
const fingers = new Map();
let pinch = null;
const spread = () => { const [a, b] = [...fingers.values()]; return Math.hypot(a.x - b.x, a.y - b.y) || 1; };
canvas.addEventListener('pointermove', (e) => {
  pointer.x = e.clientX; pointer.y = e.clientY;
  if (fingers.has(e.pointerId)) fingers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (fingers.size >= 2) { // pinch
    const now = spread();
    if (pinch) zoomBy(pinch / now);
    pinch = now; pointer.dragged = true;
    return;
  }
  if (pointer.down) {
    const dx = e.clientX - pointer.down.x, dy = e.clientY - pointer.down.y;
    if (Math.hypot(dx, dy) > 8) pointer.dragged = true;
    if (pointer.dragged && !rig.tween) {
      const mx = e.clientX - pointer.last.x, my = e.clientY - pointer.last.y;
      if (mode === 'overview') { rig.az -= mx * 0.005; snap(aerialPose()); }
      if (mode === 'section') { panBy(mx, my); hideTip(); }
      if (mode === 'seat') { rig.yaw += mx * 0.003; rig.pitch = Math.max(-0.9, Math.min(0.7, rig.pitch + my * 0.003)); applyLook(); }
    }
    pointer.last = { x: e.clientX, y: e.clientY };
    return;
  }
  if (e.pointerType !== 'touch') pointer.dirty = true;
});
canvas.addEventListener('pointerdown', (e) => {
  const t = e.pointerType === 'touch';
  if (t !== touch) { touch = t; document.body.dataset.touch = t; renderDock(); }
  fingers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (fingers.size >= 2) { pinch = spread(); pointer.dragged = true; return; }
  pointer.down = pointer.last = { x: e.clientX, y: e.clientY }; pointer.dragged = false; pointer.x = e.clientX; pointer.y = e.clientY;
});
const lift = (e) => { fingers.delete(e.pointerId); if (fingers.size < 2) pinch = null; if (fingers.size === 1) pointer.last = [...fingers.values()][0]; };
addEventListener('pointerup', (e) => {
  const was = pointer.down, multi = fingers.size > 1; lift(e);
  if (multi || fingers.size) return; // still part of a pinch: not a tap
  pointer.down = null;
  if (was && !pointer.dragged && e.target === canvas) click();
});
addEventListener('pointercancel', (e) => { lift(e); if (!fingers.size) pointer.down = null; });
// scroll or trackpad-pinch: pull back in the aerial view to see the surroundings, or zoom inside a block
canvas.addEventListener('wheel', (e) => { e.preventDefault(); zoomBy(Math.exp(e.deltaY * 0.0015)); }, { passive: false });
canvas.addEventListener('pointerleave', () => { pointer.dirty = false; hideTip(); });
function applyLook() {
  const yaw = new THREE.Quaternion().setFromAxisAngle(UP, rig.yaw);
  const pitch = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -rig.pitch);
  camera.quaternion.copy(yaw).multiply(rig.base).multiply(pitch);
}

$('enter').addEventListener('click', enterArena);
// every "go back" control carries data-d: the level to return to (0 arena, 1 section)
document.addEventListener('click', async (e) => {
  const t = e.target.closest('[data-d], [data-act], [data-seat]');
  if (!t) return;
  if (t.dataset.d !== undefined) return goTo(Number(t.dataset.d));
  if (t.dataset.act === 'sit' && active && hoverSeat >= 0) chooseSeat(active, hoverSeat);
  if (t.dataset.act === 'zoom' && preview) enterSection(preview);
  if (t.dataset.act === 'upgrade') upgrade();
  if (t.dataset.act === 'hide' || t.dataset.act === 'show') { ticketOff = t.dataset.act === 'hide'; renderTicket(); }
  if (t.dataset.seat !== undefined && basket[Number(t.dataset.seat)]) sitAt(basket[Number(t.dataset.seat)]);   // look from another seat in the order
  if (t.dataset.act === 'basket' && basket.length) sitAt(basket[basket.length - 1]);
  if (t.dataset.act === 'remove' && selected) { removeSeat(selected); $('ticket').hidden = true; goTo(1); }
  if (t.dataset.act === 'buy' && selected) {
    const r = await post('/api/purchase', { seatIds: basket.map((b) => b.id), clientId });
    if (!r.ok) { toast(r.error || 'Could not complete'); return; }
    bought = r.code; basket.forEach((b) => (taken[b.id] = 's')); renderTicket();
  }
});
addEventListener('keydown', (e) => { if (e.key === 'Escape' && depth > 0) goTo(depth - 1); });

// ---------------------------------------------------------------- data
async function post(url, body) {
  try {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    return { ...(await res.json()), ok: res.ok };
  } catch { return { ok: false, error: 'Connection problem' }; }
}
async function load() {
  const state = await (await fetch('/api/state')).json();
  settings = state.settings; taken = state.taken;
  const keep = active && active.cfg.id;
  buildSections(state.sections);
  arena.setFloor(settings.floor);
  arena.setEvent(settings.eventName, settings.eventDate);
  await arena.setCourt(settings.courtStyle);
  $('event-name').textContent = settings.eventName; $('event-date').textContent = settings.eventDate;
  $('hero-event').textContent = `${settings.eventName} · ${settings.eventDate}`;
  $('lg-free').style.background = real() ? 'linear-gradient(90deg,#1f8048 33%,#e6b422 33% 66%,#2f8fc8 66%)' : '#1f9d55';
  $('lg-pick').style.background = real() ? '#ff5a00' : '#fad201';
  $('lg-hold').style.background = real() ? '#8b5cf6' : '#00a1de';
  // a layout change while someone is zoomed in: stay if the section still exists, otherwise go back out
  hoverSec = null; hoverSeat = -1; remapBasket();
  if (mode === 'section' || mode === 'seat') {
    active = sections.get(keep) || null;
    if (!active) goTo(0);
    else if (mode === 'seat') { selected = null; $('ticket').hidden = true; goTo(1); }
    else { paint(active); renderPanel(); renderDock(); }
  }
}
function listen() {
  const es = new EventSource('/api/events');
  es.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'config') return load();
    const touched = new Set();
    for (const [id, st] of msg.changes) {
      if (inBasket(id) && st !== 's') {                              // one of this buyer's own seats
        if (!st) { const gone = basket.find((b) => b.id === id), wasOn = gone === selected; basket = basket.filter((b) => b !== gone); delete taken[id]; recount(gone.S); paint(gone.S); toast('Your hold on a seat ran out'); if (wasOn) { selected = null; $('ticket').hidden = true; goTo(1); } else { renderDock(); if (selected) renderTicket(); } }
        continue;
      }
      if (st) taken[id] = st; else delete taken[id];
      const S = sections.get(id.split(':')[0]); if (S) touched.add(S);
    }
    touched.forEach((S) => { recount(S); paint(S); });
    if (active && touched.has(active)) { renderPanel(); renderDock(); }
  };
}

// ---------------------------------------------------------------- loop
const INTRO_TARGET = new THREE.Vector3(-14, 12, 0);
function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  if (rig.tween) return;
  const p = mode === 'overview' ? aerialPose() : mode === 'section' && active ? sectionPose(active) : null;
  if (p) snap(p);
}
addEventListener('resize', resize);
const perf = { last: 0, sum: 0, n: 0 };
function watchSpeed(now) {
  const dt = now - perf.last; perf.last = now;
  // ignore pauses, fly-throughs, and windows that are not in front (browsers slow those down on purpose)
  if (document.visibilityState !== 'visible' || !document.hasFocus() || rig.tween || mode === 'intro' || dt > 250) { perf.sum = 0; perf.n = 0; return; }
  perf.sum += dt; perf.n++;
  if (perf.n < 150) return;
  // phones: under about 24 frames a second. Computers: only when it is very slow (under 14).
  if (perf.sum / perf.n > (coarse ? 42 : 70)) degrade();
  perf.sum = 0; perf.n = 0;
}
function frame(now) {
  watchSpeed(now);
  if (rig.tween) {
    const t = rig.tween, k = Math.min(1, (now - t.t0) / t.dur), e = ease(k);
    camera.position.lerpVectors(t.p0, t.pos, e);
    camera.quaternion.slerpQuaternions(t.q0, t.quat, e);
    if (t.f0 !== t.f1) { camera.fov = t.f0 + (t.f1 - t.f0) * e; camera.updateProjectionMatrix(); }
    if (t.onUpdate) t.onUpdate(k, e);
    if (k >= 1) { rig.tween = null; t.res(); pointer.dirty = !touch; }
  } else if (mode === 'intro') {
    // street-level view of the entrance, like arriving on the plaza
    const a = 0.42 + Math.sin(now * 0.00012) * 0.2, far = 118 * Math.max(1, 1.2 / camera.aspect);
    const p = pose(new THREE.Vector3(Math.sin(a) * far, 7, Math.cos(a) * far), INTRO_TARGET);
    camera.position.copy(p.pos); camera.quaternion.copy(p.quat);
  } else if (pointer.dirty) { pointer.dirty = false; pick(); }
  if (folding.size) stepFolding(now);
  arena.update(now);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

resize();
progress(0.95);
await load();
document.body.dataset.mode = 'intro';
progress(1);
listen();
requestAnimationFrame(frame);
window.__bk = { sections: () => sections, degrade, get lite() { return lite; }, rig, enterArena, enterSection, chooseSeat, get mode() { return mode; }, camera };
