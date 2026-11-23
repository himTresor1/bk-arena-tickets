// Real grass for the tour: thousands of single blades standing on the pitches and lawns around the camera.
// Where grass grows is not listed anywhere, so it is photographed: the district is drawn once from straight above
// into two small pictures, one with the colour of every grass surface (so blades on a pitch keep its stripes and
// white lines) and one with the height of the ground. A square of blades then follows the camera, and each blade
// looks itself up in those pictures: off the grass it shrinks to nothing.
import * as THREE from 'three';

const HALF = 820, CX = -110, CZ = 200, YMAX = 6.4; // the photographed square (metres) and the tallest ground in it

export function makeGrass({ renderer, scene, lite }) {
  const RES = lite ? 1024 : 2048;
  const rt = () => new THREE.WebGLRenderTarget(RES, RES, { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false });
  const colRT = rt(), hgtRT = rt();
  const top = new THREE.OrthographicCamera(-HALF, HALF, HALF, -HALF, 1, 700); top.position.set(CX, 500, CZ); top.up.set(0, 0, -1); top.lookAt(CX, 0, CZ);
  // anything that is not grass hides the grass under it and leaves the picture empty there
  const blocker = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0, blending: THREE.NoBlending, fog: false, toneMapped: false, side: THREE.DoubleSide });
  const heightMat = new THREE.ShaderMaterial({ side: THREE.DoubleSide,
    vertexShader: 'varying float vY; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vY = w.y; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: `varying float vY; void main() { gl_FragColor = vec4(clamp(vY / ${YMAX.toFixed(1)}, 0.0, 1.0), 0.0, 0.0, 1.0); }` });
  const flat = new Map(); // one plain copy of each grass material; its opacity carries how tall the grass is there
  const plain = (m, kind) => { if (!flat.has(m)) flat.set(m, new THREE.MeshBasicMaterial({ map: m.map, color: m.color, transparent: true, opacity: kind, blending: THREE.NoBlending, fog: false, toneMapped: false, side: THREE.DoubleSide })); return flat.get(m); };

  function refresh() {
    const swapped = [], hidden = [];
    scene.traverse((o) => {
      if (o.isInstancedMesh || o.userData.noMask) { if (o.visible) { hidden.push(o); o.visible = false; } return; }
      if (!o.isMesh) return;
      swapped.push([o, o.material]); o.material = o.userData.grass ? plain(o.material, o.userData.grass) : blocker;
    });
    const bg = scene.background, fog = scene.fog, target = renderer.getRenderTarget(), auto = renderer.shadowMap.autoUpdate, clear = new THREE.Color(); renderer.getClearColor(clear); const alpha = renderer.getClearAlpha();
    scene.background = null; scene.fog = null; renderer.shadowMap.autoUpdate = false; renderer.setClearColor(0x000000, 0);
    renderer.setRenderTarget(colRT); renderer.clear(); renderer.render(scene, top);
    scene.overrideMaterial = heightMat; renderer.setRenderTarget(hgtRT); renderer.clear(); renderer.render(scene, top); scene.overrideMaterial = null;
    renderer.setRenderTarget(target); renderer.setClearColor(clear, alpha); renderer.shadowMap.autoUpdate = auto; scene.background = bg; scene.fog = fog;
    for (const [o, m] of swapped) o.material = m;
    for (const o of hidden) o.visible = true;
  }

  // one blade: a tapering strip, three triangles
  const blade = new THREE.BufferAttribute(new Float32Array([-0.5, 0, 0, 0.5, 0, 0, -0.36, 0.5, 0, 0.36, 0.5, 0, 0, 1, 0]), 3);
  let r = 7; const rnd = () => ((r = (r * 16807) % 2147483647) / 2147483647);
  // two carpets follow the camera: a thick one underfoot and a thinner one of broader tufts carrying on into the distance
  const layers = (lite ? [[11, 20000, 1, 1], [30, 9000, 2.4, 1.25]] : [[16, 95000, 1, 1], [58, 80000, 2.3, 1.25]]).map(([S, N, wide, tall]) => {
  const geo = new THREE.InstancedBufferGeometry();
  geo.setAttribute('position', blade); geo.setIndex([0, 1, 2, 2, 1, 3, 2, 3, 4]);
  const seed = new Float32Array(N * 4); for (let i = 0; i < N * 4; i++) seed[i] = rnd();
  geo.setAttribute('seed', new THREE.InstancedBufferAttribute(seed, 4)); geo.instanceCount = N;
  const mat = new THREE.ShaderMaterial({
    side: THREE.DoubleSide, fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { eye: { value: new THREE.Vector3() }, time: { value: 0 }, S: { value: S }, grow: { value: new THREE.Vector2(wide, tall) },
      colMap: { value: null }, hgtMap: { value: null }, rect: { value: new THREE.Vector3(CX - HALF, CZ + HALF, 1 / (2 * HALF)) }, sun: { value: new THREE.Vector3(-0.55, 0.74, 0.38).normalize() } }]),
    vertexShader: `
      #include <common>
      #include <fog_pars_vertex>
      #include <logdepthbuf_pars_vertex>
      uniform vec3 eye, rect, sun; uniform vec2 grow; uniform float time, S; uniform sampler2D colMap, hgtMap;
      attribute vec4 seed; varying vec3 vCol;
      void main() {
        vec2 w = mod(seed.xy * S - eye.xz, S) - 0.5 * S + eye.xz;            // the square of blades wraps round the camera
        vec2 uv = vec2((w.x - rect.x) * rect.z, (rect.y - w.y) * rect.z);
        vec4 m = texture2D(colMap, uv); float ground = texture2D(hgtMap, uv).r * ${YMAX.toFixed(1)};
        float here = smoothstep(0.3, 0.6, m.a) * (1.0 - smoothstep(0.72, 1.0, distance(w, eye.xz) / (0.5 * S)));
        float lawn = smoothstep(0.75, 0.95, m.a);                           // lawns grow longer than pitches
        float H = mix(0.085, 0.26, lawn) * (0.55 + 0.9 * seed.w) * here * grow.y, W = mix(0.03, 0.042, lawn) * here * grow.x;
        float a = seed.z * 6.2832, t = position.y; vec2 dir = vec2(cos(a), sin(a));
        float lean = (0.2 + 0.55 * fract(seed.w * 7.3)) * H * t * t + sin(time * 1.6 + w.x * 0.31 + w.y * 0.23 + seed.w * 4.0) * 0.16 * H * t * t;
        vec3 p = vec3(w.x, ground + 0.015, w.y) + vec3(dir.x, 0.0, dir.y) * position.x * W + vec3(0.0, t * H, 0.0) + vec3(-dir.y, 0.0, dir.x) * lean;
        float light = 0.5 + 0.62 * clamp(dot(normalize(vec3(-dir.y * 0.5, 1.0, dir.x * 0.5)), sun), 0.0, 1.0);
        vCol = m.rgb * mix(0.55, 1.22, t) * (0.88 + 0.24 * fract(seed.w * 13.7)) * light;
        vec4 mvPosition = viewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        #include <logdepthbuf_vertex>
        #include <fog_vertex>
      }`,
    fragmentShader: `
      #include <common>
      #include <fog_pars_fragment>
      #include <logdepthbuf_pars_fragment>
      varying vec3 vCol;
      void main() {
        #include <logdepthbuf_fragment>
        gl_FragColor = vec4(vCol, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
  });
  mat.uniforms.colMap.value = colRT.texture; mat.uniforms.hgtMap.value = hgtRT.texture;
  const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.userData.noMask = true; mesh.visible = false; scene.add(mesh);
  return mesh;
  });
  let wait = 0;
  return {
    refresh, layers,
    refreshSoon() { clearTimeout(wait); wait = setTimeout(refresh, 250); }, // several models arriving together are photographed once
    update(camera, time, groundY) { // blades are only worth drawing from close to the ground
      const show = camera.position.y - groundY < 40;
      for (const m of layers) { m.visible = show; if (show) { m.material.uniforms.eye.value.copy(camera.position); m.material.uniforms.time.value = time; } }
    },
  };
}
