"""
GUA ZONE Scraper v3 - Only APIs that work in China
Sources: Bilibili API, Weibo search, NGA (mobile), Tieba (mobile)
"""
import re, json, time, os, sys, random
import urllib.request, urllib.parse, ssl

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def fetch_json(url, extra_headers=None):
    headers = {'User-Agent': UA, 'Accept': 'application/json', 'Referer': 'https://www.bilibili.com/'}
    if extra_headers:
        headers.update(extra_headers)
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ssl_ctx)
        return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"  [!] {url[:50]}... -> {e}")
        return None

def fetch(url, extra_headers=None):
    headers = {'User-Agent': UA}
    if extra_headers:
        headers.update(extra_headers)
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=12, context=ssl_ctx)
        data = resp.read()
        for enc in ['utf-8', 'gbk', 'gb18030']:
            try:
                return data.decode(enc)
            except:
                continue
        return data.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [!] {url[:50]}... -> {e}")
        return None

def strip_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# ====== BILIBILI ======
def scrape_bilibili():
    """Bilibili: search + ranking"""
    print("\n[Bilibili] Scraping...")
    posts = []

    # 1. Search API
    searches = [
        ('mhy', '原神'),
        ('mhy', '崩坏星穹铁道'),
        ('mhy', '绝区零'),
        ('kuro', '鸣潮'),
        ('kuro', '库洛游戏'),
        ('hgryph', '明日方舟'),
        ('hgryph', '鹰角网络'),
        ('cross', '原神 vs 鸣潮'),
        ('cross', '米哈游 鹰角'),
    ]

    for faction, keyword in searches:
        # Use Bilibili search API
        url = f'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={urllib.parse.quote(keyword)}&order=pubdate&page=1'
        data = fetch_json(url)
        if data and data.get('code') == 0:
            results = data.get('data', {}).get('result', [])
            for r in results[:5]:
                if isinstance(r, str):
                    continue
                title = re.sub(r'<[^>]+>', '', r.get('title', ''))
                bvid = r.get('bvid', '')
                play = r.get('play', 0)
                author = r.get('author', '')
                if title and len(title) > 5:
                    posts.append({
                        'faction': faction,
                        'source': 'Bilibili',
                        'title': strip_html(title),
                        'url': f'https://www.bilibili.com/video/{bvid}',
                        'excerpt': f'{author} | {play}播放',
                        'heat': int(play) if isinstance(play, int) else 0,
                        'tag': 'hot',
                        'comments': r.get('review', 0),
                        'time': r.get('pubdate_display', ''),
                    })
        time.sleep(0.3)

    # 2. Gaming ranking
    rank_data = fetch_json('https://api.bilibili.com/x/web-interface/ranking/v2?rid=168&type=all')
    if rank_data and rank_data.get('code') == 0:
        for item in rank_data.get('data', {}).get('list', [])[:30]:
            title = item.get('title', '')
            bvid = item.get('bvid', '')
            stat = item.get('stat', {})
            play = stat.get('view', 0)
            t = title.lower()
            faction = 'mhy'
            for f, kws in {
                'mhy': ['原神', '崩坏', '米哈游', '绝区零', '星穹铁道', '崩铁'],
                'kuro': ['鸣潮', '战双', '库洛'],
                'hgryph': ['明日方舟', '方舟', '鹰角', '终末地', '罗德岛', '粥'],
            }.items():
                if any(kw in t for kw in kws):
                    faction = f
                    break
            if any(kw in t for kw in ['原神', '鸣潮', '方舟', '崩坏', '库洛', '鹰角', '米哈游', '绝区零']):
                owner = item.get('owner', {}).get('name', '')
                posts.append({
                    'faction': faction,
                    'source': 'Bilibili热门',
                    'title': strip_html(title),
                    'url': f'https://www.bilibili.com/video/{bvid}',
                    'excerpt': f'{owner} | {play}播放',
                    'heat': play,
                    'tag': 'hot',
                    'comments': stat.get('reply', 0),
                })

    print(f"  [OK] {len(posts)} posts from Bilibili")
    return posts

# ====== NGA MOBILE ======
def scrape_nga():
    """NGA mobile API"""
    print("\n[NGA] Scraping...")
    posts = []

    boards = [
        ('mhy', 6924865),    # 原神
        ('mhy', 643),        # 崩坏3
        ('kuro', 5992731),   # 鸣潮
        ('hgryph', 637),     # 明日方舟
        ('cross', 609),      # 综合讨论
    ]

    for faction, fid in boards:
        url = f'https://bbs.nga.cn/thread.php?fid={fid}&page=1'
        html = fetch(url, {'Accept': 'text/html'})
        if not html:
            continue

        # Try to extract from NGA's embedded data
        for m in re.finditer(r'<a[^>]*href="(/read\.php\?\w+=\d+[^"]*)"[^>]*>([^<]{8,200})</a>', html):
            link = m.group(1)
            title = strip_html(m.group(2))
            if len(title) > 8:
                posts.append({
                    'faction': faction,
                    'source': 'NGA',
                    'title': title,
                    'url': f'https://bbs.nga.cn{link}',
                    'excerpt': '',
                    'heat': 0,
                    'tag': 'leak',
                })
        time.sleep(0.5)

    print(f"  [OK] {len(posts)} posts from NGA")
    return posts

# ====== TIEBA MOBILE ======
def scrape_tieba():
    """Tieba mobile API"""
    print("\n[Tieba] Scraping...")
    posts = []

    tiebas = [
        ('mhy', '原神'),
        ('kuro', '鸣潮'),
        ('hgryph', '明日方舟'),
        ('mhy', '米哈游'),
        ('cross', '二游'),
    ]

    for faction, name in tiebas:
        kw = urllib.parse.quote(name)
        # Use Tieba forum API
        url = f'https://tieba.baidu.com/f?kw={kw}&ie=utf-8&sort_type=1'
        html = fetch(url, {
            'Accept': 'text/html',
            'Cookie': 'BAIDUID=ABCDEF1234567890:FG=1',
        })
        if not html:
            continue

        # Extract thread titles
        for m in re.finditer(r'<a[^>]*class="j_th_tit[^"]*"[^>]*>([^<]+)</a>', html):
            title = strip_html(m.group(1))
            # Find link in nearby HTML
            ctx = html[max(0,m.start()-200):m.start()]
            link_m = re.search(r'href="(/p/\d+)"', ctx)
            link = f'https://tieba.baidu.com{link_m.group(1)}' if link_m else ''
            if len(title) > 5:
                posts.append({
                    'faction': faction,
                    'source': '贴吧',
                    'title': title,
                    'url': link,
                    'excerpt': '',
                    'heat': 0,
                    'tag': 'drama',
                })

        # Fallback pattern
        if not posts:
            for m in re.finditer(r'title="([^"]{8,200})"[^>]*href="(/p/\d+)"', html):
                title = strip_html(m.group(1))
                link = f'https://tieba.baidu.com{m.group(2)}'
                if len(title) > 5:
                    posts.append({
                        'faction': faction,
                        'source': '贴吧',
                        'title': title,
                        'url': link,
                        'excerpt': '',
                        'heat': 0,
                        'tag': 'drama',
                    })
        time.sleep(0.5)

    print(f"  [OK] {len(posts)} posts from Tieba")
    return posts

# ====== WEIBO SEARCH ======
def scrape_weibo():
    """Weibo mobile search"""
    print("\n[Weibo] Scraping...")
    posts = []

    searches = [
        ('mhy', '原神'),
        ('kuro', '鸣潮'),
        ('hgryph', '明日方舟'),
    ]

    for faction, keyword in searches:
        kw = urllib.parse.quote(keyword)
        url = f'https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{kw}'
        data = fetch_json(url)
        if data and data.get('ok') == 1:
            cards = data.get('data', {}).get('cards', [])
            for card in cards:
                mblog = card.get('mblog', {})
                if not mblog:
                    continue
                title = strip_html(mblog.get('text', ''))[:100]
                mid = mblog.get('mid', '') or mblog.get('id', '')
                user = mblog.get('user', {}).get('screen_name', '')
                if title and len(title) > 10:
                    posts.append({
                        'faction': faction,
                        'source': '微博',
                        'title': title,
                        'url': f'https://m.weibo.cn/status/{mid}',
                        'excerpt': f'@{user}',
                        'heat': mblog.get('attitudes_count', 0),
                        'tag': 'hot',
                    })
        time.sleep(0.5)

    print(f"  [OK] {len(posts)} posts from Weibo")
    return posts

# ====== TAG CLASSIFY ======
def classify_tag(title):
    t = title
    for tag, kws in {
        'drama': ['节奏','炎上','争议','退款','差评','翻车','道歉','辟谣','优化','bug','骂','撕','恶心','吃相','逼氪','割韭菜'],
        'battle': ['vs','对比','哪个好','碾压','吊打','碰瓷','抄袭','借鉴','谁更强','流水','排名','评分','回合'],
        'hot': ['破纪录','登顶','冠军','百万','爆火','出圈','获奖','销量','下载'],
        'leak': ['爆料','泄露','内鬼','前瞻','测试服','新角色','新版本','卫星','暗示'],
    }.items():
        if any(kw in t for kw in kws):
            return tag
    return 'leak'

# ====== MAIN ======
def main():
    print("=" * 40)
    print("GUA ZONE Scraper v3")
    print("=" * 40)

    all_posts = []

    # Scrape all sources
    all_posts.extend(scrape_bilibili())
    all_posts.extend(scrape_nga())
    all_posts.extend(scrape_tieba())
    all_posts.extend(scrape_weibo())

    # Deduplicate
    seen = set()
    unique = []
    for p in all_posts:
        if not p.get('title') or len(p['title']) < 5:
            continue
        key = p['title'][:25]
        if key not in seen:
            seen.add(key)
            p['tag'] = classify_tag(p.get('title', ''))
            unique.append(p)

    # Sort by heat
    unique.sort(key=lambda x: x.get('heat', 0), reverse=True)
    posts = unique[:60]

    # Stats
    factions = {}
    sources = {}
    tags = {}
    for p in posts:
        f = p.get('faction', 'cross')
        factions[f] = factions.get(f, 0) + 1
        s = p.get('source', '?')
        sources[s] = sources.get(s, 0) + 1
        t = p.get('tag', 'leak')
        tags[t] = tags.get(t, 0) + 1

    now = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'=' * 40}")
    print(f"Total: {len(posts)} posts")
    print(f"Factions: {factions}")
    print(f"Sources: {sources}")
    print(f"Tags: {tags}")
    print(f"Time: {now}")
    print(f"{'=' * 40}")

    # Save
    output = {
        'updated_at': now,
        'total': len(posts),
        'stats': {'factions': factions, 'sources': sources, 'tags': tags},
        'posts': posts,
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'posts.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved: {out_path}")
    return output

if __name__ == '__main__':
    main()
