"""
GUA ZONE Real Scraper - Uses web_fetch compatible endpoints only
Runs via cron, pushes real data to GitHub
"""
import json, time, os, sys, re
import urllib.request, urllib.parse, ssl

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json', 'Referer': 'https://www.bilibili.com/'})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"  [!] {e}")
        return None

def get_html(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = resp.read()
        for enc in ['utf-8', 'gbk', 'gb18030']:
            try: return data.decode(enc)
            except: pass
        return data.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [!] {e}")
        return None

def strip_tags(t):
    return re.sub(r'<[^>]+>', '', t).strip()

def classify(title):
    t = title.lower()
    for f, kws in {
        'mhy': ['原神','崩坏','米哈游','绝区零','星穹铁道','崩铁','genshin','honkai','zzz'],
        'kuro': ['鸣潮','战双','库洛','wuthering','punishing'],
        'hgryph': ['明日方舟','方舟','鹰角','终末地','arknights','罗德岛','endfield'],
    }.items():
        if any(kw in t for kw in kws):
            return f
    return 'mhy'

def classify_tag(title):
    t = title
    for tag, kws in {
        'battle': ['vs','对比','碾压','吊打','碰瓷','抄袭','借鉴','谁更强','流水','排名','哪个好','回合','互撕'],
        'drama': ['节奏','炎上','争议','退款','差评','翻车','道歉','辟谣','骂','撕','恶心','吃相','逼氪','割韭菜','爆吧','对线'],
        'hot': ['破纪录','登顶','冠军','百万','爆火','出圈','获奖','销量','下载','流水'],
        'leak': ['爆料','泄露','内鬼','前瞻','测试服','新角色','新版本','卫星','暗示','挖掘'],
    }.items():
        if any(kw in t for kw in kws):
            return tag
    return 'leak'

def main():
    print("=" * 40)
    print("GUA ZONE Scraper - Real Data")
    print("=" * 40)
    all_posts = []

    # === 1. Bilibili Gaming Rankings ===
    print("\n[Bilibili] Gaming rankings...")
    for rid in [168, 4]:  # 国产原创, 单机游戏
        data = get_json(f'https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all')
        if data and data.get('code') == 0:
            for item in data.get('data', {}).get('list', [])[:50]:
                title = item.get('title', '')
                faction = classify(title)
                if faction == 'mhy' and not any(kw in title.lower() for kw in ['原神','崩坏','米哈游','绝区零','星穹','鸣潮','方舟','鹰角','库洛']):
                    continue  # skip non-gaming content
                bvid = item.get('bvid', '')
                stat = item.get('stat', {})
                owner = item.get('owner', {}).get('name', '')
                play = stat.get('view', 0)
                if title:
                    all_posts.append({
                        'faction': faction,
                        'source': 'Bilibili',
                        'title': strip_tags(title),
                        'url': f'https://www.bilibili.com/video/{bvid}',
                        'excerpt': f'{owner} | {play}播放 | {stat.get("danmaku",0)}弹幕',
                        'heat': play,
                        'tag': 'hot',
                        'comments': stat.get('reply', 0),
                    })
            print(f"  rid={rid}: {len(data.get('data',{}).get('list',[]))} items")
        time.sleep(0.5)

    # === 2. Bilibili trending (all categories for gaming content) ===
    print("\n[Bilibili] Overall trending...")
    data = get_json('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all')
    if data and data.get('code') == 0:
        for item in data.get('data', {}).get('list', [])[:100]:
            title = item.get('title', '')
            if any(kw in title.lower() for kw in ['原神','崩坏','米哈游','绝区零','鸣潮','方舟','鹰角','库洛','战双','二游','手游','抽卡','gacha']):
                bvid = item.get('bvid', '')
                stat = item.get('stat', {})
                owner = item.get('owner', {}).get('name', '')
                all_posts.append({
                    'faction': classify(title),
                    'source': 'Bilibili',
                    'title': strip_tags(title),
                    'url': f'https://www.bilibili.com/video/{bvid}',
                    'excerpt': f'{owner} | {stat.get("view",0)}播放',
                    'heat': stat.get('view', 0),
                    'tag': 'hot',
                    'comments': stat.get('reply', 0),
                })
        print(f"  Found gaming content in trending")

    # === 3. NGA (try different URLs) ===
    print("\n[NGA] Attempting scrape...")
    nga_urls = [
        ('mhy', 'https://bbs.nga.cn/thread.php?fid=-6924865'),
        ('kuro', 'https://bbs.nga.cn/thread.php?fid=-5992731'),
        ('hgryph', 'https://bbs.nga.cn/thread.php?fid=637'),
        ('cross', 'https://bbs.nga.cn/thread.php?fid=-1'),
    ]
    for faction, url in nga_urls:
        html = get_html(url)
        if html and len(html) > 1000 and 'Error' not in html[:200]:
            for m in re.finditer(r'title="([^"]{10,200})"', html):
                title = strip_tags(m.group(1))
                if len(title) > 8:
                    href_m = re.search(r'href="(/read\.php\?\w+=\d+)"', html[max(0,m.start()-300):m.start()])
                    link = f'https://bbs.nga.cn{href_m.group(1)}' if href_m else url
                    all_posts.append({'faction': faction, 'source': 'NGA', 'title': title, 'url': link, 'excerpt': '', 'heat': 0, 'tag': classify_tag(title)})
            print(f"  {faction}: scraped")
        else:
            print(f"  {faction}: blocked")
        time.sleep(1)

    # === 4. Tieba (try mobile) ===
    print("\n[Tieba] Attempting scrape...")
    for faction, name in [('mhy','原神'),('kuro','鸣潮'),('hgryph','明日方舟'),('mhy','米哈游'),('cross','二游')]:
        html = get_html(f'https://tieba.baidu.com/f?kw={urllib.parse.quote(name)}&ie=utf-8&sort_type=1')
        if html and len(html) > 2000:
            for m in re.finditer(r'title="([^"]{8,200})"', html):
                title = strip_tags(m.group(1))
                if len(title) > 8:
                    all_posts.append({'faction': faction, 'source': '贴吧', 'title': title, 'url': '', 'excerpt': f'{name}吧', 'heat': 0, 'tag': classify_tag(title)})
            print(f"  {name}: scraped")
        else:
            print(f"  {name}: blocked")
        time.sleep(1)

    # === 5. Weibo mobile search ===
    print("\n[Weibo] Attempting scrape...")
    for faction, keyword in [('mhy','原神'),('kuro','鸣潮'),('hgryph','明日方舟')]:
        url = f'https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{urllib.parse.quote(keyword)}'
        data = get_json(url)
        if data and data.get('ok') == 1:
            for card in data.get('data', {}).get('cards', [])[:5]:
                mblog = card.get('mblog', {})
                if not mblog: continue
                title = strip_tags(mblog.get('text', ''))[:100]
                mid = mblog.get('mid', '') or mblog.get('id', '')
                user = mblog.get('user', {}).get('screen_name', '')
                if len(title) > 10:
                    all_posts.append({'faction': faction, 'source': '微博', 'title': title, 'url': f'https://m.weibo.cn/status/{mid}', 'excerpt': f'@{user}', 'heat': mblog.get('attitudes_count',0), 'tag': 'hot'})
            print(f"  {keyword}: scraped")
        else:
            print(f"  {keyword}: blocked")
        time.sleep(0.5)

    # === Deduplicate & tag ===
    seen = set()
    unique = []
    for p in all_posts:
        if not p.get('title') or len(p['title']) < 5: continue
        key = p['title'][:20]
        if key not in seen:
            seen.add(key)
            p['tag'] = classify_tag(p.get('title', ''))
            unique.append(p)

    unique.sort(key=lambda x: x.get('heat', 0), reverse=True)
    posts = unique[:80]

    factions = {}
    sources = {}
    for p in posts:
        factions[p.get('faction','cross')] = factions.get(p.get('faction','cross'),0)+1
        sources[p.get('source','?')] = sources.get(p.get('source','?'),0)+1

    now = time.strftime('%Y-%m-%d %H:%M:%S')
    output = {
        'updated_at': now,
        'total': len(posts),
        'stats': {'factions': factions, 'sources': sources},
        'posts': posts,
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'posts.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*40}")
    print(f"Total: {len(posts)}")
    print(f"Factions: {factions}")
    print(f"Sources: {sources}")
    print(f"Time: {now}")
    print(f"{'='*40}")

    return output

if __name__ == '__main__':
    main()
