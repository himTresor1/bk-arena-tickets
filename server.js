// One small server: the site (through Vite), the seat database (SQLite) and live updates.
import http from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { createServer as createVite } from 'vite';
import { defaultSections, buildSeats, seatCount, seatId, DEFAULT_SETTINGS, TIERS, LAYOUT_VERSION } from './shared/layout.js';

const PORT = Number(process.env.PORT || 4170);
const MAX_SEATS = 8; // most seats one buyer can hold in a single order
const db = new DatabaseSync(new URL('./arena.db', import.meta.url).pathname);
db.exec(`
  CREATE TABLE IF NOT EXISTS sections (id TEXT PRIMARY KEY, pos INTEGER, config TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS seats (id TEXT PRIMARY KEY, section TEXT NOT NULL, status TEXT NOT NULL, holder TEXT, expires INTEGER);
  CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
`);

const q = {
  sections: db.prepare('SELECT config FROM sections ORDER BY pos'),
  section: db.prepare('SELECT config FROM sections WHERE id = ?'),
  putSection: db.prepare('INSERT INTO sections (id, pos, config) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET config = excluded.config'),
  delSection: db.prepare('DELETE FROM sections WHERE id = ?'),
  maxPos: db.prepare('SELECT COALESCE(MAX(pos), 0) AS p FROM sections'),
  seats: db.prepare('SELECT id, status FROM seats'),
  seat: db.prepare('SELECT * FROM seats WHERE id = ?'),
  putSeat: db.prepare('INSERT INTO seats (id, section, status, holder, expires) VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET status = excluded.status, holder = excluded.holder, expires = excluded.expires'),
  delSeat: db.prepare('DELETE FROM seats WHERE id = ?'),
  heldBy: db.prepare("SELECT id FROM seats WHERE status = 'held' AND holder = ?"),
  expired: db.prepare("SELECT id FROM seats WHERE status = 'held' AND expires < ?"),
  settings: db.prepare('SELECT key, value FROM settings'),
  putSetting: db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value'),
};

const tx = (fn) => { db.exec('BEGIN'); try { const r = fn(); db.exec('COMMIT'); return r; } catch (e) { db.exec('ROLLBACK'); throw e; } };
const allSections = () => q.sections.all().map((r) => JSON.parse(r.config));
const getSettings = () => { const o = { ...DEFAULT_SETTINGS, ...Object.fromEntries(q.settings.all().map((r) => [r.key, JSON.parse(r.value)])) }; delete o.layoutVersion; return o; };

// Sell a random share of every section so the arena looks alive (placeholder sales).
function simulateSales() {
  tx(() => {
    db.exec("DELETE FROM seats WHERE status IN ('sold', 'held')");
    for (const sec of allSections()) {
      const soldOut = sec.id === '203' || sec.id === 'VIP7' || sec.id === '116';
      const share = soldOut ? 1 : 0.15 + Math.random() * 0.5;
      buildSeats(sec).forEach((row, r) => row.forEach((_, i) => {
        if (Math.random() < share) q.putSeat.run(seatId(sec.id, r + 1, i + 1), sec.id, 'sold', null, null);
      }));
    }
  });
}

const storedVersion = () => { const r = q.settings.all().find((x) => x.key === 'layoutVersion'); return r ? JSON.parse(r.value) : 1; };
if (!q.sections.all().length) {
  tx(() => defaultSections().forEach((sec, i) => q.putSection.run(sec.id, i, JSON.stringify(sec))));
  q.putSetting.run('layoutVersion', JSON.stringify(LAYOUT_VERSION));
  simulateSales();
} else if (storedVersion() !== LAYOUT_VERSION) {
  // the built-in shape of the arena changed: refresh geometry, keep each section's name, price and on/off state
  const old = new Map(allSections().map((sec) => [sec.id, sec]));
  tx(() => defaultSections().forEach((sec) => {
    const was = old.get(sec.id);
    q.putSection.run(sec.id, was ? 0 : q.maxPos.get().p + 1, JSON.stringify(was ? { ...sec, name: was.name, price: was.price, enabled: was.enabled } : sec));
  }));
  q.putSetting.run('layoutVersion', JSON.stringify(LAYOUT_VERSION));
  simulateSales();
}

// ---- Live updates (server-sent events)
const clients = new Set();
const broadcast = (msg) => { const data = `data: ${JSON.stringify(msg)}\n\n`; clients.forEach((res) => res.write(data)); };
const CODE = { sold: 's', held: 'h', blocked: 'b' };

setInterval(() => {
  const gone = q.expired.all(Date.now());
  if (!gone.length) return;
  gone.forEach((r) => q.delSeat.run(r.id));
  broadcast({ type: 'seats', changes: gone.map((r) => [r.id, null]) });
}, 10000);

function fullState() {
  const taken = {};
  for (const r of q.seats.all()) taken[r.id] = CODE[r.status];
  return { settings: getSettings(), sections: allSections(), taken, tiers: TIERS };
}

const readBody = (req) => new Promise((resolve, reject) => {
  let s = '';
  req.on('data', (c) => { s += c; if (s.length > 1e6) req.destroy(); });
  req.on('end', () => { try { resolve(s ? JSON.parse(s) : {}); } catch (e) { reject(e); } });
});
const send = (res, code, body) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(body)); };

// Only these fields of a section can be changed from the portal.
const NUM = ['price', 'rows', 'seats', 'x', 'z', 'facing', 'rowDepth', 'rise', 'baseY', 'spacing', 'r0', 'a0', 'a1', 'cx', 'cz'];
function applyPatch(sec, patch) {
  if (typeof patch.name === 'string' && patch.name.trim()) sec.name = patch.name.trim().slice(0, 24);
  if (typeof patch.enabled === 'boolean') sec.enabled = patch.enabled;
  if (typeof patch.gate === 'string') sec.gate = patch.gate.slice(0, 8);
  for (const k of NUM) if (patch[k] !== undefined && Number.isFinite(Number(patch[k]))) sec[k] = Number(patch[k]);
  sec.rows = Math.min(40, Math.max(1, Math.round(sec.rows)));
  if (sec.shape !== 'arc') sec.seats = Math.min(60, Math.max(1, Math.round(sec.seats)));
  sec.price = Math.max(0, Math.round(sec.price));
  return sec;
}

async function api(req, res, url) {
  const path = url.pathname, m = req.method;

  if (path === '/api/state' && m === 'GET') return send(res, 200, fullState());

  if (path === '/api/events' && m === 'GET') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    res.write('retry: 2000\n\n');
    clients.add(res);
    req.on('close', () => clients.delete(res));
    return;
  }

  const body = m === 'GET' ? {} : await readBody(req);

  // ---- Buyer actions
  if (path === '/api/hold' && m === 'POST') {
    const { seatId: id, clientId } = body;
    const sectionId = String(id || '').split(':')[0];
    const sec = q.section.get(sectionId);
    if (!clientId || !sec || !JSON.parse(sec.config).enabled) return send(res, 400, { error: 'Unknown seat' });
    const cur = q.seat.get(id);
    if (cur && !(cur.status === 'held' && (cur.holder === clientId || cur.expires < Date.now()))) return send(res, 409, { error: 'Seat already taken' });
    // one buyer can hold several seats for one order, up to MAX_SEATS
    if (q.heldBy.all(clientId).filter((r) => r.id !== id).length >= MAX_SEATS) return send(res, 409, { error: `You can pick up to ${MAX_SEATS} seats in one order` });
    const expires = Date.now() + getSettings().holdMinutes * 60000;
    q.putSeat.run(id, sectionId, 'held', clientId, expires);
    broadcast({ type: 'seats', changes: [[id, 'h']] });
    return send(res, 200, { ok: true, expires });
  }
  if (path === '/api/release' && m === 'POST') {
    // release one seat (seatId) or everything this buyer holds
    const changes = q.heldBy.all(String(body.clientId)).filter((r) => !body.seatId || r.id === body.seatId).map((r) => { q.delSeat.run(r.id); return [r.id, null]; });
    if (changes.length) broadcast({ type: 'seats', changes });
    return send(res, 200, { ok: true });
  }
  if (path === '/api/purchase' && m === 'POST') {
    const ids = Array.isArray(body.seatIds) ? body.seatIds.slice(0, MAX_SEATS) : [body.seatId];
    const rows = ids.map((id) => q.seat.get(String(id)));
    if (!rows.length || rows.some((cur) => !cur || cur.status !== 'held' || cur.holder !== body.clientId)) return send(res, 409, { error: 'Your hold on a seat has expired' });
    tx(() => rows.forEach((cur) => q.putSeat.run(cur.id, cur.section, 'sold', null, null)));
    broadcast({ type: 'seats', changes: rows.map((cur) => [cur.id, 's']) });
    return send(res, 200, { ok: true, code: 'BK-' + Math.random().toString(36).slice(2, 8).toUpperCase() });
  }

  // ---- Management portal (no login yet: prototype only)
  if (path === '/api/admin/settings' && m === 'PUT') {
    for (const k of Object.keys(DEFAULT_SETTINGS)) if (body[k] !== undefined) q.putSetting.run(k, JSON.stringify(k === 'holdMinutes' ? Math.max(1, Number(body[k]) || 10) : body[k]));
    broadcast({ type: 'config' });
    return send(res, 200, getSettings());
  }
  const secMatch = path.match(/^\/api\/admin\/sections\/([^/]+)$/);
  if (secMatch) {
    const id = decodeURIComponent(secMatch[1]);
    const row = q.section.get(id);
    if (!row) return send(res, 404, { error: 'No such section' });
    if (m === 'PUT') {
      const sec = applyPatch(JSON.parse(row.config), body);
      q.putSection.run(id, 0, JSON.stringify(sec));
      broadcast({ type: 'config' });
      return send(res, 200, sec);
    }
    if (m === 'DELETE') {
      if (!JSON.parse(row.config).custom) return send(res, 400, { error: 'Built-in sections can be paused, not deleted' });
      tx(() => { q.delSection.run(id); db.prepare('DELETE FROM seats WHERE section = ?').run(id); });
      broadcast({ type: 'config' });
      return send(res, 200, { ok: true });
    }
  }
  if (path === '/api/admin/sections' && m === 'POST') {
    const id = String(body.id || '').trim().replace(/[^\w-]/g, '').slice(0, 12);
    if (!id || q.section.get(id)) return send(res, 400, { error: 'Give the section a unique short name' });
    const sec = applyPatch({
      id, name: id, shape: 'straight', tier: 'floor', custom: true, enabled: true, gate: 'F',
      x: 0, z: 0, facing: 90, rows: 3, seats: 10, rowDepth: 0.9, rise: 0, baseY: 0, spacing: 0.55, price: TIERS.floor.price,
    }, body);
    q.putSection.run(id, q.maxPos.get().p + 1, JSON.stringify(sec));
    broadcast({ type: 'config' });
    return send(res, 200, sec);
  }
  if (path === '/api/admin/preset' && m === 'POST') {
    const stage = body.floor === 'stage';
    tx(() => {
      q.putSetting.run('floor', JSON.stringify(stage ? 'stage' : 'basketball'));
      for (const sec of allSections()) {
        if (sec.stageOnly) { sec.enabled = stage; q.putSection.run(sec.id, 0, JSON.stringify(sec)); }
        if (sec.courtOnly) { sec.enabled = !stage; q.putSection.run(sec.id, 0, JSON.stringify(sec)); }
      }
    });
    broadcast({ type: 'config' });
    return send(res, 200, { ok: true });
  }
  if (path === '/api/admin/seat' && m === 'POST') {
    const id = String(body.seatId || '');
    if (body.status === 'blocked' || body.status === 'sold') q.putSeat.run(id, id.split(':')[0], body.status, null, null);
    else q.delSeat.run(id);
    broadcast({ type: 'seats', changes: [[id, CODE[body.status] || null]] });
    return send(res, 200, { ok: true });
  }
  if (path === '/api/admin/sales' && m === 'POST') {
    if (body.action === 'simulate') simulateSales();
    else db.exec("DELETE FROM seats WHERE status IN ('sold', 'held')");
    broadcast({ type: 'config' });
    return send(res, 200, { ok: true });
  }
  send(res, 404, { error: 'Not found' });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname.startsWith('/api/')) {
    try { await api(req, res, url); } catch (e) { console.error(e); if (!res.headersSent) send(res, 500, { error: 'Server error' }); }
    return;
  }
  if (url.pathname === '/admin') req.url = '/admin.html';
  if (url.pathname === '/tour') req.url = '/tour.html';
  vite.middlewares(req, res);
});
const vite = await createVite({ server: { middlewareMode: true, hmr: { server } }, appType: 'mpa' });
server.listen(PORT, () => console.log(`BK Arena running at http://localhost:${PORT}  (portal: /admin)`));
export { seatCount };
