#!/usr/bin/env python3
"""Extract maintained Simplified-Chinese talent text from Enhanced Descriptions.

The upstream files contain English and zh-cn in the same localization entry.
This parser intentionally rejects unresolved runtime placeholders/markup rather
than leaking game-formatting syntax into the web UI.
"""
import ast
import json
import re
import urllib.request

BASE = "https://raw.githubusercontent.com/xsSplater/Darktide_Enhanced_Descriptions_BETA/xss0/"
FILES = [
    "Main_Modules/TALENTS_Modular.lua",
    "Main_Modules/TALENTS/TALENTS_Veteran.lua",
    "Main_Modules/TALENTS/TALENTS_Zealot.lua",
    "Main_Modules/TALENTS/TALENTS_Psyker.lua",
    "Main_Modules/TALENTS/TALENTS_Ogryn.lua",
    "Main_Modules/TALENTS/TALENTS_Arbites.lua",
    "Main_Modules/TALENTS/TALENTS_Skitarii.lua",
    "Main_Modules/TALENTS/TALENTS_Scum.lua",
]
PHRASES_EN = "Colors_Keywords_Numbers/COLORS_KWords.lua"
PHRASES_ZH = "Colors_Keywords_Numbers/COLORS_KWords_zh_cn.lua"
UA = {"User-Agent": "Darktide-BD bilingual planner"}

_RUNTIME = re.compile(
    r'%s|\{[A-Za-z0-9_]+(?::%s)?\}|\{#|CKWord\(|CNumb\(|CPhrs\(|CNote\(|Dot_[A-Za-z_]+'
)
_NUM = re.compile(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?')

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=35) as r:
        return r.read().decode("utf-8", "replace")

def normalize_name(s):
    s = (s or "").casefold()
    s = s.replace("’", "'").replace("–", "-").replace("—", "-")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _decode_lua_literal(tok):
    try:
        return ast.literal_eval(tok)
    except Exception:
        return tok[1:-1]

def _keep_first_arg(expr, fn):
    pat = re.compile(
        r"\b" + re.escape(fn) + r'\(\s*("(?:(?:\\.)|[^"\\])*")\s*(?:,[^)]*)?\)'
    )
    return pat.sub(
        lambda m: json.dumps(_decode_lua_literal(m.group(1)), ensure_ascii=False),
        expr,
    )

def _clean_expr(expr, phrases=None):
    phrases = phrases or {}
    expr = re.sub(
        r'CPhrs\(\s*"([^"]+)"\s*\)',
        lambda m: json.dumps(phrases.get(m.group(1), ""), ensure_ascii=False),
        expr,
    )
    for fn in ("CKWord", "CNumb", "CNum", "CNumber", "CValue", "CVal"):
        expr = _keep_first_arg(expr, fn)
    expr = re.sub(r'CNote(?:\w*)?\([^)]*\)', '""', expr)
    expr = re.sub(
        r"\bDot_(?:green|red|nc|yellow|orange|blue|purple|white)\b",
        '"• "',
        expr,
    )
    expr = re.sub(r"--[^\n]*", "", expr)
    toks = re.findall(r'"(?:(?:\\.)|[^"\\])*"', expr)
    text = "".join(_decode_lua_literal(t) for t in toks)
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"•\s*•\s*", "• ", text)
    return text.strip()

def _load_phrases(path):
    try:
        src = get(BASE + path)
    except Exception:
        return {}
    out = {}
    for line in src.splitlines():
        m = re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*(.+?),\s*$", line)
        if not m:
            continue
        val = _clean_expr(m.group(2), {})
        if val:
            out[m.group(1)] = val
    return out

def _params_from_block(block):
    m = re.search(r'\["loc_[^"]+"\]\s*=\s*\{\s*--([^\n]*)', block)
    if not m:
        return {}
    out = {}
    for k, v in re.findall(r"!?([A-Za-z0-9_]+)!?\s*:\s*([^,]+)", m.group(1)):
        v = v.strip()
        if (
            v
            and not v.startswith("{")
            and "->" not in v
            and not v.startswith("+colors")
        ):
            out[k] = v
    return out

def _fill_params(text, params):
    def repl(m):
        key = m.group(1)
        return params.get(key, m.group(0))
    return re.sub(r"\{([A-Za-z0-9_]+):%s\}", repl, text)

def _sanitize_zh(text):
    text = text or ""
    text = re.sub(r'\{#color\([^}]*\)\}', "", text, flags=re.I)
    text = re.sub(r'\{#reset\(\)\}', "", text, flags=re.I)
    text = re.sub(r'\{#[^}]+\}', "", text)
    text = text.replace("危机值产生", "危机值生成")
    text = re.sub(
        r"压制\s*(\d+(?:\.\d+)?%?)\s*危机值",
        r"平息\1危机值",
        text,
    )
    text = text.replace("没甚么", "没什么")
    text = re.sub(r"\s+([，。；：！？])", r"\1", text)
    return text.strip()

def _sanitize_en(text):
    text = text or ""
    text = re.sub(r'\{#color\([^}]*\)\}', "", text, flags=re.I)
    text = re.sub(r'\{#reset\(\)\}', "", text, flags=re.I)
    text = re.sub(r'\{#[^}]+\}', "", text)
    return text.strip()

def _extract_lang(block, lang, phrases):
    if lang == "en":
        start = r"\ben\s*=\s*"
    else:
        start = r'\["' + re.escape(lang) + r'"\]\s*=\s*'
    m = re.search(
        start
        + r'(.*?)(?=\n\s*(?:[A-Za-z][A-Za-z0-9_-]*|\["[^"]+"\])\s*=|\n\s*\},)',
        block,
        re.S,
    )
    if not m:
        return ""
    text = _clean_expr(m.group(1), phrases)
    text = _fill_params(text, _params_from_block(block))
    text = text.replace(" 。", "。").replace(" ，", "，").replace(" %", "%")
    return _sanitize_en(text) if lang == "en" else _sanitize_zh(text)

def _entry_chunks(block):
    starts = list(re.finditer(r'^\s*\["loc_[^"]+"\]\s*=\s*\{', block, re.M))
    if not starts:
        return [block]
    out = []
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(block)
        out.append(block[m.start():end])
    return out

_ROMAN = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,"X":10}
_ROMAN_REV = {v:k for k,v in _ROMAN.items()}

def _expand_single_range_header(label, entry_count):
    if entry_count != 1:
        return []
    m = re.fullmatch(
        r'(.+?)\s+(I|II|III|IV|V|VI|VII|VIII|IX|X)-(I|II|III|IV|V|VI|VII|VIII|IX|X)',
        (label or "").strip(),
    )
    if not m:
        return []
    base, a, b = m.groups()
    lo, hi = _ROMAN[a], _ROMAN[b]
    if lo > hi:
        lo, hi = hi, lo
    return [f"{base} {_ROMAN_REV[i]}" for i in range(lo, hi + 1)]

def _header_name(label):
    label = (label or "").strip()
    # Handles both:
    #   Passive 4 - Warp Expenditure
    #   PASSIVES - ПАССИВНЫЙ - 42 - Ablative Motion Routines - Процедуры ...
    m = re.search(
        r"\b\d+(?:-\d+)*\s*-\s*(.+?)(?:\s*-\s*[\u0400-\u04FF].*)?$",
        label,
    )
    if m:
        name = m.group(1).strip()
        if name and "/" not in name:
            return name
    parts = [p.strip() for p in label.split(" - ") if p.strip()]
    for cand in reversed(parts):
        if re.search(r"[\u0400-\u04FF]", cand):
            continue
        if re.fullmatch(r"\d+(?:-\d+)*", cand):
            continue
        if re.match(r"^(?:PASSIVE|PASSIVES|BLITZ|ABILITY|AURA|KEYSTONE)\b", cand, re.I):
            continue
        if cand and "/" not in cand:
            return cand
    return ""

def _safe(text):
    return bool(text) and not _RUNTIME.search(text)

def _number_magnitudes(text):
    out = []
    for m in _NUM.finditer(text or ""):
        token = m.group(0).lstrip("+-").rstrip("%")
        try:
            value = float(token)
            out.append(("%g" % value))
        except Exception:
            out.append(token)
    return sorted(out)

def _pair_safe(en, zh):
    if not (_safe(en) and _safe(zh)):
        return False
    # Signed values may be expressed by Chinese verbs such as “降低”, and % may
    # be supplied by a localization helper on only one side. Compare magnitudes.
    return _number_magnitudes(en) == _number_magnitudes(zh)

def load_bilingual_descriptions():
    en_phrases = _load_phrases(PHRASES_EN)
    zh_phrases = _load_phrases(PHRASES_ZH)
    out = {}
    details = {}
    for path in FILES:
        try:
            src = get(BASE + path)
        except Exception:
            continue
        headers = list(
            re.finditer(r"^\s*--\[\+\s*(.*?)\s*\+\]--[^\n]*", src, re.M)
        )
        for i, h in enumerate(headers):
            label = h.group(1).strip()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(src)
            block = src[h.end():end]
            chunks = _entry_chunks(block)

            names = []
            name = _header_name(label)
            if name and not name.startswith("+"):
                names = [name]
            else:
                names = _expand_single_range_header(label, len(chunks))
            if not names:
                continue

            ens, zhs = [], []
            diagnostic_en, diagnostic_cn = [], []
            for chunk in chunks:
                en = _extract_lang(chunk, "en", en_phrases)
                zh = _extract_lang(chunk, "zh-cn", zh_phrases)
                if _safe(en):
                    diagnostic_en.append(en)
                if _safe(zh):
                    diagnostic_cn.append(zh)
                if _pair_safe(en, zh):
                    ens.append(en)
                    zhs.append(zh)

            safe_en = "\n".join(ens).strip()
            safe_cn = "\n".join(zhs).strip()
            unpaired_en = "\n".join(diagnostic_en).strip() if not safe_en else ""
            unpaired_cn = "\n".join(diagnostic_cn).strip() if not safe_cn else ""

            for name in names:
                key = normalize_name(name)
                if not key:
                    continue
                record = {
                    "name": name,
                    "en": safe_en,
                    "cn": safe_cn,
                    "unpaired_en": unpaired_en,
                    "unpaired_cn": unpaired_cn,
                    "pairValid": bool(safe_en and safe_cn),
                    "source": path,
                }
                if not any((record["en"], record["cn"], record["unpaired_en"], record["unpaired_cn"])):
                    continue
                score = len(record["en"]) + len(record["cn"])
                old = out.get(key)
                old_score = len(old.get("en", "")) + len(old.get("cn", "")) if old else -1
                if score > old_score:
                    out[key] = record
                    details[key] = {"name": name, "source": path}
    return out, details

def load_chinese_descriptions():
    pairs, details = load_bilingual_descriptions()
    out = {k: v["cn"] for k, v in pairs.items() if v.get("cn")}
    return out, details

if __name__ == "__main__":
    pairs, _ = load_bilingual_descriptions()
    cn = {k: v["cn"] for k, v in pairs.items() if v.get("cn")}
    paired = {k: v for k, v in pairs.items() if v.get("en") and v.get("cn")}
    print("Chinese descriptions:", len(cn))
    print("Safe bilingual pairs:", len(paired))
    for k in (
        "warp expenditure",
        "battle meditation",
        "smite",
        "ablative motion routines",
        "gunsmith",
    ):
        print(k, "=>", json.dumps(pairs.get(k, {}), ensure_ascii=False)[:900])
