// BK Arena seating layout. Shared by the server (seeding, counts) and the browser (3D).
// Units are metres. x = east, z = south, y = up. The court's long axis runs east–west.
// Every section is plain data, so the management portal can edit, pause or add sections.

const D2R = Math.PI / 180;

export const TIERS = {
  lower: { label: 'Lower Bowl', price: 15000 },
  upper: { label: 'Upper Bowl', price: 5000 },
  vip: { label: 'VIP Box', price: 100000 },
  platform: { label: 'Platform', price: 10000 },
  floor: { label: 'Floor', price: 30000 },
};

const LOWER = { tier: 'lower', rows: 14, seats: 14, rowDepth: 0.8, rise: 0.42, baseY: 0.9, spacing: 0.5 };
const UPPER = { tier: 'upper', rows: 10, seats: 14, rowDepth: 0.8, rise: 0.5, baseY: 10.8, spacing: 0.5 };

// Front edge of the lower bowl: a rectangle with rounded corners.
const SIDE_X = 24.5; // east/west straight stands
const SIDE_Z = 12.8; // north/south straight stands
export const CORNER = { x: 19.5, z: 7.8, r: 5 };
export const TUNNEL_HALF = 2.3, TUNNEL_ROOF = 5.4;
export const LAYOUT_VERSION = 4; // bump when the built-in geometry changes; the server then refreshes stored sections

function straight(id, x, z, facing, base, extra = {}) {
  return { id, name: id, shape: 'straight', x, z, facing, enabled: true, ...base, ...extra };
}
function arc(id, cx, cz, a0, a1, base, extra = {}) {
  return { id, name: id, shape: 'arc', cx, cz, r0: CORNER.r, a0, a1, enabled: true, ...base, ...extra };
}

export function defaultSections() {
  const s = [];
  const xs5 = [-15.6, -7.8, 0, 7.8, 15.6];
  const lowerBack = (rows) => rows * LOWER.rowDepth + 0.6;
  const platformY = (rows) => LOWER.baseY + rows * LOWER.rise;
  const PLAT = { tier: 'platform', rows: 1, seats: 8, rowDepth: 1, rise: 0, spacing: 0.75, price: 10000 };

  // ---- Lower bowl, south sideline: 120 … 116 (west → east)
  ['120', '119', '118', '117', '116'].forEach((id, i) =>
    s.push(straight(id, xs5[i], SIDE_Z, 90, LOWER, { price: 15000, gate: 'S' })));
  // ---- Lower bowl, north sideline: 105 … 109 (106 and 108 are shorter, with a platform behind)
  ['105', '106', '107', '108', '109'].forEach((id, i) => {
    const short = id === '106' || id === '108';
    s.push(straight(id, xs5[i], -SIDE_Z, 270, LOWER, { price: 15000, gate: 'N', rows: short ? 11 : 14 }));
  });
  s.push(straight('P5', xs5[1], -SIDE_Z - lowerBack(11), 270, PLAT, { baseY: platformY(11), gate: 'N' }));
  s.push(straight('P6', xs5[3], -SIDE_Z - lowerBack(11), 270, PLAT, { baseY: platformY(11), gate: 'N' }));
  // ---- Lower bowl, west and east ends (shorter, platforms behind on the west)
  s.push(straight('102', -SIDE_X, -3.9, 180, LOWER, { price: 10000, gate: 'W', rows: 11 }));
  s.push(straight('101', -SIDE_X, 3.9, 180, LOWER, { price: 10000, gate: 'W', rows: 11 }));
  s.push(straight('P3', -SIDE_X - lowerBack(11), -3.9, 180, PLAT, { baseY: platformY(11), gate: 'W' }));
  s.push(straight('P2', -SIDE_X - lowerBack(11), 3.9, 180, PLAT, { baseY: platformY(11), gate: 'W' }));
  s.push(straight('112', SIDE_X, -3.9, 0, LOWER, { price: 10000, gate: 'E' }));
  s.push(straight('113', SIDE_X, 3.9, 0, LOWER, { price: 10000, gate: 'E' }));
  // ---- Lower bowl corners (curved wedges)
  const C = CORNER, corner = { price: 10000 };
  // each corner is two wedges with an entrance tunnel cut between them along the diagonal
  const T = TUNNEL_HALF + 0.4;
  s.push(arc('114', C.x, C.z, 2, 45, LOWER, { ...corner, gate: 'E', cut: { a: 45, half: T } }));
  s.push(arc('115', C.x, C.z, 45, 88, LOWER, { ...corner, gate: 'S', cut: { a: 45, half: T } }));
  s.push(arc('121', -C.x, C.z, 92, 135, LOWER, { ...corner, gate: 'S', cut: { a: 135, half: T } }));
  s.push(arc('122', -C.x, C.z, 135, 178, LOWER, { ...corner, gate: 'W', cut: { a: 135, half: T } }));
  s.push(arc('103', -C.x, -C.z, 182, 225, LOWER, { ...corner, gate: 'W', cut: { a: 225, half: T } }));
  s.push(arc('104', -C.x, -C.z, 225, 268, LOWER, { ...corner, gate: 'N', cut: { a: 225, half: T } }));
  s.push(arc('110', C.x, -C.z, 272, 315, LOWER, { ...corner, gate: 'N', cut: { a: 315, half: T } }));
  s.push(arc('111', C.x, -C.z, 315, 358, LOWER, { ...corner, gate: 'E', cut: { a: 315, half: T } }));
  // Corner platforms P1 (south-west) and P4 (north-west)
  // (they sit on the roof of the corner tunnels)
  const pr = 13.4, k = Math.SQRT1_2;
  s.push(straight('P1', -C.x - pr * k, C.z + pr * k, 135, PLAT, { baseY: TUNNEL_ROOF + 0.1, seats: 5, gate: 'W' }));
  s.push(straight('P4', -C.x - pr * k, -C.z - pr * k, 225, PLAT, { baseY: TUNNEL_ROOF + 0.1, seats: 5, gate: 'W' }));

  // ---- VIP boxes, south side between the two bowls: VIP10 … VIP1 (west → east)
  const vipZ = SIDE_Z + 14 * LOWER.rowDepth + 1.2;
  for (let i = 0; i < 10; i++) {
    s.push(straight(`VIP${10 - i}`, -17.55 + i * 3.9, vipZ, 90, {
      tier: 'vip', rows: 2, seats: 6, rowDepth: 1.0, rise: 0.3, baseY: 7.5, spacing: 0.58, price: 100000, gate: 'VIP',
    }));
  }

  // ---- Upper bowl
  const upZ = vipZ - 0.2, upX = SIDE_X + 11 * LOWER.rowDepth + 2.9;
  const xs7 = [-26, -16, -8, 0, 8, 16, 26];
  ['222', '221', '220', '219', '218', '217', '216'].forEach((id, i) =>
    s.push(straight(id, xs7[i], upZ, 90, UPPER, { price: 5000, gate: 'S', seats: i === 0 || i === 6 ? 22 : 14 })));
  ['205', '206', '207', '208', '209', '210', '211'].forEach((id, i) =>
    s.push(straight(id, xs7[i], -upZ, 270, UPPER, { price: 5000, gate: 'N', seats: i === 0 || i === 6 ? 22 : 14 })));
  const zs4 = [-12.3, -4.1, 4.1, 12.3];
  ['204', '203', '202', '201'].forEach((id, i) =>
    s.push(straight(id, -upX, zs4[i], 180, UPPER, { price: 5000, gate: 'W', seats: 15 })));
  ['212', '213', '214', '215'].forEach((id, i) =>
    s.push(straight(id, upX, zs4[i], 0, UPPER, { price: 5000, gate: 'E', seats: 15 })));

  // ---- Floor: courtside blocks behind each basket (always there for basketball)
  const CS = { tier: 'floor', rows: 3, seats: 8, rowDepth: 0.9, rise: 0, baseY: 0, spacing: 0.55, price: 50000, gate: 'F' };
  [['87', -5.2], ['86', 0], ['85', 5.2]].forEach(([id, z]) => s.push(straight(id, -17.5, z, 180, CS)));
  [['94', -5.2], ['93', 0], ['92', 5.2]].forEach(([id, z]) => s.push(straight(id, 17.5, z, 0, CS)));
  // ---- Floor: courtside rows along both sidelines (basketball only; they make way for the stage and its floor seats)
  const SIDE = { tier: 'floor', rows: 2, seats: 18, rowDepth: 0.9, rise: 0, baseY: 0, spacing: 0.55, price: 60000, gate: 'F', courtOnly: true };
  s.push(straight('C1', -7.2, 10.25, 90, SIDE)); s.push(straight('C2', 7.2, 10.25, 90, SIDE));     // south sideline
  s.push(straight('C3', -7.2, -10.25, 270, SIDE)); s.push(straight('C4', 7.2, -10.25, 270, SIDE)); // north sideline, either side of the scorer's table
  // ---- Floor: curved blocks added on the court for centre-stage events (paused by default)
  const FA = { tier: 'floor', rows: 6, rowDepth: 0.85, rise: 0, baseY: 0, spacing: 0.55, price: 30000, gate: 'F', r0: 8.5, enabled: false, stageOnly: true };
  s.push(arc('90', 0, 0, 5, 65, LOWER, FA));
  s.push(arc('91', 0, 0, -65, -5, LOWER, FA));
  s.push(arc('88', 0, 0, 115, 175, LOWER, FA));
  s.push(arc('89', 0, 0, 185, 245, LOWER, FA));
  return s;
}

// Returns every seat of a section: rows[r][s] = { x, y, z, ry } (ry = rotation so the seat faces the court).
export function buildSeats(sec) {
  const rows = [];
  const sp = sec.spacing || 0.5;
  for (let r = 0; r < sec.rows; r++) {
    const row = [];
    const y = sec.baseY + r * sec.rise;
    if (sec.shape === 'arc') {
      const radius = sec.r0 + r * sec.rowDepth;
      const span = (sec.a1 - sec.a0) * D2R;
      const n = Math.max(1, Math.floor((radius * span) / sp));
      const ca = sec.cut ? sec.cut.a * D2R : 0;
      for (let i = 0; i < n; i++) {
        const a = sec.a0 * D2R + (span * (i + 0.5)) / n;
        const ox = Math.cos(a), oz = Math.sin(a);
        // leave the tunnel clear: skip seats too close to the cut line
        if (sec.cut && Math.abs(radius * Math.sin(a - ca)) < sec.cut.half) continue;
        row.push({ x: sec.cx + ox * radius, y, z: sec.cz + oz * radius, ry: Math.atan2(-ox, -oz) });
      }
    } else {
      const a = sec.facing * D2R;
      const ox = Math.cos(a), oz = Math.sin(a);
      const tx = -oz, tz = ox;
      const ry = Math.atan2(-ox, -oz);
      for (let i = 0; i < sec.seats; i++) {
        const off = (i - (sec.seats - 1) / 2) * sp;
        row.push({ x: sec.x + ox * r * sec.rowDepth + tx * off, y, z: sec.z + oz * r * sec.rowDepth + tz * off, ry });
      }
    }
    rows.push(row);
  }
  return rows;
}

export const seatCount = (sec) => buildSeats(sec).reduce((n, row) => n + row.length, 0);

export const seatId = (sectionId, row, seat) => `${sectionId}:${row}:${seat}`; // row and seat are 1-based

export const DEFAULT_SETTINGS = {
  eventName: 'Kigali Basketball Finals',
  eventDate: 'Sat 12 Dec 2026 · 18:00',
  currency: 'RWF',
  floor: 'basketball', // 'basketball' or 'stage'
  holdMinutes: 10,
  seatColors: 'real', // 'real' = the arena's own green/yellow/blue mix, 'green' = every free seat green
  courtStyle: 'league', // 'league' = wood with yellow keys and a green surround, 'teal' = wood with teal paint
};
