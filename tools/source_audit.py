#!/usr/bin/env python3
"""Audit talent provenance and high-value mechanics against trusted sources.

This complements audit_text.py:
- every displayed node must declare where its English/Chinese name and English description came from;
- official Depths of the Damned preview changes are checked by talent name + numeric tokens;
- Just a Dream is checked against Fatshark's Bound by Duty notes and current game-source behavior.
"""
import json, re, sys
from pathlib import Path
from collections import Counter

raw=Path("tree-data.js").read_text(encoding="utf-8").strip()
prefix="window.TREE_DATA="
if not raw.startswith(prefix):
    raise SystemExit("bad tree-data.js")
payload=raw[len(prefix):]
if payload.endswith(";"): payload=payload[:-1]
data=json.loads(payload)

def norm(s):
    s=(s or "").replace("’","'").replace("–","-").replace("—","-").strip().lower()
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def nums(s):
    return sorted(x.lstrip("+-") for x in re.findall(r"[-+]?\d+(?:\.\d+)?%?",s or ""))

issues=[]
nodes=[]
for tree in (data.get("classes") or [])+(data.get("liveClasses") or []):
    for n in tree.get("nodes",[]):
        if n.get("cat")=="root": continue
        nodes.append((tree,n))
        en=n.get("en","")
        cn=n.get("cn","")
        if not en: issues.append(("fatal","missing_en_name",tree.get("patch"),tree.get("key"),n.get("s"),""))
        if not n.get("nameSourceEn"): issues.append(("high","missing_en_name_source",tree.get("patch"),tree.get("key"),n.get("s"),en))
        if cn and cn!=en and not n.get("nameSourceCn"): issues.append(("high","missing_cn_name_source",tree.get("patch"),tree.get("key"),n.get("s"),en))
        if n.get("desc") and not n.get("descSourceEn"): issues.append(("high","missing_en_desc_source",tree.get("patch"),tree.get("key"),n.get("s"),en))

# Official preview expectations. These are intentionally limited to explicit changes in
# Fatshark's Sep 18 2026 preview; unchanged talents remain sourced from current live data.
official_preview={
  "found some more":["1%","15"],
  "faithful frenzy":["5%"],
  "holy revenant":["25%"],
  "zealous pilgrim":["5"],
  "fire and fury":["12","3"],
  "risen":["5","8","5"],
  "got your back":["7.5%","5%"],
  "holy tools":["20%","5"],
  "wait in line":["20%"],
  "purifying hatred":["15%"],
  "the voice of terra":["10%"],
  "out of pocket":["10%"],
  "unseen blade":["20%"],
  "focused warp":["15%"],
  "peril equilibrium":["75%","2%"],
  "psykinetic grip":["20%"],
  "guardsman":["25%"],
  "sharpshooter":["1%","5"],
  "close and kill":["7.5%"],
}
future_by_name={}
for tree,n in nodes:
    if tree.get("patch")=="future":
        future_by_name.setdefault(norm(n.get("en")),[]).append(n)

for name,required in official_preview.items():
    arr=future_by_name.get(name,[])
    if not arr:
        issues.append(("high","official_preview_talent_missing","future","*",name,""))
        continue
    combined=" ".join((n.get("desc") or "")+" "+(n.get("advancedEn") or "") for n in arr)
    found=nums(combined)
    for token in required:
        if token.lstrip("+-") not in found:
            issues.append(("high","official_preview_value_missing","future","*",name,token))

# Just a Dream: official user-facing effect + code behavior.
jad=[]
for tree,n in nodes:
    if norm(n.get("en"))=="just a dream":
        jad.append((tree,n))
if not jad:
    issues.append(("fatal","just_a_dream_missing","*","psyker","*",""))
else:
    for tree,n in jad:
        desc=n.get("desc","")
        if "25%" not in desc or "Peril" not in desc:
            issues.append(("fatal","just_a_dream_effect_wrong",tree.get("patch"),tree.get("key"),n.get("s"),desc))
        if n.get("cn") not in ("如梦似幻","如夢似幻"):
            issues.append(("medium","just_a_dream_cn_name_unverified",tree.get("patch"),tree.get("key"),n.get("s"),n.get("cn","")))
        if "97%" not in (n.get("mechanicsEn","")):
            issues.append(("high","just_a_dream_mechanics_note_missing",tree.get("patch"),tree.get("key"),n.get("s"),""))
        if "Max Health" not in n.get("mechanicsEn","") or "Max Toughness" not in n.get("mechanicsEn",""):
            issues.append(("high","just_a_dream_no_direct_stat_note_missing",tree.get("patch"),tree.get("key"),n.get("s"),""))

sev=Counter(x[0] for x in issues)
src_name=Counter(n.get("nameSourceCn","") for _,n in nodes)
src_desc=Counter(n.get("descSource","") for _,n in nodes)
print("AUDITED_NODES",len(nodes))
print("CN_NAME_SOURCES",json.dumps(src_name,ensure_ascii=False,sort_keys=True))
print("CN_DESC_SOURCES",json.dumps(src_desc,ensure_ascii=False,sort_keys=True))
print("ISSUES",json.dumps(dict(sev),ensure_ascii=False,sort_keys=True))
for x in issues:
    print(json.dumps({"severity":x[0],"kind":x[1],"patch":x[2],"class":x[3],"node":x[4],"detail":x[5]},ensure_ascii=False))

# Fail on factual/provenance problems. Medium is advisory (e.g. source naming preference).
fatal_or_high=sum(v for k,v in sev.items() if k in ("fatal","high"))
sys.exit(1 if fatal_or_high else 0)
