#!/usr/bin/env python3
import re, json, html as htmllib, urllib.request, concurrent.futures, os, sys
from pathlib import Path

UA={'User-Agent':'Mozilla/5.0 (Darktide-BD bilingual planner)'}
BASE='https://darktide.gameslantern.com'
CLASSES=[
 {'key':'veteran','name':'Veteran','cn':'老兵','ig':'veteran','page':'veteran-sharpshooter','future':True},
 {'key':'zealot','name':'Zealot','cn':'狂信徒','ig':'zealot','page':'zealot-preacher','future':True},
 {'key':'psyker','name':'Psyker','cn':'灵能者','ig':'psyker','page':'psyker-psykinetic','future':True},
 {'key':'ogryn','name':'Ogryn','cn':'欧格林','ig':'ogryn','page':'ogryn-skullbreaker','future':True},
]
FOLDER_CAT={'keystone':'keystone','keystone_modifier':'keymod','ability':'ability',
            'ability_modifier':'abilmod','aura':'aura','tactical':'blitz','default':'passive',
            'broker_stimm':'stimm'}

def get(url,binary=False,tries=3):
    for i in range(tries):
        try:
            req=urllib.request.Request(url,headers=UA)
            with urllib.request.urlopen(req,timeout=35) as r:
                return r.read() if binary else r.read().decode('utf-8','replace')
        except Exception as e:
            if i==tries-1:
                print('GET FAIL',url,e,file=sys.stderr)
                return None

def strip_tags(s):
    s=re.sub(r'<[^>]+>',' ',s or '')
    return re.sub(r'\s+',' ',htmllib.unescape(s)).strip()

def img_attrs(tag):
    d={}
    for k in ('x','y','width','height'):
        m=re.search(k+r'="([^"]+)"',tag); d[k]=float(m.group(1)) if m else None
    m=re.search(r'(?:xlink:href|href)="([^"]+)"',tag); d['href']=m.group(1) if m else ''
    return d

def pick_tree_svgs(page):
    svgs=re.findall(r'<svg\b.*?</svg>',page,re.S)
    candidates=[]
    for s in svgs:
        lines=s.count('<line')
        abilities=s.count('/abilities/')
        if lines>=10 and abilities>=10:
            candidates.append((lines,abilities,s))
    return [x[2] for x in candidates]

def extract_svg(svg,ig,rootkey):
    nodes=[]; seen=set()
    for am in re.finditer(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>',svg,re.S):
        href,inner=am.group(1),am.group(2)
        if '/abilities/' not in href: continue
        slug=href.split('/abilities/')[-1].strip('/')
        if not slug or slug in seen: continue
        seen.add(slug)
        imgs=[img_attrs(m.group(0)) for m in re.finditer(r'<image\b[^>]*?/?>',inner,re.S)]
        if not imgs: continue
        base=imgs[0]; x,y,w=base['x'],base['y'],base['width'] or 80
        if x is None or y is None: continue
        allh=' '.join(i['href'] for i in imgs)
        shape='c'
        if 'square' in allh: shape='s'
        elif 'hex' in allh: shape='h'
        elif 'diamond' in allh: shape='d'
        cat='passive'
        for i in imgs:
            h=i['href']
            if f'/talents/{ig}/' in h:
                mf=re.search(rf'/talents/{ig}/([^/]+)/',h)
                cat=FOLDER_CAT.get(mf.group(1),'passive') if mf else 'passive'
                x,y,w=i['x'],i['y'],i['width'] or w
                break
        nodes.append({'s':slug,'slug':slug,'x':round(x+w/2),'y':round(y+w/2),'shape':shape,'cat':cat})
    rootm=re.search(r'<image\b[^>]*?(?:xlink:href|href)="([^"]*?/talent_root/[^"]+)"[^>]*?/?>',svg,re.S)
    if rootm:
        ri=img_attrs(rootm.group(0))
        if ri['x'] is not None and ri['y'] is not None:
            rw=ri['width'] or 90
            nodes.append({'s':rootkey,'slug':'','x':round(ri['x']+rw/2),'y':round(ri['y']+rw/2),'shape':'c','cat':'root'})
    edges=[]
    for lm in re.finditer(r'<line\b[^>]*>',svg):
        t=lm.group(0)
        def gv(k):
            m=re.search(k+r'="([^"]+)"',t)
            return round(float(m.group(1))) if m else None
        vals=[gv('x1'),gv('y1'),gv('x2'),gv('y2')]
        if None not in vals: edges.append(vals)
    return nodes,edges

TYPE_RE=re.compile(r'text-\[#707d67\][^>]*>\s*<div>([^<]+)</div>')
NAME_RE=re.compile(r'text-\[#d7e4ce\][^"]*text-lg[^"]*">([^<]+)<')
DESC_RE=re.compile(r'text-\[#a7be97\][^"]*leading-5[^"]*">(.*?)</div>',re.S)

def fetch_desc(slug):
    h=get(f'{BASE}/abilities/{slug}')
    if not h:return slug,{'n':slug.replace('-',' ').title(),'t':'','d':''}
    t=TYPE_RE.search(h);n=NAME_RE.search(h);d=DESC_RE.search(h)
    return slug,{'n':strip_tags(n.group(1)) if n else slug.replace('-',' ').title(),
                 't':strip_tags(t.group(1)) if t else '',
                 'd':strip_tags(d.group(1)) if d else ''}

def translation_map():
    url='https://raw.githubusercontent.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/main/Referneces/Translation.md'
    text=get(url) or ''
    out={}
    for line in text.splitlines():
        m=re.match(r'\s*\*\s+(.+?)\s+-\s+(.+?)\s*$',line)
        if m:
            en=m.group(1).strip().strip('*_ ')
            zh=m.group(2).strip().strip('*_ ')
            if en and zh: out.setdefault(en,zh)
    try:
        from opencc import OpenCC
        cc=OpenCC('t2s')
        out={k:cc.convert(v) for k,v in out.items()}
    except Exception:
        pass
    return out

def nearest(nodes,x,y):
    best=None;bd=10**18
    for n in nodes:
        d=(n['x']-x)**2+(n['y']-y)**2
        if d<bd:bd=d;best=n
    return best if bd<=1800 else None

classes=[]
all_slugs=set()
for cl in CLASSES:
    page=get(f'{BASE}/classes/{cl["page"]}')
    if not page: raise SystemExit('Could not fetch '+cl['page'])
    svgs=pick_tree_svgs(page)
    print(cl['name'],'candidate trees',len(svgs))
    if not svgs: raise SystemExit('No talent tree SVGs for '+cl['name'])
    idx=1 if cl['future'] and len(svgs)>1 else 0
    nodes,raw_edges=extract_svg(svgs[idx],cl['ig'],f'root-{cl["ig"]}')
    for n in nodes:
        if n['slug']:all_slugs.add(n['slug'])
    edges=[]
    for x1,y1,x2,y2 in raw_edges:
        a=nearest(nodes,x1,y1);b=nearest(nodes,x2,y2)
        if a and b and a['s']!=b['s']:
            pair=[a['s'],b['s']]
            if pair not in edges and pair[::-1] not in edges:edges.append(pair)
    xs=[n['x'] for n in nodes];ys=[n['y'] for n in nodes]
    pad=75
    classes.append({**cl,'budget':30,'viewbox':[min(xs)-pad,min(ys)-pad,max(xs)-min(xs)+pad*2,max(ys)-min(ys)+pad*2],
                    'nodes':nodes,'edges':edges})

DESC={}
with concurrent.futures.ThreadPoolExecutor(max_workers=18) as ex:
    for slug,info in ex.map(fetch_desc,sorted(all_slugs)):
        DESC[slug]=info
TR=translation_map()
for cl in classes:
    for n in cl['nodes']:
        if n['cat']=='root':
            n['en']=cl['name'];n['cn']=cl['cn'];n['type']='Class';n['desc']=''
        else:
            canonical=n['slug'].split('/')[-1]
            info=DESC.get(canonical,{})
            en=info.get('n') or n['slug'].replace('-',' ').title()
            if en.startswith('Depths Of The Damned/'):
                en=en.split('/')[-1]
            n['en']=en;n['cn']=TR.get(en,en);n['type']=info.get('t','');n['desc']=info.get('d','')
        n.pop('slug',None)

out={'version':'Depths of the Damned Future update','source':'Games Lantern','generated_by':'tools/scrape_future.py','classes':classes}
Path('tree-data.js').write_text('window.TREE_DATA='+json.dumps(out,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
print('WROTE tree-data.js',os.path.getsize('tree-data.js'))
