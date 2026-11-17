import { seatCount } from '../shared/layout.js';
import { useDemoBackendIfNeeded } from './demo-backend.js';

await useDemoBackendIfNeeded(); // on a static host there is no server: run the seat database in the browser instead

const $ = (id) => document.getElementById(id);
const TIER = { lower: 'Lower bowl', upper: 'Upper bowl', vip: 'VIP box', platform: 'Platform', floor: 'Floor' };
let state = null, filter = 'all', busy = false;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
async function call(method, url, body) {
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json();
  if (!res.ok) { say(data.error || 'Something went wrong'); throw new Error(data.error); }
  return data;
}
let timer;
function say(text) { const el = $('msg'); el.textContent = text; el.hidden = false; clearTimeout(timer); timer = setTimeout(() => (el.hidden = true), 2200); }

async function load() {
  state = await (await fetch('/api/state')).json();
  const sold = {};
  for (const [id, st] of Object.entries(state.taken)) if (st !== 'h') { const k = id.split(':')[0]; sold[k] = (sold[k] || 0) + 1; }
  state.sections.forEach((s) => { s.total = seatCount(s); s.sold = Math.min(s.total, sold[s.id] || 0); });
  render();
}

function render() {
  const { settings, sections } = state;
  const live = sections.filter((s) => s.enabled);
  const total = live.reduce((n, s) => n + s.total, 0), sold = live.reduce((n, s) => n + s.sold, 0);
  const revenue = live.reduce((n, s) => n + s.sold * s.price, 0);
  $('stats').innerHTML = [
    ['Seats on sale', total.toLocaleString('en-US')],
    ['Sold', `${sold.toLocaleString('en-US')} (${total ? Math.round((sold / total) * 100) : 0}%)`],
    ['Available', (total - sold).toLocaleString('en-US')],
    ['Sales so far', `${settings.currency} ${revenue.toLocaleString('en-US')}`],
    ['Sections paused', sections.length - live.length],
  ].map(([k, v]) => `<div class="stat"><small>${k}</small><b>${v}</b></div>`).join('');

  const f = $('event-form');
  if (!f.contains(document.activeElement)) for (const k of ['eventName', 'eventDate', 'currency', 'holdMinutes', 'seatColors', 'courtStyle']) f.elements[k].value = settings[k];
  $('floor-seg').querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.floor === settings.floor));

  $('filters').innerHTML = [['all', 'All'], ...Object.entries(TIER)].map(([k, v]) =>
    `<button data-filter="${k}" class="${filter === k ? 'on' : ''}">${v}</button>`).join('');

  const focused = document.activeElement && document.activeElement.closest && document.activeElement.closest('#rows');
  if (focused) return; // don't redraw the table under someone's cursor
  $('rows').innerHTML = sections.filter((s) => filter === 'all' || s.tier === filter).map((s) => {
    const straight = s.shape !== 'arc';
    const pos = straight && s.tier === 'floor'
      ? `<input class="sm" type="number" step="0.5" data-k="x" value="${s.x}" aria-label="x"> <input class="sm" type="number" step="0.5" data-k="z" value="${s.z}" aria-label="z"> <input class="sm" type="number" step="5" data-k="facing" value="${s.facing}" aria-label="facing">`
      : '<span style="color:#10151d60">fixed</span>';
    return `<tr data-id="${esc(s.id)}" class="${s.enabled ? '' : 'off'}">
      <td><span class="sw"><input type="checkbox" data-k="enabled" ${s.enabled ? 'checked' : ''} aria-label="On sale"><i></i></span></td>
      <td><input class="name" data-k="name" value="${esc(s.name)}" aria-label="Name"></td>
      <td><span class="tier ${s.tier}">${TIER[s.tier] || s.tier}</span></td>
      <td><input type="number" min="0" step="500" data-k="price" value="${s.price}" aria-label="Price"></td>
      <td><input class="sm" type="number" min="1" max="40" data-k="rows" value="${s.rows}" aria-label="Rows"></td>
      <td>${straight ? `<input class="sm" type="number" min="1" max="60" data-k="seats" value="${s.seats}" aria-label="Seats per row">` : '<span style="color:#10151d60">curved</span>'}</td>
      <td>${pos}</td>
      <td><span class="meter"><i style="width:${s.total ? (s.sold / s.total) * 100 : 0}%"></i></span>${s.sold} / ${s.total}</td>
      <td>${s.custom ? '<button class="danger" data-del>Remove</button>' : ''}</td>
    </tr>`;
  }).join('');
}

$('rows').addEventListener('change', async (e) => {
  const tr = e.target.closest('tr'), k = e.target.dataset.k;
  if (!tr || !k) return;
  const value = e.target.type === 'checkbox' ? e.target.checked : e.target.type === 'number' ? Number(e.target.value) : e.target.value;
  await call('PUT', `/api/admin/sections/${encodeURIComponent(tr.dataset.id)}`, { [k]: value });
  say('Saved');
  e.target.blur(); load();
});
$('rows').addEventListener('click', async (e) => {
  if (!e.target.matches('[data-del]')) return;
  await call('DELETE', `/api/admin/sections/${encodeURIComponent(e.target.closest('tr').dataset.id)}`);
  say('Block removed'); load();
});
$('filters').addEventListener('click', (e) => { if (e.target.dataset.filter) { filter = e.target.dataset.filter; render(); } });
$('event-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  await call('PUT', '/api/admin/settings', Object.fromEntries(new FormData(e.target)));
  document.activeElement.blur(); say('Event saved'); load();
});
$('floor-seg').addEventListener('click', async (e) => {
  if (!e.target.dataset.floor) return;
  await call('POST', '/api/admin/preset', { floor: e.target.dataset.floor });
  say('Floor layout changed'); load();
});
$('add-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  await call('POST', '/api/admin/sections', Object.fromEntries(new FormData(e.target)));
  e.target.elements.id.value = ''; say('Block added'); load();
});
for (const [id, action, text] of [['simulate', 'simulate', 'Sample sales reshuffled'], ['clear', 'clear', 'All sales cleared']]) {
  $(id).addEventListener('click', async () => {
    if (busy) return; busy = true;
    try { await call('POST', '/api/admin/sales', { action }); say(text); await load(); } finally { busy = false; }
  });
}

new EventSource('/api/events').onmessage = () => load();
load();
