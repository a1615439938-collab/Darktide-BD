#!/usr/bin/env python3
"""Audit Simplified-Chinese talent translation quality.

This catches issues the factual/numeric audits cannot:
- newer maintained name corrections being hidden by an older glossary;
- untranslated preview talent names;
- inconsistent Darktide terminology in displayed Chinese;
- English talent-name leakage inside Chinese descriptions;
- obvious malformed or region-mismatched wording.

Sources are read-only:
- SyuanTsai maintained glossary/name table and Sep 18 Depths preview translation;
- the generated tree-data.js currently shipped by this site.
"""
import json, re, sys, urllib.request
from pathlib import Path
from collections import Counter
from opencc import OpenCC

cc=OpenCC("t2s")

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Darktide-BD-translation-audit"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","replace")

def norm_name(s):
    s=(s or "").replace("’","'").replace("–","-").replace("—","-").strip()
    s=re.sub(r"[!?.…]+$","",s)
    s=s.lower()
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

raw=Path("tree-data.js").read_text(encoding="utf-8").strip()
prefix="window.TREE_DATA="
if not raw.startswith(prefix):
    raise SystemExit("bad tree-data.js")
payload=raw[len(prefix):]
if payload.endswith(";"): payload=payload[:-1]
data=json.loads(payload)

GLOSSARY_URL="https://raw.githubusercontent.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/main/Referneces/Translation.md"
PREVIEW_URL="https://raw.githubusercontent.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/main/%E5%85%AC%E5%91%8A/2026-09-18_%E8%A9%9B%E5%92%92%E6%B7%B1%E6%B7%B5%E5%B9%B3%E8%A1%A1%E6%80%A7%E6%9B%B4%E6%96%B0_%E7%B9%81%E4%B8%AD%E7%BF%BB%E8%AD%AF.md"

glossary_text=fetch(GLOSSARY_URL)
preview_text=fetch(PREVIEW_URL)

glossary={}
for line in glossary_text.splitlines():
    m=re.match(r"\s*[-*]\s+(.+?)\s+-\s+(.+?)\s*$",line)
    if not m: continue
    en=m.group(1).strip().strip("*_ ")
    zh=m.group(2).strip().strip("*_ ")
    if en and zh:
        glossary.setdefault(norm_name(en),cc.convert(zh))

preview_names={}
for line in preview_text.splitlines():
    m=re.search(r"^\s*[-*]\s+([^（(]+?)\s*[（(]([^()（）]+)[)）]",line)
    if not m: continue
    zh=m.group(1).strip().strip("*_ -－")
    en=m.group(2).strip()
    if en and zh:
        preview_names[norm_name(en)]=cc.convert(zh)

nodes=[]
for bucket in ("classes","liveClasses"):
    patch="future" if bucket=="classes" else "live"
    for tree in data.get(bucket,[]) or []:
        for n in tree.get("nodes",[]) or []:
            if n.get("cat")=="root": continue
            nodes.append((patch,tree,n))

issues=[]
def add(sev,kind,patch,tree,n,detail):
    issues.append({
        "severity":sev,"kind":kind,"patch":patch,"class":tree.get("key",""),
        "node":n.get("s",""),"en":n.get("en",""),"cn":n.get("cn",""),"detail":detail
    })

def effective_cn(n):
    source=n.get("descSource","")
    if n.get("descCn") and source!="manual-reviewed":
        return n.get("descCn","")
    if n.get("advancedEn") and n.get("advancedCn"):
        return n.get("advancedCn","")
    return n.get("descCn","")

def display_equiv(a,b):
    # Ignore full-width/ASCII punctuation differences only; wording differences still matter.
    trans=str.maketrans({"！":"!","？":"?","，":",","。":".","：":":","；":";","（":"(", "）":")"})
    aa=re.sub(r"\s+","",str(a or "").translate(trans))
    bb=re.sub(r"\s+","",str(b or "").translate(trans))
    return aa==bb

# Compare against the latest formal glossary plus the dated future-patch translation.
# This avoids treating historical candidates in the Enhanced Descriptions workspace
# as authoritative over the maintained formal glossary.
MANUAL_NAME_CORRECTIONS={
    "superiority complex":"优越情结",
    "precision strikes":"精准打击",
    "malocator":"生化武器官",
    "coated weaponry":"涂毒武装",
    "a tertium welcome":"特提恩式欢迎",
}
for patch,tree,n in nodes:
    en=n.get("en","")
    cn=n.get("cn","")
    key=norm_name(en)
    if cn==en and tree.get("key")!="hivescum-stimm":
        add("high","untranslated_talent_name",patch,tree,n,"Chinese display name equals English source")
    if patch=="future" and key in preview_names and not display_equiv(cn,preview_names[key]):
        add("high","preview_name_mismatch",patch,tree,n,f"expected={preview_names[key]}")
    formal=glossary.get(key)
    if formal and key not in MANUAL_NAME_CORRECTIONS and not display_equiv(cn,formal):
        add("medium","latest_glossary_name_mismatch",patch,tree,n,f"latest_formal={formal}")
    expected=MANUAL_NAME_CORRECTIONS.get(key)
    if expected and not display_equiv(cn,expected):
        add("high","known_name_translation_error",patch,tree,n,f"expected={expected}")

# High-confidence terminology/style problems in the displayed Chinese.
checks=[
    ("high","peril_term_uses_crisis",re.compile(r"危机(?:值)?"),"Peril should use 反噬 in the maintained glossary"),
    ("high","carapace_term_uses_hardshell",re.compile(r"硬壳"),"Carapace should use 甲壳护甲"),
    ("medium","traditional_region_probability",re.compile(r"机率"),"Use Mainland Simplified 几率/概率"),
    ("medium","formal_pronoun_inconsistent",re.compile(r"您"),"Site uses 你 consistently"),
    ("medium","meter_uses_gongchi",re.compile(r"公尺"),"Use 米 in Simplified-Chinese UI"),
    ("medium","soulblaze_term_inconsistent",re.compile(r"灵魂烈焰"),"Use maintained 灵魂之火"),
    ("medium","coherency_term_inconsistent",re.compile(r"连携"),"Use maintained 协同"),
    ("medium","crit_chance_wordy",re.compile(r"暴击(?:命中)?几率"),"Prefer 暴击率 for Critical Hit Chance"),
    ("high","malformed_range_double_minus",re.compile(r"\d\s*-\s*-\s*\d"),"Malformed numeric range"),
    ("medium","spacing_before_game_term",re.compile(r"(?:韧性|伤害|盟友|反噬)\s{2,}"),"Suspicious spacing"),
]
for patch,tree,n in nodes:
    text=effective_cn(n)
    for sev,kind,rx,detail in checks:
        if rx.search(text):
            add(sev,kind,patch,tree,n,detail)

# Find English talent titles leaking into Chinese descriptions even when a Chinese
# title exists. This is different from English weapon model names, which are allowed.
name_map={}
for _,_,n in nodes:
    en=(n.get("en") or "").strip()
    cn=(n.get("cn") or "").strip()
    if en and cn and en!=cn and len(en)>=5:
        name_map[en]=cn
english_titles=sorted(name_map.items(),key=lambda kv:len(kv[0]),reverse=True)
for patch,tree,n in nodes:
    text=effective_cn(n)
    leaks=[]
    for en,cn in english_titles:
        if en==n.get("en"): continue
        if re.search(r"(?<![A-Za-z])"+re.escape(en)+r"(?![A-Za-z])",text,re.I):
            leaks.append(f"{en}->{cn}")
            if len(leaks)>=5: break
    if leaks:
        add("medium","english_talent_name_leaked_into_cn",patch,tree,n,"; ".join(leaks))

# Compact report.
sev=Counter(x["severity"] for x in issues)
kind=Counter(x["kind"] for x in issues)
report={
    "audited_nodes":len(nodes),
    "severity_counts":dict(sev),
    "kind_counts":dict(kind),
    "issues":issues,
}
Path("translation-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("TRANSLATION_AUDITED_NODES",len(nodes))
print("TRANSLATION_ISSUES_BY_SEVERITY",json.dumps(dict(sev),ensure_ascii=False,sort_keys=True))
print("TRANSLATION_ISSUES_BY_KIND",json.dumps(dict(kind),ensure_ascii=False,sort_keys=True))
for x in issues[:220]:
    print(json.dumps(x,ensure_ascii=False))
if len(issues)>220:
    print("TRANSLATION_ISSUES_TRUNCATED",len(issues)-220)

# High-confidence translation errors fail CI; medium findings remain review items.
sys.exit(1 if sev.get("high",0) else 0)
