#!/usr/bin/env python3
import re
import json
import hashlib
import base64
import html as htmllib
import urllib.request
import concurrent.futures
import os
import sys
from pathlib import Path
from enhanced_zh import load_chinese_descriptions, load_bilingual_descriptions, normalize_name

MANUAL_ZH_PATH = Path(__file__).with_name('manual_zh.json')
try:
    MANUAL_ZH = json.loads(MANUAL_ZH_PATH.read_text(encoding='utf-8'))
except Exception:
    MANUAL_ZH = {}

MANUAL_CURRENT_PATH = Path(__file__).with_name('manual_current_cn.json')
try:
    MANUAL_CURRENT_CN = json.loads(MANUAL_CURRENT_PATH.read_text(encoding='utf-8'))
except Exception:
    MANUAL_CURRENT_CN = {}

MAINTAINED_TEXT_FALLBACK_PATH = Path(__file__).with_name('maintained_text_fallback.json')
try:
    MAINTAINED_TEXT_FALLBACK = json.loads(MAINTAINED_TEXT_FALLBACK_PATH.read_text(encoding='utf-8'))
except Exception:
    MAINTAINED_TEXT_FALLBACK = {}

def exact_reviewed_cn(en, desc):
    item = MANUAL_CURRENT_CN.get(en or '')
    if not isinstance(item, dict):
        return ''
    return item.get('cn','') if item.get('desc','') == (desc or '') else ''

def manual_desc_key(en, desc):
    raw = ((en or '') + '\0' + (desc or '')).encode('utf-8')
    return hashlib.sha1(raw).hexdigest()[:16]


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


# Games Lantern's future-tree SVG can expose some stat nodes without tooltip values.
# These values are cross-checked against the matching current node plus the published
# Depths of the Damned stat-node removals/rearrangements. Keep them keyed by the full
# future-tree slug so regeneration cannot silently turn them back into placeholders.
FUTURE_STAT_VALUE_OVERRIDES = {
    'depths-of-the-damned/toughness-damage-reduction-e9803f5f': ('+10% Toughness Damage Reduction.', '韧性伤害减免+10%。'),
    'depths-of-the-damned/toughness-boost-05f0f182': ('+25 Toughness.', '韧性+25。'),
    'depths-of-the-damned/melee-damage-boost-cffd3f48': ('+15% Melee Damage.', '近战伤害+15%。'),
    'depths-of-the-damned/melee-damage-boost-0e0cbc5b': ('+10% Melee Damage.', '近战伤害+10%。'),
    'depths-of-the-damned/toughness-damage-reduction-f19a0ccc': ('+10% Toughness Damage Reduction.', '韧性伤害减免+10%。'),
    'depths-of-the-damned/melee-damage-boost-cae861f3': ('+10% Melee Damage.', '近战伤害+10%。'),
    'depths-of-the-damned/toughness-boost-51f63e01': ('+25 Toughness.', '韧性+25。'),
    'depths-of-the-damned/toughness-boost-e8d6645b': ('+25 Toughness.', '韧性+25。'),
    'depths-of-the-damned/toughness-damage-reduction-d116b71e': ('+10% Toughness Damage Reduction.', '韧性伤害减免+10%。'),
    'depths-of-the-damned/toughness-damage-reduction-e0dd7125': ('+10% Toughness Damage Reduction.', '韧性伤害减免+10%。'),
    'depths-of-the-damned/toughness-damage-reduction-ee9c4ad4': ('+10% Toughness Damage Reduction.', '韧性伤害减免+10%。'),
    'depths-of-the-damned/ranged-damage-boost-f424381c': ('+10% Ranged Damage.', '远程伤害+10%。'),
    'depths-of-the-damned/melee-damage-boost-53898f4e': ('+10% Melee Damage.', '近战伤害+10%。'),
    'depths-of-the-damned/cleave-boost-fa9cb3e8': ('+25% Cleave.', '顺劈+25%。'),
    'depths-of-the-damned/impact-boost-96c8eedb': ('+25% Impact.', '冲击+25%。'),
    'depths-of-the-damned/toughness-boost-f3ac2cfc': ('+25 Toughness.', '韧性+25。'),
    'depths-of-the-damned/critical-chance-boost-42c40f11': ('+5% Critical Hit Chance.', '暴击率+5%。'),
    'depths-of-the-damned/melee-damage-boost-1bb21487': ('+10% Melee Damage.', '近战伤害+10%。'),
    'depths-of-the-damned/potent-tox-5bca9c55': ('+10% Toxin Strength.', '毒素强度+10%。'),
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
    s = re.sub(r'[!?.…]+$', '', s)
    return normalize_name(s)

def dedupe_display_name(name, canonical):
    name = clean_display_name(name)
    m = re.search(r'-(\d+)$', canonical or '')
    if m and name.endswith(' ' + m.group(1)):
        name = name[:-(len(m.group(1)) + 1)].rstrip()
    return name

TRANSLATION_SOURCE = {}

def translation_map():
    urls = [
        'https://raw.githubusercontent.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/main/Referneces/Translation.md',
        'https://raw.githubusercontent.com/xsSplater/Darktide_Enhanced_Descriptions_BETA/xss0/AI%20Document/Translation%20Table%20-%20zh-tw.md',
    ]
    announcement_url = 'https://raw.githubusercontent.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/main/%E5%85%AC%E5%91%8A/2026-09-18_%E8%A9%9B%E5%92%92%E6%B7%B1%E6%B7%B5%E5%B9%B3%E8%A1%A1%E6%80%A7%E6%9B%B4%E6%96%B0_%E7%B9%81%E4%B8%AD%E7%BF%BB%E8%AD%AF.md'
    raw = {}
    for source_index, url in enumerate(urls):
        source_label = 'syuantsai-glossary' if source_index == 0 else 'enhanced-translation-table'
        text = get(url) or ''
        for line in text.splitlines():
            m = re.match(r'\s*[-*]\s+(.+?)\s+-\s+(.+?)\s*$', line)
            if not m:
                continue
            en = m.group(1).strip().strip('*_ ')
            zh = m.group(2).strip().strip('*_ ')
            if en and zh:
                key = name_key(en)
                if key not in raw:
                    raw[key] = zh
                    TRANSLATION_SOURCE[key] = source_label

    announcement = get(announcement_url) or ''
    for line in announcement.splitlines():
        m = re.search(r'^\s*[-*]\s+([^（(]+?)\s*[（(]([^()（）]+)[)）]', line)
        if not m:
            continue
        zh = m.group(1).strip().strip('*_ ')
        en = m.group(2).strip()
        if en and zh:
            key = name_key(en)
            if key not in raw:
                raw[key] = zh
                TRANSLATION_SOURCE[key] = 'syuantsai-fatshark-preview-translation'

    try:
        from opencc import OpenCC
        cc = OpenCC('t2s')
        raw = {k: cc.convert(v) for k, v in raw.items()}
    except Exception:
        pass

    # High-confidence name corrections. These override the older formal glossary only
    # where a later maintained name table explicitly corrected a typo/stale translation,
    # or where the old glossary contains an unambiguous typo.
    maintained_curated = {
        'cleave boost':'顺劈增幅',
        'impact boost':'冲击增幅',
        'critical chance boost':'暴击率增幅',
        'ranged damage boost':'远程伤害增幅',
        'superiority complex':'优越情结',
        'precision strikes':'精准打击',
        'malocator':'生化武器官',
        'coated weaponry':'涂毒武装',
        'a tertium welcome':'特提恩式欢迎',
    }
    for en, zh in maintained_curated.items():
        raw[en] = zh
        TRANSLATION_SOURCE[en] = 'maintained-name-correction'

    # Fallbacks only where no maintained display-name entry was found.
    curated = {
        'melee damage boost':'近战伤害提升',
        'toughness boost':'韧性提升',
        'health boost':'生命提升',
        'stamina boost':'耐力提升',
        'damage boost':'伤害提升',
        'just getting started':'热身完毕',
        'vulture s mark':'兀鹫印记',
        'potent tox':'强效毒素',
        'kinetic energy distributors':'动能分配器',
    }
    for en, zh in curated.items():
        if en not in raw:
            raw[en] = zh
            TRANSLATION_SOURCE[en] = 'manual-name-fallback'
    return raw

def numeric_multiset(s):
    vals = re.findall(r'[-+]?\d+(?:\.\d+)?%?', s or '')
    # Sign can be expressed linguistically in Chinese ("降低 10%") rather than as "-10%".
    return sorted(v.lstrip('+-') for v in vals)

def safe_paired_text(en, cn):
    if not en or not cn:
        return False
    if re.search(r'\{[A-Za-z0-9_]+(?::%s)?\}|\{#|CKWord\(|CNumb\(|CPhrs\(|CNote\(|Dot_[A-Za-z_]+', en + ' ' + cn):
        return False
    return numeric_multiset(en) == numeric_multiset(cn)

def word_set(s):
    stop={'the','a','an','and','or','of','to','for','in','on','your','you','is','are','with','by','from','this','that'}
    return {w for w in re.findall(r"[a-z0-9']+", (s or '').lower()) if w not in stop}

def numeric_subset(required, candidate):
    """Every mechanics number in required must appear in candidate with equal multiplicity.
    Candidate may contain extra implementation/detail numbers.
    """
    req=list(numeric_multiset(required))
    got=list(numeric_multiset(candidate))
    for value in req:
        if value not in got:
            return False
        got.remove(value)
    return True

def advanced_matches_base(base_en, enhanced_en):
    if not base_en or not enhanced_en:
        return False
    if not numeric_subset(base_en, enhanced_en):
        return False
    bw, ew = word_set(base_en), word_set(enhanced_en)
    if not bw:
        return True
    # Enhanced text may be much longer; require enough shared mechanics vocabulary
    # to avoid attaching an old description to a reworked talent with the same name.
    coverage = len(bw & ew) / max(1, len(bw))
    return coverage >= 0.42

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

FUTURE_PREVIEW_CN = {
    name_key('Found Some More'):'每15秒补充1%弹药。',
    name_key('Zealous Pilgrim'):'使用战斗技能后，获得持续5秒的不会死亡效果。隐秘领域：离开隐身时开始；不屈灵魂合唱：收起圣物时开始；惩戒邪恶/忠诚之怒：使用技能时开始。',
    name_key('Fire and Fury'):'在不会死亡效果持续期间，武器攻击会对敌人施加燃烧（最多12层），近战攻击每次施加3层。',
    name_key('Risen'):'在不会死亡效果持续期间，每秒获得+5最大韧性，最多叠加8次，加成持续5秒。',
    name_key('Got Your Back'):'以近战攻击击杀正在锁定队友的敌人时，为该队友恢复7.5%韧性，并额外为自己恢复5%韧性。',
    name_key('Holy Tools'):'使用武器特殊动作后5秒内，下一次近战攻击的伤害+20%。',
    name_key('Wait in Line'):'受到的远程攻击伤害-20%。',
    name_key('Purifying Hatred'):'对燃烧或遭电击的敌人造成的伤害+15%。',
    name_key('Focused Warp'):'亚空间伤害+15%。',
    name_key('Peril Equilibrium'):'非亚空间的近战或远程攻击命中时，每次产生2%反噬；通过此效果最多累积至75%。',
    name_key('Psykinetic Grip'):'颅脑崩裂、惩戒与灵能攻击的伤害+20%。',
    name_key('Kinetic Repulsion'):'“整合型艾曼纳图斯力场”激活期间，每次受到的生命值伤害最多为50。',
}

FUTURE_PREVIEW_EN = {
    name_key('Found Some More'):'Replenish 1% Ammo every 15s.',
    name_key('Zealous Pilgrim'):'Using your Ability grants 5s of Unkillable. Shroudfield: starts on leaving Stealth; Chorus of Spiritual Fortitude: starts on unwielding the relic; Chastise the Wicked / Fury of the Faithful: on ability use.',
    name_key('Fire and Fury'):'While Unkillable, weapon attacks apply Burn (up to 12 stacks). Melee attacks apply 3 stacks.',
    name_key('Risen'):'While Unkillable, each second, gain +5 Max Toughness, stacking 8 times, lasting 5 seconds.',
    name_key('Got Your Back'):'Killing an enemy that is targeting an ally, with a melee attack, restores 7.5% Toughness to that ally and an additional 5% to yourself.',
    name_key('Holy Tools'):'+20% Damage on your next Melee Attack, within 5s after activating your Weapon Special.',
    name_key('Wait in Line'):'-20% damage taken from ranged attacks.',
    name_key('Purifying Hatred'):'+15% damage vs Burning or Electrocuted enemies.',
    name_key('Focused Warp'):'+15% Warp damage.',
    name_key('Peril Equilibrium'):'Non-Warp melee/ranged hits generate Peril up to 75% by 2% per hit.',
    name_key('Psykinetic Grip'):'+20% damage for Brain Rupture, Smite, and Assail.',
    name_key('Kinetic Repulsion'):'Limit all Health Damage Taken while Integrated Refraction Emitter is active to 50.',
}


# Explicit Sep 18, 2026 Fatshark preview overrides.
# English mechanics come from Fatshark's official preview; Simplified Chinese is a
# script-converted form of SyuanTsai's maintained Traditional-Chinese transcription
# of that official preview, not a free-form machine translation.
FATSHARK_FUTURE_OVERRIDES = {
    # Ogryn
    name_key('Dominate'): {
        'en': '+15% Rending for 10 s on Elite Kill.',
        'cn': '击杀精英敌人后获得+15%撕裂，持续10秒。'
    },
    name_key('Keep Shooting'): {
        'en': '+20% Reload Speed when reloading an Empty Clip.',
        'cn': '空弹匣装填时，装填速度+20%。'
    },
    name_key('Soften Them Up'): {
        'en': 'Enemies damaged by your Melee Attacks take +15% more Damage for 5 s.',
        'cn': '被你的近战攻击命中的敌人额外受到15%伤害，持续5秒。'
    },
    name_key('Go Again!'): {
        'en': 'Staggering an Enemy replenishes 1.5% Cooldown of Loyal Protector.',
        'cn': '使敌人踉跄可恢复“忠诚护卫”1.5%的冷却时间。'
    },
    name_key('Maximum Firepower'): {
        'en': '+100% Ability Cooldown Regeneration for 2.5 s when Lucky Bullet triggers.',
        'cn': '触发“幸运子弹”时，技能冷却恢复速度+100%，持续2.5秒。'
    },
    name_key('Bruiser'): {
        'en': '50% Ability Cooldown Regeneration for 4 s after you or an Ally in Coherency kills an Elite Enemy.',
        'cn': '你或协同范围内的盟友击杀精英敌人后，技能冷却恢复速度+50%，持续4秒。'
    },
    name_key('Indomitable'): {
        'en': 'Charge forward with great force, knocking back and Staggering Enemies. Gain +25% Attack Speed and +25% Movement Speed for 5 s. The charge stops on collision with Monstrosities. Base Cooldown: 25 s. This is an augmented version of Bull Rush with +100% charge distance.',
        'cn': '向前强力冲锋，击退并使敌人踉跄。获得+25%攻击速度和+25%移动速度，持续5秒。撞上巨兽时会停止冲锋。基础冷却时间25秒。该技能是“蛮牛冲撞”的强化版本，冲锋距离提高100%。'
    },

    # Zealot
    name_key('Faithful Frenzy'): {
        'en': '+10% Melee Attack Speed and +5% Movement Speed.',
        'cn': '近战攻击速度+10%，移动速度+5%。'
    },
    name_key('Until Death'): {
        'en': 'Fatal Damage instead makes you Unkillable for 8 s. Occurs every 120 s.',
        'cn': '受到致命伤害时改为进入8秒不会死亡状态。每120秒最多触发一次。'
    },
    name_key('Holy Revenant'): {
        'en': 'Triggering Until Death knocks back nearby Enemies. While Unkillable, dealing Damage restores Health, up to 25% of Max Health. Mutually exclusive with Zealous Pilgrim.',
        'cn': '触发“死战到底”时会击退附近敌人。在不会死亡状态持续期间，造成伤害可恢复生命值，最多恢复至最大生命值的25%。无法与“狂热朝圣者”同时选择。'
    },
    name_key('The Voice of Terra'): {
        'en': 'While Shooting, replenish 10% Toughness per second.',
        'cn': '射击期间每秒恢复10%韧性。'
    },
    name_key('Out of Pocket'): {
        'en': 'Melee Kills replenish 10% of the missing Ammo in your current Magazine.',
        'cn': '近战击杀时，补回当前弹匣已消耗弹药的10%。'
    },
    name_key('Unseen Blade'): {
        'en': '+20% Damage vs Enemies not targeting you.',
        'cn': '对未锁定你的敌人造成的伤害+20%。'
    },
    name_key("Retributor's Stance"): {
        'en': 'During its Duration, replenish 0.5% Toughness per second per spent Stack of Momentum, up to 10%.',
        'cn': '效果持续期间，每消耗一层“势能”每秒恢复0.5%韧性，最高10%。'
    },
    name_key('Chorus of Spiritual Fortitude'): {
        'en': 'Wield a holy relic that releases 5 energy pulses every 0.8 s. While channeling, Allies in Coherency are Stun Immune and Unkillable. Each pulse Replenishes 45% Toughness and also grants +15 Max Toughness, up to +75 total. After the first pulse, only Enemies within 8 m are Staggered or Suppressed by later pulses. Base Cooldown: 60 s.',
        'cn': '挥舞圣物，每0.8秒释放一次能量脉冲，共5次。引导期间，协同范围内的盟友免疫眩晕且不会死亡。每次脉冲恢复45%韧性，并额外提供+15最大韧性，最多累计+75。第一次脉冲后，后续脉冲只会使8米内的敌人踉跄或受到压制。基础冷却时间60秒。'
    },
    name_key('Holy Cause'): {
        'en': 'Each pulse grants +8% Toughness Damage Reduction to you and Allies in Coherency, stacking up to 5 times. Lasts 10 s.',
        'cn': '每次脉冲为你和协同范围内的盟友提供+8%韧性伤害减免，最多叠加5层，持续10秒。'
    },
    name_key("Ecclesiarch's Call"): {
        'en': 'Each pulse grants +6% Damage to you and Allies in Coherency, stacking up to 5 times. Lasts 10 s.',
        'cn': '每次脉冲为你和协同范围内的盟友提供+6%伤害，最多叠加5层，持续10秒。'
    },

    # Psyker
    name_key('Mind in Motion'): {
        'en': 'Your Movement Speed is not reduced while Quelling Peril or Reloading. Gain +5% Movement Speed.',
        'cn': '平息危机值或装填时移动速度不会降低，并获得+5%移动速度。'
    },
    name_key("Psykinetic's Aura"): {
        'en': 'Gain 50% Ability Cooldown Regeneration for 3 s when you kill an Elite or Specialist Enemy.',
        'cn': '你击杀精英或专家敌人时，技能冷却恢复速度+50%，持续3秒。'
    },
    name_key('Perilous Combustion'): {
        'en': 'Killing an Elite or Specialist Enemy applies 2 stacks of Soulblaze to nearby Enemies, causing Damage over time.',
        'cn': '击杀精英或专家敌人时，对附近敌人施加2层灵魂烈焰，持续造成伤害。'
    },
    name_key('Surety of Arms'): {
        'en': '30% Reload Speed while below 80% Peril. On Reload generate up to 15% Peril based on the Percentage of the Clip Restored.',
        'cn': '危机值低于80%时，装填速度+30%。装填时根据恢复的弹匣比例最多生成15%危机值。'
    },

    # Veteran
    name_key('Duck and Dive'): {
        'en': '+30% Stamina on avoiding Ranged Attacks by Dodging, Sprinting or Sliding. Gain +5% Movement Speed.',
        'cn': '通过闪避、疾跑或滑铲躲开远程攻击时恢复30%耐力，并获得+5%移动速度。'
    },
    name_key('Survivalist'): {
        'en': 'Replenish 0.5% Ammo for you and Allies in Coherency whenever any of you Kill an Elite or Specialist Enemy. This can only occur once every 5 s. This is the improved version of the Aura; its base value is 0.25%.',
        'cn': '你或协同范围内的盟友击杀精英或专家敌人时，为你和盟友补充0.5%弹药；每5秒最多触发一次。该数值为强化后的光环效果，基础值为0.25%。'
    },
    name_key('Close and Kill'): {
        'en': '+7.5% Movement Speed for you and Allies in Coherency.',
        'cn': '你和协同范围内的盟友获得+7.5%移动速度。'
    },
    name_key('Duty and Honour'): {
        'en': 'Voice of Command also provides you and Allies in Coherency with +75 Toughness for 10 s. This can exceed maximum Toughness.',
        'cn': '“发号施令”还会为你和协同范围内的盟友提供+75韧性，持续10秒；该效果可以超过最大韧性。'
    },

    # Arbites
    name_key('Nuncio-Aquila'): {
        'en': 'Deploy a Nuncio-Aquila in the target direction. After a tap / quick deploy, it now slowly follows the Arbites. Allies within 7.5 m Replenish 7.5% Toughness per second, gain +30% Suppression Dealt, +30% Impact and -25% Recoil, and are Immune to Stun, Slowdown and Suppression. Enemies within 7.5 m have +15% Damage Taken. Lasts 20 s. 60 s Cooldown.',
        'cn': '向目标方向部署“天鹰使节”。点按或快速部署后，它现在会缓慢跟随法务官。7.5米内的盟友每秒恢复7.5%韧性，获得+30%压制效果、+30%冲击、-25%后坐力，并免疫眩晕、减速与压制。7.5米内的敌人受到的伤害+15%。持续20秒，冷却60秒。'
    },
    name_key('Lone Wolf'): {
        'en': 'You are no longer accompanied by your Cyber-Mastiff. Gain +15% Toughness Damage Reduction, +10% Attack Speed, +20% Damage, and +1 Charge on Blitz Abilities. Replenish Arbites Grenade every 45 s or Voltaic Shock Mine every 90 s depending on the chosen Blitz.',
        'cn': '你将不再有赛博獒随行。获得+15%韧性伤害减免、+10%攻击速度、+20%伤害，并使闪击技能最大充能次数+1。根据所选闪击技能自动恢复充能：“仲裁官手榴弹”每45秒恢复一次，“伏打电击地雷”每90秒恢复一次。'
    },

    # Hive Scum
    name_key('Rampage!'): {
        'en': 'Replenish all Toughness and enter Rampage! for 10 s. For the duration, gain +35% Melee Power, +20% Melee Attack Speed and +25% Damage Reduction, and become Stun and Suppression Immune. Melee Strikes extend the duration by 0.3 s. After 20 s, the duration extension from each hit is reduced. Base Cooldown: 30 s.',
        'cn': '恢复全部韧性并进入“横冲直撞！”状态10秒。持续期间获得+35%近战威力、+20%近战攻击速度和+25%伤害减免，并免疫眩晕与压制。近战命中可延长0.3秒持续时间；累计持续时间达到20秒后，每次命中提供的延长效果降低。基础冷却时间30秒。'
    },
    name_key('Sample Collector'): {
        'en': 'Kills replenish 0.5 s of Cartel Special Cooldown. Killing Chem Toxin infected Enemies instead replenishes 1 s.',
        'cn': '击杀敌人恢复0.5秒“帮派特技”冷却时间；击杀感染化学毒素的敌人改为恢复1秒。'
    },

    # Skitarii
    name_key('Advanced Combat Doctrines'): {
        'en': 'Spend 25% Capacitance and Swap to your Secondary Weapon. Your weapon locks onto enemies close to your targeting reticule, granting inhuman accuracy. Gain -90% Spread and -60% Recoil while active. Drain 10% Capacitance per second and 1% per shot; drain pauses while reloading. The Ability ends if you switch away, reach 0% Capacitance with 0 Charges, or reactivate it. Requires at least 1 Charge. No Cooldown. After use, gain +25% Reload Speed for 5 s.',
        'cn': '消耗25%电容量并切换至副武器。武器会锁定准星附近的敌人，使你获得近乎非人的精准度；持续期间散布降低90%，后坐力降低60%。激活期间每秒消耗10%电容量，每次射击额外消耗1%；装填时暂停消耗。若切离副武器、电容量降至0%且充能次数也为0，或再次激活技能，技能都会结束。至少拥有1次充能时才能使用，无冷却时间。使用后5秒内装填速度+25%。'
    },
    name_key('Voltaic Motivator'): {
        'en': 'When using Voltaic Emitter, gain +5% Attack Speed plus an additional +5% per Charge spent for 15 s.',
        'cn': '使用“电能发射器”时获得+5%攻击速度，并且每消耗一次充能再额外获得+5%攻击速度，持续15秒。'
    },
    name_key('Voltaic Overcharge'): {
        'en': 'Voltaic Emitter restores 25% Toughness per Charge spent, plus an additional 1% Toughness for each Enemy hit by the Electric Discharge.',
        'cn': '“电能发射器”每消耗一次充能恢复25%韧性；电能冲击每命中一名敌人，额外恢复1%韧性。'
    },
    name_key('Higher Purpose'): {
        'en': 'Elite and Specialist Kills restore an additional +2.5% Capacitance.',
        'cn': '击杀精英或专家敌人时，额外恢复2.5%电容量。'
    },
    name_key('Noospheric Command'): {
        'en': 'Ordering your Servo-Skull to attack an Enemy greatly increases its Fire Rate for 2 s. Costs 30% Capacitance.',
        'cn': '命令伺服头骨攻击敌人时，会大幅提高其射速2秒，消耗30%电容量。'
    },
    name_key('Voltaic Burst'): {
        'en': 'Staggering Enemies with a Push applies Electrocution, dealing Damage and Stunning them. 12 s Cooldown.',
        'cn': '用推击使敌人踉跄时，会施加电击，造成伤害并眩晕敌人。冷却时间12秒。'
    },
    name_key('Ammunition Deposit'): {
        'en': 'Gain +25 Toughness. You and Allies in Coherency have +15% Ammo Reserve.',
        'cn': '获得+25韧性。你和协同范围内的盟友获得+15%弹药储备。'
    },
    name_key('System Shock'): {
        'en': 'Electrocuting an Enemy applies 3 Stacks of 2.5% Brittleness.',
        'cn': '使敌人遭受电击时，对其施加3层、每层2.5%的脆弱。'
    },
    name_key('Galvanized Coating'): {
        'en': 'You are Stun Immune and have +15% Damage Resistance. Taking Melee Damage spends 7.5% Capacitance.',
        'cn': '你免疫眩晕并获得+15%伤害抗性。受到近战伤害时消耗7.5%电容量。'
    },
    name_key('Target-Neutralization Feedback'): {
        'en': 'Weakspot Kills grant Stun and Suppression Immunity for 5 s.',
        'cn': '弱点击杀会使你免疫眩晕与压制，持续5秒。'
    },
    name_key('Salvation Doctrine'): {
        'en': 'Gain +25% Damage Resistance while Reviving an Ally. Gain +25% Revive Speed.',
        'cn': '救起盟友期间获得+25%伤害减免，并获得+25%救援速度。'
    },
    name_key('Superior Tracking Litanies'): {
        'en': '-50% Movement Speed penalty while Bracing or Aiming Down Sights. Additionally, gain -45% Spread.',
        'cn': '架枪或瞄准时的移动速度惩罚降低50%；此外，散布降低45%。'
    },
    name_key('Force Distribution Actuators'): {
        'en': 'Your Pushes have +75% Impact when at or above 50% Stamina.',
        'cn': '耐力达到或高于50%时，推击的冲击+75%。'
    },
}

FUTURE_ROOT_PASSIVES = {
    'ogryn': {
        'en': 'Base Toughness: 125. Iconic Passive — Towering Presence: +50% Coherency Radius.',
        'cn': '基础韧性：125。招牌被动“卓越气场”：协同半径+50%。'
    },
    'zealot': {
        'en': 'Base Toughness: 125. Iconic Passive — Blood Redemption: +75% Toughness Replenishment from Melee Kills.',
        'cn': '基础韧性：125。招牌被动“鲜血救赎”：近战击杀的韧性恢复加成+75%。'
    },
    'psyker': {
        'en': 'Base Critical Hit Chance: 10%.',
        'cn': '基础暴击率：10%。'
    },
    'veteran': {
        'en': 'Iconic Passive — Guardsman: +25% Ranged Damage. Iconic Passive — Sharpshooter: Elite and Specialist Kills restore 1% Ammo, 5 s Cooldown.',
        'cn': '招牌被动“帝国卫兵”：远程伤害+25%。招牌被动“神射手”：击杀精英或专家敌人时恢复1%弹药，冷却5秒。'
    },
}

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

# English talent/ability titles that are safe to localize when they appear inside
# Chinese mechanics text. This deliberately excludes generic category words that
# could be enemy/weapon terminology in another context.
INLINE_TALENT_NAMES = {
    "Martyrdom","Telekine Shield","Scrier's Gaze","Castigator's Stance","Rampage!",
    "Infiltrate","Fury of the Faithful","Blazing Piety","Assail","Venting Shriek",
    "Empowered Psionics","Feel No Pain","Indomitable","Adrenaline Frenzy","Stimm Supply",
    "Voice of Command","Loyal Protector","Executioner's Stance","Smoke Grenade",
    "Krak Grenade","Frag Grenade","Shroudfield","Brain Rupture","Smite","Break the Line",
    "Desperado","Enhanced Desperado","Until Death","Chastise the Wicked",
    "Chorus of Spiritual Fortitude"
}

def normalize_cn_display(text, class_key=''):
    """Normalize maintained Traditional-Chinese-derived text for this zh-CN UI."""
    if not text:
        return text
    s = str(text)
    # Darktide glossary terminology / Mainland Simplified register.
    if class_key == 'psyker':
        s = s.replace('亚空间危机', '亚空间反噬')
        s = s.replace('臨界危機', '临界反噬').replace('临界危机', '临界反噬')
        s = s.replace('危机值', '反噬').replace('危機值', '反噬')
        # Remaining Psyker "危机" occurrences in these talent texts refer to Peril.
        s = s.replace('危机', '反噬').replace('危機', '反噬')
    s = s.replace('硬壳护甲', '甲壳护甲').replace('硬壳', '甲壳护甲')
    s = s.replace('甲壳甲', '甲壳护甲').replace('防弹甲', '防弹护甲')
    s = s.replace('灵魂烈焰', '灵魂之火')
    s = s.replace('连携', '协同').replace('連攜', '协同')
    s = s.replace('机率', '几率').replace('機率', '几率')
    s = s.replace('公尺', '米')
    s = s.replace('您', '你')
    s = s.replace('作战技能', '战斗技能')
    s = s.replace('暴击命中几率', '暴击率').replace('暴击几率', '暴击率')
    s = s.replace('暴擊命中機率', '暴击率').replace('暴擊機率', '暴击率')
    s = re.sub(r'(\d+(?:\.\d+)?)\s*-\s*-\s*(\d+(?:\.\d+)?)', r'\1–\2', s)
    # Common spacing artifacts from concatenated Enhanced Descriptions fragments.
    s = s.replace('协同 盟友', '协同范围内的盟友')
    s = s.replace('协同范围内盟友', '协同范围内的盟友')
    s = s.replace('韧性 伤害', '韧性伤害').replace('腐败 抗性', '腐败抗性')
    s = s.replace('反噬 等级', '反噬')
    s = re.sub(r'([\u4e00-\u9fff])\s+([，。；：！？])', r'\1\2', s)
    return s

def localize_inline_talent_names(trees):
    # Build the map from the same canonical display names already selected for nodes.
    title_map = {}
    for cl in trees:
        for n in cl.get('nodes', []):
            en, cn = n.get('en',''), n.get('cn','')
            if en in INLINE_TALENT_NAMES and cn and cn != en:
                title_map[en] = cn
    pairs = sorted(title_map.items(), key=lambda kv: len(kv[0]), reverse=True)
    for cl in trees:
        class_key = cl.get('parent') or cl.get('key','')
        for n in cl.get('nodes', []):
            for field in ('descCn','advancedCn','mechanicsCn'):
                text = n.get(field,'')
                if not text:
                    continue
                for en, cn in pairs:
                    text = re.sub(r'(?<![A-Za-z])' + re.escape(en) + r'(?![A-Za-z])', cn, text, flags=re.I)
                n[field] = normalize_cn_display(text, class_key)

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
                root_passive = FUTURE_ROOT_PASSIVES.get(cl.get('key')) if cl.get('patch') == 'future' else None
                if root_passive:
                    n['mechanicsEn'] = root_passive['en']
                    n['mechanicsCn'] = root_passive['cn']
                    n['mechanicsSource'] = 'fatshark-official-preview+syuantsai-preview-translation'
            else:
                canonical = n['slug'].split('/')[-1]
                info = DESC.get(canonical, {})
                en = dedupe_display_name(info.get('n') or canonical.replace('-',' ').title(), canonical)
                n['en'] = en
                n['nameSourceEn'] = 'games-lantern'
                n['cn'] = TR.get(name_key(en), en)
                n['nameSourceCn'] = TRANSLATION_SOURCE.get(name_key(en), 'source-name-untranslated')
                # Stimm Lab names such as Hypex/Kalma/Vultoprene are product/formula labels.
                # Keep the source name intact rather than inventing a transliteration, but make
                # the Chinese UI meaning explicit when no maintained Chinese title exists.
                if cl.get('key') == 'hivescum-stimm' and n['cn'] == en:
                    n['cn'] = en + '（兴奋剂配方）'
                n['type'] = info.get('t','')
                n['desc'] = info.get('d','')
                n['descSourceEn'] = 'games-lantern'
                official_override = FATSHARK_FUTURE_OVERRIDES.get(name_key(en)) if cl.get('patch') == 'future' else None
                if official_override:
                    n['desc'] = official_override['en']
                    n['descCn'] = official_override['cn']
                    n['descSourceEn'] = 'fatshark-official-preview'
                    n['descSource'] = 'syuantsai-fatshark-preview-translation'
                future_en = FUTURE_PREVIEW_EN.get(name_key(en), '') if cl.get('patch') == 'future' else ''
                if not n['desc'] and future_en:
                    n['desc'] = future_en
                    n['descSourceEn'] = 'fatshark-official-preview'
                pair = BI_DESC.get(normalize_name(en), {})
                pair_en = pair.get('en','')
                pair_cn = pair.get('cn','')
                preview_cn = FUTURE_PREVIEW_CN.get(name_key(en), '') if cl.get('patch') == 'future' else ''
                reviewed_cn = MANUAL_ZH.get(manual_desc_key(en, n['desc']), '')
                exact_cn = exact_reviewed_cn(en, n['desc'])
                if official_override:
                    pass
                elif preview_cn and numeric_multiset(n['desc']) == numeric_multiset(preview_cn):
                    n['descCn'] = preview_cn
                    n['descSource'] = 'fatshark-preview-zh'
                    n['descSourceEn'] = 'fatshark-official-preview'
                elif pair_cn and compatible_base_translation(n['desc'], pair_en):
                    n['descCn'] = pair_cn
                    n['descSource'] = 'community-aligned'
                elif reviewed_cn:
                    n['descCn'] = reviewed_cn
                    n['descSource'] = 'manual-reviewed'
                elif exact_cn:
                    n['descCn'] = exact_cn
                    n['descSource'] = 'manual-reviewed-current-tooltip'
                else:
                    n['descCn'] = ''
                    n['descSource'] = 'base-english-only'
                pair_safe = safe_paired_text(pair_en, pair_cn)
                advanced_current = pair_safe and advanced_matches_base(n['desc'], pair_en)
                # Enhanced Descriptions is valuable for hidden mechanics, but it can lag
                # behind balance changes. Only retain it when it still contains every
                # numeric mechanic from the current base tooltip and enough matching terms.
                if official_override:
                    n['advancedEn'] = ''
                    n['advancedCn'] = ''
                else:
                    n['advancedEn'] = pair_en if advanced_current else ''
                    n['advancedCn'] = pair_cn if advanced_current else ''

                fallback_key = f"{cl.get('patch','')}|{cl.get('key','')}|{n.get('s','')}"
                fallback_text = MAINTAINED_TEXT_FALLBACK.get(fallback_key, {})
                if fallback_text and fallback_text.get('desc','') == n.get('desc',''):
                    # Never carry maintained text across a changed English tooltip.
                    # This fallback exists only to survive transient upstream/source-fetch loss.
                    if not n.get('descCn') and fallback_text.get('descCn'):
                        n['descCn'] = fallback_text['descCn']
                        n['descSource'] = fallback_text.get('descSource') or n.get('descSource','base-aligned')
                    if not (n.get('advancedEn') and n.get('advancedCn')) and fallback_text.get('advancedEn') and fallback_text.get('advancedCn'):
                        n['advancedEn'] = fallback_text['advancedEn']
                        n['advancedCn'] = fallback_text['advancedCn']

                future_stat = FUTURE_STAT_VALUE_OVERRIDES.get(n.get('slug', '')) if cl.get('patch') == 'future' and n.get('cat') == 'stat' else None
                if future_stat:
                    n['desc'], n['descCn'] = future_stat
                    n['descSourceEn'] = 'games-lantern'
                    n['descSource'] = 'manual-reviewed'

                if name_key(en) == 'just a dream':
                    # Fatshark's official Bound by Duty notes give the user-facing effect.
                    # Decompiled game source confirms the actual threshold (97%) and that
                    # both Health and Toughness damage contribute to the Peril conversion.
                    n['desc'] = 'While below Critical Peril, 25% of Damage Taken is converted into Peril.'
                    n['descSourceEn'] = 'fatshark-official-bound-by-duty'
                    n['mechanicsEn'] = 'Implementation check: below 97% Peril, incoming damage is multiplied by 0.75 and the prevented portion from both Health and Toughness damage is converted into Peril. This talent does not directly increase Max Health or Max Toughness. Peril generated by it can interact with Quietude.'
                    n['mechanicsCn'] = '机制核对：危机值低于97%时，代码实现会将受到的伤害乘以0.75，并把生命值伤害与韧性伤害中被减免的部分转化为危机值。该天赋本身不会直接提高最大生命值或最大韧性；它生成的危机值可以与“宁静”联动。'
                    n['mechanicsSource'] = 'darktide-game-source+fatshark-official'
                if cl.get('patch') == 'future' and name_key(en) == 'axial slash':
                    n['mechanicsEn'] = 'Official Depths preview: Axial Slash damage now falls off across 6 targets from 500 to 300; Impact falls off from 100 to 50.'
                    n['mechanicsCn'] = '官方“诅咒深渊”预览：轴向斩击现在会在6个目标间产生衰减，伤害由500递减至300，冲击由100递减至50。'
                    n['mechanicsSource'] = 'fatshark-official-preview+syuantsai-preview-translation'
                if not n['desc'] and n.get('cat') == 'stat':
                    n['desc'] = f"{en}. Exact stat value is not available from the current preview data source."
                    n['descCn'] = f"{n['cn']}。当前预览数据源未提供可靠的具体数值。"
                    n['descSource'] = 'stat-source-missing'
            n.pop('slug', None)

attach_info(future_classes)
attach_info(live_classes)

# Normalize terminology only after both trees have their final display names, so
# inline English talent titles can be replaced consistently in live and future text.
localize_inline_talent_names(future_classes + live_classes)

all_nodes=[n for tree in (future_classes+live_classes) for n in tree['nodes'] if n.get('cat')!='root']
zh_hits=sum(1 for n in all_nodes if n.get('descCn'))
advanced_hits=sum(1 for n in all_nodes if n.get('advancedEn') and n.get('advancedCn'))
print('base-aligned zh-cn coverage', zh_hits, 'of', len(all_nodes))
print('paired advanced-mechanics coverage', advanced_hits, 'of', len(all_nodes))
reviewed_hits=sum(1 for n in all_nodes if n.get('descSource') == 'manual-reviewed')
print('manual-reviewed base coverage', reviewed_hits, 'of', len(all_nodes))
exact_reviewed_hits=sum(1 for n in all_nodes if n.get('descSource') == 'manual-reviewed-current-tooltip')
print('exact current-tooltip reviewed coverage', exact_reviewed_hits, 'of', len(all_nodes))

out = {
    'version': 'Depths of the Damned Future update',
    'liveVersion': 'Skitarii Class Live',
    'source': 'Games Lantern + Fatshark official notes + maintained translation sources',
    'sourceRefs': {
        'games-lantern':'https://darktide.gameslantern.com/build-editor',
        'fatshark-bound-by-duty':'https://www.playdarktide.com/news/bound-by-duty-free-update-out-now',
        'fatshark-depths-preview':'https://forums.fatsharkgames.com/t/preview-upcoming-balance-changes/125587',
        'darktide-game-source':'https://github.com/Aussiemon/Darktide-Source-Code',
        'syuantsai-glossary':'https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/blob/main/Referneces/Translation.md',
        'enhanced-descriptions':'https://github.com/xsSplater/Darktide_Enhanced_Descriptions_BETA'
    },
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
