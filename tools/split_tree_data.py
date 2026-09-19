#!/usr/bin/env python3
"""Split the generated talent payload so layout/text can render before icon art.

tree-core.js is intentionally small and contains every gameplay/text field.
tree-icons.js contains only the large base64 icon map and is loaded lazily.
tree-data.js remains the canonical generated artifact for audits/backward compatibility.
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
icon_js="window.TREE_ICONS="+json.dumps(icons,ensure_ascii=False,separators=(",",":"))+";\n"
Path("tree-core.js").write_text(core,encoding="utf-8")
Path("tree-icons.js").write_text(icon_js,encoding="utf-8")

print("tree-data.js MB",round(src.stat().st_size/1048576,2))
print("tree-core.js MB",round(Path("tree-core.js").stat().st_size/1048576,2))
print("tree-icons.js MB",round(Path("tree-icons.js").stat().st_size/1048576,2))
print("icons",len(icons))
