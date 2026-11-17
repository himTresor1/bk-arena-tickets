// The building and everything that isn't a seat: ground, facade, roof, court, stage, scoreboard.
import * as THREE from 'three';
import { CORNER, TUNNEL_HALF, TUNNEL_ROOF } from '../shared/layout.js';
import { dress, texture, reflect, loadSet } from './textures.js';

export const COLORS = { green: 0x1f9d55, yellow: 0xfad201, blue: 0x00a1de, sold: 0x5a6068, black: 0x121418,
  rGreen: 0x1f8048, rYellow: 0xe6b422, rBlue: 0x2f8fc8, orange: 0xff5a00, violet: 0x8b5cf6 }; // r* = the real seat colours
const RX = 54, RZ = 54, WALL_H = 23; // the arena is a round drum, 108 m across

function canvasTexture(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

// ---- Facade textures, drawn to match the real building at dusk
// Upper band: bronze screen cut with Imigongo-style patterns (circles, diamonds, hatching).
function latticeTexture() {
  return canvasTexture(2048, 512, (g, w, h) => {
    g.fillStyle = '#3a2d28'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#b79a88'; g.lineWidth = 7; g.lineCap = 'square';
    const P = 256;
    for (let p = 0; p < w / P; p++) {
      const x0 = p * P, cx = x0 + P / 2, cy = h / 2;
      g.save(); g.beginPath(); g.rect(x0 + 5, 5, P - 10, h - 10); g.clip();
      const kind = [0, 2][p % 2];
      if (kind === 0) for (let r = 14; r < 330; r += 22) { g.beginPath(); g.arc(cx + (p % 2 ? 40 : -30), cy + (p % 3 ? 60 : -40), r, 0, Math.PI * 2); g.stroke(); }
      if (kind === 1) for (let r = 16; r < 420; r += 24) { g.beginPath(); g.moveTo(cx, cy - r * 1.6); g.lineTo(cx + r, cy); g.lineTo(cx, cy + r * 1.6); g.lineTo(cx - r, cy); g.closePath(); g.stroke(); }
      if (kind === 2) for (let d = -h; d < P + h; d += 24) {
        g.beginPath(); g.moveTo(x0 + d, 0); g.lineTo(x0 + d + h / 2, h / 2); g.lineTo(x0 + d, h); g.stroke();
      }
      if (kind === 3) for (let d = -h; d < P + h; d += 24) {
        g.beginPath(); g.moveTo(x0 + d, 0); g.lineTo(x0 + d + h, h); g.stroke();
        if (d % 48 === 0) { g.beginPath(); g.moveTo(x0 + d + h, 0); g.lineTo(x0 + d, h); g.stroke(); }
      }
      g.restore();
      g.strokeRect(x0 + 3, 3, P - 6, h - 6);
    }
  });
}
// Middle band: curtain-wall glass reflecting the evening sky, lit from inside near the floor.
function glassTexture() {
  return canvasTexture(1024, 256, (g, w, h) => {
    const sky = g.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#3b2f27'); sky.addColorStop(0.55, '#6e5038'); sky.addColorStop(1, '#b48e60');
    g.fillStyle = sky; g.fillRect(0, 0, w, h);
    for (let x = 0; x < w; x += 32) { g.fillStyle = `rgba(120,70,0,${Math.random() * 0.10})`; g.fillRect(x, 0, 32, h); }
    g.fillStyle = '#3a2c12';
    for (let x = 0; x < w; x += 32) g.fillRect(x, 0, 3, h);
    g.fillRect(0, h * 0.5, w, 3); g.fillRect(0, 0, w, 5);
  });
}
// Ground floor: beige walls, glass doors glowing warm, a few colourful posters.
function storefrontTexture() {
  return canvasTexture(1024, 256, (g, w, h) => {
    g.fillStyle = '#d9c7a6'; g.fillRect(0, 0, w, h);
    for (let x = 0, i = 0; x < w; x += 128, i++) {
      if (i % 4 === 3) continue; // solid wall bay
      const glow = g.createLinearGradient(0, 40, 0, h);
      glow.addColorStop(0, '#d9bd92'); glow.addColorStop(1, '#a87a4a');
      g.fillStyle = glow; g.fillRect(x + 8, 50, 112, h - 50);
      g.fillStyle = '#3b3329';
      for (let k = 0; k <= 4; k++) g.fillRect(x + 8 + k * 27, 50, 3, h - 50);
      g.fillRect(x + 8, 120, 112, 3);
    }
  });
}
function lettersTexture() {
  return canvasTexture(1400, 240, (g, w, h) => {
    g.font = '900 210px "Arial Black", Geist, "Helvetica Neue", Arial, sans-serif';
    g.textBaseline = 'middle'; g.textAlign = 'center';
    const text = 'BK ARENA', step = w / (text.length + 0.3);
    g.fillStyle = '#0b0b0c';
    [...text].forEach((ch, i) => { if (ch !== ' ') g.fillText(ch, step * (i + 0.65), h / 2 + 8); });
  });
}
function drawScreen(g, w, h, name, date) {
  const bg = g.createLinearGradient(0, 0, w, h);
  bg.addColorStop(0, '#0c1322'); bg.addColorStop(1, '#141d33');
  g.fillStyle = bg; g.fillRect(0, 0, w, h);
  g.strokeStyle = 'rgba(250,210,1,.12)'; g.lineWidth = 2;
  for (let x = -h; x < w; x += 28) { g.beginPath(); g.moveTo(x, h); g.lineTo(x + h, 0); g.stroke(); }
  g.textAlign = 'center'; g.textBaseline = 'middle';
  let size = 104; const label = String(name || 'BK ARENA').toUpperCase();
  do { g.font = `800 ${size}px Geist, "Helvetica Neue", Arial, sans-serif`; size -= 6; } while (g.measureText(label).width > w * 0.86 && size > 30);
  g.fillStyle = '#f5d36b'; g.fillRect(w * 0.3, h * 0.2, w * 0.4, 4); g.fillRect(w * 0.3, h * 0.72, w * 0.4, 4);
  g.fillStyle = '#ffffff'; g.fillText(label, w / 2, h * 0.47);
  g.font = '500 26px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillStyle = '#f5d36b';
  g.fillText(String(date || ''), w / 2, h * 0.85);
}

// ---- Interior textures
// Wall between the two bowls: dark cladding, a strip of lounge windows, exit signs, blank sponsor boards.
function concourseTexture() {
  return canvasTexture(1024, 256, (g, w, h) => {
    g.fillStyle = '#23272d'; g.fillRect(0, 0, w, h);
    for (let x = 0; x < w; x += 64) { g.fillStyle = 'rgba(0,0,0,.25)'; g.fillRect(x, 0, 2, h); }
    for (let x = 16; x < w; x += 128) { // windows
      const glow = g.createLinearGradient(0, 60, 0, 150);
      glow.addColorStop(0, '#5b4a2c'); glow.addColorStop(1, '#2c2a26');
      g.fillStyle = glow; g.fillRect(x, 62, 96, 84);
      g.strokeStyle = '#0e1013'; g.lineWidth = 4; g.strokeRect(x, 62, 96, 84);
      g.beginPath(); g.moveTo(x + 32, 62); g.lineTo(x + 32, 146); g.moveTo(x + 64, 62); g.lineTo(x + 64, 146); g.stroke();
    }
    for (let x = 100; x < w; x += 256) { g.fillStyle = '#1fa85a'; g.fillRect(x, 28, 34, 16); g.fillStyle = '#fff'; g.fillRect(x + 6, 33, 12, 6); g.fillRect(x + 22, 31, 6, 10); }
    g.fillStyle = '#15181c'; g.fillRect(0, h - 26, w, 26);
  });
}
// Advertising ribbon along the front of the upper tier.
function ribbonTexture() {
  return canvasTexture(1024, 64, (g, w, h) => {
    g.fillStyle = '#0a1a3a'; g.fillRect(0, 0, w, h);
    g.font = '800 34px Geist, "Helvetica Neue", Arial, sans-serif'; g.textBaseline = 'middle';
    for (let x = 0, i = 0; x < w; x += 256, i++) {
      g.fillStyle = '#e9f3ff'; g.fillRect(x + 6, 10, 112, 44);
      g.fillStyle = '#0a1a3a'; g.fillText('BK', x + 14, 33); g.fillStyle = '#1668c4'; g.fillText('ARENA', x + 62, 33, 52);
      g.fillStyle = ['#fad201', '#00a1de', '#1f9d55', '#ffffff'][i % 4]; g.fillRect(x + 130, 10, 112, 44);
      g.fillStyle = '#0a1a3a'; g.font = '700 22px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillText('KIGALI', x + 146, 33);
      g.font = '800 34px Geist, "Helvetica Neue", Arial, sans-serif';
    }
  });
}
// Roof steelwork seen from below.
function trussTexture() {
  return canvasTexture(512, 512, (g, w, h) => {
    g.fillStyle = '#0c0e11'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#2b3037'; g.lineWidth = 5;
    for (let i = 0; i <= 4; i++) { const p = (i * w) / 4; g.beginPath(); g.moveTo(p, 0); g.lineTo(p, h); g.moveTo(0, p); g.lineTo(w, p); g.stroke(); }
    g.lineWidth = 2; g.strokeStyle = '#23272d';
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
      const x = (i * w) / 4, y = (j * h) / 4, c = w / 4;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + c, y + c); g.moveTo(x + c, y); g.lineTo(x, y + c); g.stroke();
    }
  });
}
function panelTexture() {
  return canvasTexture(256, 256, (g, w, h) => {
    g.fillStyle = '#1d2026'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#111317'; g.lineWidth = 3;
    for (let i = 0; i <= 4; i++) { g.beginPath(); g.moveTo((i * w) / 4, 0); g.lineTo((i * w) / 4, h); g.moveTo(0, (i * h) / 2); g.lineTo(w, (i * h) / 2); g.stroke(); }
  });
}
function screenTexture(lines) {
  return canvasTexture(512, 288, (g, w, h) => {
    g.fillStyle = '#10151d'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#05070a'; g.lineWidth = 14; g.strokeRect(0, 0, w, h);
    g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#f5d36b';
    g.font = '800 76px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillText(lines[0], w / 2, h * 0.42);
    g.fillStyle = '#dfe7f2'; g.font = '500 30px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillText(lines[1], w / 2, h * 0.7);
  });
}
// Build a mesh from a list of quads: each quad is four [x, y, z] corners in order.
function quads(list, uRep = 1) {
  const pos = [], uv = [], idx = [];
  list.forEach((q, i) => {
    q.forEach((p) => pos.push(p[0], p[1], p[2]));
    uv.push(0, 0, uRep, 0, uRep, 1, 0, 1);
    const k = i * 4; idx.push(k, k + 1, k + 2, k, k + 2, k + 3);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
// Upright wall from (x0, z0) to (x1, z1); the top can slope from yt0 to yt1.
const wallQ = (x0, z0, x1, z1, yb, yt0, yt1 = yt0) => [[x0, yb, z0], [x1, yb, z1], [x1, yt1, z1], [x0, yt0, z0]];

// A band that follows the oval: from (offset o0, height y0) up to (offset o1, height y1).
function ring(o0, y0, o1, y1, { a0 = 0, a1 = Math.PI * 2, seg = 128, uRep = 1, flip = false } = {}) {
  const pos = [], uv = [], idx = [];
  for (let i = 0; i <= seg; i++) {
    const t = i / seg, a = a0 + (a1 - a0) * t, c = Math.cos(a), s = Math.sin(a);
    pos.push(c * (RX + o0), y0, s * (RZ + o0), c * (RX + o1), y1, s * (RZ + o1));
    const u = (flip ? 1 - t : t) * uRep; uv.push(u, 0, u, 1);
    if (i < seg) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// Basketball court to FIBA dimensions (28 x 15 m) inside a 2 m teal run-off: maple boards, teal keys, white 5 cm lines.
function courtTexture() {
  const PX = 64; // pixels per metre
  return canvasTexture(32 * PX, 19 * PX, (g, w, h) => {
    const m = (v) => v * PX, WOOD = '#d3b05c', TEAL = '#1b98a8', LINE = '#f4f6f2';
    const ox = m(2), oz = m(2), cw = m(28), ch = m(15), cy = oz + ch / 2;
    g.fillStyle = TEAL; g.fillRect(0, 0, w, h);
    g.fillStyle = WOOD; g.fillRect(ox, oz, cw, ch);
    let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let y = oz; y < oz + ch; y += 6) {                                   // boards run the length of the court
      g.fillStyle = `rgba(${rnd() < 0.5 ? '120,70,10' : '255,235,170'},${0.03 + rnd() * 0.07})`; g.fillRect(ox, y, cw, 6);
      g.fillStyle = 'rgba(90,50,10,.18)';
      for (let x = ox + rnd() * m(1.5); x < ox + cw; x += m(1.2 + rnd() * 1.2)) g.fillRect(x, y, 1.5, 6);
    }
    g.strokeStyle = LINE; g.lineWidth = 0.05 * PX + 0.8; g.lineCap = 'butt';
    for (const side of [0, 1]) {
      const dir = side ? -1 : 1, base = side ? ox + cw : ox, hoop = base + dir * m(1.575);
      g.fillStyle = TEAL; g.fillRect(side ? base - m(5.8) : base, cy - m(2.45), m(5.8), m(4.9));          // the key
      g.strokeRect(side ? base - m(5.8) : base, cy - m(2.45), m(5.8), m(4.9));
      g.beginPath(); g.arc(base + dir * m(5.8), cy, m(1.8), side ? Math.PI / 2 : -Math.PI / 2, side ? -Math.PI / 2 : Math.PI / 2); g.stroke();   // free-throw semicircle
      // three-point line: straight 0.9 m in from each sideline, then an arc of radius 6.75 m about the hoop
      const dz = m(7.5 - 0.9), dxArc = Math.sqrt(m(6.75) ** 2 - dz ** 2), ang = Math.asin(dz / m(6.75));
      g.beginPath(); g.moveTo(base, cy - dz); g.lineTo(hoop + dir * dxArc, cy - dz); g.stroke();
      g.beginPath(); g.moveTo(base, cy + dz); g.lineTo(hoop + dir * dxArc, cy + dz); g.stroke();
      g.beginPath(); if (side) g.arc(hoop, cy, m(6.75), Math.PI - ang, Math.PI + ang); else g.arc(hoop, cy, m(6.75), -ang, ang); g.stroke();
      // no-charge semicircle under the basket
      g.beginPath(); if (side) g.arc(hoop, cy, m(1.25), Math.PI / 2, Math.PI * 1.5); else g.arc(hoop, cy, m(1.25), -Math.PI / 2, Math.PI / 2); g.stroke();
      for (const s2 of [-1, 1]) { g.beginPath(); g.moveTo(hoop, cy + s2 * m(1.25)); g.lineTo(hoop - dir * m(0.375), cy + s2 * m(1.25)); g.stroke(); }
      // rebound place marks along the key
      for (const d of [1.75, 2.6, 3.0, 3.85, 4.7]) for (const s2 of [-1, 1]) { g.beginPath(); g.moveTo(base + dir * m(d), cy + s2 * m(2.45)); g.lineTo(base + dir * m(d), cy + s2 * m(2.55)); g.stroke(); }
      // throw-in marks outside the sidelines
      for (const s2 of [-1, 1]) { g.beginPath(); g.moveTo(base + dir * m(8.325), cy + s2 * m(7.5)); g.lineTo(base + dir * m(8.325), cy + s2 * m(7.65)); g.stroke(); }
    }
    g.strokeRect(ox, oz, cw, ch);                                              // boundary
    g.beginPath(); g.moveTo(ox + cw / 2, oz); g.lineTo(ox + cw / 2, oz + ch); g.stroke();   // halfway line
    g.beginPath(); g.arc(ox + cw / 2, cy, m(1.8), 0, Math.PI * 2); g.stroke(); // centre circle
  });
}
// Polished black concrete floor, with soft pools of light where the floodlights hit it.
function floorTexture() {
  return canvasTexture(1024, 1024, (g, w, h) => {
    g.fillStyle = '#060707'; g.fillRect(0, 0, w, h);
    const pool = (x, y, r, a) => { const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, `rgba(150,158,160,${a})`); gr.addColorStop(1, 'rgba(150,158,160,0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); };
    pool(w / 2, h / 2, w * 0.3, 0.26);
    for (let i = 0; i < 16; i++) { const a = (i / 16) * Math.PI * 2; pool(w / 2 + Math.cos(a) * w * 0.2, h / 2 + Math.sin(a) * h * 0.15, w * 0.1, 0.2); }
    for (const [x, z] of [[-9, -6], [9, -6], [-9, 6], [9, 6]]) pool(w / 2 + (x / 108) * w, h / 2 + (z / 108) * h, w * 0.07, 0.22);
  });
}
function textSprite(text, { size = 120, color = '#fff', glow = null } = {}) {
  const tex = canvasTexture(1024, 256, (g, w, h) => {
    g.font = `800 ${size}px Geist, "Helvetica Neue", Arial, sans-serif`;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    if (glow) { g.shadowColor = glow; g.shadowBlur = 40; }
    g.fillStyle = color; g.fillText(text, w / 2, h / 2);
  });
  return tex;
}

// An oval band anywhere on the site (used for the neighbouring stadium).
function oval(cx, cz, rx0, rz0, y0, rx1, rz1, y1, seg = 96, uRep = 1) {
  const pos = [], uv = [], idx = [];
  for (let i = 0; i <= seg; i++) {
    const a = (i / seg) * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
    pos.push(cx + c * rx0, y0, cz + s * rz0, cx + c * rx1, y1, cz + s * rz1);
    uv.push((i / seg) * uRep, 0, (i / seg) * uRep, 1);
    if (i < seg) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// Everything around the building. The forecourt, ring road and car parks follow drone footage of the site; the hills,
// houses, planting and traffic beyond are invented. Layers sit at different heights so nothing flickers where they overlap:
// grass -0.40, paving -0.20, car parks -0.12, roads -0.10, painted crossings -0.08.
const AMAHORO = { x: 300, z: 40, rx: 128, rz: 108 }; // position is an estimate: move it here if it is on the wrong side
function surroundings(scene, assets = {}) {
  const std = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 1, side: THREE.DoubleSide, ...extra });
  // a textured ground material: the UVs are set in metres from the geometry, so the texture keeps its real-world size
  const tex = (color, name, extra = {}) => { const m = dress(std(color, extra), name, { env: 0.6 }); m.userData.metric = true; return m; };
  const metricUV = (geo) => { const p = geo.attributes.position, flat = geo.type === 'PlaneGeometry' || geo.type === 'CircleGeometry', uv = new Float32Array(p.count * 2);
    for (let i = 0; i < p.count; i++) { uv[i * 2] = p.getX(i); uv[i * 2 + 1] = flat ? p.getY(i) : p.getZ(i); } geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); };
  const add = (geo, m) => { if (m.userData.metric) metricUV(geo); const mesh = new THREE.Mesh(geo, m); scene.add(mesh); return mesh; };
  const ground = (w, dpt, x, z, y, m, rot = 0) => { const p = add(new THREE.PlaneGeometry(w, dpt), m); p.rotation.x = -Math.PI / 2; p.rotation.z = rot; p.position.set(x, y, z); return p; };
  const deg = Math.PI / 180, rnd = (() => { let r = 11; return () => ((r = (r * 16807) % 2147483647) / 2147483647); })();
  const o = new THREE.Object3D(), col = new THREE.Color();
  const S = AMAHORO, RING = RX + 71, AVENUE = RZ + 76;        // centre line of the ring road; where the approach avenue leaves it

  const grass = add(new THREE.CircleGeometry(1400, 64), tex(0x7c8a4c, 'grass')); grass.rotation.x = -Math.PI / 2; grass.position.y = -0.4;

  // ---- forecourt: beige pavers, with the curved terraces that fan out from the main entrance
  add(ring(-1, -0.2, 30, -0.2), tex(0xb9ac90, 'paving'));
  for (let k = 0; k < 5; k++) {
    add(ring(30 + k * 7, -0.2, 37 + k * 7, -0.2, { a0: 18 * deg, a1: 162 * deg, seg: 64 }), tex(k % 2 ? 0xb9ac90 : 0xab9e82, 'paving'));
    add(ring(30 + k * 7, -0.16, 30.5 + k * 7, -0.16, { a0: 18 * deg, a1: 162 * deg, seg: 64 }), std(0x8f8776));
  }
  add(ring(30, -0.2, 66, -0.2, { a0: 162 * deg, a1: 378 * deg, seg: 96 }), tex(0x86924f, 'grass'));     // lawn round the back of the building
  const benchMat = std(0x6b6456);
  for (let k = 0; k < 5; k++) for (let i = 0; i < 5; i += 2) {
    const a = (38 + i * 26 + (k % 2) * 13) * deg, off = 33.5 + k * 7;
    const b = add(new THREE.BoxGeometry(3, 0.5, 1.2), benchMat); b.position.set(Math.cos(a) * (RX + off), 0.05, Math.sin(a) * (RZ + off)); b.rotation.y = -a + Math.PI / 2;
  }

  // ---- roads: asphalt with solid edge lines and a dashed centre line (the texture runs along the road)
  const roadMat = (uRep) => {
    const m = std(0xffffff);
    m.map = texture('road_color.jpg', { srgb: true, repeat: [uRep, 1] }); m.normalMap = texture('road_normal.jpg', { repeat: [uRep, 1] }); m.roughnessMap = texture('road_rough.jpg', { repeat: [uRep, 1] });
    if (!m.map) m.color.set(0x55585a);
    return reflect(m, 0.3);
  };
  add(ring(66, -0.1, 76, -0.1, { uRep: 1 }), roadMat(Math.round((2 * Math.PI * RING) / 12)));
  const strip = (x0, z0, x1, z1, w = 10, y = -0.1) => {                 // a straight two-way road between two points
    const dx = x1 - x0, dz = z1 - z0, len = Math.hypot(dx, dz), nx = (-dz / len) * (w / 2), nz = (dx / len) * (w / 2);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([x0 + nx, y, z0 + nz, x1 + nx, y, z1 + nz, x1 - nx, y, z1 - nz, x0 - nx, y, z0 - nz], 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2)); g.setIndex([0, 1, 2, 0, 2, 3]); g.computeVertexNormals();
    return add(g, roadMat(Math.max(1, Math.round(len / 12))));
  };
  const ROADS = [[0, AVENUE - 0.5, 0, AVENUE + 330], [-420, AVENUE + 335, 420, AVENUE + 335], [-(RX + 75.5), -20, -160, -20], [RX + 75.5, 40, S.x - S.rx - 8, 40], [0, -(RZ + 75.5), 0, -(RZ + 96)]];
  ROADS.forEach((r) => strip(...r));
  const white = std(0xe4e3db);
  for (const c of [90, 28, 152, 270]) for (let j = 0; j < 7; j++) add(ring(67.2 + j * 1.2, -0.08, 67.9 + j * 1.2, -0.08, { a0: (c - 1.5) * deg, a1: (c + 1.5) * deg, seg: 4 }), white);

  // ---- car parks: marked bays either side of each row line, with a driving aisle between rows
  const lotMat = (ru, rv, ov = 0) => { const m = std(0xffffff); m.map = texture('parking_color.jpg', { srgb: true, repeat: [ru, rv] }); m.roughnessMap = texture('parking_rough.jpg', { repeat: [ru, rv] });
    if (m.map) { m.map.offset.y = ov; m.roughnessMap.offset.y = ov; } else m.color.set(0x6a6c6c); m.userData.metric = true; return m; };
  const LOTS = [{ x: -225, z: -20, w: 132, d: 96 }, { x: 0, z: -(RZ + 150), w: 154, d: 96 }, { x: S.x - S.rx - 70, z: S.z + 118, w: 99, d: 64 }];
  LOTS.forEach((L) => ground(L.w, L.d, L.x, L.z, -0.12, lotMat(1 / 2.75, 1 / 16)));
  const bayArcs = [[-72, 14], [166, 252]];
  bayArcs.forEach(([a0, a1]) => { const arcLen = ((a1 - a0) * deg) * (RX + 79.5); const g = ring(76, -0.12, 83, -0.12, { a0: a0 * deg, a1: a1 * deg, seg: 48, uRep: 1 });
    const m = lotMat(Math.round(arcLen / 2.75), 0.3, 0.52); m.userData.metric = false; add(g, m); });

  // ---- cars: three models from Blender, painted per car; parked in the bays and driving round the ring road
  const paint = [0xf2f2f2, 0xd9d9d6, 0x1b1b1d, 0x8b8f96, 0x8f1a1a, 0x1d3f7a, 0xc9c2b2, 0x2b2d31, 0x5d6b73, 0x7a1f2b];
  const paintMat = reflect(new THREE.MeshStandardMaterial({ roughness: 0.3, metalness: 0.55 }), 0.8), glassMat = reflect(new THREE.MeshStandardMaterial({ color: 0x141c20, roughness: 0.06, metalness: 0.7 }), 1.2);
  const trimMat = new THREE.MeshStandardMaterial({ color: 0x0c0d0e, roughness: 0.7 }), lightMat = new THREE.MeshBasicMaterial({ color: 0xf6f3e6 });
  const MODELS = assets.cars && assets.cars.length ? assets.cars : [{ body: new THREE.BoxGeometry(1.85, 0.75, 4.3).translate(0, 0.62, 0), glass: new THREE.BoxGeometry(1.6, 0.55, 2.2).translate(0, 1.26, -0.2) }];
  const fleet = (count) => MODELS.map((g) => {
    const parts = [new THREE.InstancedMesh(g.body, paintMat, count), new THREE.InstancedMesh(g.glass, glassMat, count)];
    if (g.trim) parts.push(new THREE.InstancedMesh(g.trim, trimMat, count)); if (g.lights) parts.push(new THREE.InstancedMesh(g.lights, lightMat, count));
    parts.forEach((p) => { p.count = 0; scene.add(p); }); return { parts, n: 0 };
  });
  const place = (set, i, x, z, ry) => { o.position.set(x, -0.1, z); o.rotation.set(0, ry, 0); o.scale.setScalar(1); o.updateMatrix(); set.parts.forEach((p) => p.setMatrixAt(i, o.matrix)); };
  const parked = fleet(420);
  const park = (x, z, ry) => { const set = parked[Math.floor(rnd() * parked.length)]; if (set.n >= 420) return; place(set, set.n, x, z, ry); set.parts[0].setColorAt(set.n, col.setHex(paint[Math.floor(rnd() * paint.length)])); set.n++; };
  bayArcs.forEach(([a0, a1]) => { const stepA = (2.75 / (RX + 79.5)) / deg; for (let a = a0 + stepA / 2; a < a1; a += stepA) if (rnd() < 0.68) { const c = Math.cos(a * deg), s = Math.sin(a * deg); park(c * (RX + 79.6), s * (RZ + 79.6), Math.atan2(-c, -s)); } });
  LOTS.forEach((L, li) => { for (let row = -L.d / 2 + 8; row < L.d / 2; row += 16) for (let x = -L.w / 2 + 2.75 / 2 + (((L.w / 2) % 2.75)); x < L.w / 2 - 1; x += 2.75) for (const side of [-1, 1]) if (rnd() < (li === 0 ? 0.7 : 0.5)) park(L.x + Math.round((x - 1.375) / 2.75) * 2.75 + 1.375, L.z + row + side * 2.75, side > 0 ? Math.PI : 0); });
  parked.forEach((set) => set.parts.forEach((p) => { p.count = set.n; p.instanceMatrix.needsUpdate = true; if (p.instanceColor) p.instanceColor.needsUpdate = true; }));
  const MOV = 8, moving = fleet(MOV), drivers = [];
  moving.forEach((set, mi) => { for (let i = 0; i < MOV; i++) { const inner = (i + mi) % 2 === 0; drivers.push({ set, i, a: rnd() * Math.PI * 2, lane: inner ? 68.6 : 73.4, speed: (inner ? 1 : -1) * (7 + rnd() * 5) }); set.parts[0].setColorAt(i, col.setHex(paint[Math.floor(rnd() * paint.length)])); }
    set.parts.forEach((p) => (p.count = MOV)); });
  for (const [bx, bz, c] of [[-22, RZ + 79.6, 0xf2f2ee], [-38, RZ + 79.6, 0x2e7d4f]]) {
    const bus = add(new THREE.BoxGeometry(12, 3.0, 2.55), reflect(new THREE.MeshStandardMaterial({ color: c, roughness: 0.35, metalness: 0.3 }), 0.5)); bus.position.set(bx, 1.75, bz); bus.rotation.y = bx * 0.012;
    const win = add(new THREE.BoxGeometry(11.5, 1.05, 2.6), glassMat); win.position.set(bx, 2.4, bz); win.rotation.y = bus.rotation.y;
    for (const wx of [-4, 4]) { const wheel = add(new THREE.BoxGeometry(1.1, 0.9, 2.62), trimMat); wheel.position.set(bx + wx * Math.cos(bus.rotation.y), 0.35, bz - wx * Math.sin(bus.rotation.y)); wheel.rotation.y = bus.rotation.y; }
  }
  const booth = add(new THREE.BoxGeometry(3, 2.8, 3), dress(std(0xd9d2c2), 'concrete')); booth.position.set(9, 1.2, RZ + 80.5);

  // ---- Amahoro Stadium next door: oval bowl in the flag colours under a white ring roof
  const seatTex = canvasTexture(512, 64, (g, w, h) => {
    const c = ['#2f8fd0', '#e6b422', '#1f8048'];
    for (let x = 0; x < w; x += 16) for (let y = 0; y < h; y += 8) { g.fillStyle = c[y < 24 ? 0 : y < 44 ? 1 : 2]; if (Math.random() < 0.25) g.fillStyle = c[Math.floor(Math.random() * 3)]; g.fillRect(x, y, 16, 8); }
  });
  seatTex.wrapS = THREE.RepeatWrapping;
  add(oval(S.x, S.z, S.rx, S.rz, 0, S.rx + 3, S.rz + 3, 27, 96), dress(std(0xb8b0a2), 'concrete', { repeat: [40, 2] }));
  add(oval(S.x, S.z, S.rx - 58, S.rz - 58, 2, S.rx - 4, S.rz - 4, 25, 96, 12), new THREE.MeshStandardMaterial({ map: seatTex, roughness: 0.9, side: THREE.DoubleSide }));
  add(oval(S.x, S.z, S.rx - 44, S.rz - 44, 33, S.rx + 6, S.rz + 6, 29, 96), std(0xecebe6));
  add(oval(S.x, S.z, S.rx + 6, S.rz + 6, 29, S.rx + 3, S.rz + 3, 27, 96), std(0xd6d4cd));
  add(oval(S.x, S.z, 0.1, 0.1, 0.1, S.rx - 58, S.rz - 58, 0.1, 96), std(0x7d8a8f));
  const pitchTex = canvasTexture(256, 128, (g, w, h) => { for (let i = 0; i < 12; i++) { g.fillStyle = i % 2 ? '#2f7d36' : '#38903f'; g.fillRect((i * w) / 12, 0, w / 12 + 1, h); } g.strokeStyle = '#fff'; g.lineWidth = 2; g.strokeRect(4, 4, w - 8, h - 8); g.beginPath(); g.moveTo(w / 2, 4); g.lineTo(w / 2, h - 4); g.stroke(); g.beginPath(); g.arc(w / 2, h / 2, 18, 0, 7); g.stroke(); });
  const pitch = ground(68, 105, S.x, S.z, 0.2, new THREE.MeshStandardMaterial({ map: pitchTex, roughness: 1 })); pitch.rotation.z = Math.PI / 2; pitch.scale.set(105 / 68, 68 / 105, 1);
  ground(95, 70, 150, -190, -0.3, tex(0xb2846d, 'grass')); // bare red-earth plot behind

  // ---- planting: three kinds of tree and clipped shrubs from Blender, each a little different in size and shade
  const leafMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide });
  const KINDS = assets.trees && assets.trees.length ? assets.trees : [new THREE.IcosahedronGeometry(2.6, 1).translate(0, 4, 0)];
  const BUSH = assets.bush || new THREE.IcosahedronGeometry(0.8, 1).translate(0, 0.5, 0);
  if (!assets.trees) leafMat.vertexColors = false, leafMat.color.set(0x4f7a3a);
  const groves = KINDS.map((g) => { const m = new THREE.InstancedMesh(g, leafMat, 700); m.count = 0; scene.add(m); return m; });
  const hedge = new THREE.InstancedMesh(BUSH, leafMat, 900); hedge.count = 0; scene.add(hedge);
  const onRoad = (x, z, pad) => ROADS.some(([x0, z0, x1, z1]) => { const dx = x1 - x0, dz = z1 - z0, t = Math.max(0, Math.min(1, ((x - x0) * dx + (z - z0) * dz) / (dx * dx + dz * dz))); return Math.hypot(x - x0 - dx * t, z - z0 - dz * t) < pad; });
  const inLot = (x, z, pad) => LOTS.some((L) => Math.abs(x - L.x) < L.w / 2 + pad && Math.abs(z - L.z) < L.d / 2 + pad);
  const clear = (x, z, pad = 6) => Math.hypot(x, z) < RX + 86 || onRoad(x, z, 5 + pad) || inLot(x, z, pad)
    || ((x - S.x) / (S.rx + 14)) ** 2 + ((z - S.z) / (S.rz + 14)) ** 2 < 1 || (Math.abs(x - 150) < 52 && Math.abs(z + 190) < 40);
  const plant = (kind, x, z, scale) => { const m = groves[kind % groves.length]; if (m.count >= 700) return;
    o.position.set(x, -0.35, z); o.rotation.set(0, rnd() * 6.28, 0); o.scale.set(scale, scale * (0.9 + rnd() * 0.25), scale); o.updateMatrix(); m.setMatrixAt(m.count, o.matrix);
    m.setColorAt(m.count, col.setRGB(0.8 + rnd() * 0.3, 0.85 + rnd() * 0.25, 0.75 + rnd() * 0.3)); m.count++; };
  const shrub = (x, z, scale) => { if (hedge.count >= 900) return; o.position.set(x, -0.2, z); o.rotation.set(0, rnd() * 6.28, 0); o.scale.setScalar(scale); o.updateMatrix(); hedge.setMatrixAt(hedge.count, o.matrix);
    hedge.setColorAt(hedge.count, col.setRGB(0.85 + rnd() * 0.25, 0.9 + rnd() * 0.2, 0.8 + rnd() * 0.2)); hedge.count++; };
  for (let i = 0; i < 1500; i++) { const a = rnd() * Math.PI * 2, r = 100 + rnd() * 520, x = Math.cos(a) * r, z = Math.sin(a) * r; if (!clear(x, z)) plant(rnd() < 0.62 ? 0 : rnd() < 0.7 ? 1 : 2, x, z, 0.8 + rnd() * 0.6); }   // scattered over the lawns
  for (let z = AVENUE + 16; z < AVENUE + 320; z += 13) for (const sx of [-1, 1]) plant(2, sx * 9.5, z, 1.05);                                   // palms lining the avenue
  for (let a = 0; a < 360; a += 6) { const x = Math.cos(a * deg) * (RX + 90), z = Math.sin(a * deg) * (RZ + 90); if (!onRoad(x, z, 9) && !inLot(x, z, 3)) plant(a % 12 ? 0 : 1, x, z, 0.95); }  // a ring of shade trees outside the ring road
  for (let a = 164; a < 376; a += 2.2) { if (Math.abs(((a + 90) % 360) - 0) < 5) continue; shrub(Math.cos(a * deg) * (RX + 63.5), Math.sin(a * deg) * (RZ + 63.5), 1.1); }                      // hedge inside the ring road, round the lawn
  for (let k = 0; k < 5; k++) for (let i = 1; i < 5; i += 2) { const a0 = (38 + i * 26 + (k % 2) * 13) * deg, off = 33.5 + k * 7; for (let j = -3; j <= 3; j++) { const a = a0 + (j * 1.0) / (RX + off); shrub(Math.cos(a) * (RX + off), Math.sin(a) * (RZ + off), 1.0); } } // planters on the terraces
  LOTS.forEach((L) => { for (let x = -L.w / 2; x <= L.w / 2; x += 2.4) for (const sz of [-1, 1]) shrub(L.x + x, L.z + sz * (L.d / 2 + 1.6), 0.9); });                              // hedges along the car parks
  [...groves, hedge].forEach((m) => { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; });

  // ================= The wider world (invented, in the spirit of Kigali): hills, a neighbourhood, lamps, flags =================
  const hillMat = tex(0x7f8b55, 'grass', { flatShading: true });
  for (let i = 0; i < 20; i++) {
    const a = (i / 20) * Math.PI * 2 + rnd() * 0.3, r = 900 + rnd() * 420;
    const hill = add(new THREE.SphereGeometry(1, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2), hillMat);
    hill.scale.set(240 + rnd() * 280, 60 + rnd() * 120, 240 + rnd() * 280); hill.position.set(Math.cos(a) * r, -3, Math.sin(a) * r);
  }
  const H = 760, walls = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0), dress(new THREE.MeshStandardMaterial({ roughness: 0.9 }), 'concrete'), H);
  const roofs = new THREE.InstancedMesh(new THREE.ConeGeometry(0.74, 1, 4).rotateY(Math.PI / 4).translate(0, 0.5, 0), new THREE.MeshStandardMaterial({ roughness: 0.8, flatShading: true }), H);
  const wallCols = [0xe9e2d0, 0xd8c9a8, 0xf1ede2, 0xc9b58f, 0xbfc4c2], roofCols = [0xa5553a, 0x9c4a33, 0x7d8286, 0xb1643f, 0x5d7a52];
  let hn = 0;
  for (let i = 0; i < 2600 && hn < H; i++) {
    const a = rnd() * Math.PI * 2, r = 250 + rnd() * 900, x = Math.cos(a) * r, z = Math.sin(a) * r;
    if (clear(x, z, 22) || ((x - S.x) / (S.rx + 60)) ** 2 + ((z - S.z) / (S.rz + 60)) ** 2 < 1) continue;
    const tall = rnd() < 0.06, w = tall ? 14 + rnd() * 12 : 7 + rnd() * 7, dd = tall ? 12 + rnd() * 10 : 6 + rnd() * 6, hh = tall ? 14 + rnd() * 26 : 3 + rnd() * 3.5;
    const lift = Math.max(0, r - 820) * 0.09;
    o.position.set(x, lift - 0.3, z); o.rotation.set(0, rnd() * Math.PI, 0); o.scale.set(w, hh, dd); o.updateMatrix(); walls.setMatrixAt(hn, o.matrix);
    walls.setColorAt(hn, col.setHex(tall ? 0xc9d2d4 : wallCols[Math.floor(rnd() * wallCols.length)]));
    o.position.y = lift - 0.3 + hh; o.scale.set(w * 1.08, tall ? 0.4 : 1.6 + rnd() * 1.2, dd * 1.08); o.updateMatrix(); roofs.setMatrixAt(hn, o.matrix);
    roofs.setColorAt(hn, col.setHex(tall ? 0x6f7477 : roofCols[Math.floor(rnd() * roofCols.length)]));
    hn++;
  }
  walls.count = roofs.count = hn; scene.add(walls, roofs);
  const poleMat = dress(new THREE.MeshStandardMaterial({ color: 0x8d9296, metalness: 0.6 }), 'metal'), lampMat = new THREE.MeshBasicMaterial({ color: 0xfff4d6 });
  const poles = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.09, 0.12, 8.5, 8).translate(0, 4.25, 0), poleMat, 80), heads = new THREE.InstancedMesh(new THREE.BoxGeometry(1.1, 0.14, 0.3).translate(0.5, 8.5, 0), lampMat, 80);
  let ln = 0;
  const lamp = (x, z, ry) => { o.position.set(x, -0.2, z); o.rotation.set(0, ry, 0); o.scale.setScalar(1); o.updateMatrix(); poles.setMatrixAt(ln, o.matrix); heads.setMatrixAt(ln, o.matrix); ln++; };
  for (let i = 0; i < 36; i++) { const a = (i / 36) * Math.PI * 2; lamp(Math.cos(a) * (RX + 77.2), Math.sin(a) * (RZ + 77.2), -a + Math.PI); }
  for (let i = 0; i < 24; i++) lamp(i % 2 ? 6.2 : -6.2, AVENUE + 12 + i * 13, i % 2 ? Math.PI : 0);
  poles.count = heads.count = ln; scene.add(poles, heads);
  const flagTex = canvasTexture(192, 128, (g, w, h) => {
    g.fillStyle = '#00a1de'; g.fillRect(0, 0, w, h / 2); g.fillStyle = '#fad201'; g.fillRect(0, h / 2, w, h / 4); g.fillStyle = '#20603d'; g.fillRect(0, h * 0.75, w, h / 4);
    g.fillStyle = '#e5be01'; g.beginPath(); g.arc(w * 0.8, h * 0.24, 13, 0, 7); g.fill();
    g.strokeStyle = '#e5be01'; g.lineWidth = 2; for (let k = 0; k < 24; k++) { const t = (k / 24) * Math.PI * 2; g.beginPath(); g.moveTo(w * 0.8 + Math.cos(t) * 15, h * 0.24 + Math.sin(t) * 15); g.lineTo(w * 0.8 + Math.cos(t) * 23, h * 0.24 + Math.sin(t) * 23); g.stroke(); }
  });
  const flags = [];
  for (const angle of [22, 29, 36, 43, 137, 144, 151, 158]) {      // two groups either side of the entrance, clear of the opening view
    const a = angle * deg, x = Math.cos(a) * (RX + 61), z = Math.sin(a) * (RZ + 61);
    const pole = add(new THREE.CylinderGeometry(0.07, 0.09, 11, 8), poleMat); pole.position.set(x, 5.3, z);
    const geo = new THREE.PlaneGeometry(3.4, 2.2, 8, 1); geo.translate(1.7, 0, 0);
    const flag = add(geo, new THREE.MeshStandardMaterial({ map: flagTex, side: THREE.DoubleSide, roughness: 0.9 })); flag.position.set(x, 9.6, z); flag.rotation.y = 0.5;
    flags.push(flag);
  }
  let last = 0;
  return (now) => {                                                 // called every frame: traffic and flags
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    drivers.forEach((d) => {
      d.a += (d.speed * dt) / (RX + d.lane);
      const c = Math.cos(d.a), sn = Math.sin(d.a), dir = Math.sign(d.speed);
      place(d.set, d.i, c * (RX + d.lane), sn * (RZ + d.lane), Math.atan2(-sn * dir, c * dir));
    });
    moving.forEach((set) => set.parts.forEach((p) => (p.instanceMatrix.needsUpdate = true)));
    flags.forEach((f, k) => { const q = f.geometry.attributes.position; for (let v = 0; v < q.count; v++) q.setZ(v, Math.sin(q.getX(v) * 1.6 - now * 0.004 + k) * 0.16 * (q.getX(v) / 3.4)); q.needsUpdate = true; });
  };
}

export function buildArena(scene, assets = {}) {
  const A = { roofParts: [], interiorOnly: [], update: () => {} };

  // ---- Lights
  scene.add(new THREE.HemisphereLight(0xeef3ff, 0x3a3f48, 1.45));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(30, 80, 40); scene.add(sun);
  const fill = new THREE.DirectionalLight(0xbfd8ff, 0.7); fill.position.set(-40, 50, -30); scene.add(fill);

  const d = new THREE.Object3D();
  A.update = surroundings(scene, assets);

  // ---- The building, bottom to top (fallback: hidden by the site when the Blender exterior loads)
  const TOP = WALL_H + 0.5, F1 = 6.6; // roof edge, first-floor terrace height
  const mat = (tex, glow, extra = {}) => new THREE.MeshStandardMaterial({ map: tex, emissiveMap: tex, emissive: 0xffffff, emissiveIntensity: glow, roughness: 0.6, ...extra });
  const wrap = (t) => { t.wrapS = THREE.RepeatWrapping; return t; };
  const beige = new THREE.MeshStandardMaterial({ color: 0xd9cdb6, roughness: 0.8 });
  const add = (geo, m) => { const mesh = new THREE.Mesh(geo, m); scene.add(mesh); return mesh; };
  // inside face of the shell (what you see from the seats)
  { const t = wrap(panelTexture()); t.wrapT = THREE.RepeatWrapping; t.repeat.set(40, 3);
    add(ring(-0.5, 0, -0.5, TOP), new THREE.MeshStandardMaterial({ map: t, roughness: 1, side: THREE.BackSide })); } // set in from the outside glass so the two never overlap
  const extStart = scene.children.length; // everything added from here to the floor is outside-only
  // ground floor: recessed shopfronts behind a ring of round columns, warm lights in the ceiling
  add(ring(-4, 0, -4, F1, { uRep: 10 }), mat(wrap(storefrontTexture()), 0.55));
  add(ring(-4, F1, 3, F1), new THREE.MeshStandardMaterial({ color: 0xe9dcc4, emissive: 0xc9a273, emissiveIntensity: 0.5, side: THREE.DoubleSide }));
  const cols = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.6, 0.6, F1, 14), beige, 44);
  for (let i = 0; i < 44; i++) {
    const a = ((i + 0.5) / 44) * Math.PI * 2;
    d.position.set(Math.cos(a) * (RX + 2), F1 / 2, Math.sin(a) * (RZ + 2)); d.scale.setScalar(1); d.rotation.set(0, 0, 0); d.updateMatrix(); cols.setMatrixAt(i, d.matrix);
  }
  scene.add(cols);
  // first-floor terrace with a glass rail
  add(ring(3, F1 - 0.2, 3, F1 + 0.9), beige);
  add(ring(0, F1 + 0.9, 3, F1 + 0.9), new THREE.MeshStandardMaterial({ color: 0xbfb5a2, roughness: 0.9, side: THREE.DoubleSide }));
  add(ring(2.9, F1 + 0.9, 2.9, F1 + 2.0), new THREE.MeshStandardMaterial({ color: 0xfff3c4, transparent: true, opacity: 0.18, roughness: 0.1, side: THREE.DoubleSide }));
  // glass curtain wall
  add(ring(0, F1 + 0.9, 0, 16.2, { uRep: 9 }), mat(wrap(glassTexture()), 0.4, { roughness: 0.2, metalness: 0.3 }));
  // patterned bronze screen, leaning outward towards the roof
  const lat = wrap(latticeTexture());
  add(ring(1.2, 15.4, 2.6, TOP, { uRep: 6 }), mat(lat, 0.38, { side: THREE.DoubleSide, roughness: 0.8 }));
  add(ring(0, TOP, 2.6, TOP), new THREE.MeshStandardMaterial({ color: 0x2a221b, roughness: 0.9, side: THREE.DoubleSide }));
  // LED screen set into the bronze band, right of the entrance: shows the current event
  const screenCanvas = document.createElement('canvas'); screenCanvas.width = 1024; screenCanvas.height = 264;
  const screenTex = new THREE.CanvasTexture(screenCanvas); screenTex.colorSpace = THREE.SRGBColorSpace; screenTex.anisotropy = 8;
  const deg = Math.PI / 180;
  A.eventScreen = add(ring(1.75, 16.2, 2.85, TOP - 0.7, { a0: 56 * deg, a1: 91 * deg, seg: 32, flip: true }), new THREE.MeshBasicMaterial({ map: screenTex }));
  A.setEvent = (name, date) => { drawScreen(screenCanvas.getContext('2d'), 1024, 264, name, date); screenTex.needsUpdate = true; };
  A.setEvent('BK ARENA', '');
  // big lit letters standing on the terrace edge
  add(ring(3.3, F1 + 1.0, 3.3, F1 + 5.6, { a0: 64 * deg, a1: 95 * deg, seg: 32, flip: true }),
    new THREE.MeshBasicMaterial({ map: lettersTexture(), transparent: true, alphaTest: 0.3, side: THREE.DoubleSide }));

  // ---- Plaza furniture: welcome board, vendor tents, planter
  const boardTex = canvasTexture(768, 480, (g, w, h) => {
    g.fillStyle = '#16233d'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#00a1de'; g.fillRect(0, 0, w, 150); g.fillStyle = '#fad201'; g.fillRect(0, 150, w, 60); g.fillStyle = '#20603d'; g.fillRect(0, 210, w, 60);
    g.fillStyle = '#fff'; g.textAlign = 'left'; g.font = '500 44px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillText('Welcome to', 40, 360);
    g.font = '800 64px Geist, "Helvetica Neue", Arial, sans-serif'; g.fillText('BK Arena', 40, 430);
  });
  const board = new THREE.Mesh(new THREE.BoxGeometry(10, 6.2, 0.4), [0, 1, 2, 3].map(() => new THREE.MeshStandardMaterial({ color: 0x1a1f29 }))
    .concat([new THREE.MeshBasicMaterial({ map: boardTex }), new THREE.MeshStandardMaterial({ color: 0x1a1f29 })]));
  board.position.set(-14, 9.4, RZ + 17); scene.add(board);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 6.4, 10), new THREE.MeshStandardMaterial({ color: 0x9aa0a8, roughness: 0.5 }));
  pole.position.set(-14, 3.2, RZ + 17); scene.add(pole);
  const tentMat = new THREE.MeshStandardMaterial({ color: 0xc8102e, roughness: 0.7, flatShading: true });
  for (const [x, z] of [[-34, RZ + 9], [-26, RZ + 11]]) {
    const top = new THREE.Mesh(new THREE.ConeGeometry(3.4, 1.6, 4), tentMat); top.rotation.y = Math.PI / 4; top.position.set(x, 3.4, z); scene.add(top);
    for (const [dx, dz] of [[-2.2, -2.2], [2.2, -2.2], [-2.2, 2.2], [2.2, 2.2]]) {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.6, 6), pole.material); leg.position.set(x + dx, 1.3, z + dz); scene.add(leg);
    }
  }
  const planter = new THREE.Mesh(new THREE.BoxGeometry(16, 0.9, 3), new THREE.MeshStandardMaterial({ color: 0x2f6a3a, roughness: 1 }));
  planter.position.set(20, 0.3, RZ + 20); scene.add(planter);

  // ---- Roof (fades away when you enter)
  const roofMat = new THREE.MeshStandardMaterial({ color: 0xd8d0bd, roughness: 0.85, metalness: 0.05, transparent: true });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 24, 0, Math.PI * 2, 0, Math.PI / 2), roofMat);
  dome.scale.set(RX + 2.4, 6.5, RZ + 2.4); dome.position.y = TOP; scene.add(dome);
  A.roofParts.push(dome);
  A.setRoof = (o) => A.roofParts.forEach((m) => { m.material.opacity = o; m.visible = o > 0.01; });

  A.eventScreen.visible = false; // the event board on the facade was removed at the owner's request
  A.codedExterior = scene.children.slice(extStart);

  // ---- Arena floor
  const floor = new THREE.Mesh(new THREE.CircleGeometry(1, 96), dress(new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveMap: floorTexture(), emissiveIntensity: 0.09 }), 'floor', { repeat: [107 / 6, 107 / 6], relief: 0.35 }));
  floor.rotation.x = -Math.PI / 2; floor.scale.set(RX - 0.5, RZ - 0.5, 1); floor.position.y = 0; scene.add(floor);

  // Basketball court + hoops
  const court = new THREE.Group();
  const cm = new THREE.Mesh(new THREE.PlaneGeometry(32, 19), new THREE.MeshStandardMaterial({ roughness: 1 }));
  cm.rotation.x = -Math.PI / 2; cm.position.y = 0.04; court.add(cm);
  // the court's paint scheme: 'league' (wood, yellow keys, green surround, black lines) or 'teal'
  A.setCourt = async (style) => {
    const name = style === 'teal' ? 'court' : 'courtb';
    await loadSet(name);                                            // only the scheme in use is downloaded
    const c = texture(name + '_color.jpg', { srgb: true });
    if (!c) { cm.material.map = courtTexture(); cm.material.roughness = 0.32; cm.material.needsUpdate = true; return; }
    cm.material.map = c; cm.material.normalMap = texture(name + '_normal.jpg'); cm.material.normalScale = new THREE.Vector2(0.35, 0.35); cm.material.roughnessMap = texture(name + '_rough.jpg'); cm.material.needsUpdate = true;
    logo.visible = style !== 'teal' && !!logo.material.map;
  };
  // If you have the right to use a league's logo, save it as public/textures/center_logo.png and it is laid over the centre circle.
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(5.4, 5.4), new THREE.MeshStandardMaterial({ transparent: true, roughness: 0.4 }));
  logo.rotation.x = -Math.PI / 2; logo.position.y = 0.05; logo.visible = false; court.add(logo);
  fetch('/textures/center_logo.png', { method: 'HEAD' }).then((r) => { if (!r.ok || !(r.headers.get('content-type') || '').startsWith('image')) return;
    new THREE.TextureLoader().load('/textures/center_logo.png', (t) => { t.colorSpace = THREE.SRGBColorSpace; logo.material.map = t; logo.material.needsUpdate = true; logo.visible = true; }); }).catch(() => {});
  // scorer's table on the north sideline, between the two courtside blocks
  const table = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.78, 0.7), new THREE.MeshStandardMaterial({ color: 0x0c0d10, roughness: 0.5 })); table.position.set(0, 0.39, -10.0); court.add(table);
  const tableFront = new THREE.Mesh(new THREE.PlaneGeometry(4.1, 0.62), new THREE.MeshBasicMaterial({ color: 0x1d5fd6 })); tableFront.position.set(0, 0.4, -9.64); court.add(tableFront);
  const dark = new THREE.MeshStandardMaterial({ color: 0x1b6b63, roughness: 0.6 });
  const glass = new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, roughness: 0.1 });
  const orange = new THREE.MeshStandardMaterial({ color: 0xff5a1f });
  for (const s of [-1, 1]) {
    const base = new THREE.Mesh(new THREE.BoxGeometry(2.2, 1.1, 1.3), dark); base.position.set(s * 16.4, 0.55, 0);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.28, 0.28), dark); arm.position.set(s * 14.6, 2.6, 0); arm.rotation.z = s * -0.55;
    const board = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.05, 1.8), glass); board.position.set(s * 12.8, 3.45, 0);
    const hoop = new THREE.Mesh(new THREE.TorusGeometry(0.23, 0.025, 8, 24), orange); hoop.rotation.x = Math.PI / 2; hoop.position.set(s * 12.42, 3.05, 0);
    const net = new THREE.Mesh(new THREE.CylinderGeometry(0.225, 0.13, 0.42, 12, 3, true), new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true }));
    net.position.set(s * 12.42, 2.83, 0);
    const lines = new THREE.LineBasicMaterial({ color: 0xffffff });
    const outer = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(1.8, 1.05)), lines), inner = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(0.59, 0.45)), lines);
    for (const l of [outer, inner]) { l.rotation.y = Math.PI / 2; l.position.set(s * 12.76, 3.45, 0); }
    inner.position.y = 3.275;
    const clock = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.36, 0.62), new THREE.MeshStandardMaterial({ color: 0x08090a })); clock.position.set(s * 12.9, 4.3, 0);
    court.add(base, arm, board, hoop, net, outer, inner, clock);
  }
  scene.add(court);

  // Centre stage (for concerts and shows)
  const stage = new THREE.Group();
  const sMat = new THREE.MeshStandardMaterial({ color: 0x8d9096, roughness: 0.5 });
  const deck = new THREE.Mesh(new THREE.CylinderGeometry(4.6, 4.8, 1.3, 8), sMat); deck.position.y = 0.65; deck.rotation.y = Math.PI / 8; stage.add(deck);
  for (let i = 0; i < 4; i++) {
    const wing = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.3, 2.6), sMat);
    wing.position.set(Math.cos((i * Math.PI) / 2) * 5.2, 0.65, Math.sin((i * Math.PI) / 2) * 5.2); stage.add(wing);
  }
  const spk = new THREE.MeshStandardMaterial({ color: 0x0b0b0d, roughness: 0.4 });
  for (let i = 0; i < 8; i++) {
    const a = (i + 0.5) * (Math.PI / 4);
    const b = new THREE.Mesh(new THREE.BoxGeometry(1.5, 1.8, 1.5), spk);
    b.position.set(Math.cos(a) * 7.2, 0.9, Math.sin(a) * 7.2); b.rotation.y = -a + Math.PI / 4; stage.add(b);
  }
  const mic = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 0.12, 24), spk); mic.position.y = 1.36; stage.add(mic);
  scene.add(stage);
  // the Blender-built stage (A.stageModel, set by the site) takes over from this coded one when it has loaded
  A.setFloor = (mode) => { court.visible = mode !== 'stage'; stage.visible = !A.stageModel && mode === 'stage'; if (A.stageModel) A.stageModel.visible = mode === 'stage'; };

  // ---- Scoreboard cube and ceiling rig: only shown from inside the bowl
  const cube = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(6.5, 4.2, 6.5), new THREE.MeshStandardMaterial({ color: 0xf2f2f2, emissive: 0xffffff, emissiveIntensity: 0.25 }));
  const band = new THREE.Mesh(new THREE.BoxGeometry(6.7, 0.5, 6.7), new THREE.MeshStandardMaterial({ color: 0x111111 }));
  band.position.y = -0.9; cube.add(body, band); cube.position.y = 17.5;
  const trussTex = trussTexture(); trussTex.wrapS = trussTex.wrapT = THREE.RepeatWrapping; trussTex.repeat.set(7, 6);
  const ceiling = new THREE.Mesh(new THREE.CircleGeometry(1, 64), new THREE.MeshBasicMaterial({ map: trussTex, side: THREE.DoubleSide }));
  ceiling.rotation.x = Math.PI / 2; ceiling.scale.set(RX + 1, RZ + 1, 1); ceiling.position.y = WALL_H + 0.4;
  const lamps = new THREE.Group();
  const lampMat = new THREE.MeshBasicMaterial({ color: 0xfff6dc });
  for (let i = 0; i < 14; i++) for (let k = 0; k < 4; k++) { // clusters of floodlights on the trusses
    const a = (i / 14) * Math.PI * 2;
    const l = new THREE.Mesh(new THREE.SphereGeometry(0.42, 8, 6), lampMat);
    l.position.set(Math.cos(a) * 27 + (k - 1.5) * 1.3 * Math.sin(a), WALL_H - 0.5, Math.sin(a) * 19 - (k - 1.5) * 1.3 * Math.cos(a)); lamps.add(l);
  }
  scene.add(cube, ceiling, lamps);
  A.interiorOnly.push(cube, ceiling, lamps);
  A.setInterior = (on) => A.interiorOnly.forEach((m) => (m.visible = on));

  // ================= Inside the bowl: everything that isn't a seat =================
  // Key lines (metres): WZ / WX = wall behind the lower bowl, UPX / UPZ = where the upper tier ends.
  const WZ = 24.4, WX = 36.1, UPX = 32, UPZ = 16.4, CR = 16.6, DECK = 6.75, SOFFIT = 9.3, UPY = 10.9, BACKY = 15.3;
  const shellZ = (x) => RZ * Math.sqrt(1 - (x / RX) ** 2) - 0.3, shellX = (z) => RX * Math.sqrt(1 - (z / RZ) ** 2) - 0.3;
  const dk = new THREE.MeshStandardMaterial({ color: 0x1b1e23, roughness: 0.95, side: THREE.DoubleSide });
  const blk = new THREE.MeshStandardMaterial({ color: 0x0d0f12, roughness: 0.9, side: THREE.DoubleSide });
  const cTex = wrap(concourseTexture());
  const wallMat = new THREE.MeshStandardMaterial({ map: cTex, emissiveMap: cTex, emissive: 0xffffff, emissiveIntensity: 0.3, roughness: 0.9, side: THREE.DoubleSide });
  const inside = new THREE.Group(); scene.add(inside);
  A.codedInside = inside; // hidden by the site once the Blender-built structure has loaded
  const put = (geo, m) => { const mesh = new THREE.Mesh(geo, m); inside.add(mesh); return mesh; };

  // -- wall between the bowls, under the whole front of the upper tier (windows, exits, boards)
  put(quads([wallQ(-UPX, -WZ, UPX, -WZ, 6, UPY)], 8), wallMat);                       // north
  put(quads([wallQ(WX, -UPZ, WX, UPZ, 6, UPY)], 4), wallMat);                         // east
  put(quads([wallQ(-WX, UPZ, -WX, -UPZ, 6, UPY)], 4), wallMat);                       // west
  put(quads([wallQ(UPX, WZ, CORNER.x, WZ, 6, UPY), wallQ(-CORNER.x, WZ, -UPX, WZ, 6, UPY)], 1.5), wallMat); // south, either side of the boxes
  // -- upper tier: side walls at its four ends, ceiling underneath, floor behind the top row
  const ends = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const zs = shellZ(UPX), xs = shellX(UPZ);
    ends.push(wallQ(sx * UPX, sz * WZ, sx * UPX, sz * (WZ + 8.6), DECK, UPY, BACKY + 0.6), wallQ(sx * UPX, sz * (WZ + 8.6), sx * UPX, sz * zs, DECK, BACKY + 0.6));
    ends.push(wallQ(sx * WX, sz * UPZ, sx * (WX + 8.3), sz * UPZ, DECK, UPY, BACKY + 0.6), wallQ(sx * (WX + 8.3), sz * UPZ, sx * xs, sz * UPZ, DECK, BACKY + 0.6));
  }
  put(quads(ends), dk);
  const flat = [];
  const strip = (pts) => { for (let i = 0; i < pts.length - 1; i++) flat.push([pts[i][0], pts[i][1], pts[i + 1][1], pts[i + 1][0]]); };
  const steps = (n, f) => Array.from({ length: n + 1 }, (_, i) => f(i / n));
  for (const s of [-1, 1]) {
    strip(steps(16, (t) => { const x = -UPX + 2 * UPX * t; return [[x, SOFFIT, s * WZ], [x, SOFFIT, s * shellZ(x)]]; }));           // ceiling under N/S upper
    strip(steps(8, (t) => { const z = -UPZ + 2 * UPZ * t; return [[s * WX, SOFFIT, z], [s * shellX(z), SOFFIT, z]]; }));            // ceiling under E/W upper
    strip(steps(16, (t) => { const x = -UPX + 2 * UPX * t; return [[x, BACKY, s * 32.6], [x, BACKY, s * shellZ(x)]]; }));           // walkway behind N/S top row
    strip(steps(8, (t) => { const z = -UPZ + 2 * UPZ * t; return [[s * 43.8, BACKY, z], [s * shellX(z), BACKY, z]]; }));            // walkway behind E/W top row
  }
  // -- corners: low wall round the top of the curved stands, open concourse behind, pillar with a screen
  const parapet = [], tv = screenTexture(['BK ARENA', 'KIGALI']);
  const pillarMat = new THREE.MeshStandardMaterial({ color: 0xa9a08c, roughness: 0.85 });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const cx = sx * CORNER.x, cz = sz * CORNER.z;
    const arc = steps(14, (t) => { const a = (t * Math.PI) / 2; return [cx + sx * Math.cos(a) * CR, cz + sz * Math.sin(a) * CR]; });
    for (let i = 0; i < arc.length - 1; i++) parapet.push(wallQ(arc[i][0], arc[i][1], arc[i + 1][0], arc[i + 1][1], 6, 7.5));
    strip(arc.map(([x, z]) => { const k = 1 / Math.sqrt((x / RX) ** 2 + (z / RZ) ** 2) - 0.01; return [[x, DECK, z], [x * k, DECK, z * k]]; }));
    const pillar = new THREE.Mesh(new THREE.BoxGeometry(5.6, WALL_H - DECK, 2.6), pillarMat);
    pillar.position.set(sx * 35.4, DECK + (WALL_H - DECK) / 2, sz * 22.2); pillar.rotation.y = Math.atan2(-sx, -sz); inside.add(pillar);
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(4.4, 2.5), new THREE.MeshBasicMaterial({ map: tv }));
    screen.position.set(sx * (35.4 - 0.935), 13.6, sz * (22.2 - 0.935)); screen.rotation.y = Math.atan2(-sx, -sz); inside.add(screen);
  }
  put(quads(parapet), dk);
  put(quads(flat), dk);

  // -- advertising ribbon along the front of the upper tier
  const ribMat = new THREE.MeshBasicMaterial({ color: 0x1d5fd6, side: THREE.DoubleSide }); // plain blue until real adverts are supplied
  put(quads([wallQ(UPX, WZ - 0.12, -UPX, WZ - 0.12, 9.75, 10.8), wallQ(-UPX, -WZ + 0.12, UPX, -WZ + 0.12, 9.75, 10.8)], 8), ribMat);
  put(quads([wallQ(WX - 0.55, -UPZ, WX - 0.55, UPZ, 9.75, 10.8), wallQ(-WX + 0.55, UPZ, -WX + 0.55, -UPZ, 9.75, 10.8)], 4), ribMat);
  // -- scoreboards high on the two end walls
  const board2 = screenTexture(['HOME  00 : 00  AWAY', 'BK ARENA']);
  for (const sx of [-1, 1]) {
    const sb = new THREE.Mesh(new THREE.PlaneGeometry(11, 4.6), new THREE.MeshBasicMaterial({ map: board2 }));
    sb.position.set(sx * 51.6, 19.4, 0); sb.rotation.y = -sx * Math.PI / 2; inside.add(sb);
  }

  // -- entrance tunnels through the four corners
  const tun = [], glow = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const cx = sx * CORNER.x, cz = sz * CORNER.z, dx = sx * Math.SQRT1_2, dz = sz * Math.SQRT1_2, tx = -dz, tz = dx, H = TUNNEL_HALF;
    const at = (r, side) => [cx + dx * r + tx * side, cz + dz * r + tz * side];
    const top = (r) => 0.9 + ((r - CORNER.r) / 0.8) * 0.42 + 0.3; // follows the rake of the seats beside it
    for (const side of [-H, H]) {
      const a = at(4.6, side), b = at(CR, side);
      tun.push(wallQ(a[0], a[1], b[0], b[1], 0, top(4.6), top(CR)));
    }
    const m1 = at(11.2, -H), m2 = at(11.2, H), e1 = at(CR - 0.1, -H), e2 = at(CR - 0.1, H);
    tun.push(wallQ(m1[0], m1[1], m2[0], m2[1], 3.6, TUNNEL_ROOF));                                                  // lintel over the mouth
    tun.push([[m1[0], TUNNEL_ROOF, m1[1]], [m2[0], TUNNEL_ROOF, m2[1]], [e2[0], TUNNEL_ROOF, e2[1]], [e1[0], TUNNEL_ROOF, e1[1]]]); // roof (a platform sits on it)
    tun.push([[m1[0], 3.6, m1[1]], [m2[0], 3.6, m2[1]], [e2[0], 3.6, e2[1]], [e1[0], 3.6, e1[1]]]);                 // tunnel ceiling
    glow.push(wallQ(e1[0], e1[1], e2[0], e2[1], 0, 3.6));                                                           // daylight at the far door
  }
  // kept as a fallback: the site hides these when the Blender-built tunnels load
  A.codedTunnels = [put(quads(tun), blk), put(quads(glow), new THREE.MeshBasicMaterial({ color: 0xffe9bd, side: THREE.DoubleSide }))];

  // -- Skyboxes on the south side: each box is a glass-fronted room with its armchairs inside,
  //    stepped so the back row sees over the front, and a lounge behind.
  const X0 = -19.5, BOXW = 3.9, FLOOR = 7.5, DEPTH = 7, H = SOFFIT - FLOOR;
  put(quads([wallQ(CORNER.x, WZ, -CORNER.x, WZ, 6, FLOOR + 0.1)]), dk);                                              // solid front below the glass
  const carpet = new THREE.MeshStandardMaterial({ color: 0x3b2520, roughness: 1 });
  const wood = new THREE.MeshStandardMaterial({ color: 0x8a5a2a, emissive: 0xe08a3a, emissiveIntensity: 0.4, roughness: 0.8 });
  const dkWood = new THREE.MeshStandardMaterial({ color: 0x3a2618, emissive: 0x7a4418, emissiveIntensity: 0.25, roughness: 0.9 });
  const frame = new THREE.MeshStandardMaterial({ color: 0x0c0d10, roughness: 0.5, metalness: 0.4 });
  const bx = (w, h, dpt, x, y, z, m) => { const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, dpt), m); mesh.position.set(x, y, z); inside.add(mesh); return mesh; };
  bx(39.2, 0.3, DEPTH, 0, FLOOR - 0.17, WZ + DEPTH / 2, carpet);                                                     // floor
  bx(39.2, 0.3, 1.2, 0, FLOOR + 0.13, WZ + 1.9, carpet);                                                             // step for the back row
  bx(39.2, H, 0.2, 0, FLOOR + H / 2, WZ + DEPTH, wood);                                                              // back wall
  bx(39, 0.05, 0.4, 0, SOFFIT - 0.04, WZ + 2.6, new THREE.MeshBasicMaterial({ color: 0xffe2b0 }));                   // ceiling light strips
  bx(39, 0.05, 0.4, 0, SOFFIT - 0.04, WZ + 5.2, new THREE.MeshBasicMaterial({ color: 0xffe2b0 }));
  const glassMat = new THREE.MeshPhysicalMaterial({ color: 0xeaf6ff, transparent: true, opacity: 0.1, roughness: 0, metalness: 0, side: THREE.DoubleSide, depthWrite: false });
  put(quads([wallQ(CORNER.x, WZ + 0.05, -CORNER.x, WZ + 0.05, FLOOR + 0.1, SOFFIT)]), glassMat).renderOrder = 5;    // clear glass front
  for (const y of [FLOOR + 0.13, SOFFIT - 0.05]) bx(39.2, 0.08, 0.09, 0, y, WZ + 0.05, frame);                       // glass frame, top and bottom
  for (let i = 0; i <= 10; i++) {
    const x = X0 + i * BOXW;
    bx(0.14, H, 0.12, x, FLOOR + H / 2, WZ + 0.05, frame);                                                           // post between boxes
    bx(0.14, H, DEPTH, x, FLOOR + H / 2, WZ + DEPTH / 2, dkWood);                                                    // wall between boxes
    if (i === 10) break;
    const cx = x + BOXW / 2;
    bx(0.04, H, 0.06, cx, FLOOR + H / 2, WZ + 0.05, frame);                                                          // slim mullion mid-box
    bx(2.6, 0.45, 0.85, cx, FLOOR + 0.22, WZ + 6.2, frame); bx(2.6, 0.5, 0.2, cx, FLOOR + 0.7, WZ + 6.55, frame);    // sofa
    const table = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 1.05, 12), dkWood); table.position.set(cx - 0.9, FLOOR + 0.52, WZ + 4.2); inside.add(table);
    const stool = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.75, 10), frame); stool.position.set(cx - 0.2, FLOOR + 0.37, WZ + 4.4); inside.add(stool);
    bx(1.6, 0.9, 0.05, cx + 0.6, FLOOR + 1.45, WZ + DEPTH - 0.14, new THREE.MeshBasicMaterial({ color: 0x1a2a44 })); // wall TV
  }
  return A;
}

// Floating section number above each block.
export function makeLabel(text) {
  const tex = canvasTexture(256, 128, (g, w, h) => {
    g.font = `700 ${text.length > 4 ? 54 : 72}px Geist, "Helvetica Neue", Arial, sans-serif`;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineWidth = 10; g.strokeStyle = 'rgba(0,0,0,.75)'; g.strokeText(text, w / 2, h / 2);
    g.fillStyle = '#fff'; g.fillText(text, w / 2, h / 2);
  });
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sp.scale.set(5.2, 2.6, 1); sp.renderOrder = 10;
  return sp;
}
