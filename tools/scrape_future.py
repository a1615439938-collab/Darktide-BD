#!/usr/bin/env python3
import re
import json
import base64
import html as htmllib
import urllib.request
import concurrent.futures
import os
import sys
from pathlib import Path
from enhanced_zh import load_chinese_descriptions, load_bilingual_descriptions, normalize_name

UA = {'User-Agent':'Mozilla/5.0 (Darktide-BD bilingual planner)'}
BASE = 'https://darktide.gameslantern.com'

CLASSES = [
    {'key':'veteran','name':'Veteran','cn':'老兵','ig':'veteran','page':'veteran-sharpshooter'},
    {'key':'zealot','name':'Zealot','cn':'狂信徒','ig':'zealot','page':'zealot-preacher'},
    {'key':'psyker','name':'Psyker','cn':'灵能者','ig':'psyker','page':'psyker-psykinetic'},
    {'key':'ogryn','name':'Ogryn','cn':'欧格林','ig':'ogryn','page':'ogryn-skullbreaker'},
    {'key':'arbites','name':'Arbites','cn':'仲裁官','ig':'adamant','page':'arbites'},
    {'key':'skitarii','name':'Skitarii','cn':'护教军','ig':'cryptic','page':'skitarii'},
    {'key':'hivescum','name':'Hive Scum','cn':'巢都渣滓','ig':'broker','page':'hive-scum'},
]

FOLDER_CAT = {
    'keystone':'keystone',
    'keystone_modifier':'keymod',
    'ability':'ability',
    'ability_modifier':'abilmod',
    'aura':'aura',
    'tactical':'blitz',
    'default':'passive',
    'broker_stimm':'stimm',
}

def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=35) as r:
                return r.read() if binary else r.read().decode('utf-8','replace')
        except Exception as e:
            if i == tries - 1:
                print('GET FAIL', url, e, file=sys.stderr)
                return None

def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', htmllib.unescape(s)).strip()

def clean_display_name(s):
    s = (s or '').strip()
    # Games Lantern stat-node slugs sometimes end in an opaque content hash.
    s = re.sub(r'[ _-]+[A-Fa-f0-9]{8,}$', '', s).strip()
    return s

def img_attrs(tag):
    d = {}
    for k in ('x','y','width','height'):
        m = re.search(k + r'="([^"]+)"', tag)
        d[k] = float(m.group(1)) if m else None
    m = re.search(r'(?:xlink:href|href)="([^"]+)"', tag)
    d['href'] = m.group(1) if m else ''
    return d

def pick_tree_svgs(page):
    svgs = re.findall(r'<svg\b.*?</svg>', page, re.S)
    candidates = []
    for s in svgs:
        lines = s.count('<line')
        abilities = s.count('/abilities/')
        if lines >= 10 and abilities >= 10:
            candidates.append((lines, abilities, s))
    return [x[2] for x in candidates]

def extract_svg(svg, ig, rootkey):
    nodes = []
    raw_edges = []
    icon_urls = {}
    seen = set()

    for am in re.finditer(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', svg, re.S):
        href, inner = am.group(1), am.group(2)
        if '/abilities/' not in href:
            continue

        slug = href.split('/abilities/')[-1].strip('/')
        if not slug or slug in seen:
            continue
        seen.add(slug)

        imgs = [img_attrs(m.group(0)) for m in re.finditer(r'<image\b[^>]*?/?>', inner, re.S)]
        if not imgs:
            continue

        base = imgs[0]
        x, y, w = base['x'], base['y'], base['width'] or 80
        if x is None or y is None:
            continue

        allh = ' '.join(i['href'] for i in imgs)
        shape = 'c'
        if 'square' in allh:
            shape = 's'
        elif 'hex' in allh:
            shape = 'h'
        elif 'diamond' in allh:
            shape = 'd'

        cat = 'stat'
        art = None
        for i in imgs:
            h = i['href']
            if '/talents/' in h and ('/' + ig + '/') in h:
                art = h
                mf = re.search(r'/talents/' + re.escape(ig) + r'/([^/]+)/', h)
                cat = FOLDER_CAT.get(mf.group(1), 'passive') if mf else 'passive'
                x, y, w = i['x'], i['y'], i['width'] or w
                break

        if art:
            icon_urls[slug] = art if art.startswith('http') else BASE + art

        nodes.append({
            's': slug,
            'slug': slug,
            'x': round(x + w / 2),
            'y': round(y + w / 2),
            'shape': shape,
            'cat': cat,
        })

    rootm = re.search(r'<image\b[^>]*?(?:xlink:href|href)="([^"]*?/talent_root/[^"]+)"[^>]*?/?>', svg, re.S)
    if rootm:
        ri = img_attrs(rootm.group(0))
        if ri['x'] is not None and ri['y'] is not None:
            rw = ri['width'] or 90
            rurl = rootm.group(1)
            icon_urls[rootkey] = rurl if rurl.startswith('http') else BASE + rurl
            nodes.append({
                's': rootkey,
                'slug': '',
                'x': round(ri['x'] + rw / 2),
                'y': round(ri['y'] + rw / 2),
                'shape': 'c',
                'cat': 'root',
            })

    for lm in re.finditer(r'<line\b[^>]*>', svg):
        t = lm.group(0)
        def gv(k):
            m = re.search(k + r'="([^"]+)"', t)
            return round(float(m.group(1))) if m else None
        vals = [gv('x1'), gv('y1'), gv('x2'), gv('y2')]
        if None not in vals:
            raw_edges.append(vals)

    return nodes, raw_edges, icon_urls

def nearest(nodes, x, y):
    best = None
    bd = 10**18
    for n in nodes:
        d = (n['x'] - x)**2 + (n['y'] - y)**2
        if d < bd:
            bd = d
            best = n
    return best if bd <= 1800 else None

def build_tree(meta, svg, patch, parent=None, sub_label=None, sub_label_cn=None, rootkey=None):
    rootkey = rootkey or ('root-' + meta['ig'])
    nodes, raw_edges, icons = extract_svg(svg, meta['ig'], rootkey)
    edges = []
    for x1, y1, x2, y2 in raw_edges:
        a = nearest(nodes, x1, y1)
        b = nearest(nodes, x2, y2)
        if a and b and a['s'] != b['s']:
            pair = [a['s'], b['s']]
            if pair not in edges and pair[::-1] not in edges:
                edges.append(pair)

    if not nodes:
        raise RuntimeError('No nodes for ' + meta['name'] + ' ' + patch)

    xs = [n['x'] for n in nodes]
    ys = [n['y'] for n in nodes]
    pad = 70

    tree = {
        **meta,
        'patch': patch,
        'budget': 30,
        'viewbox': [min(xs)-pad, min(ys)-pad, max(xs)-min(xs)+2*pad, max(ys)-min(ys)+2*pad],
        'nodes': nodes,
        'edges': edges,
    }
    if parent:
        tree['parent'] = parent
    if sub_label:
        tree['subLabel'] = sub_label
    if sub_label_cn:
        tree['subLabelCn'] = sub_label_cn
    return tree, icons

TYPE_RE = re.compile(r'text-\[#707d67\][^>]*>\s*<div>([^<]+)</div>')
NAME_RE = re.compile(r'text-\[#d7e4ce\][^"]*text-lg[^"]*">([^<]+)<')
DESC_RE = re.compile(r'text-\[#a7be97\][^"]*leading-5[^"]*">(.*?)</div>', re.S)

def fetch_desc(slug):
    h = get(BASE + '/abilities/' + slug)
    if not h:
        return slug, {'n': clean_display_name(slug.replace('-',' ').title()), 't':'', 'd':''}
    t = TYPE_RE.search(h)
    n = NAME_RE.search(h)
    d = DESC_RE.search(h)
    return slug, {
        'n': clean_display_name(strip_tags(n.group(1)) if n else slug.replace('-',' ').title()),
        't': strip_tags(t.group(1)) if t else '',
        'd': strip_tags(d.group(1)) if d else '',
    }

def name_key(s):
    s = (s or '').replace('’', "'").replace('–', '-').replace('—', '-').strip()
    s = re.sub(r'[!?.…]+
future_classes = []
live_classes = []
all_slugs = set()
all_icon_urls = {}

hive_svgs = None
for meta in CLASSES:
    page = get(BASE + '/classes/' + meta['page'])
    if not page:
        raise SystemExit('Could not fetch ' + meta['page'])
    svgs = pick_tree_svgs(page)
    print(meta['name'], 'candidate trees', len(svgs))
    if not svgs:
        raise SystemExit('No talent tree SVGs for ' + meta['name'])

    if meta['key'] == 'hivescum':
        hive_svgs = svgs
        live_idx = 0
        future_idx = 2 if len(svgs) >= 4 else min(1, len(svgs)-1)
    else:
        live_idx = 0
        future_idx = 1 if len(svgs) > 1 else 0

    live_tree, live_icons = build_tree(meta, svgs[live_idx], 'live')
    future_tree, future_icons = build_tree(meta, svgs[future_idx], 'future')
    live_classes.append(live_tree)
    future_classes.append(future_tree)
    all_icon_urls.update(live_icons)
    all_icon_urls.update(future_icons)

    for tree in (live_tree, future_tree):
        for n in tree['nodes']:
            if n['slug']:
                all_slugs.add(n['slug'].split('/')[-1])

    print(meta['name'], 'live', len(live_tree['nodes']), 'nodes;', 'future', len(future_tree['nodes']), 'nodes')

if hive_svgs and len(hive_svgs) >= 4:
    base_meta = {
        'key':'hivescum-stimm',
        'name':'Hive Scum — Stimm Lab',
        'cn':'巢都渣滓 — 兴奋剂实验室',
        'ig':'broker',
        'page':'hive-scum',
    }
    live_stimm, live_icons = build_tree(
        base_meta, hive_svgs[1], 'live',
        parent='hivescum', sub_label='Stimm Lab', sub_label_cn='兴奋剂实验室',
        rootkey='root-brokerstimm'
    )
    future_stimm, future_icons = build_tree(
        base_meta, hive_svgs[3], 'future',
        parent='hivescum', sub_label='Stimm Lab', sub_label_cn='兴奋剂实验室',
        rootkey='root-brokerstimm'
    )
    live_classes.append(live_stimm)
    future_classes.append(future_stimm)
    all_icon_urls.update(live_icons)
    all_icon_urls.update(future_icons)
    for tree in (live_stimm, future_stimm):
        for n in tree['nodes']:
            if n['slug']:
                all_slugs.add(n['slug'].split('/')[-1])
    print('Hive Scum Stimm Lab live', len(live_stimm['nodes']), 'nodes;', 'future', len(future_stimm['nodes']), 'nodes')

DESC = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for slug, info in ex.map(fetch_desc, sorted(all_slugs)):
        DESC[slug] = info

TR = translation_map()
ZH_DESC, ZH_DESC_META = load_chinese_descriptions()
BI_DESC, BI_DESC_META = load_bilingual_descriptions()
print('name translations', len(TR))
print('community zh-cn descriptions', len(ZH_DESC))
print('safe bilingual enhanced pairs', sum(1 for v in BI_DESC.values() if v.get('en') and v.get('cn')))

def dl_icon(item):
    key, url = item
    b = get(url, binary=True)
    if not b:
        return key, None
    return key, 'data:image/webp;base64,' + base64.b64encode(b).decode()

ICONS = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for key, uri in ex.map(dl_icon, all_icon_urls.items()):
        if uri:
            ICONS[key] = uri

print('icons downloaded', len(ICONS), 'of', len(all_icon_urls))

def attach_info(trees):
    for cl in trees:
        for n in cl['nodes']:
            if n['cat'] == 'root':
                n['en'] = cl['name']
                n['cn'] = cl['cn']
                n['type'] = 'Class'
                n['desc'] = ''
                n['descCn'] = ''
                n['advancedEn'] = ''
                n['advancedCn'] = ''
                n['descSource'] = 'class'
            else:
                canonical = n['slug'].split('/')[-1]
                info = DESC.get(canonical, {})
                en = clean_display_name(info.get('n') or canonical.replace('-',' ').title())
                n['en'] = en
                n['cn'] = TR.get(name_key(en), en)
                n['type'] = info.get('t','')
                n['desc'] = info.get('d','')
                pair = BI_DESC.get(normalize_name(en), {})
                pair_en = pair.get('en','')
                pair_cn = pair.get('cn','')
                # Main bilingual text must describe the same layer as Games Lantern's base English.
                n['descCn'] = pair_cn if pair_cn and compatible_base_translation(n['desc'], pair_en) else ''
                if pair_en and pair_cn:
                    n['advancedEn'] = pair_en
                    n['advancedCn'] = pair_cn
                n['descSource'] = 'community-aligned' if n['descCn'] else 'base-english-only'
            n.pop('slug', None)

attach_info(future_classes)
attach_info(live_classes)

all_nodes=[n for tree in (future_classes+live_classes) for n in tree['nodes'] if n.get('cat')!='root']
zh_hits=sum(1 for n in all_nodes if n.get('descCn'))
advanced_hits=sum(1 for n in all_nodes if n.get('advancedEn') and n.get('advancedCn'))
print('base-aligned zh-cn coverage', zh_hits, 'of', len(all_nodes))
print('paired advanced-mechanics coverage', advanced_hits, 'of', len(all_nodes))

out = {
    'version': 'Depths of the Damned Future update',
    'liveVersion': 'Skitarii Class Live',
    'source': 'Games Lantern',
    'generated_by': 'tools/scrape_future.py',
    'classes': future_classes,
    'liveClasses': live_classes,
    'icons': ICONS,
}
Path('tree-data.js').write_text(
    'window.TREE_DATA=' + json.dumps(out, ensure_ascii=False, separators=(',',':')) + ';\n',
    encoding='utf-8'
)
print('WROTE tree-data.js size(MB):', round(os.path.getsize('tree-data.js') / 1e6, 2))
, '', s)
    return normalize_name(s)

def translation_map():
    urls = [
        'https://raw.githubusercontent.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/main/Referneces/Translation.md',
        'https://raw.githubusercontent.com/xsSplater/Darktide_Enhanced_Descriptions_BETA/xss0/AI%20Document/Translation%20Table%20-%20zh-tw.md',
    ]
    raw = {}
    for url in urls:
        text = get(url) or ''
        for line in text.splitlines():
            m = re.match(r'\s*[-*]\s+(.+?)\s+-\s+(.+?)\s*
future_classes = []
live_classes = []
all_slugs = set()
all_icon_urls = {}

hive_svgs = None
for meta in CLASSES:
    page = get(BASE + '/classes/' + meta['page'])
    if not page:
        raise SystemExit('Could not fetch ' + meta['page'])
    svgs = pick_tree_svgs(page)
    print(meta['name'], 'candidate trees', len(svgs))
    if not svgs:
        raise SystemExit('No talent tree SVGs for ' + meta['name'])

    if meta['key'] == 'hivescum':
        hive_svgs = svgs
        live_idx = 0
        future_idx = 2 if len(svgs) >= 4 else min(1, len(svgs)-1)
    else:
        live_idx = 0
        future_idx = 1 if len(svgs) > 1 else 0

    live_tree, live_icons = build_tree(meta, svgs[live_idx], 'live')
    future_tree, future_icons = build_tree(meta, svgs[future_idx], 'future')
    live_classes.append(live_tree)
    future_classes.append(future_tree)
    all_icon_urls.update(live_icons)
    all_icon_urls.update(future_icons)

    for tree in (live_tree, future_tree):
        for n in tree['nodes']:
            if n['slug']:
                all_slugs.add(n['slug'].split('/')[-1])

    print(meta['name'], 'live', len(live_tree['nodes']), 'nodes;', 'future', len(future_tree['nodes']), 'nodes')

if hive_svgs and len(hive_svgs) >= 4:
    base_meta = {
        'key':'hivescum-stimm',
        'name':'Hive Scum — Stimm Lab',
        'cn':'巢都渣滓 — 兴奋剂实验室',
        'ig':'broker',
        'page':'hive-scum',
    }
    live_stimm, live_icons = build_tree(
        base_meta, hive_svgs[1], 'live',
        parent='hivescum', sub_label='Stimm Lab', sub_label_cn='兴奋剂实验室',
        rootkey='root-brokerstimm'
    )
    future_stimm, future_icons = build_tree(
        base_meta, hive_svgs[3], 'future',
        parent='hivescum', sub_label='Stimm Lab', sub_label_cn='兴奋剂实验室',
        rootkey='root-brokerstimm'
    )
    live_classes.append(live_stimm)
    future_classes.append(future_stimm)
    all_icon_urls.update(live_icons)
    all_icon_urls.update(future_icons)
    for tree in (live_stimm, future_stimm):
        for n in tree['nodes']:
            if n['slug']:
                all_slugs.add(n['slug'].split('/')[-1])
    print('Hive Scum Stimm Lab live', len(live_stimm['nodes']), 'nodes;', 'future', len(future_stimm['nodes']), 'nodes')

DESC = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for slug, info in ex.map(fetch_desc, sorted(all_slugs)):
        DESC[slug] = info

TR = translation_map()
ZH_DESC, ZH_DESC_META = load_chinese_descriptions()
print('community zh-cn descriptions', len(ZH_DESC))

def dl_icon(item):
    key, url = item
    b = get(url, binary=True)
    if not b:
        return key, None
    return key, 'data:image/webp;base64,' + base64.b64encode(b).decode()

ICONS = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for key, uri in ex.map(dl_icon, all_icon_urls.items()):
        if uri:
            ICONS[key] = uri

print('icons downloaded', len(ICONS), 'of', len(all_icon_urls))

def attach_info(trees):
    for cl in trees:
        for n in cl['nodes']:
            if n['cat'] == 'root':
                n['en'] = cl['name']
                n['cn'] = cl['cn']
                n['type'] = 'Class'
                n['desc'] = ''
                n['descCn'] = ''
            else:
                canonical = n['slug'].split('/')[-1]
                info = DESC.get(canonical, {})
                en = clean_display_name(info.get('n') or canonical.replace('-',' ').title())
                n['en'] = en
                n['cn'] = TR.get(en, en)
                n['type'] = info.get('t','')
                n['desc'] = info.get('d','')
                n['descCn'] = ZH_DESC.get(normalize_name(en), '')
            n.pop('slug', None)

attach_info(future_classes)
attach_info(live_classes)

all_nodes=[n for tree in (future_classes+live_classes) for n in tree['nodes'] if n.get('cat')!='root']
zh_hits=sum(1 for n in all_nodes if n.get('descCn'))
print('zh-cn description coverage', zh_hits, 'of', len(all_nodes))

out = {
    'version': 'Depths of the Damned Future update',
    'liveVersion': 'Skitarii Class Live',
    'source': 'Games Lantern',
    'generated_by': 'tools/scrape_future.py',
    'classes': future_classes,
    'liveClasses': live_classes,
    'icons': ICONS,
}
Path('tree-data.js').write_text(
    'window.TREE_DATA=' + json.dumps(out, ensure_ascii=False, separators=(',',':')) + ';\n',
    encoding='utf-8'
)
print('WROTE tree-data.js size(MB):', round(os.path.getsize('tree-data.js') / 1e6, 2))
, line)
            if not m:
                continue
            en = m.group(1).strip().strip('*_ ')
            zh = m.group(2).strip().strip('*_ ')
            if en and zh:
                raw.setdefault(name_key(en), zh)
    try:
        from opencc import OpenCC
        cc = OpenCC('t2s')
        raw = {k: cc.convert(v) for k, v in raw.items()}
    except Exception:
        pass

    # Small, explicit fallbacks for generic stat nodes and known table gaps.
    curated = {
        'cleave boost':'顺劈提升',
        'impact boost':'冲击提升',
        'critical chance boost':'暴击率提升',
        'ranged damage boost':'远程伤害提升',
        'melee damage boost':'近战伤害提升',
        'toughness boost':'韧性提升',
        'health boost':'生命提升',
        'stamina boost':'耐力提升',
        'damage boost':'伤害提升',
        'just getting started':'热身完毕',
        'vulture s mark':'兀鹫印记',
        'potent tox':'强效毒素',
    }
    for en, zh in curated.items():
        raw.setdefault(en, zh)
    return raw

def numeric_multiset(s):
    vals = re.findall(r'[-+]?\d+(?:\.\d+)?%?', s or '')
    return sorted(v.lstrip('+') for v in vals)

def word_set(s):
    stop={'the','a','an','and','or','of','to','for','in','on','your','you','is','are','with','by','from','this','that'}
    return {w for w in re.findall(r"[a-z0-9']+", (s or '').lower()) if w not in stop}

def compatible_base_translation(base_en, enhanced_en):
    if not base_en or not enhanced_en:
        return False
    if numeric_multiset(base_en) != numeric_multiset(enhanced_en):
        return False
    bw, ew = word_set(base_en), word_set(enhanced_en)
    if not bw:
        return False
    coverage = len(bw & ew) / max(1, len(bw))
    ratio = len(enhanced_en) / max(1, len(base_en))
    return coverage >= 0.72 and 0.60 <= ratio <= 1.55

future_classes = []
live_classes = []
all_slugs = set()
all_icon_urls = {}

hive_svgs = None
for meta in CLASSES:
    page = get(BASE + '/classes/' + meta['page'])
    if not page:
        raise SystemExit('Could not fetch ' + meta['page'])
    svgs = pick_tree_svgs(page)
    print(meta['name'], 'candidate trees', len(svgs))
    if not svgs:
        raise SystemExit('No talent tree SVGs for ' + meta['name'])

    if meta['key'] == 'hivescum':
        hive_svgs = svgs
        live_idx = 0
        future_idx = 2 if len(svgs) >= 4 else min(1, len(svgs)-1)
    else:
        live_idx = 0
        future_idx = 1 if len(svgs) > 1 else 0

    live_tree, live_icons = build_tree(meta, svgs[live_idx], 'live')
    future_tree, future_icons = build_tree(meta, svgs[future_idx], 'future')
    live_classes.append(live_tree)
    future_classes.append(future_tree)
    all_icon_urls.update(live_icons)
    all_icon_urls.update(future_icons)

    for tree in (live_tree, future_tree):
        for n in tree['nodes']:
            if n['slug']:
                all_slugs.add(n['slug'].split('/')[-1])

    print(meta['name'], 'live', len(live_tree['nodes']), 'nodes;', 'future', len(future_tree['nodes']), 'nodes')

if hive_svgs and len(hive_svgs) >= 4:
    base_meta = {
        'key':'hivescum-stimm',
        'name':'Hive Scum — Stimm Lab',
        'cn':'巢都渣滓 — 兴奋剂实验室',
        'ig':'broker',
        'page':'hive-scum',
    }
    live_stimm, live_icons = build_tree(
        base_meta, hive_svgs[1], 'live',
        parent='hivescum', sub_label='Stimm Lab', sub_label_cn='兴奋剂实验室',
        rootkey='root-brokerstimm'
    )
    future_stimm, future_icons = build_tree(
        base_meta, hive_svgs[3], 'future',
        parent='hivescum', sub_label='Stimm Lab', sub_label_cn='兴奋剂实验室',
        rootkey='root-brokerstimm'
    )
    live_classes.append(live_stimm)
    future_classes.append(future_stimm)
    all_icon_urls.update(live_icons)
    all_icon_urls.update(future_icons)
    for tree in (live_stimm, future_stimm):
        for n in tree['nodes']:
            if n['slug']:
                all_slugs.add(n['slug'].split('/')[-1])
    print('Hive Scum Stimm Lab live', len(live_stimm['nodes']), 'nodes;', 'future', len(future_stimm['nodes']), 'nodes')

DESC = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for slug, info in ex.map(fetch_desc, sorted(all_slugs)):
        DESC[slug] = info

TR = translation_map()
ZH_DESC, ZH_DESC_META = load_chinese_descriptions()
print('community zh-cn descriptions', len(ZH_DESC))

def dl_icon(item):
    key, url = item
    b = get(url, binary=True)
    if not b:
        return key, None
    return key, 'data:image/webp;base64,' + base64.b64encode(b).decode()

ICONS = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for key, uri in ex.map(dl_icon, all_icon_urls.items()):
        if uri:
            ICONS[key] = uri

print('icons downloaded', len(ICONS), 'of', len(all_icon_urls))

def attach_info(trees):
    for cl in trees:
        for n in cl['nodes']:
            if n['cat'] == 'root':
                n['en'] = cl['name']
                n['cn'] = cl['cn']
                n['type'] = 'Class'
                n['desc'] = ''
                n['descCn'] = ''
            else:
                canonical = n['slug'].split('/')[-1]
                info = DESC.get(canonical, {})
                en = clean_display_name(info.get('n') or canonical.replace('-',' ').title())
                n['en'] = en
                n['cn'] = TR.get(en, en)
                n['type'] = info.get('t','')
                n['desc'] = info.get('d','')
                n['descCn'] = ZH_DESC.get(normalize_name(en), '')
            n.pop('slug', None)

attach_info(future_classes)
attach_info(live_classes)

all_nodes=[n for tree in (future_classes+live_classes) for n in tree['nodes'] if n.get('cat')!='root']
zh_hits=sum(1 for n in all_nodes if n.get('descCn'))
print('zh-cn description coverage', zh_hits, 'of', len(all_nodes))

out = {
    'version': 'Depths of the Damned Future update',
    'liveVersion': 'Skitarii Class Live',
    'source': 'Games Lantern',
    'generated_by': 'tools/scrape_future.py',
    'classes': future_classes,
    'liveClasses': live_classes,
    'icons': ICONS,
}
Path('tree-data.js').write_text(
    'window.TREE_DATA=' + json.dumps(out, ensure_ascii=False, separators=(',',':')) + ';\n',
    encoding='utf-8'
)
print('WROTE tree-data.js size(MB):', round(os.path.getsize('tree-data.js') / 1e6, 2))
