// Writes blender/layout.json: every section and every seat position, for building the arena in Blender.
// Coordinates here are the website's (metres, x = east, y = up, z = south).
// In Blender (z up) use: blender_x = x, blender_y = -z, blender_z = y, and rotate a seat by `ry` about the up axis.
import fs from 'node:fs';
import { defaultSections, buildSeats, CORNER, TUNNEL_HALF, TUNNEL_ROOF, LAYOUT_VERSION } from '../shared/layout.js';

let sections = defaultSections();
try { // prefer what the running site has (names, prices, paused sections, added floor blocks)
  const res = await fetch('http://localhost:4170/api/state', { signal: AbortSignal.timeout(2000) });
  if (res.ok) sections = (await res.json()).sections;
} catch { /* site not running: use the built-in layout */ }

const r = (n) => Math.round(n * 1000) / 1000;
const out = {
  layoutVersion: LAYOUT_VERSION,
  units: 'metres',
  axes: 'x east, y up, z south (three.js). Blender: (x, -z, y)',
  shell: { rx: 54, rz: 43, wallHeight: 23 },
  corner: CORNER, tunnel: { halfWidth: TUNNEL_HALF, roofY: TUNNEL_ROOF },
  sections: sections.map((cfg) => ({
    ...cfg,
    seatList: buildSeats(cfg).flatMap((row, ri) => row.map((s, si) => [ri + 1, si + 1, r(s.x), r(s.y), r(s.z), r(s.ry)])), // row, seat, x, y, z, ry
  })),
};
fs.writeFileSync(new URL('../blender/layout.json', import.meta.url), JSON.stringify(out));
const seats = out.sections.reduce((n, s) => n + s.seatList.length, 0);
console.log(`blender/layout.json: ${out.sections.length} sections, ${seats} seats, ${(fs.statSync(new URL('../blender/layout.json', import.meta.url)).size / 1024).toFixed(0)} KB`);
