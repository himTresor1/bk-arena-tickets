// Demo mode. The real site talks to server.js (seat database + live updates). On a static host such as Vercel there is no
// such server, so this file stands in for it inside the browser: the same /api/... calls work, the data lives in this
// browser's storage, and other tabs of the same browser stay in step. Nothing here runs when the real server answers.
import { defaultSections, buildSeats, seatId, DEFAULT_SETTINGS, TIERS, LAYOUT_VERSION } from '../shared/layout.js';

const KEY = 'bk-arena-demo';
const CODE = { sold: 's', held: 'h', blocked: 'b' };
const MAX_SEATS = 8;
let db = null, channel = null;
const listeners = new Set();

function simulateSales() {
  for (const id of Object.keys(db.seats)) if (db.seats[id][0] !== 'blocked') delete db.seats[id];
  for (const sec of db.sections) {
    const soldOut = sec.id === '203' || sec.id === 'VIP7' || sec.id === '116';
    const share = soldOut ? 1 : 0.15 + Math.random() * 0.5;
    buildSeats(sec).forEach((row, r) => row.forEach((_, i) => { if (Math.random() < share) db.seats[seatId(sec.id, r + 1, i + 1)] = ['sold']; }));
  }
}
function load() {
  try { db = JSON.parse(localStorage.getItem(KEY)); } catch { db = null; }
  if (!db || db.layoutVersion !== LAYOUT_VERSION) {
    const old = new Map(((db && db.sections) || []).map((s) => [s.id, s]));
    db = {
      layoutVersion: LAYOUT_VERSION, settings: (db && db.settings) || {}, seats: {},
      sections: defaultSections().map((sec) => { const was = old.get(sec.id); return was ? { ...sec, name: was.name, price: was.price, enabled: was.enabled } : sec; }),
    };
    simulateSales(); save();
  }
}
function save() { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch { /* storage full or blocked: the demo still works until the page closes */ } }
const settings = () => ({ ...DEFAULT_SETTINGS, ...db.settings });
function broadcast(msg) { listeners.forEach((fn) => fn(msg)); if (channel) channel.postMessage(msg); }
const reply = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

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

function handle(method, path, body) {
  load(); // pick up anything another tab changed
  if (path === '/api/state') {
    const taken = {};
    for (const [id, v] of Object.entries(db.seats)) taken[id] = CODE[v[0]];
    return reply(200, { settings: settings(), sections: db.sections, taken, tiers: TIERS, demo: true });
  }
  if (path === '/api/hold') {
    const id = String(body.seatId || ''), sec = db.sections.find((s) => s.id === id.split(':')[0]);
    if (!body.clientId || !sec || !sec.enabled) return reply(400, { error: 'Unknown seat' });
    const cur = db.seats[id];
    if (cur && !(cur[0] === 'held' && (cur[1] === body.clientId || cur[2] < Date.now()))) return reply(409, { error: 'Seat already taken' });
    if (Object.entries(db.seats).filter(([k, v]) => v[0] === 'held' && v[1] === body.clientId && k !== id).length >= MAX_SEATS) return reply(409, { error: `You can pick up to ${MAX_SEATS} seats in one order` });
    const expires = Date.now() + settings().holdMinutes * 60000;
    db.seats[id] = ['held', body.clientId, expires];
    save(); broadcast({ type: 'seats', changes: [[id, 'h']] });
    return reply(200, { ok: true, expires });
  }
  if (path === '/api/release') {
    const changes = [];
    for (const [k, v] of Object.entries(db.seats)) if (v[0] === 'held' && v[1] === String(body.clientId) && (!body.seatId || k === body.seatId)) { delete db.seats[k]; changes.push([k, null]); }
    if (changes.length) { save(); broadcast({ type: 'seats', changes }); }
    return reply(200, { ok: true });
  }
  if (path === '/api/purchase') {
    const ids = Array.isArray(body.seatIds) ? body.seatIds.slice(0, MAX_SEATS) : [body.seatId];
    if (!ids.length || ids.some((k) => { const cur = db.seats[k]; return !cur || cur[0] !== 'held' || cur[1] !== body.clientId; })) return reply(409, { error: 'Your hold on a seat has expired' });
    ids.forEach((k) => (db.seats[k] = ['sold'])); save(); broadcast({ type: 'seats', changes: ids.map((k) => [k, 's']) });
    return reply(200, { ok: true, code: 'BK-' + Math.random().toString(36).slice(2, 8).toUpperCase() });
  }
  if (path === '/api/admin/settings' && method === 'PUT') {
    for (const k of Object.keys(DEFAULT_SETTINGS)) if (body[k] !== undefined) db.settings[k] = k === 'holdMinutes' ? Math.max(1, Number(body[k]) || 10) : body[k];
    save(); broadcast({ type: 'config' });
    return reply(200, settings());
  }
  const m = path.match(/^\/api\/admin\/sections\/([^/]+)$/);
  if (m) {
    const id = decodeURIComponent(m[1]), i = db.sections.findIndex((s) => s.id === id);
    if (i < 0) return reply(404, { error: 'No such section' });
    if (method === 'PUT') { applyPatch(db.sections[i], body); save(); broadcast({ type: 'config' }); return reply(200, db.sections[i]); }
    if (method === 'DELETE') {
      if (!db.sections[i].custom) return reply(400, { error: 'Built-in sections can be paused, not deleted' });
      db.sections.splice(i, 1);
      for (const k of Object.keys(db.seats)) if (k.startsWith(id + ':')) delete db.seats[k];
      save(); broadcast({ type: 'config' });
      return reply(200, { ok: true });
    }
  }
  if (path === '/api/admin/sections' && method === 'POST') {
    const id = String(body.id || '').trim().replace(/[^\w-]/g, '').slice(0, 12);
    if (!id || db.sections.some((s) => s.id === id)) return reply(400, { error: 'Give the section a unique short name' });
    const sec = applyPatch({ id, name: id, shape: 'straight', tier: 'floor', custom: true, enabled: true, gate: 'F', x: 0, z: 0, facing: 90, rows: 3, seats: 10, rowDepth: 0.9, rise: 0, baseY: 0, spacing: 0.55, price: TIERS.floor.price }, body);
    db.sections.push(sec); save(); broadcast({ type: 'config' });
    return reply(200, sec);
  }
  if (path === '/api/admin/preset') {
    const stage = body.floor === 'stage';
    db.settings.floor = stage ? 'stage' : 'basketball';
    for (const sec of db.sections) { if (sec.stageOnly) sec.enabled = stage; if (sec.courtOnly) sec.enabled = !stage; }
    save(); broadcast({ type: 'config' });
    return reply(200, { ok: true });
  }
  if (path === '/api/admin/seat') {
    const id = String(body.seatId || '');
    if (body.status === 'blocked' || body.status === 'sold') db.seats[id] = [body.status]; else delete db.seats[id];
    save(); broadcast({ type: 'seats', changes: [[id, CODE[body.status] || null]] });
    return reply(200, { ok: true });
  }
  if (path === '/api/admin/sales') {
    if (body.action === 'simulate') simulateSales(); else for (const k of Object.keys(db.seats)) if (db.seats[k][0] !== 'blocked') delete db.seats[k];
    save(); broadcast({ type: 'config' });
    return reply(200, { ok: true });
  }
  return reply(404, { error: 'Not found' });
}

// Stands in for the live-update stream: delivers changes made in this tab and in other tabs of the same browser.
class DemoEvents {
  constructor() { this.onmessage = null; this._fn = (msg) => { if (this.onmessage) this.onmessage({ data: JSON.stringify(msg) }); }; listeners.add(this._fn); }
  close() { listeners.delete(this._fn); }
}

// Call once at start-up. Returns true when demo mode was switched on (no real server answered).
export async function useDemoBackendIfNeeded() {
  try {
    const res = await fetch('/api/state', { headers: { Accept: 'application/json' } });
    if (res.ok && (res.headers.get('content-type') || '').includes('json')) return false; // the real server is there
  } catch { /* no server at all */ }
  load();
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return realFetch(input, init);
    let body = {};
    try { body = init.body ? JSON.parse(init.body) : {}; } catch { /* not JSON */ }
    return handle((init.method || 'GET').toUpperCase(), url.pathname, body);
  };
  window.EventSource = DemoEvents;
  if ('BroadcastChannel' in window) { channel = new BroadcastChannel(KEY); channel.onmessage = (e) => { load(); listeners.forEach((fn) => fn(e.data)); }; }
  setInterval(() => { // release holds that have run out
    load(); const gone = Object.entries(db.seats).filter(([, v]) => v[0] === 'held' && v[2] < Date.now()).map(([k]) => k);
    if (!gone.length) return;
    gone.forEach((k) => delete db.seats[k]); save(); broadcast({ type: 'seats', changes: gone.map((k) => [k, null]) });
  }, 10000);
  document.documentElement.dataset.demo = 'true';
  return true;
}
