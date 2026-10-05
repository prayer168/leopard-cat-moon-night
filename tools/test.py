# Playwright 截圖測試：筆電與平板三種尺寸，走過標題、計畫板、夜間行動、戰報、結案
from playwright.sync_api import sync_playwright
import os, subprocess, tarfile, json
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if not os.path.exists('/tmp/three-r128.js'):
    subprocess.run(['npm', 'pack', 'three@0.128.0', '--silent', '--pack-destination', '/tmp'], check=True)
    with tarfile.open('/tmp/three-0.128.0.tgz') as t:
        open('/tmp/three-r128.js', 'w').write(t.extractfile('package/build/three.min.js').read().decode())
three = open('/tmp/three-r128.js').read()
url = 'file://' + os.path.abspath(os.path.join(ROOT, 'index.html'))
out = lambda n: os.path.join(ROOT, 'shot-' + n + '.png')
sizes = [('laptop', 1366, 768, False), ('tablet-land', 1024, 768, True), ('tablet-port', 768, 1024, True)]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
    for name, w, h, touch in sizes:
        ctx = b.new_context(viewport={'width': w, 'height': h}, has_touch=touch, is_mobile=touch)
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.route('**/three.min.js', lambda r: r.fulfill(body=three, content_type='application/javascript'))
        pg.route('https://fonts.**', lambda r: r.abort())
        pg.goto(url); pg.wait_for_timeout(1200)
        pg.screenshot(path=out(name + '-1title'))
        pg.click('text=開始行動'); pg.wait_for_timeout(500)
        pg.click('text=凌晨 2 點'); pg.wait_for_timeout(200)
        pg.screenshot(path=out(name + '-2plan'), full_page=False)
        ov = pg.evaluate("document.getElementById('board').scrollWidth > document.getElementById('board').clientWidth + 1")
        pg.click('text=今晚出動！'); pg.wait_for_timeout(2500)
        pg.screenshot(path=out(name + '-3run'))
        pg.click('#btnPause'); pg.wait_for_timeout(200)
        pg.click('button:has-text("放棄今晚")'); pg.wait_for_timeout(300)
        pg.screenshot(path=out(name + '-4report'))
        pg.click('text=回到計畫板'); pg.wait_for_timeout(400)
        for i in range(3):
            pg.click('text=躲起來，睡一晚'); pg.wait_for_timeout(250)
        pg.evaluate("document.getElementById('board').scrollTop = 99999")
        pg.screenshot(path=out(name + '-5plan-later'))
        # 結案畫面
        state = {'c': {'startLD': 12, 'night': 29, 'stock': 7, 'hungry': 0, 'raids': 6, 'journal': [{'ld': ((11 + i) % 30) + 1, 'raided': i % 4 == 0, 'ok': True, 'got': 5, 'h0': 19} for i in range(29)], 'notes': ['hello', 'mice'], 'over': False}, 'p': {'sound': False}}
        pg.evaluate("s => localStorage.setItem('shihu-heist-v2', s)", json.dumps(state))
        pg.reload(); pg.wait_for_timeout(1000)
        pg.click('text=繼續行動'); pg.wait_for_timeout(300)
        pg.click('text=躲起來，睡一晚'); pg.wait_for_timeout(400)
        pg.screenshot(path=out(name + '-6final'))
        print(name, 'board overflow:', ov, 'errors:', errs[:5])
        ctx.close()
    b.close()
