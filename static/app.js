/* Mumbai Local Graph Lab: front end. All graph computation happens in Python (network.py). */
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const NS = 'http://www.w3.org/2000/svg';
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const c of kids.flat(3)) { if (c == null || c === false) continue; el.append(c.nodeType ? c : document.createTextNode(String(c))); }
  return el;
}
function s(tag, attrs, ...kids) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  for (const c of kids.flat(3)) if (c != null) el.append(c.nodeType ? c : document.createTextNode(String(c)));
  return el;
}
const api = (url, opt) => fetch(url, opt).then(r => r.json());
const board = name => h('span', { class: 'sb' }, name);
const chip = g => h('span', { class: 'chip g-' + g }, h('i', null, g), NET.groups[g].name);

let NET = null;
const state = { tab: 'trip', src: '', dst: '', mode: 'stops', pick: 'src', route: null, closed: new Set(), stranded: new Set(), hl: new Set() };
let ANALYSIS = null;
const VB0 = { x: 0, y: 10, w: 1200, h: 1420 };
let vb = { ...VB0 };
const pos = {}, stationEls = {}, labelEls = {};

/* ---------- map ---------- */
function buildMap() {
  const svg = $('#map');
  svg.replaceChildren();
  NET.stations.forEach(st => { pos[st.name] = [st.x, st.y]; });
  const edgeLayer = s('g', { id: 'edges' }), routeLayer = s('g', { id: 'route' }), stLayer = s('g'), labLayer = s('g');
  NET.edges.forEach(e => {
    const [x1, y1] = pos[e.a], [x2, y2] = pos[e.b];
    e.groups.forEach((g, i) => edgeLayer.append(s('line', { x1, y1, x2, y2, class: 'edge g-' + g + (i === 0 ? ' base' : ' top'), 'data-a': e.a, 'data-b': e.b })));
  });
  NET.stations.forEach(st => {
    const hub = st.groups.length > 1 || st.degree > 2;
    const c = s('circle', { cx: st.x, cy: st.y, r: hub ? 6.5 : 4, class: 'stn' + (hub ? ' hub' : ''), 'data-name': st.name }, s('title', null, st.full + ' (' + st.groups.map(g => NET.groups[g].name).join(', ') + ')'));
    c.addEventListener('click', ev => { ev.stopPropagation(); clickStation(st.name); });
    stationEls[st.name] = c; stLayer.append(c);
    const major = hub || st.degree === 1;
    const left = st.groups.length === 1 && st.groups[0] === 'W';
    const t = s('text', { x: st.x + (left ? -10 : 10), y: st.y + 4.5, class: 'lab ' + (major ? 'major' : 'minor'), 'text-anchor': left ? 'end' : 'start' }, st.name);
    labelEls[st.name] = t; labLayer.append(t);
  });
  svg.append(edgeLayer, routeLayer, stLayer, labLayer);
  applyVB();
  $('#legend').replaceChildren(...Object.entries(NET.groups).map(([g, v]) => h('span', { class: 'g-' + g }, h('i'), v.name)), h('span', null, '◯ ring = hub or interchange'));
}
function applyVB() {
  $('#map').setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  $('#map').classList.toggle('zoomed', VB0.w / vb.w > 1.7);
}
function zoomAt(f, cx, cy) {
  const nw = Math.max(260, Math.min(VB0.w * 1.2, vb.w / f)), k = nw / vb.w;
  vb = { x: cx - (cx - vb.x) * k, y: cy - (cy - vb.y) * k, w: nw, h: vb.h * k };
  applyVB();
}
function svgPoint(ev) { const svg = $('#map'), pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY; return pt.matrixTransform(svg.getScreenCTM().inverse()); }
function setupMapControls() {
  const svg = $('#map'); let drag = null;
  svg.addEventListener('wheel', ev => { ev.preventDefault(); const p = svgPoint(ev); zoomAt(ev.deltaY < 0 ? 1.18 : 1 / 1.18, p.x, p.y); }, { passive: false });
  svg.addEventListener('pointerdown', ev => { if (ev.target.classList.contains('stn')) return; drag = { x: ev.clientX, y: ev.clientY, vb: { ...vb } }; svg.setPointerCapture(ev.pointerId); svg.classList.add('panning'); });
  svg.addEventListener('pointermove', ev => {
    if (!drag) return; const r = svg.getBoundingClientRect(); const k = Math.max(drag.vb.w / r.width, drag.vb.h / r.height);
    vb = { ...drag.vb, x: drag.vb.x - (ev.clientX - drag.x) * k, y: drag.vb.y - (ev.clientY - drag.y) * k }; applyVB();
  });
  const end = () => { drag = null; svg.classList.remove('panning'); };
  svg.addEventListener('pointerup', end); svg.addEventListener('pointercancel', end);
  $('#zin').onclick = () => zoomAt(1.4, vb.x + vb.w / 2, vb.y + vb.h / 2);
  $('#zout').onclick = () => zoomAt(1 / 1.4, vb.x + vb.w / 2, vb.y + vb.h / 2);
  $('#zreset').onclick = () => { vb = { ...VB0 }; applyVB(); };
}
function focusOn(names) {
  const pts = names.map(n => pos[n]).filter(Boolean); if (!pts.length) return;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]); const pad = 90;
  const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
  const r = $('#map').getBoundingClientRect(); const ar = r.width / Math.max(1, r.height);
  let w = x1 - x0, hh = y1 - y0; if (w / hh < ar) w = hh * ar; else hh = w / ar;
  w = Math.min(w, VB0.w * 1.2); hh = w / ar;
  vb = { x: (x0 + x1) / 2 - w / 2, y: (y0 + y1) / 2 - hh / 2, w, h: hh }; applyVB();
}
function paintMap() {
  const route = state.route;
  const on = new Set(route ? route.path : []);
  Object.entries(stationEls).forEach(([n, el]) => {
    el.classList.toggle('on', on.has(n));
    el.classList.toggle('closed', state.closed.has(n));
    el.classList.toggle('stranded', state.stranded.has(n));
    el.classList.toggle('hl', state.hl.has(n));
    labelEls[n].classList.toggle('show', on.has(n) || state.closed.has(n) || state.hl.has(n) || n === state.src || n === state.dst);
  });
  document.querySelectorAll('#edges .edge').forEach(el => {
    const a = el.dataset.a, b = el.dataset.b;
    el.classList.toggle('dim', state.closed.has(a) || state.closed.has(b) || state.stranded.has(a) || state.stranded.has(b));
  });
  const rl = $('#route'); rl.replaceChildren();
  if (route) {
    const d = route.path.map((n, i) => (i ? 'L' : 'M') + pos[n][0] + ' ' + pos[n][1]).join(' ');
    rl.append(s('path', { d, class: 'rcase' }), s('path', { d, class: 'rline' }));
    route.path.forEach((n, i) => { if (i === 0 || i === route.path.length - 1) rl.append(s('text', { x: pos[n][0], y: pos[n][1] + 4, class: 'rnum' }, i === 0 ? 'A' : 'B')); });
  }
}
function clickStation(name) {
  if (state.tab === 'crit') { toggleClosed(name); return; }
  if (state.pick === 'src') { state.src = name; state.pick = 'dst'; } else { state.dst = name; state.pick = 'src'; }
  if (state.tab !== 'trip') setTab('trip'); else { syncTripInputs(); if (state.src && state.dst) runTrip(); else paintMap(); }
}

/* ---------- tabs ---------- */
function setTab(t) {
  state.tab = t;
  document.querySelectorAll('.tab').forEach(b => b.setAttribute('aria-selected', b.dataset.tab === t ? 'true' : 'false'));
  if (t !== 'trip' && t !== 'crit') state.route = null;
  if (t !== 'trip') { vb = { ...VB0 }; applyVB(); }
  state.hl = new Set();
  if (t !== 'crit') { state.closed = new Set(); state.stranded = new Set(); }
  ({ trip: renderTrip, crit: renderCrit, euler: renderEuler, rel: renderRel })[t]();
  paintMap();
}
const panel = () => $('#panel');
function syl(txt) { return h('span', { class: 'syl' }, txt); }
function how(...text) { return h('details', { class: 'how' }, h('summary', null, 'How this works'), ...text.map(x => h('p', null, x))); }
function stationInputs() { return h('datalist', { id: 'stlist' }, NET.stations.map(x => h('option', { value: x.name }, x.full))); }

/* ---------- 1. plan a trip ---------- */
function syncTripInputs() { if ($('#src')) { $('#src').value = state.src; $('#dst').value = state.dst; } }
function renderTrip() {
  const p = panel(); p.replaceChildren();
  const src = h('input', { type: 'text', id: 'src', list: 'stlist', placeholder: 'e.g. Churchgate', autocomplete: 'off', value: state.src });
  const dst = h('input', { type: 'text', id: 'dst', list: 'stlist', placeholder: 'e.g. Thane', autocomplete: 'off', value: state.dst });
  const out = h('div', { id: 'tripout', class: 'panel' });
  const mode = h('div', { class: 'seg' },
    ...[['stops', 'Fewest stops'], ['changes', 'Fewest interchanges']].map(([v, l]) => h('label', null, h('input', { type: 'radio', name: 'mode', value: v, checked: state.mode === v, onchange: () => { state.mode = v; runTrip(); } }), l)));
  p.append(stationInputs(), h('div', { class: 'card' }, h('h2', null, 'Plan a trip'), syl('Module 6: BFS, shortest path'),
    h('div', { class: 'row' }, h('label', { class: 'field' }, h('span', null, 'From'), src), h('label', { class: 'field' }, h('span', null, 'To'), dst),
      h('button', { class: 'btn', type: 'button', title: 'Swap', onclick: () => { [state.src, state.dst] = [state.dst, state.src]; syncTripInputs(); runTrip(); } }, '⇄ Swap')),
    mode, h('div', { class: 'row' }, h('button', { class: 'btn go', type: 'button', onclick: () => { state.src = src.value.trim(); state.dst = dst.value.trim(); runTrip(); } }, 'Find route')),
    h('p', { class: 'muted' }, 'Type two stations, or click two stations on the map.'),
    how('BFS (breadth-first search) checks every station 1 stop from the start, then every station 2 stops away, then 3, and so on. The first time it reaches your destination, that route is the shortest possible, because all shorter routes were already tried.',
        'Each train service (for example Central to Kasara) is treated separately, so changing from one service to another counts as one interchange.')), out);
  src.addEventListener('change', () => { state.src = src.value.trim(); });
  dst.addEventListener('change', () => { state.dst = dst.value.trim(); });
  if (!state.src) { state.src = 'Churchgate'; state.dst = 'Thane'; syncTripInputs(); }
  runTrip();
}
async function runTrip() {
  const out = $('#tripout'); if (!out) return;
  if (!state.src || !state.dst) { out.replaceChildren(); state.route = null; paintMap(); return; }
  const r = await api(`/api/route?src=${encodeURIComponent(state.src)}&dst=${encodeURIComponent(state.dst)}&mode=${state.mode}`);
  out.replaceChildren();
  if (r.error || !r.route) { state.route = null; out.append(h('div', { class: 'note bad' }, r.error || 'No route.')); paintMap(); return; }
  const R = r.route; state.route = R;
  const legs = [];
  R.legs.forEach((l, i) => {
    if (i > 0) legs.push(h('div', { class: 'change' }, '↻ Change trains at ' + l.stations[0]));
    legs.push(h('div', { class: 'leg g-' + l.group }, h('div', { class: 'top2' }, chip(l.group), h('b', null, l.name.replace(/^[^:]+: /, '')), h('span', { class: 'muted' }, l.stops + (l.stops === 1 ? ' stop' : ' stops'))),
      h('div', { class: 'top2' }, board(l.stations[0]), '→', board(l.stations[l.stations.length - 1])),
      h('details', null, h('summary', null, 'All stations on this leg'), h('ol', null, l.stations.map(n => h('li', null, n))))));
  });
  out.append(h('div', { class: 'card' }, h('div', { class: 'summary' }, h('span', null, h('b', null, R.stops), 'stops'), h('span', null, h('b', null, R.interchanges), R.interchanges === 1 ? 'interchange' : 'interchanges')), ...legs));
  paintMap(); focusOn(R.path);
}

/* ---------- 2. critical stations and what-if ---------- */
function toggleClosed(n) { if (state.closed.has(n)) state.closed.delete(n); else state.closed.add(n); renderCrit(); }
async function renderCrit() {
  const A = ANALYSIS;
  const p = panel(); const keep = $('#wsrc') ? [$('#wsrc').value, $('#wdst').value] : [state.src, state.dst];
  const inp = h('input', { type: 'text', id: 'wadd', list: 'stlist', placeholder: 'Type a station to close', autocomplete: 'off' });
  const add = () => { const v = inp.value.trim(); if (NET.stations.some(x => x.name === v)) { state.closed.add(v); renderCrit(); } };
  inp.addEventListener('change', add);
  const src = h('input', { type: 'text', id: 'wsrc', list: 'stlist', value: keep[0], placeholder: 'From', autocomplete: 'off' });
  const dst = h('input', { type: 'text', id: 'wdst', list: 'stlist', value: keep[1], placeholder: 'To', autocomplete: 'off' });
  const out = h('div', { id: 'wout', class: 'panel' });
  p.replaceChildren(stationInputs(),
    h('div', { class: 'card' }, h('h2', null, 'Critical stations'), syl('Module 6: connectivity, cut vertices'),
      h('p', null, 'Closing some stations splits the network into separate pieces. Such a station is a ', h('b', null, 'cut vertex'), '. ', h('b', null, A.cut_vertices), ' of the ', A.counts.V, ' stations are cut vertices. The ten whose closure cuts off the most stations:'),
      h('div', { class: 'tw' }, h('table', null, h('thead', null, h('tr', null, h('th', null, 'Station closed'), h('th', null, 'Stations cut off'))),
        h('tbody', null, A.critical.map(x => h('tr', null, h('td', null, h('button', { class: 'link', onclick: () => { state.hl = new Set([x.station]); paintMap(); focusOn([x.station]); } }, x.station)), h('td', { class: 'num' }, x.stranded)))))),
      how('Remove the station from the graph, then run BFS from any other station. If BFS cannot reach every remaining station, the graph has broken into pieces (components), so the closed station was a cut vertex.')),
    h('div', { class: 'card' }, h('h2', null, 'What if a station closes?'), syl('Module 6: connected components'),
      h('p', { class: 'muted' }, 'Click stations on the map, or type a name. Try Thane or Dadar.'),
      h('div', { class: 'row' }, h('label', { class: 'field' }, h('span', null, 'Close a station'), inp), h('button', { class: 'btn', type: 'button', onclick: add }, 'Close')),
      h('div', { class: 'tags' }, [...state.closed].map(n => h('span', { class: 'tag' }, n, h('button', { 'aria-label': 'Reopen ' + n, onclick: () => toggleClosed(n) }, '×')))),
      h('div', { class: 'row' }, h('label', { class: 'field' }, h('span', null, 'Check a trip from'), src), h('label', { class: 'field' }, h('span', null, 'to'), dst)),
      h('div', { class: 'row' }, h('button', { class: 'btn go', type: 'button', onclick: renderCrit }, 'Recompute'), h('button', { class: 'btn', type: 'button', onclick: () => { state.closed = new Set(); renderCrit(); } }, 'Reopen all'))), out);
  const body = { closed: [...state.closed], src: src.value.trim(), dst: dst.value.trim(), mode: state.mode };
  const r = await api('/api/disrupt', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (state.tab !== 'crit') return;
  state.stranded = new Set(r.stranded); state.route = r.route_checked && state.closed.size ? r.route : null;
  if (state.closed.size) out.append(h('div', { class: 'card' }, h('div', { class: 'note ' + (r.connected ? 'ok' : 'bad') }, r.connected ? 'The rest of the network is still connected.' : r.pieces.length + ' separate pieces now. ' + r.stranded.length + ' stations are cut off from the main network (faded on the map).'),
    r.stranded.length ? h('p', { class: 'muted' }, r.stranded.join(', ')) : null));
  if (r.route_checked && state.closed.size) out.append(h('div', { class: 'card' }, r.route ? [h('div', { class: 'summary' }, h('span', null, h('b', null, r.route.stops), 'stops'), h('span', null, h('b', null, r.route.interchanges), 'interchanges')), ...r.route.legs.map(l => h('p', null, chip(l.group), ' ', l.stations[0], ' → ', l.stations[l.stations.length - 1], ' (' + l.stops + ' stops)'))] : h('div', { class: 'note bad' }, 'No route between these stations with the closures in place.')));
  paintMap();
}

/* ---------- 3. Euler and Hamilton ---------- */
async function renderEuler() {
  const p = panel(); p.replaceChildren(h('div', { class: 'note' }, 'Loading…'));
  const E = await api('/api/euler'); if (state.tab !== 'euler') return;
  const c = ANALYSIS.counts;
  p.replaceChildren(
    h('div', { class: 'card' }, h('h2', null, 'Can you ride every track exactly once?'), syl('Module 6: Euler path and circuit'),
      h('div', { class: 'note ' + (E.status === 'none' ? 'bad' : 'ok') }, E.status === 'none' ? 'No. No Euler path or circuit exists.' : 'Yes. An Euler ' + E.status + ' exists.'),
      h('p', null, 'The rule needs 0 stations with an odd number of tracks (for a circuit) or exactly 2 (for a path). This network has ', h('b', null, E.odd.length), ' odd stations, so the answer is no.'),
      h('p', { class: 'muted' }, E.odd.join(', ')),
      h('button', { class: 'btn', type: 'button', onclick: () => { state.hl = new Set(E.odd); paintMap(); } }, 'Show the odd stations on the map'),
      how('Each time you pass through a station you use one track to come in and a different one to leave, so the tracks at that station are used up in pairs. Only the start and end stations can have an odd number of tracks.',
          'Handshake lemma check: all the degrees add up to ' + c.degree_sum + ' = 2 × ' + c.E + ', which is why the number of odd stations is always even.')),
    h('div', { class: 'card' }, h('h2', null, 'Can you visit every station exactly once?'), syl('Module 6: Hamiltonian path'),
      h('div', { class: 'note ' + (E.hamilton.path_possible ? 'ok' : 'bad') }, E.hamilton.path_possible ? 'Yes. A Hamiltonian path is possible.' : 'No. No Hamiltonian path or cycle exists.'),
      h('p', null, 'The map has ', h('b', null, E.hamilton.pendants.length), ' dead-end stations: ', E.hamilton.pendants.join(', '), '.'),
      h('button', { class: 'btn', type: 'button', onclick: () => { state.hl = new Set(E.hamilton.pendants); paintMap(); } }, 'Show the dead ends'),
      how('A dead-end station has only one track. If a trip visits it once, the trip must start or end there. A trip has only two ends, but there are ' + E.hamilton.pendants.length + ' dead ends, so it cannot be done.')));
}

/* ---------- 4. services as a relation (Module 3) ---------- */
async function renderRel() {
  const p = panel(); p.replaceChildren(h('div', { class: 'note' }, 'Loading…'));
  const R = await api('/api/relation'); if (state.tab !== 'rel') return;
  const head = ids => h('thead', null, h('tr', null, h('th'), ids.map(i => h('th', { class: 'c g-' + R.groups[i], title: R.names[i], style: 'color:var(--c)' }, i))));
  const matrix = M => h('div', { class: 'tw' }, h('table', { class: 'mat' }, head(R.ids), h('tbody', null, M.map((row, i) => h('tr', null, h('th', { class: 'g-' + R.groups[R.ids[i]], style: 'color:var(--c)', title: R.names[R.ids[i]] }, R.ids[i]), row.map(v => h('td', { class: v ? 'one' : '' }, v)))))));
  p.replaceChildren(
    h('div', { class: 'card' }, h('h2', null, 'Train services as a relation'), syl('Module 3: relations, matrix'),
      h('p', null, 'Let S be the 7 train services. Say ', h('b', null, 'a R b'), ' when services a and b share at least one station, so a passenger can change from one to the other.'),
      h('div', { class: 'tw' }, h('table', null, h('thead', null, h('tr', null, h('th', null, 'Code'), h('th', null, 'Service'))), h('tbody', null, R.ids.map(i => h('tr', null, h('td', null, i), h('td', null, R.names[i])))))),
      h('h3', null, 'Matrix of R (1 = share a station)'), matrix(R.M),
      how('R is reflexive (a service shares stations with itself) and symmetric (if a shares with b, then b shares with a). It is not transitive: Western (W) shares a station with the Harbour CSMT to Goregaon service (HG), and HG shares stations with the Harbour CSMT to Panvel service (HP), but W and HP share none.')),
    h('div', { class: 'card' }, h('h2', null, 'Transitive closure'), syl('Module 3: Warshall’s algorithm'),
      h('p', null, 'Warshall’s algorithm adds a 1 whenever a can reach b through some chain of services. Every entry becomes 1, so from any service you can reach any other by changing trains.'),
      matrix(R.closure),
      how('For each service k in turn, Warshall asks: if a connects to k and k connects to b, then a connects to b. Doing this for every k fills in all the indirect connections.')));
}

/* ---------- numbers strip ---------- */
function renderStrip() {
  const c = ANALYSIS.counts;
  $('#strip').replaceChildren(
    h('span', null, h('b', null, c.V), ' stations (vertices)'),
    h('span', null, h('b', null, c.E), ' tracks (edges)'),
    h('span', null, 'Handshake lemma: sum of degrees ', h('b', null, c.degree_sum), ' = 2 × ', h('b', null, c.E))
  );
}

/* ---------- start ---------- */
async function init() {
  NET = await api('/api/network');
  ANALYSIS = await api('/api/analysis');
  renderStrip();
  buildMap(); setupMapControls();
  document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
  setTab('trip');
}
init();
