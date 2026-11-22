#!/usr/bin/env python3
"""One-off import of the old bilkite.ucoz.com crawl into content files.
Usage: python3 tools/import_legacy.py <crawl_dir>  (crawl_dir has map.json, pages/, img/)"""
import json, re, os, sys, html, hashlib, shutil, difflib
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify
from PIL import Image

CRAWL = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'src/content')
MEDIA = os.path.join(ROOT, 'public/media')
m = json.load(open(f'{CRAWL}/map.json'))

CATS = {7: 'protivovazpalitelni', 9: 'imunna-sistema', 4: 'hranosmilane', 5: 'kravoobrashtenie',
        8: 'pikocho-polova-sistema', 10: 'zhenska-linia', 44: 'aromaterapia'}
PAGES = {2: 'za-nas', 3: 'porachka', 11: 'za-sportuvashti', 53: 'tradicionna-kitajska-medicina',
         85: 'preporaki-na-kitajcite', 91: 'programa-hranosmilane', 92: 'programa-otdelitelna-sistema',
         98: 'programa-hronichna-umora', 132: 'art-terapia-sakralni-simvoli', 54: 'za-distributori',
         117: 'kitajska-tradicionna-medicina', 93: 'programa-otdelitelna-sistema-2'}
FORCE_ACTIVE = {74}

def key(u):
    a = re.match(r'/index/(?:[^/]+/)?0-(\d+)$', u)
    if a: return ('page', int(a.group(1)))
    a = re.match(r'/publ/[^/]+/\d+-\d+-\d+-(\d+)$', u)
    if a: return ('publ', int(a.group(1)))
    a = re.match(r'/(news|blog)/[^/]+/[\d-]+-(\d+)$', u)
    if a: return (a.group(1), int(a.group(2)))
    a = re.match(r'/load/[^/]+/\d+-\d+-\d+-(\d+)$', u)
    if a: return ('load', int(a.group(1)))
    a = re.match(r'/forum/\d+-(\d+)-1$', u)
    if a: return ('forum', int(a.group(1)))
    if u == '/': return ('home', 0)
    if re.match(r'/[a-z_\-]+$', u) and u not in ('/publ', '/faq', '/register'): return ('land', u[1:])
    return None

def slugify(s):
    s = s.lower().replace('_', '-')
    s = re.sub(r'[^a-z0-9-]+', '-', s)
    return re.sub(r'-+', '-', s).strip('-')

TR = dict(zip('абвгдежзийклмнопрстуфхцчшщъьюя', ['a','b','v','g','d','e','zh','z','i','j','k','l','m','n','o','p','r','s','t','u','f','h','c','ch','sh','sht','a','','ju','ja']))
def translit(s):
    return slugify(''.join(TR.get(ch, ch) for ch in s.lower()))

# ---- collect raw docs
docs = {}
for u, fn in m.items():
    k = key(u)
    if not k or fn.startswith('ERR'): continue
    d = docs.setdefault(k, {'urls': [], 'file': fn})
    d['urls'].append(u)

def load(d):
    return BeautifulSoup(open(f'{CRAWL}/pages/{d["file"]}').read(), 'lxml')

def body_of(k, soup):
    """returns (title, body_tag, date)"""
    kind = k[0]
    title = soup.title.get_text().strip()
    date = None
    if kind in ('page', 'home'):
        b = soup.select_one('.page-content-wrapper')
        title = re.sub(r'^Билкови продукти - ', '', title)
        return title, b, None
    if kind == 'forum':
        posts = soup.select('.posttdMessage')
        b = soup.new_tag('div')
        for i, p in enumerate(posts):
            if i: b.append(soup.new_tag('hr'))
            w = soup.new_tag('div'); w.extend(list(p.contents)); b.append(w)
        title = title.split(' - Форум')[0].strip()
        dt = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', soup.get_text())
        return title[:1].upper() + title[1:], b, None
    b = soup.select_one('td.eText') or soup.select_one('td.eMessage')
    t = soup.select_one('.eTitle')
    if t:
        for x in t.select('div'): x.decompose()
        title = t.get_text(' ', strip=True)
    else:
        title = title.split(' - ')[0]
    txt = soup.get_text(' ')
    a = re.search(r'/(\d{4})-(\d{2})-(\d{2})-\d+$', d['urls'][0])
    if a: date = '-'.join(a.groups())
    else:
        a = re.search(r'(20\d\d)-(\d\d)-(\d\d), \d', txt) or None
        if a: date = '-'.join(a.groups())
        else:
            a = re.search(r'\((\d\d)\.(\d\d)\.(20\d\d)\)', txt)
            if a: date = f'{a.group(3)}-{a.group(2)}-{a.group(1)}'
    return title, b, date

for k, d in docs.items():
    soup = load(d)
    if soup.title is None: d['body'] = None; continue
    d['title'], d['body'], d['date'] = body_of(k, soup)
    d['text'] = re.sub(r'\s+', ' ', d['body'].get_text(' ')).strip() if d['body'] else ''
docs = {k: d for k, d in docs.items() if d.get('body') is not None}

# ---- classify & slugs
def best_named(d):
    c = [re.match(r'/(?:index|publ|news|blog|load)/([^/]+)/', u) for u in d['urls']]
    c = [x.group(1) for x in c if x and not re.match(r'^[\d-]+$', x.group(1))]
    return max(c, key=len) if c else None

cat_links = {}
for cid in CATS:
    ids = []
    for a in docs[('page', cid)]['body'].select('a[href]'):
        x = re.search(r'/index/(?:[^/"]+/)?0-(\d+)$', a['href'])
        if x and int(x.group(1)) not in ids and int(x.group(1)) != 3: ids.append(int(x.group(1)))
    cat_links[cid] = ids
active = set(i for v in cat_links.values() for i in v) | FORCE_ACTIVE

used = set()
def uniq(s, suffix):
    s = s[:70].strip('-') or 'item'
    if s in used: s = f'{s}-{suffix}'
    used.add(s); return s

land_dupe = {}
for k, d in sorted(docs.items(), key=lambda x: str(x[0])):
    kind, n = k
    if kind == 'page':
        if n in CATS: d['type'], d['slug'] = 'categories', CATS[n]
        elif n in PAGES: d['type'], d['slug'] = 'pages', PAGES[n]
        else:
            d['type'] = 'products'
            d['slug'] = uniq(slugify(best_named(d) or '') or translit(d['title']), n)
            d['status'] = 'active' if n in active else 'archive'
    elif kind == 'home': d['type'], d['slug'] = 'pages', 'nachalo'
    else:
        d['type'] = 'articles'
        base = n if kind == 'land' else (best_named(d) or translit(d['title']))
        d['slug'] = uniq(slugify(base) if re.match(r'^[a-z0-9_\-]+$', base) else translit(base), f'{kind}-{n}')
        d['source'] = kind

# landing pages duplicate publ entries: merge when texts match
for k, d in list(docs.items()):
    if k[0] != 'land': continue
    for k2, d2 in docs.items():
        if k2[0] == 'publ' and difflib.SequenceMatcher(None, d['text'][:3000], d2['text'][:3000]).quick_ratio() > 0.97 and abs(len(d['text'])-len(d2['text'])) < 200:
            d2['urls'] += d['urls']; d2['slug'] = d['slug']; del docs[k]; break

newurl = {}
PREFIX = {'categories': '/catalog/', 'products': '/product/', 'articles': '/articles/', 'pages': '/info/'}
for k, d in docs.items():
    if d['slug'] == 'nachalo': d['new'] = '/'
    elif d['slug'] == 'porachka': d['new'] = '/order/'
    elif d['slug'] == 'za-nas': d['new'] = '/about/'
    else: d['new'] = PREFIX[d['type']] + d['slug'] + '/'
    for u in d['urls']: newurl[u] = d['new']
newurl.update({'/publ': '/articles/', '/publ/': '/articles/', '/publ/1': '/articles/', '/faq': '/faq/', '/faq/': '/faq/',
               '/blog/': '/articles/', '/news/': '/articles/', '/load/': '/articles/', '/load/1': '/articles/', '/forum/': '/articles/'})

def resolve(href):
    h = href.strip()
    x = re.match(r'(?:https?:)?//(?:www\.)?bilkite\.ucoz\.com(/.*)?$', h, re.I)
    if x: h = x.group(1) or '/'
    elif not h.startswith('/'): return None
    h = h.split('#')[0]
    if h in newurl: return newurl[h]
    if h.rstrip('/') in newurl: return newurl[h.rstrip('/')]
    k = key(h)
    if k and k in docs: return docs[k]['new']
    if re.match(r'/publ/\d', h) or h.startswith('/publ/?'): return '/articles/'
    return False

# ---- media
os.makedirs(MEDIA, exist_ok=True)
media_done = {}
def media(src):
    if src.startswith('/.s/') or 'noavatar' in src: return None
    p = re.sub(r'^(?:https?:)?//(?:www\.)?bilkite\.ucoz\.com', '', src).split('?')[0]
    if p.startswith('http'): return src
    local = f'{CRAWL}/img/' + p.lstrip('/').replace('/', '__')
    if not os.path.exists(local): return None
    if local in media_done: return media_done[local]
    name = translit(os.path.splitext(os.path.basename(p))[0]) or hashlib.md5(p.encode()).hexdigest()[:8]
    out = f'{name}.webp'; i = 2
    while out in media_done.values(): out = f'{name}-{i}.webp'; i += 1
    try:
        im = Image.open(local); im.load()
        if im.mode not in ('RGB', 'RGBA'): im = im.convert('RGBA' if 'A' in im.mode or im.mode == 'P' else 'RGB')
        im.thumbnail((1400, 1400))
        im.save(os.path.join(MEDIA, out), 'WEBP', quality=84)
    except Exception as e:
        print('IMG FAIL', local, e); return None
    media_done[local] = '/media/' + out
    return media_done[local]

# ---- html -> markdown
report = {'unresolved': [], 'missing_img': [], 'prices': []}
BOILER = re.compile(r'^(За контакти:?|Email:\s*bilkite1@gmail\.com|E-mail:\s*bilkite1@gmail\.com|Тел:?\s*\+359 ?886 ?031 ?394|bilkite1@gmail\.com|Варна, .ВМСофт Лаб. ООД)$', re.I)

def clean(d):
    b = d['body']
    for x in b.select('script, style, #nativeroll_video_cont, .js-teasers-wrapper, form, input, iframe[src*="facebook"], .ucoz-forum-post-signature'):
        x.decompose()
    imgs = []
    for im in b.select('img'):
        src = media(im.get('src', ''))
        if not src:
            if '/.s/' not in im.get('src', ''): report['missing_img'].append((d['slug'], im.get('src')))
            im.decompose(); continue
        alt = (im.get('alt') or '').strip()
        imgs.append((src, alt)); im.attrs = {'src': src, 'alt': alt}
    for a in b.select('a[href]'):
        h = a['href']
        if h.startswith(('mailto:', 'tel:')): continue
        if h.startswith('javascript') or '/go?' in h and 'facebook.com/hashtag' in h or 'plus.google.com' in h:
            a.unwrap(); continue
        if h.startswith('/go?'): h = h[4:]
        r = resolve(h)
        if r: a.attrs = {'href': r}
        elif r is False:
            report['unresolved'].append((d['slug'], h)); a.attrs = {'href': 'https://bilkite.ucoz.com' + h if h.startswith('/') else h}
        else: a.attrs = {'href': h}
        if not a.get_text(strip=True) and not a.select('img'): a.decompose()
    for t in b.find_all(True):
        if t.name in ('font', 'span', 'o:p', 'u', 'center', 'div') and t.name != 'div': t.unwrap()
    for t in b.find_all(True):
        keep = {'a': ['href'], 'img': ['src', 'alt'], 'td': ['colspan', 'rowspan'], 'th': ['colspan', 'rowspan']}.get(t.name, [])
        t.attrs = {k: v for k, v in t.attrs.items() if k in keep}
    for t in b.find_all('h1'): t.name = 'h2'
    md = markdownify(str(b), heading_style='ATX', bullets='-', strip=['div'])
    return md, imgs

UPPER = re.compile(r'^[A-ZА-Я0-9 ,\-–/().:!„“"]+$')
def tidy(md, kind):
    md = md.replace('\xa0', ' ').replace('\r', '')
    md = re.sub(r'[ \t]+\n', '\n', md)
    lines = [l.rstrip() for l in md.split('\n')]
    blocks = re.split(r'\n{2,}', '\n'.join(lines))
    out = []
    for bl in blocks:
        s = bl.strip()
        if not s: continue
        plain = re.sub(r'[*_\[\]]|\(mailto:[^)]*\)|\(tel:[^)]*\)', '', s).strip()
        if all(BOILER.match(x.strip()) for x in plain.split('\n') if x.strip()): continue
        # "LABEL\n\ntext" inside one block
        parts = s.split('\n', 1)
        head = re.sub(r'^\*\*(.+?)\*\*$', r'\1', parts[0].strip()).strip(' :')
        if UPPER.match(head) and 3 < len(head) < 70 and re.search(r'[А-ЯA-Z]{3}', head) and not s.startswith(('|', '#', '-', '!')):
            out.append('## ' + head[:1] + head[1:].lower())
            if len(parts) > 1 and parts[1].strip(): out.append(parts[1].strip())
            continue
        mm = re.match(r'^\*\*([^*\n]{3,110})\*\*$', s)
        if mm and not re.search(r'\d\s*(€|лв)', s):
            out.append('### ' + mm.group(1).strip()); continue
        out.append(s)
    md = '\n\n'.join(out)
    md = re.sub(r'(?m)^(#+ .+)\n\n(?=#+ )', r'\1\n\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md

PRICE = re.compile(r'(?:(\d+(?:[.,]\d+)?)\s*€\s*)?(\d+(?:[.,]\d+)?)\s*€')
def price_of(md):
    """find 'Цена ...' line near the end; returns (price, old, line)"""
    for bl in reversed(md.split('\n\n')):
        pl = re.sub(r'[*~_]', '', bl)
        if re.search(r'(?i)цена', pl) and '€' in pl and len(pl) < 160:
            nums = [float(x.replace(',', '.')) for x in re.findall(r'(\d+(?:[.,]\d+)?)\s*€', pl)]
            if not nums: continue
            if len(nums) >= 2 and ('~~' in bl or re.search(r'(?i)промоц', pl)): return min(nums[:2]), max(nums[:2]), bl
            return nums[0], None, bl
    return None, None, None

def fm(d):
    def val(v):
        if isinstance(v, (list, dict)): return json.dumps(v, ensure_ascii=False)
        if isinstance(v, (int, float)) and not isinstance(v, bool): return str(v)
        if v is None: return 'null'
        return json.dumps(str(v), ensure_ascii=False)
    return '---\n' + '\n'.join(f'{k}: {val(v)}' for k, v in d.items() if v is not None) + '\n---\n\n'

for t in ('products', 'categories', 'articles', 'pages'):
    shutil.rmtree(f'{OUT}/{t}/bg', ignore_errors=True); os.makedirs(f'{OUT}/{t}/bg')

prod_cats = {}
for cid, ids in cat_links.items():
    for i in ids: prod_cats.setdefault(i, []).append(CATS[cid])

redirects = {}
inventory = []
for k, d in sorted(docs.items(), key=lambda x: str(x[0])):
    md, imgs = clean(d)
    md = tidy(md, d['type'])
    meta = {'title': re.sub(r'\s+', ' ', d['title']).strip()}
    if d['type'] == 'products':
        if meta['title'].isupper(): meta['title'] = ' '.join(w.capitalize() for w in meta['title'].split())
        price, old, line = price_of(md)
        if line and len(re.sub(r'[*~_ ]|Промоция|цена|Цена|!|:|\.|€|[\d,]', '', line)) < 12:
            md = md.replace(line, '').strip()
        report['prices'].append((d['slug'], price, old, (line or '')[:90]))
        meta.update(legacyId=k[1], status=d['status'], categories=prod_cats.get(k[1], []), price=price, oldPrice=old)
        if re.search(r'(?i)не е налич|не е в наличност', md[:200]): meta['status'] = 'unavailable'
        if imgs:
            meta['image'] = imgs[0][0]; meta['imageAlt'] = imgs[0][1] or None
            md = re.sub(r'!\[[^\]]*\]\(' + re.escape(imgs[0][0]) + r'\)\s*', '', md, count=1).strip()
    elif d['type'] == 'articles':
        meta.update(source=d['source'], legacyId=k[1] if isinstance(k[1], int) else None, date=d['date'])
        if imgs: meta['image'] = imgs[0][0]
    else:
        meta.update(legacyId=k[1])
        if imgs and d['type'] == 'categories':
            meta['image'] = imgs[0][0]
            md = re.sub(r'\[?!\[[^\]]*\]\(' + re.escape(imgs[0][0]) + r'\)(\]\([^)]*\))?\s*', '', md, count=1).strip()
    meta['legacyUrls'] = sorted(set(d['urls']))
    md = re.sub(r'\n{3,}', '\n\n', md)
    open(f'{OUT}/{d["type"]}/bg/{d["slug"]}.md', 'w').write(fm(meta) + md + '\n')
    for u in d['urls']: redirects[u] = d['new']
    inventory.append({'old': sorted(set(d['urls'])), 'new': d['new'], 'type': d['type'], 'title': meta['title'], 'chars': len(d['text'])})

os.makedirs(f'{ROOT}/src/data', exist_ok=True)
json.dump(dict(sorted({**newurl, **redirects}.items())), open(f'{ROOT}/src/data/legacy-redirects.json', 'w'), ensure_ascii=False, indent=1)
json.dump(inventory, open(f'{ROOT}/tools/legacy-inventory.json', 'w'), ensure_ascii=False, indent=1)
json.dump(report, open(f'{CRAWL}/import-report.json', 'w'), ensure_ascii=False, indent=1)
import collections
print(collections.Counter(d['type'] for d in docs.values()), 'media', len(media_done))
print('unresolved', len(report['unresolved']), 'missing img', report['missing_img'])
