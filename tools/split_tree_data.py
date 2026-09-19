#!/usr/bin/env python3
"""Split generated talent data into a light core plus lazy icon packs.

Outputs:
- tree-core.js: all layout/text/mechanics, no base64 art
- tree-icons.js: full icon map kept for backward compatibility
- tree-icons-<class>.js: only the art needed by that base class across live/future

The browser loads tree-core.js immediately and then fetches only the current
class's ~1 MB icon pack, instead of the former ~9 MB all-class image payload.
"""
import json
from pathlib import Path

src=Path("tree-data.js")
raw=src.read_text(encoding="utf-8").strip()
prefix="window.TREE_DATA="
if not raw.startswith(prefix):
    raise SystemExit("Unexpected tree-data.js format")
payload=raw[len(prefix):]
if payload.endswith(";"):
    payload=payload[:-1]
data=json.loads(payload)
icons=data.pop("icons",{})

core="window.TREE_DATA="+json.dumps(data,ensure_ascii=False,separators=(",",":"))+";\n"
Path("tree-core.js").write_text(core,encoding="utf-8")

# Full pack remains available as a compatibility/debug artifact but is no longer
# requested by the normal application path.
icon_js="window.TREE_ICONS="+json.dumps(icons,ensure_ascii=False,separators=(",",":"))+";\n"
Path("tree-icons.js").write_text(icon_js,encoding="utf-8")

base_sets={}
for tree in (data.get("classes") or []) + (data.get("liveClasses") or []):
    base=tree.get("parent") or tree.get("key")
    if not base:
        continue
    keys=base_sets.setdefault(base,set())
    for node in tree.get("nodes",[]):
        s=node.get("s")
        if s in icons:
            keys.add(s)

for base,keys in sorted(base_sets.items()):
    pack={k:icons[k] for k in sorted(keys)}
    js=(
        "window.TREE_ICONS=Object.assign(window.TREE_ICONS||{},"
        +json.dumps(pack,ensure_ascii=False,separators=(",",":"))
        +");\n"
    )
    path=Path(f"tree-icons-{base}.js")
    path.write_text(js,encoding="utf-8")
    print(path.name,"MB",round(path.stat().st_size/1048576,2),"icons",len(pack))

print("tree-data.js MB",round(src.stat().st_size/1048576,2))
print("tree-core.js MB",round(Path("tree-core.js").stat().st_size/1048576,2))
print("tree-icons.js MB",round(Path("tree-icons.js").stat().st_size/1048576,2))
print("icons",len(icons))
