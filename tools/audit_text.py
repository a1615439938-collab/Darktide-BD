#!/usr/bin/env python3
# Audit version: 8
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
RAW_MARKUP = re.compile(r"(?:\{#(?:color|reset)|CKWord\(|CNumb\(|CPhrs\(|CNote\(|Dot_(?:green|red|nc|yellow|orange|blue|purple|white))")
PLACEHOLDER = re.compile(r"(?:%s|\{[A-Za-z0-9_]+(?::%s)?\}|\$\{[^}]+\})")
HTMLISH = re.compile(r"<\/?(?:span|div|br|p|strong|em)\b", re.I)
NUM = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")
URLISH = re.compile(r"https?://")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

BAD_ZH_PATTERNS = [
    (re.compile(r"危机值产生"), "awkward_peril_generation"),
    (re.compile(r"压制\s*\d+(?:\.\d+)?%?\s*危机值"), "quell_mistranslated_as_suppress"),
    (re.compile(r"自动辅助翻译"), "word_substitution_fallback_visible"),
]

def nums(s):
    # Sign may be expressed linguistically in Chinese ("降低 10%") rather than with "-10%".
    return Counter(m.group(0).lstrip("+-") for m in NUM.finditer(s or ""))

def cjk_count(s):
    return len(CJK.findall(s or ""))

def latin_count(s):
    return len(LATIN.findall(s or ""))

def norm_name(s):
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()

def issue(kind, severity, tree, n, detail=""):
    issues.append({
        "severity": severity,
        "kind": kind,
        "patch": tree.get("patch", ""),
        "class": tree.get("key", ""),
        "class_name": tree.get("name", ""),
        "node": n.get("s", ""),
        "en": n.get("en", ""),
        "cn": n.get("cn", ""),
        "source": n.get("descSource", ""),
        "detail": detail,
    })

def audit_text_field(tree, n, label, txt, chinese=False):
    if not txt:
        return
    m = RAW_MARKUP.search(txt)
    if m:
        issue("raw_markup_" + label, "fatal", tree, n, m.group(0))
    m = HTMLISH.search(txt)
    if m:
        issue("html_markup_" + label, "fatal", tree, n, m.group(0))
    m = CONTROL.search(txt)
    if m:
        issue("control_character_" + label, "fatal", tree, n)
    m = URLISH.search(txt)
    if m:
        issue("url_leaked_" + label, "medium", tree, n)
    m = PLACEHOLDER.search(txt)
    if m:
        issue("unresolved_placeholder_" + label, "high", tree, n, m.group(0))
    if chinese and cjk_count(txt) == 0 and latin_count(txt) >= 12:
        issue("chinese_field_untranslated_" + label, "high", tree, n)

def audit_numeric_pair(tree, n, label, en, cn):
    if not en or not cn:
        return
    en_nums = nums(en)
    cn_nums = nums(cn)
    extra = list((cn_nums - en_nums).elements())
    missing = list((en_nums - cn_nums).elements())
    if extra or missing:
        detail = []
        if extra:
            detail.append("extra_cn=" + ",".join(extra[:10]))
        if missing:
            detail.append("missing_cn=" + ",".join(missing[:10]))
        # Same-layer bilingual pairs should preserve mechanics numbers exactly.
        severity = "high" if len(extra) + len(missing) >= 2 else "medium"
        issue("numeric_mismatch_" + label, severity, tree, n, "; ".join(detail))

issues = []
all_nodes = []
trees = (DATA.get("classes") or []) + (DATA.get("liveClasses") or [])

for tree in trees:
    for n in tree.get("nodes", []):
        if n.get("cat") == "root":
            continue
        all_nodes.append((tree, n))

        en = (n.get("en") or "").strip()
        cn = (n.get("cn") or "").strip()
        ed = (n.get("desc") or "").strip()
        cd = (n.get("descCn") or "").strip()
        ae = (n.get("advancedEn") or "").strip()
        ac = (n.get("advancedCn") or "").strip()
        source = (n.get("descSource") or "").strip()

        if not en:
            issue("missing_en_name", "fatal", tree, n)
        if HEX_ID.search(en) or HEX_ID.search(cn):
            issue("internal_hex_in_name", "fatal", tree, n)
        if INTERNAL.search(en + " " + cn):
            issue("internal_key_in_name", "fatal", tree, n)
        if "\n" in en or "\n" in cn:
            issue("newline_in_name", "high", tree, n)

        if cn and norm_name(cn) == norm_name(en) and latin_count(en) >= 3 and cjk_count(cn) == 0:
            issue("untranslated_cn_name", "high", tree, n)
        elif cn and cjk_count(cn) == 0 and latin_count(cn) >= 3:
            issue("cn_name_has_no_chinese", "medium", tree, n)

        audit_text_field(tree, n, "base_en_desc", ed, chinese=False)
        audit_text_field(tree, n, "base_cn_desc", cd, chinese=True)
        audit_text_field(tree, n, "advanced_en_desc", ae, chinese=False)
        audit_text_field(tree, n, "advanced_cn_desc", ac, chinese=True)

        if ed and CJK.search(ed):
            issue("english_description_contains_chinese", "high", tree, n)
        if ae and CJK.search(ae):
            issue("advanced_english_contains_chinese", "high", tree, n)

        # The main card may use either a base-aligned pair or a paired enhanced description.
        has_base_pair = bool(ed and cd)
        has_advanced_pair = bool(ae and ac)
        if ed and not has_base_pair and not has_advanced_pair:
            issue("missing_renderable_cn_pair", "medium", tree, n)

        # A half-populated enhanced pair is unsafe because the UI must never mix layers.
        if bool(ae) != bool(ac):
            issue("incomplete_advanced_pair", "fatal", tree, n)

        if has_base_pair:
            audit_numeric_pair(tree, n, "base_pair", ed, cd)
        if has_advanced_pair:
            audit_numeric_pair(tree, n, "advanced_pair", ae, ac)

        if source == "community-aligned" and not has_base_pair:
            issue("source_metadata_inconsistent", "fatal", tree, n, source)
        if source == "fatshark-preview-zh" and not has_base_pair:
            issue("source_metadata_inconsistent", "fatal", tree, n, source)

        for pat, kind in BAD_ZH_PATTERNS:
            for label, txt in (("base_cn", cd), ("advanced_cn", ac)):
                m = pat.search(txt)
                if m:
                    issue(kind + "_" + label, "high", tree, n, m.group(0))

# Same English talent should normally keep one Chinese display name across live/future.
name_map = defaultdict(lambda: defaultdict(set))
for tree, n in all_nodes:
    en = norm_name(n.get("en"))
    if en:
        name_map[en][(n.get("cn") or "").strip()].add(
            (tree.get("patch"), tree.get("key"), n.get("s"))
        )
for en, vals in name_map.items():
    cnvals = [x for x in vals if x]
    if len(cnvals) > 1:
        tree, n = next((t, node) for t, node in all_nodes if norm_name(node.get("en")) == en)
        issue("inconsistent_cn_name", "medium", tree, n, " | ".join(sorted(cnvals)[:6]))

# Same enhanced English should not map to many unrelated Chinese texts.
desc_map = defaultdict(set)
desc_node = {}
for tree, n in all_nodes:
    ae = re.sub(r"\s+", " ", (n.get("advancedEn") or "").strip())
    ac = re.sub(r"\s+", " ", (n.get("advancedCn") or "").strip())
    if ae and ac:
        desc_map[ae].add(ac)
        desc_node.setdefault(ae, (tree, n))
for ae, acs in desc_map.items():
    if len(acs) > 2:
        tree, n = desc_node[ae]
        issue("same_advanced_en_many_cn_variants", "medium", tree, n, f"{len(acs)} Chinese variants")

severity_order = {"fatal": 0, "high": 1, "medium": 2, "low": 3}
issues.sort(key=lambda x: (
    severity_order.get(x["severity"], 9),
    x["kind"], x["class"], x["en"], x["patch"]
))

counts = Counter((x["severity"], x["kind"]) for x in issues)
sev = Counter(x["severity"] for x in issues)
renderable = sum(
    1 for _, n in all_nodes
    if n.get("descCn") or (n.get("advancedEn") and n.get("advancedCn"))
)
base_pairs = sum(1 for _, n in all_nodes if n.get("desc") and n.get("descCn"))
advanced_pairs = sum(1 for _, n in all_nodes if n.get("advancedEn") and n.get("advancedCn"))

print(f"AUDITED_NODES={len(all_nodes)}")
print(f"RENDERABLE_CN_PAIRS={renderable}")
print(f"BASE_CN_PAIRS={base_pairs}")
print(f"ADVANCED_CN_PAIRS={advanced_pairs}")
print("SEVERITY_COUNTS=" + json.dumps(dict(sev), ensure_ascii=False, sort_keys=True))
print("TOP_CATEGORIES")
for (severity, kind), count in counts.most_common(50):
    print(f"{severity:6} {count:4} {kind}")

missing_by_cat = Counter()
missing_unique = defaultdict(set)
for x in issues:
    if x["kind"]=="missing_renderable_cn_pair":
        node = next((n for t,n in all_nodes if t.get("patch")==x["patch"] and t.get("key")==x["class"] and n.get("s")==x["node"]), None)
        cat = node.get("cat","") if node else ""
        missing_by_cat[cat] += 1
        missing_unique[cat].add(x["en"])
print("MISSING_PAIR_BREAKDOWN")
for cat,count in missing_by_cat.most_common():
    print(f"{cat or 'unknown':10} {count:4} rows / {len(missing_unique[cat]):3} unique names")

print("\nSAMPLES")
for x in issues[:260]:
    print(json.dumps(x, ensure_ascii=False))

missing_unique_map = {}
for x in issues:
    if x["kind"] != "missing_renderable_cn_pair":
        continue
    node = next((n for t,n in all_nodes if t.get("patch")==x["patch"] and t.get("key")==x["class"] and n.get("s")==x["node"]), None)
    if not node:
        continue
    en = (node.get("en") or "").strip()
    desc = (node.get("desc") or "").strip()
    key = (en, desc)
    item = missing_unique_map.setdefault(key, {
        "en": en,
        "cn_name": (node.get("cn") or "").strip(),
        "desc": desc,
        "cat": node.get("cat",""),
        "classes": set(),
        "patches": set(),
    })
    item["classes"].add(x["class"])
    item["patches"].add(x["patch"])
missing_unique = []
for item in missing_unique_map.values():
    item["classes"] = sorted(item["classes"])
    item["patches"] = sorted(item["patches"])
    missing_unique.append(item)
missing_unique.sort(key=lambda x:(x["cat"],x["en"],x["desc"]))

report = {
    "audited_nodes": len(all_nodes),
    "renderable_cn_pairs": renderable,
    "base_cn_pairs": base_pairs,
    "advanced_cn_pairs": advanced_pairs,
    "severity_counts": dict(sev),
    "category_counts": {f"{s}:{k}": v for (s, k), v in counts.items()},
    "missing_unique": missing_unique,
    "issues": issues,
}
Path("text-audit.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

fatal = sev.get("fatal", 0)
print(f"FATAL_COUNT={fatal}")
sys.exit(1 if fatal else 0)
