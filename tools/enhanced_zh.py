#!/usr/bin/env python3
"""Extract Simplified Chinese talent descriptions from Enhanced Descriptions.

The upstream project maintains zh-cn strings alongside English talent data.
We use talent names as the join key because Games Lantern exposes names/slugs,
while the mod uses Darktide localization keys.
"""
import ast
import json
import re
import urllib.request

BASE="https://raw.githubusercontent.com/xsSplater/Darktide_Enhanced_Descriptions_BETA/xss0/"
FILES=[
    "Main_Modules/TALENTS/TALENTS_Veteran.lua",
    "Main_Modules/TALENTS/TALENTS_Zealot.lua",
    "Main_Modules/TALENTS/TALENTS_Psyker.lua",
    "Main_Modules/TALENTS/TALENTS_Ogryn.lua",
    "Main_Modules/TALENTS/TALENTS_Arbites.lua",
    "Main_Modules/TALENTS/TALENTS_Skitarii.lua",
    "Main_Modules/TALENTS/TALENTS_Scum.lua",
]
PHRASES="Colors_Keywords_Numbers/COLORS_KWords_zh_cn.lua"
UA={"User-Agent":"Darktide-BD bilingual planner"}

def get(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=35) as r:
        return r.read().decode("utf-8","replace")

def normalize_name(s):
    s=(s or "").casefold()
    s=s.replace("’","'").replace("–","-").replace("—","-")
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def _decode_lua_literal(tok):
    try:
        return ast.literal_eval(tok)
    except Exception:
        return tok[1:-1]

def _keep_first_arg(expr, fn):
    pat=re.compile(r"\b"+re.escape(fn)+r'\(\s*("(?:(?:\\.)|[^"\\])*")\s*(?:,[^)]*)?\)')
    return pat.sub(lambda m: json.dumps(_decode_lua_literal(m.group(1)),ensure_ascii=False),expr)

def _clean_expr(expr, phrases=None):
    phrases=phrases or {}
    # Resolve reusable Chinese phrases first.
    expr=re.sub(
        r'CPhrs\(\s*"([^"]+)"\s*\)',
        lambda m: json.dumps(phrases.get(m.group(1),""),ensure_ascii=False),
        expr,
    )
    # These helpers visually style a human-readable first argument.
    for fn in ("CKWord","CNumb","CNum","CNumber","CValue","CVal"):
        expr=_keep_first_arg(expr,fn)
    # Notes are extra technical footnotes and can be omitted when unresolved.
    expr=re.sub(r'CNote(?:\w*)?\([^)]*\)', '""', expr)
    # Colored bullet tokens: keep semantic separation without game markup.
    expr=re.sub(r"\bDot_(?:green|red|nc|yellow|orange|blue|purple|white)\b", '"• "', expr)
    # Strip comments because they may contain quoted strings unrelated to the UI.
    expr=re.sub(r"--[^\n]*","",expr)
    toks=re.findall(r'"(?:(?:\\.)|[^"\\])*"',expr)
    text="".join(_decode_lua_literal(t) for t in toks)
    text=text.replace("\r","")
    text=re.sub(r"[ \t]+"," ",text)
    text=re.sub(r" *\n *","\n",text)
    text=re.sub(r"\n{3,}","\n\n",text)
    text=re.sub(r"•\s*•\s*","• ",text)
    return text.strip()

def _load_phrases():
    try:
        src=get(BASE+PHRASES)
    except Exception:
        return {}
    out={}
    # Phrase table is intentionally line-oriented upstream.
    for line in src.splitlines():
        m=re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*(.+?),\s*$",line)
        if not m:
            continue
        val=_clean_expr(m.group(2),{})
        if val:
            out[m.group(1)]=val
    return out

def _params_from_block(block):
    # The localization entry usually annotates resolved values:
    # -- toughness: 15%, duration: 3, instant_toughness: 2.5%, +colors
    m=re.search(r'\["loc_[^"]+"\]\s*=\s*\{\s*--([^\n]*)',block)
    if not m:
        return {}
    out={}
    for k,v in re.findall(r"([A-Za-z0-9_]+)\s*:\s*([^,]+)",m.group(1)):
        v=v.strip()
        if v and not v.startswith("{"):
            out[k]=v
    return out

def _fill_params(text, params):
    def repl(m):
        key=m.group(1)
        return params.get(key,m.group(0))
    return re.sub(r"\{([A-Za-z0-9_]+):%s\}",repl,text)

def _extract_zh(block, phrases):
    m=re.search(
        r'\["zh-cn"\]\s*=\s*(.*?)(?=\n\s*(?:[A-Za-z][A-Za-z0-9_-]*|\["[^"]+"\])\s*=|\n\s*\},)',
        block,
        re.S,
    )
    if not m:
        return ""
    text=_clean_expr(m.group(1),phrases)
    text=_fill_params(text,_params_from_block(block))
    text=text.replace(" 。","。").replace(" ，","，").replace(" %","%")
    return text.strip()

def load_chinese_descriptions():
    phrases=_load_phrases()
    out={}
    details={}
    for path in FILES:
        try:
            src=get(BASE+path)
        except Exception:
            continue
        headers=list(re.finditer(r"^\s*--\[\+\s*(.*?)\s*\+\]--[^\n]*",src,re.M))
        for i,h in enumerate(headers):
            label=h.group(1).strip()
            if " - " not in label:
                continue
            # "Passive 4 - Warp Expenditure" -> "Warp Expenditure"
            name=label.split(" - ",1)[1].strip()
            if not name or name.startswith("+"):
                continue
            end=headers[i+1].start() if i+1<len(headers) else len(src)
            block=src[h.end():end]
            zh=_extract_zh(block,phrases)
            if not zh:
                continue
            key=normalize_name(name)
            if not key:
                continue
            # Prefer the longer maintained description if duplicate headings exist.
            if key not in out or len(zh)>len(out[key]):
                out[key]=zh
                details[key]={"name":name,"source":path}
    return out,details

if __name__=="__main__":
    m,_=load_chinese_descriptions()
    print("Chinese descriptions:",len(m))
    for k in ("warp expenditure","voice of command","smite"):
        print(k,"=>",m.get(k,"")[:400])
