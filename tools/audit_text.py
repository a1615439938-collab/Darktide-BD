#!/usr/bin/env python3
# Audit version: 2
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

RAW = Path("tree-data.js").read_text(encoding="utf-8")
PREFIX = "window.TREE_DATA="
if not RAW.startswith(PREFIX):
    raise SystemExit("tree-data.js does not start with window.TREE_DATA=")
payload = RAW[len(PREFIX):].strip()
if payload.endswith(";"):
    payload = payload[:-1]
DATA = json.loads(payload)

CJK = re.compile(r"[\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")
HEX_ID = re.compile(r"(?:^|[ _-])[A-Fa-f0-9]{8,}$")
INTERNAL = re.compile(r"(?:\bloc_[A-Za-z0-9_]+\b|\btalent_[A-Za-z0-9_]+\b|\b0x[A-Fa-f0-9]+\b)")
RAW_MARKUP = re.compile(r"(?:\{#(?:color|reset)|\{[A-Za-z0-9_]+:%s\}|CKWord\(|CNumb\(|CPhrs\(|Dot_(?:green|red|nc|yellow|orange|blue|purple|white)|\.\.)")
HTMLISH = re.compile(r"<\/?(?:span|div|br|p|strong|em)\b", re.I)
PLACEHOLDER = re.compile(r"(?:%s|\{[A-Za-z0-9_]+\}|\$\{[^}]+\})")
NUM = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")
URLISH = re.compile(r"https?://")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Phrases that have already shown up as low-quality or misleading translations.
BAD_ZH_PATTERNS = [
    (re.compile(r"危机值产生"), "awkward_peril_generation"),
    (re.compile(r"压制\s*\d+(?:\.\d+)?%?\s*危机值"), "quell_mistranslated_as_suppress"),
    (re.compile(r"暂无可靠的简中预览效果说明"), "missing_cn_description"),
    (re.compile(r"自动辅助翻译"), "fallback_translation_visible"),
]

def nums(s):
    return Counter(m.group(0).lstrip("+") for m in NUM.finditer(s or ""))

def cjk_count(s): return len(CJK.findall(s or ""))
def latin_count(s): return len(LATIN.findall(s or ""))

def norm_name(s):
    return re.sub(r"\s+"," ",(s or "").strip()).casefold()

def issue(kind, severity, tree, n, detail=""):
    issues.append({
        "severity":severity,
        "kind":kind,
        "patch":tree.get("patch",""),
        "class":tree.get("key",""),
        "class_name":tree.get("name",""),
        "node":n.get("s",""),
        "en":n.get("en",""),
        "cn":n.get("cn",""),
        "detail":detail,
    })

issues=[]
all_nodes=[]
trees=(DATA.get("classes") or [])+(DATA.get("liveClasses") or [])
for tree in trees:
    for n in tree.get("nodes",[]):
        if n.get("cat")=="root":
            continue
        all_nodes.append((tree,n))
        en=(n.get("en") or "").strip()
        cn=(n.get("cn") or "").strip()
        ed=(n.get("desc") or "").strip()
        cd=(n.get("descCn") or "").strip()

        if not en:
            issue("missing_en_name","fatal",tree,n)
        if HEX_ID.search(en) or HEX_ID.search(cn):
            issue("internal_hex_in_name","fatal",tree,n)
        if INTERNAL.search(en+" "+cn):
            issue("internal_key_in_name","fatal",tree,n)

        # A Chinese field that is just the English name is not localized.
        if cn and norm_name(cn)==norm_name(en) and latin_count(en)>=3 and cjk_count(cn)==0:
            issue("untranslated_cn_name","high",tree,n)
        elif cn and cjk_count(cn)==0 and latin_count(cn)>=3:
            issue("cn_name_has_no_chinese","medium",tree,n)

        for label,txt in (("en_desc",ed),("cn_desc",cd)):
            if RAW_MARKUP.search(txt):
                issue("raw_markup_"+label,"fatal",tree,n,RAW_MARKUP.search(txt).group(0))
            if HTMLISH.search(txt):
                issue("html_markup_"+label,"fatal",tree,n,HTMLISH.search(txt).group(0))
            if CONTROL.search(txt):
                issue("control_character_"+label,"fatal",tree,n)
            if URLISH.search(txt):
                issue("url_leaked_"+label,"medium",tree,n)
            if PLACEHOLDER.search(txt):
                issue("unresolved_placeholder_"+label,"high",tree,n,PLACEHOLDER.search(txt).group(0))

        if cd:
            if cjk_count(cd)==0 and latin_count(cd)>=12:
                issue("cn_description_untranslated","high",tree,n)
            en_nums=nums(ed)
            cn_nums=nums(cd)
            extra=list((cn_nums-en_nums).elements())
            missing=list((en_nums-cn_nums).elements())
            if len(extra)>=2:
                issue("cn_has_extra_numbers","high",tree,n,", ".join(extra[:8]))
            elif extra:
                issue("cn_has_extra_number","medium",tree,n,", ".join(extra[:8]))
            if len(missing)>=2:
                issue("cn_missing_numbers","high",tree,n,", ".join(missing[:8]))
            elif missing:
                issue("cn_missing_number","medium",tree,n,", ".join(missing[:8]))

            if len(ed)>=40:
                # Very rough mismatch detector. Chinese is normally shorter in characters than English.
                ratio=len(cd)/max(1,len(ed))
                if ratio>1.75:
                    issue("cn_much_longer_than_en","high",tree,n,f"ratio={ratio:.2f}")
                elif ratio<0.18:
                    issue("cn_much_shorter_than_en","medium",tree,n,f"ratio={ratio:.2f}")

            for pat,kind in BAD_ZH_PATTERNS:
                m=pat.search(cd)
                if m:
                    issue(kind,"high",tree,n,m.group(0))
        elif ed:
            issue("missing_cn_description_source","medium",tree,n)

        if ed and CJK.search(ed):
            issue("english_description_contains_chinese","high",tree,n)

        if "\n" in en or "\n" in cn:
            issue("newline_in_name","high",tree,n)

# Cross-patch inconsistencies: same English talent name should normally keep one Chinese display name.
name_map=defaultdict(lambda: defaultdict(set))
for tree,n in all_nodes:
    en=norm_name(n.get("en"))
    if en:
        name_map[en][(n.get("cn") or "").strip()].add((tree.get("patch"),tree.get("key"),n.get("s")))
for en,vals in name_map.items():
    cnvals=[x for x in vals if x]
    if len(cnvals)>1:
        samples=" | ".join(sorted(cnvals)[:5])
        tree,n=next((t,n) for t,n in all_nodes if norm_name(n.get("en"))==en)
        issue("inconsistent_cn_name","medium",tree,n,samples)

# Exact English descriptions mapping to many Chinese descriptions can reveal mismatched source layers.
desc_map=defaultdict(set)
desc_node={}
for tree,n in all_nodes:
    ed=re.sub(r"\s+"," ",(n.get("desc") or "").strip())
    cd=re.sub(r"\s+"," ",(n.get("descCn") or "").strip())
    if ed and cd:
        desc_map[ed].add(cd)
        desc_node.setdefault(ed,(tree,n))
for ed,cds in desc_map.items():
    if len(cds)>2:
        tree,n=desc_node[ed]
        issue("same_en_desc_many_cn_variants","medium",tree,n,f"{len(cds)} Chinese variants")

severity_order={"fatal":0,"high":1,"medium":2,"low":3}
issues.sort(key=lambda x:(severity_order.get(x["severity"],9),x["kind"],x["class"],x["en"]))

counts=Counter((x["severity"],x["kind"]) for x in issues)
sev=Counter(x["severity"] for x in issues)
print(f"AUDITED_NODES={len(all_nodes)}")
print("SEVERITY_COUNTS="+json.dumps(dict(sev),ensure_ascii=False,sort_keys=True))
print("TOP_CATEGORIES")
for (severity,kind),count in counts.most_common(40):
    print(f"{severity:6} {count:4} {kind}")

print("\nSAMPLES")
for x in issues[:220]:
    print(json.dumps(x,ensure_ascii=False))

report={
    "audited_nodes":len(all_nodes),
    "severity_counts":dict(sev),
    "category_counts":{f"{s}:{k}":v for (s,k),v in counts.items()},
    "issues":issues,
}
Path("text-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

# Only parser/markup/internal-ID leaks are build breakers. Semantic warnings remain reviewable.
fatal=sev.get("fatal",0)
print(f"FATAL_COUNT={fatal}")
sys.exit(1 if fatal else 0)
