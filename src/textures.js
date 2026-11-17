// Surface textures (public/textures, made by scripts/make_textures.py). Each has a colour map, a normal map for relief
// and a roughness map for where it is shiny or dull. Colour maps are near-neutral, so a material's own colour tints them.
// Models from Blender carry UVs measured in metres, so a texture that covers N metres just repeats every N units.
import * as THREE from 'three';

export const TILE = { concrete: 4, floor: 6, paving: 2.4, asphalt: 3, metal: 1, wood: 2, plastic: 0.3, fabric: 0.5, leather: 0.4, roof: 6, grass: 8, led: 0.5 };
const FLAT = new Set(['led']); // colour only, no relief or roughness maps
const cache = new Map();
// The sky as a reflection map. It is only given to materials that ask for it (`env`), never to the whole scene,
// because indoors there is a roof: the sky must not light the court or the floor.
let ENV = null;
export const setEnvironment = (t) => { ENV = t; };
export function reflect(mat, strength) { if (ENV && strength > 0) { mat.envMap = ENV; mat.envMapIntensity = strength; mat.needsUpdate = true; } return mat; }

// Load the images up front, so textures can be handed out (and cloned with different repeats) without waiting.
// `onProgress(fraction)` is called as files arrive, for the loading screen. The court is not loaded here: only the
// paint scheme in use is fetched, by loadSet().
const loader = new THREE.TextureLoader();
async function fetchAll(files, onProgress) {
  let done = 0;
  await Promise.all(files.map(async (f) => {
    if (!cache.has(f)) {
      try { const t = await loader.loadAsync('/textures/' + f + '?v=' + __BUILD__); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; cache.set(f, t); }
      catch { console.warn('texture missing:', f); }
    }
    if (onProgress) onProgress(++done / files.length);
  }));
}
export async function preload(onProgress) {
  const files = ['sky.jpg', 'lattice_color.jpg', 'parking_color.jpg', 'parking_rough.jpg', 'road_color.jpg', 'road_normal.jpg', 'road_rough.jpg'];
  for (const name of Object.keys(TILE)) { files.push(`${name}_color.jpg`); if (!FLAT.has(name)) files.push(`${name}_normal.jpg`, `${name}_rough.jpg`); }
  await fetchAll(files, onProgress);
}
const sets = new Map();
export function loadSet(name) { // colour, relief and shine maps for one named texture, fetched once
  if (!sets.has(name)) sets.set(name, fetchAll([`${name}_color.jpg`, `${name}_normal.jpg`, `${name}_rough.jpg`]));
  return sets.get(name);
}
export function texture(file, { srgb = false, repeat = null } = {}) {
  const src = cache.get(file);
  if (!src) return null;
  const t = src.clone();
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) t.repeat.set(repeat[0], repeat[1]);
  t.needsUpdate = true;
  return t;
}
// Put a texture set on a material. `tile` is how many metres one copy of the texture covers.
export function dress(mat, name, { tile = TILE[name], relief = 0.6, repeat = null, keepMap = false, env = null } = {}) {
  const rep = repeat || [1 / tile, 1 / tile];
  const colour = texture(`${name}_color.jpg`, { srgb: true, repeat: rep });
  if (!colour) return mat;
  if (name === 'led') { mat.emissiveMap = colour; if (!keepMap) mat.map = colour; }
  else {
    if (!keepMap) mat.map = colour;
    const n = texture(`${name}_normal.jpg`, { repeat: rep }), r = texture(`${name}_rough.jpg`, { repeat: rep });
    if (n && relief) { mat.normalMap = n; mat.normalScale = new THREE.Vector2(relief, relief); }
    if (r) { mat.roughnessMap = r; mat.roughness = 1; }
  }
  if (env) reflect(mat, env);
  mat.needsUpdate = true;
  return mat;
}

// Which texture each Blender material gets. `env` is how strongly it reflects the sky (low indoors).
const BY_NAME = {
  Bowl_Concrete: ['concrete', { relief: 0.5 }], Tunnel_Wall: ['concrete'], Rail_Steel: ['metal'],
  S_Wall: ['concrete'], S_Dark: ['concrete'], S_Concrete: ['concrete'], S_Pillar: ['concrete'], S_Stone: ['concrete', { relief: 0.2 }], S_Ceiling: ['concrete'], S_BoxCeiling: ['concrete'],
  S_Steel: ['metal'], S_Truss: ['metal'], S_Wood: ['wood'], S_WoodLight: ['wood'], S_Carpet: ['fabric'], S_Rug: ['fabric'], S_Leather: ['leather'],
  S_AccentYellow: ['fabric'], S_AccentBlue: ['fabric'], S_Screen: ['led'], S_Ribbon: ['led'], S_Scoreboard: ['led'],
  E_Roof: ['roof'], E_RoofEdge: ['metal'], E_Cream: ['concrete'], E_Beige: ['concrete'], E_Soffit: ['concrete'], E_Rail: ['metal'], E_Mullion: ['metal'], E_Letters: ['plastic'], E_Behind: ['concrete'],
  St_Deck: ['wood', { relief: 0.4 }], St_Riser: ['wood'], St_Skirt: ['fabric'], St_Truss: ['metal'], St_Barrier: ['metal'], St_Black: ['plastic'], St_Screen: ['led'],
};
// Texture every material in a loaded model by its Blender name.
export function dressModel(root, env) {
  const done = new Set();
  root.traverse((o) => {
    if (!o.isMesh || !o.material || done.has(o.material)) return;
    done.add(o.material);
    const entry = BY_NAME[o.material.name];
    if (entry) dress(o.material, entry[0], { ...(entry[1] || {}), env });
    else if (env) reflect(o.material, env);
  });
}
