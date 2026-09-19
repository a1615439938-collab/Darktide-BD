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

# Official Sep 18 2026 Depths of the Damned preview expectations.
# Values below are explicit in Fatshark's preview. For baseline/Iconic passives that
# are not selectable nodes (e.g. Guardsman / Sharpshooter), inspect the class root.
official_preview={
  # Ogryn
  "dominate":["15%","10"],
  "keep shooting":["20%"],
  "soften them up":["15%","5"],
  "go again":["1.5%"],
  "maximum firepower":["100%","2.5"],
  "bruiser":["50%","4"],
  "indomitable":["25","25%","100%"],
  "found some more":["1%","15"],
  # Zealot
  "faithful frenzy":["10%","5%"],
  "until death":["8","120"],
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
  "retributor s stance":["0.5%","10%"],
  "chorus of spiritual fortitude":["5","0.8","45%","15","75","8","60"],
  "holy cause":["8%","5","10"],
  "ecclesiarch s call":["6%","5","10"],
  # Psyker
  "mind in motion":["5%"],
  "focused warp":["15%"],
  "peril equilibrium":["75%","2%"],
  "psykinetic grip":["20%"],
  "psykinetic s aura":["50%","3"],
  "perilous combustion":["2"],
  "surety of arms":["30%","80%","15%"],
  # Veteran
  "duck and dive":["30%","5%"],
  "survivalist":["0.5%","5","0.25%"],
  "close and kill":["7.5%"],
  "duty and honour":["75","10"],
  # Arbites
  "nuncio aquila":["7.5","7.5%","30%","30%","25%","15%","20","60"],
  "lone wolf":["15%","10%","20%","1","45","90"],
  # Hive Scum
  "rampage":["35%","20%","25%","10","30"],
  "sample collector":["0.5","1"],
  # Skitarii
  "advanced combat doctrines":["25%","90%","60%","10%","1%","5"],
  "voltaic motivator":["5%","5%","15"],
  "voltaic overcharge":["25%","1%"],
  "higher purpose":["2.5%"],
  "noospheric command":["30%","2"],
  "voltaic burst":["12"],
  "ammunition deposit":["25","15%"],
  "system shock":["3","2.5%"],
  "galvanized coating":["15%","7.5%"],
  "target neutralization feedback":["5"],
  "salvation doctrine":["25%","25%"],
  "superior tracking litanies":["50%","45%"],
  "force distribution actuators":["75%","50%"],
}

future_by_name={}
future_roots={}
for tree in (data.get("classes") or []):
    if tree.get("patch")!="future":
        continue
    for n in tree.get("nodes",[]):
        if n.get("cat")=="root":
            future_roots[tree.get("key")]=n
            continue
        future_by_name.setdefault(norm(n.get("en")),[]).append(n)

for name,required in official_preview.items():
    arr=future_by_name.get(name,[])
    if not arr:
        issues.append(("high","official_preview_talent_missing","future","*",name,""))
        continue
    combined=" ".join((n.get("desc") or "")+" "+(n.get("advancedEn") or "")+" "+(n.get("mechanicsEn") or "") for n in arr)
    found=nums(combined)
    for token in required:
        if token.lstrip("+-") not in found:
            issues.append(("high","official_preview_value_missing","future","*",name,token))
    for n in arr:
        if n.get("descSourceEn")!="fatshark-official-preview" and name not in {
            "found some more","zealous pilgrim","fire and fury","risen","got your back",
            "holy tools","wait in line","purifying hatred","focused warp","peril equilibrium","psykinetic grip"
        }:
            issues.append(("high","official_preview_source_not_applied","future",n.get("class","*"),n.get("s"),name))

# Baseline/Iconic passives belong to the class start node rather than costing talent points.
root_expectations={
  "ogryn":["125","50%"],
  "zealot":["125","75%"],
  "psyker":["10%"],
  "veteran":["25%","1%","5"],
}
for cls,required in root_expectations.items():
    root=future_roots.get(cls)
    if not root:
        issues.append(("high","future_class_root_missing","future",cls,"root",""))
        continue
    combined=(root.get("mechanicsEn") or "")
    found=nums(combined)
    for token in required:
        if token.lstrip("+-") not in found:
            issues.append(("high","iconic_passive_value_missing","future",cls,root.get("s"),token))
    if root.get("mechanicsSource")!="fatshark-official-preview+syuantsai-preview-translation":
        issues.append(("high","iconic_passive_source_missing","future",cls,root.get("s"),root.get("mechanicsSource","")))

# Preview explicitly removes Readiness Doctrines.
if future_by_name.get("readiness doctrines"):
    issues.append(("high","removed_future_talent_still_present","future","skitarii","readiness doctrines",""))

# Axial Slash keeps the same player-facing title/summary, but its cleave damage/impact
# profile changes in the official preview; require that detailed mechanics note.
axial=future_by_name.get("axial slash",[])
if axial:
    mechanics=" ".join(n.get("mechanicsEn","") for n in axial)
    for token in ("500","300","100","50","6"):
        if token not in nums(mechanics):
            issues.append(("high","axial_slash_preview_value_missing","future","skitarii",axial[0].get("s"),token))
else:
    issues.append(("high","official_preview_talent_missing","future","skitarii","axial slash",""))

# High-value Psyker text checks where upstream maintained Simplified Chinese has
# historically dropped semantic cues. Prefer a safe maintained bilingual pair.
battle=[]
smite=[]
for tree,n in nodes:
    nn=norm(n.get("en"))
    if nn=="battle meditation":
        battle.append((tree,n))
    elif nn=="smite":
        smite.append((tree,n))

for tree,n in battle:
    cn=(n.get("advancedCn") or n.get("descCn") or "")
    en=(n.get("advancedEn") or n.get("desc") or "")
    if "降低" not in cn:
        issues.append(("high","battle_meditation_reduction_missing",tree.get("patch"),tree.get("key"),n.get("s"),cn))
    if "平息" not in cn:
        issues.append(("high","battle_meditation_quell_term_missing",tree.get("patch"),tree.get("key"),n.get("s"),cn))
    for token in ("10%","10%","10%"):
        if token not in en:
            issues.append(("high","battle_meditation_english_value_missing",tree.get("patch"),tree.get("key"),n.get("s"),en))
            break

for tree,n in smite:
    cn=(n.get("advancedCn") or n.get("descCn") or "")
    en=(n.get("advancedEn") or n.get("desc") or "")
    if n.get("advancedEn") and n.get("advancedCn"):
        for token in ("16","100%","8.5%"):
            if token not in en or token not in cn:
                issues.append(("high","smite_maintained_pair_value_missing",tree.get("patch"),tree.get("key"),n.get("s"),token))
    if re.search(r'\{#|\{[A-Za-z0-9_]+(?::%s)?\}',cn):
        issues.append(("fatal","smite_markup_leaked",tree.get("patch"),tree.get("key"),n.get("s"),cn))

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
