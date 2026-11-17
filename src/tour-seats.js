// Amahoro Stadium's seats for the tour: every chair is a real one, the same tip-up chair as in BK Arena
// (public/models/chair.glb), drawn many at a time. Where the rows run comes from public/tour/amahoro_seats.json,
// written by blender/py/110_amahoro.py together with the stepped terraces the chairs stand on.
// The stand is cut into 36 wedges per tier; each wedge shows the full chair when you are close and a
// four-triangle stand-in when you are far, so 40,000 chairs stay light on a phone.
const BLUE = 0x2f8fc8, YELLOW = 0xe6b422, GREEN = 0x1f8048; // the arena's seat colours
const hash = (a, b, c) => { let h = (Math.imul(a + 7, 374761393) ^ Math.imul(b + 3, 668265263) ^ Math.imul(c + 11, 2246822519)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };

export async function addAmahoroSeats({ THREE, scene, root, loader, V = '', coarse = false }) {
  const lay = await fetch('/tour/amahoro_seats.json' + V).then((r) => r.json());
  const N = lay.front.length, o = new THREE.Object3D(), col = new THREE.Color();

  // ---- the chair: plastic back and folded-up seat in one piece, steel frame apart (only drawn close up)
  const plain = (g, m) => { // position + normal only, un-indexed, optionally moved by a matrix
    g = g.index ? g.toNonIndexed() : g.clone(); if (m) g.applyMatrix4(m);
    const out = new THREE.BufferGeometry(); out.setAttribute('position', g.attributes.position); out.setAttribute('normal', g.attributes.normal); return out;
  };
  const join = (list) => {
    const n = list.reduce((s, g) => s + g.attributes.position.count, 0), P = new Float32Array(n * 3), Nn = new Float32Array(n * 3); let k = 0;
    for (const g of list) { P.set(g.attributes.position.array, k); Nn.set(g.attributes.normal.array, k); k += g.attributes.position.count * 3; }
    const out = new THREE.BufferGeometry(); out.setAttribute('position', new THREE.BufferAttribute(P, 3)); out.setAttribute('normal', new THREE.BufferAttribute(Nn, 3)); return out;
  };
  const panUp = new THREE.Matrix4().makeTranslation(0, 0.45, -0.15).multiply(new THREE.Matrix4().makeRotationX(-1.44)); // empty seats stand folded, as in the arena
  // stand-in for far away: the back as one sheet and the folded seat in front of it
  const quad = (x, y0, z0, y1, z1) => [-x, y0, z0, x, y0, z0, x, y1, z1, -x, y0, z0, x, y1, z1, -x, y1, z1];
  const farGeo = new THREE.BufferGeometry();
  farGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array([...quad(0.225, 0.42, -0.2, 0.94, -0.26), ...quad(0.22, 0.45, -0.15, 0.85, -0.1)]), 3));
  farGeo.computeVertexNormals();
  let nearGeo = farGeo, frameGeo = null;
  try {
    const g = await loader.loadAsync('/models/chair.glb' + V), get = (n) => g.scene.getObjectByName(n).geometry;
    nearGeo = join([plain(get('Back_far')), plain(get('Pan_far'), panUp)]); frameGeo = plain(get('Frame_far'));
  } catch (err) { console.warn('arena chair not loaded, Amahoro uses the simple one:', err.message); }
  const plastic = new THREE.MeshStandardMaterial({ roughness: 0.42, side: THREE.DoubleSide });
  const steel = new THREE.MeshStandardMaterial({ color: 0x15171a, roughness: 0.5, metalness: 0.7 });

  // ---- where the chairs go. Model metres: x east, y up, z = minus the Blender y (the model is exported y-up).
  const rowPt = (i, s) => { const f = lay.front[i % N], b = lay.back[i % N]; return [f[0] + (b[0] - f[0]) * s, f[1] + (b[1] - f[1]) * s]; };
  const wedges = [];
  for (const tier of ['lower', 'upper']) {
    const rows = lay[tier], R = rows.length;
    for (let a = 0; a < N; a += lay.aisleEvery) { // one wedge between two aisles
      const seats = [];
      rows.forEach(([s, z], r) => {
        const pts = []; for (let k = 0; k <= lay.aisleEvery; k++) pts.push(rowPt(a + k, s));
        const cum = [0]; for (let k = 1; k < pts.length; k++) cum.push(cum[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
        const L = cum[cum.length - 1];
        let lo = lay.aisleHalf, hi = L - lay.aisleHalf;
        if (tier === 'upper' && r >= lay.vomRows[0] && r <= lay.vomRows[1]) { // keep clear of the tunnel mouths
          if (a % lay.vomEvery === 0) lo = cum[1] * lay.vomFrac + 0.45;
          if ((a + lay.aisleEvery) % lay.vomEvery === 0) hi = L - (L - cum[cum.length - 2]) * lay.vomFrac - 0.45;
        }
        const n = Math.floor((hi - lo) / lay.pitch); if (n < 1) return;
        const pad = (hi - lo - n * lay.pitch) / 2;
        for (let q = 0; q < n; q++) {
          const d = lo + pad + (q + 0.5) * lay.pitch; let k = 1; while (k < cum.length - 1 && cum[k] < d) k++;
          const t = (d - cum[k - 1]) / (cum[k] - cum[k - 1]), p0 = pts[k - 1], p1 = pts[k], tx = p1[0] - p0[0], ty = p1[1] - p0[1], tl = Math.hypot(tx, ty);
          const inx = -ty / tl, iny = tx / tl; // towards the pitch (the rows run anticlockwise)
          // colours as in the real stands: blue above, yellow in the middle, green by the pitch, mixed in small patches
          const f = r / (R - 1), own = hash(a, r, q), patch = hash(a + 500, r >> 1, Math.floor(q / 3)), h = hash(q, a, r) < 0.5 ? patch : own;
          const c = tier === 'upper' ? (h < 0.82 - f * 1.9 ? YELLOW : BLUE) : (h < 0.78 - f * 0.62 ? GREEN : YELLOW);
          seats.push([p0[0] + tx * t, z, -(p0[1] + ty * t), Math.atan2(inx, -iny), c]);
        }
      });
      if (!seats.length) continue;
      const mesh = new THREE.InstancedMesh(farGeo, plastic, seats.length);
      const frame = frameGeo ? new THREE.InstancedMesh(frameGeo, steel, seats.length) : null;
      const c = new THREE.Vector3();
      seats.forEach(([x, y, z, ry, hex], i) => {
        o.position.set(x, y, z); o.rotation.set(0, ry, 0); o.updateMatrix(); mesh.setMatrixAt(i, o.matrix); if (frame) frame.setMatrixAt(i, o.matrix);
        mesh.setColorAt(i, col.setHex(hex)); c.x += x; c.y += y; c.z += z;
      });
      c.divideScalar(seats.length);
      mesh.instanceColor.needsUpdate = true; mesh.receiveShadow = !coarse; mesh.castShadow = false; mesh.computeBoundingSphere();
      if (frame) { frame.visible = false; frame.castShadow = false; frame.boundingSphere = mesh.boundingSphere; root.add(frame); }
      root.add(mesh); wedges.push({ mesh, frame, centre: c, detail: 'far' });
    }
  }

  // ---- detail follows the camera: call update(camera) every frame (cheap: 72 distance checks)
  const NEAR = coarse ? 50 : 95, FRAME = coarse ? 22 : 45, world = new THREE.Vector3();
  function update(camera) {
    for (const w of wedges) {
      const d = world.copy(w.centre).applyMatrix4(root.matrixWorld).distanceTo(camera.position);
      const want = d < NEAR ? 'near' : d > NEAR + 12 ? 'far' : w.detail;
      if (want !== w.detail) { w.detail = want; w.mesh.geometry = want === 'near' ? nearGeo : farGeo; }
      if (w.frame) w.frame.visible = d < FRAME;
    }
  }
  root.updateMatrixWorld(true);
  return { update, wedges, count: wedges.reduce((s, w) => s + w.mesh.count, 0) };
}
