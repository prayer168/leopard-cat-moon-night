from playwright.sync_api import sync_playwright
import os, subprocess, tarfile, io
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# 測試時從 npm 取得 Three.js r128，不依賴外部 CDN
if not os.path.exists('/tmp/three-r128.js'):
    subprocess.run(['npm','pack','three@0.128.0','--silent','--pack-destination','/tmp'], check=True)
    with tarfile.open('/tmp/three-0.128.0.tgz') as t:
        open('/tmp/three-r128.js','w').write(t.extractfile('package/build/three.min.js').read().decode())
three = open('/tmp/three-r128.js').read()
url = 'file://' + os.path.abspath(os.path.join(ROOT,'index.html'))
sizes = [('laptop',1366,768,False),('tablet-land',1024,768,True),('tablet-port',768,1024,True)]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    for name,w,h,touch in sizes:
        ctx = b.new_context(viewport={'width':w,'height':h}, has_touch=touch, is_mobile=touch)
        pg = ctx.new_page()
        errs=[]
        pg.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.route('**/three.min.js', lambda r: r.fulfill(body=three, content_type='application/javascript'))
        pg.route('https://fonts.**', lambda r: r.abort())
        pg.goto(url); pg.wait_for_timeout(1500)
        pg.screenshot(path=os.path.join(ROOT,'shot-%s-title.png'%name))
        # overflow check
        ov = pg.evaluate("document.querySelector('#panel').scrollWidth > document.querySelector('#panel').clientWidth+1")
        pg.click('text=開始冒險'); pg.wait_for_timeout(300)
        pg.click('text=出發'); pg.wait_for_timeout(1500)
        pg.screenshot(path=os.path.join(ROOT,'shot-%s-sneak.png'%name))
        # 進入第 4 關月曆
        pg.evaluate("localStorage.setItem('shihu-moon-progress', JSON.stringify({done:{1:true,2:true,3:true}}))")
        pg.reload(); pg.wait_for_timeout(1200)
        pg.click('text=上弦？下弦？'); pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(ROOT,'shot-%s-cal.png'%name))
        calov = pg.evaluate("document.querySelector('#panel').scrollWidth > document.querySelector('#panel').clientWidth+1")
        pg.click('.cal button >> nth=10'); pg.click('text=就是這一晚，出發！'); pg.wait_for_timeout(1200)
        pg.screenshot(path=os.path.join(ROOT,'shot-%s-sneak4.png'%name))
        print(name, 'overflow', ov, calov, 'errors', errs[:5])
        ctx.close()
    b.close()
