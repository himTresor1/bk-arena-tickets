"""Turn the OpenStreetMap extract (reference/complex/osm/map.osm) into a plain site plan in metres: blender/site.json.
Origin is the centre of BK Arena. x = east, z = south (the website's ground axes). Also draws blender/renders/site_plan.png.
Run:  ~/.blender-mcp/venv/bin/python scripts/site_from_osm.py
"""
import json, math, os, xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "reference/complex/osm/map.osm")
LAT0, LON0 = -1.953181, 30.115636  # BK Arena
KX, KZ = 111320 * math.cos(math.radians(LAT0)), 110574
WIDTH = {"trunk": 15, "trunk_link": 7, "primary": 12, "primary_link": 7, "secondary": 10, "tertiary": 8, "residential": 6,
         "unclassified": 6, "service": 4.5, "footway": 2, "path": 1.6, "cycleway": 2}

root = ET.parse(SRC).getroot()
node = {}
trees = []
for n in root.iter("node"):
    p = (round((float(n.get("lon")) - LON0) * KX, 2), round(-(float(n.get("lat")) - LAT0) * KZ, 2))
    node[n.get("id")] = p
    tags = {t.get("k"): t.get("v") for t in n.findall("tag")}
    if tags.get("natural") == "tree":
        trees.append(p)

ways = {}
for w in root.iter("way"):
    tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
    pts = [node[nd.get("ref")] for nd in w.findall("nd") if nd.get("ref") in node]
    ways[w.get("id")] = (tags, pts)


def ring(pts):
    return pts[:-1] if len(pts) > 2 and pts[0] == pts[-1] else pts


def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


site = {"origin": {"lat": LAT0, "lon": LON0}, "buildings": [], "roads": [], "parking": [], "pitches": [], "tracks": [], "pools": [],
        "walls": [], "green": [], "trees": trees, "stadiums": []}


def building(wid, tags, pts):
    p = ring(pts)
    if len(p) < 3 or area(p) < 6:
        return
    lv = tags.get("building:levels")
    try:
        lv = int(float(lv))
    except (TypeError, ValueError):
        lv = None
    site["buildings"].append({"id": wid, "pts": p, "levels": lv, "name": tags.get("name"), "kind": tags.get("building"),
                              "use": tags.get("amenity") or tags.get("shop") or tags.get("tourism") or tags.get("office")})


for wid, (tags, pts) in ways.items():
    if tags.get("leisure") == "stadium":
        site["stadiums"].append({"id": wid, "name": tags.get("name"), "pts": ring(pts)})
        continue
    if "building" in tags:
        building(wid, tags, pts)
    elif tags.get("highway") in WIDTH and len(pts) > 1:
        cls = tags["highway"]
        site["roads"].append({"id": wid, "cls": cls, "name": tags.get("name"), "pts": pts, "width": WIDTH[cls],
                              "oneway": tags.get("oneway") == "yes", "closed": pts[0] == pts[-1]})
    elif tags.get("amenity") == "parking" and len(pts) > 3:
        site["parking"].append({"id": wid, "pts": ring(pts)})
    elif tags.get("leisure") == "pitch":
        site["pitches"].append({"id": wid, "sport": tags.get("sport"), "pts": ring(pts)})
    elif tags.get("leisure") == "swimming_pool":
        site["pools"].append({"id": wid, "pts": ring(pts)})
    elif tags.get("barrier") in ("wall", "fence") and len(pts) > 1:
        site["walls"].append({"id": wid, "pts": pts})
    elif tags.get("leisure") in ("park", "garden", "recreation_ground") or tags.get("landuse") in ("grass", "forest") or tags.get("natural") in ("scrub", "wood"):
        site["green"].append({"id": wid, "pts": ring(pts)})

for rel in root.iter("relation"):
    tags = {t.get("k"): t.get("v") for t in rel.findall("tag")}
    outer = [ways[m.get("ref")][1] for m in rel.findall("member") if m.get("type") == "way" and m.get("role") == "outer" and m.get("ref") in ways]
    inner = [ways[m.get("ref")][1] for m in rel.findall("member") if m.get("type") == "way" and m.get("role") == "inner" and m.get("ref") in ways]
    if tags.get("leisure") == "track" and outer:
        site["tracks"].append({"id": rel.get("id"), "outer": ring(outer[0]), "inner": ring(inner[0]) if inner else None})
    elif "building" in tags:
        for o in outer:
            building("r" + rel.get("id"), tags, o)

json.dump(site, open(os.path.join(ROOT, "blender/site.json"), "w"))
print({k: len(v) for k, v in site.items() if isinstance(v, list)})

# ---- a picture of the plan, 1 px = 1 m, to check positions by eye
from PIL import Image, ImageDraw
xs = [p[0] for b in site["buildings"] for p in b["pts"]]; zs = [p[1] for b in site["buildings"] for p in b["pts"]]
x0, x1, z0, z1 = min(xs) - 20, max(xs) + 20, min(zs) - 20, max(zs) + 20
S = 1.6
img = Image.new("RGB", (int((x1 - x0) * S), int((z1 - z0) * S)), (236, 232, 222))
d = ImageDraw.Draw(img)
P = lambda pts: [((x - x0) * S, (z - z0) * S) for x, z in pts]
for g in site["green"]: d.polygon(P(g["pts"]), fill=(190, 215, 170))
for a in site["parking"]: d.polygon(P(a["pts"]), fill=(200, 200, 205))
for r in sorted(site["roads"], key=lambda r: r["width"]): d.line(P(r["pts"]), fill=(255, 255, 255) if r["width"] < 10 else (250, 220, 120), width=max(1, int(r["width"] * S)))
for t in site["tracks"]: d.polygon(P(t["outer"]), fill=(200, 110, 90))
for a in site["pitches"]: d.polygon(P(a["pts"]), fill=(90, 170, 90))
for a in site["pools"]: d.polygon(P(a["pts"]), fill=(90, 170, 230))
for s in site["stadiums"]: d.polygon(P(s["pts"]), outline=(200, 40, 40))
for b in site["buildings"]: d.polygon(P(b["pts"]), fill=(150, 120, 100) if not b["levels"] else (90, 90, 150))
for w in site["walls"]: d.line(P(w["pts"]), fill=(60, 60, 60), width=1)
for t in site["trees"]: d.ellipse([(t[0] - x0) * S - 3, (t[1] - z0) * S - 3, (t[0] - x0) * S + 3, (t[1] - z0) * S + 3], fill=(40, 130, 40))
for gx in range(int(x0 // 100) * 100, int(x1), 100):
    d.line([((gx - x0) * S, 0), ((gx - x0) * S, img.size[1])], fill=(210, 205, 195)); d.text(((gx - x0) * S + 2, 2), str(gx), fill=(0, 0, 0))
for gz in range(int(z0 // 100) * 100, int(z1), 100):
    d.line([(0, (gz - z0) * S), (img.size[0], (gz - z0) * S)], fill=(210, 205, 195)); d.text((2, (gz - z0) * S + 2), str(gz), fill=(0, 0, 0))
os.makedirs(os.path.join(ROOT, "blender/renders"), exist_ok=True)
img.save(os.path.join(ROOT, "blender/renders/site_plan.png"))
print("extent x", round(x0), round(x1), "z", round(z0), round(z1), img.size)
