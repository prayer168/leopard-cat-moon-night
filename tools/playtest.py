# 石虎月夜行 自動試玩測試
# 用 Playwright 開瀏覽器，由程式自己操控石虎實際玩遊戲，並錄影每一個情境。
# 用法：python3 tools/playtest.py [情境編號...]   例如 python3 tools/playtest.py 1 2 3
import os, sys, json, math, time, subprocess, tarfile
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'test-output')
os.makedirs(os.path.join(OUT, 'video'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'shots'), exist_ok=True)
if not os.path.exists('/tmp/three-r128.js'):
    subprocess.run(['npm', 'pack', 'three@0.128.0', '--silent', '--pack-destination', '/tmp'], check=True)
    with tarfile.open('/tmp/three-0.128.0.tgz') as t:
        open('/tmp/three-r128.js', 'w').write(t.extractfile('package/build/three.min.js').read().decode())
THREE = open('/tmp/three-r128.js').read()
URL = 'file://' + os.path.join(ROOT, 'index.html') + '#test'
RESULTS = []


def check(scn, name, ok, detail=''):
    RESULTS.append({'scenario': scn, 'check': name, 'ok': bool(ok), 'detail': str(detail)})
    print(('  PASS ' if ok else '  FAIL ') + name + ('  (' + str(detail) + ')' if detail else ''), flush=True)


def caption(pg, text):
    pg.evaluate("""t => { var c = document.getElementById('testcap');
      if (!c) { c = document.createElement('div'); c.id = 'testcap';
        c.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:9999;background:rgba(20,16,12,.88);color:#ffe14d;font:700 18px/1.4 "Noto Sans CJK TC",sans-serif;padding:8px 14px;border-radius:6px;max-width:70%;pointer-events:none';
        document.body.appendChild(c); }
      c.textContent = 'AI 測試中：' + t; }""", text)


def open_page(p, name, w=960, h=540, touch=False, save=None):
    ctx = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader']).new_context(
        viewport={'width': w, 'height': h}, has_touch=touch, is_mobile=touch,
        record_video_dir=os.path.join(OUT, 'video', name), record_video_size={'width': w, 'height': h})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    pg.route('https://fonts.**', lambda r: r.abort())
    if save is not None:
        pg.add_init_script('try{if(!sessionStorage.getItem("seeded")){localStorage.setItem("shihu-heist-v2",' + json.dumps(json.dumps(save)) + ');sessionStorage.setItem("seeded","1");}}catch(e){}')
    pg.goto(URL)
    pg.wait_for_timeout(1200)
    return ctx, pg, errs


def st(pg):
    return pg.evaluate('window.__shihu.state()')


def world(pg):
    return pg.evaluate('window.__shihu.world()')


KEYS = {'L': 'ArrowLeft', 'R': 'ArrowRight', 'U': 'ArrowUp', 'D': 'ArrowDown'}


class Pad:
    def __init__(self, pg):
        self.pg, self.down = pg, set()

    def set(self, want):
        for k in list(self.down):
            if k not in want:
                self.pg.keyboard.up(KEYS[k]); self.down.discard(k)
        for k in want:
            if k not in self.down:
                self.pg.keyboard.down(KEYS[k]); self.down.add(k)

    def steer(self, vx, vz):
        n = math.hypot(vx, vz)
        want = set()
        if n > 0.01:
            vx, vz = vx / n, vz / n
            if vx < -0.38: want.add('L')
            if vx > 0.38: want.add('R')
            if vz < -0.38: want.add('U')
            if vz > 0.38: want.add('D')
        self.set(want)


def danger_vec(w, p, margin=2.5):
    # 遠離農夫的手電筒扇形與月光圈
    ax = az = 0.0
    for f in w['farmers']:
        dx, dz = p['x'] - f['x'], p['z'] - f['z']
        d = math.hypot(dx, dz) + 1e-6
        reach = max(6.5, f['visR']) + margin
        if d < reach:
            k = (reach - d) / reach
            ax += dx / d * k * 3.0
            az += dz / d * k * 3.0
    return ax, az


def bot_run(pg, mode='win', max_sec=150, want_mice=99, log=None):
    """mode: win = 抓田鼠後回家；caught = 故意走向農夫；idle = 原地不動；wander = 在田裡兜圈"""
    pad = Pad(pg)
    t0 = time.time()
    last = None; last_move_t = time.time(); side = 1
    while time.time() - t0 < max_sec:
        s = st(pg)
        if not s['run'] or s['run']['ended']:
            break
        w = world(pg); p = w['p']; r = s['run']
        if log is not None: log.append(r)
        if mode == 'idle':
            pad.set(set())
        elif mode == 'caught':
            f = min(w['farmers'], key=lambda f: math.hypot(f['x'] - p['x'], f['z'] - p['z']))
            pad.steer(f['x'] - p['x'], f['z'] - p['z'])
        else:
            left_h = r['h0'] + 3 - r['hour']
            todo = [m for m in w['mice'] if not m['got']]
            go_home = r['got'] >= want_mice or not todo or left_h < 1.0
            if mode == 'wander' and not go_home:
                tx, tz = (8 * math.cos(time.time() * 0.6), 9 + 2 * math.sin(time.time() * 0.6))
            elif go_home:
                tx, tz = 0.5, 18
            else:
                m = min(todo, key=lambda m: math.hypot(m['x'] - p['x'], m['z'] - p['z']))
                tx, tz = m['x'], m['z']
            vx, vz = tx - p['x'], tz - p['z']
            n = math.hypot(vx, vz) + 1e-6
            vx, vz = vx / n, vz / n
            ax, az = danger_vec(w, p, 1.5 if go_home else 2.5)
            vx += ax; vz += az
            # 卡住就往旁邊繞
            if last and math.hypot(p['x'] - last[0], p['z'] - last[1]) > 0.15:
                last_move_t = time.time()
            if time.time() - last_move_t > 1.2:
                vx, vz = -vz * side, vx * side
                if time.time() - last_move_t > 2.4:
                    side = -side; last_move_t = time.time()
            last = (p['x'], p['z'])
            pad.steer(vx, vz)
        pg.wait_for_timeout(70)
    pad.set(set())
    return st(pg)


def board_click(pg, text):
    pg.locator('button', has_text=text).first.click()
    pg.wait_for_timeout(350)


def depart(pg, label):
    board_click(pg, label)
    board_click(pg, '今晚出動')
    pg.wait_for_timeout(600)


def finish(scn, ctx, pg, errs):
    check(scn, '沒有 JavaScript 錯誤', not errs, '; '.join(errs[:3]))
    vid = pg.video.path() if pg.video else None
    ctx.close(); ctx.browser.close()
    return vid


def shot(pg, name):
    pg.screenshot(path=os.path.join(OUT, 'shots', name + '.png'))


# ---------------- 情境 ----------------
def s1(p):
    scn = '1 標題與計畫板'
    ctx, pg, errs = open_page(p, 's1')
    caption(pg, '標題畫面，確認檔案封面與石虎照片')
    check(scn, '標題文字正確', pg.locator('h1').first.inner_text().replace('\n', '') == '石虎月夜行')
    check(scn, '石虎照片已產生', pg.evaluate("document.querySelector('.suspect img').src.indexOf('data:image') === 0"))
    pg.wait_for_timeout(800); shot(pg, 's1-title')
    caption(pg, '按「開始行動」，進入第 1 晚的作戰計畫板')
    board_click(pg, '開始行動')
    s = st(pg)
    check(scn, '第 1 晚是農曆十二', s['ld'] == 12 and s['night'] == 0, s['ld'])
    check(scn, '月相日記有 30 格', pg.locator('.jgrid .slot').count() == 30)
    check(scn, '還沒選時間前，出動按鈕不能按', pg.locator('.go').is_disabled())
    caption(pg, '選「凌晨 2 點」，時間軸出現紅框，出動按鈕亮起')
    board_click(pg, '凌晨 2 點')
    check(scn, '時間軸出現行動紅框', pg.locator('.tl-win').count() == 1)
    check(scn, '出動按鈕可以按了', not pg.locator('.go').is_disabled())
    check(scn, '貓頭鷹情報出現', pg.locator('.sticky').count() >= 1)
    shot(pg, 's1-plan')
    caption(pg, '打開情報簿，拖曳祕密圖裡的月亮')
    board_click(pg, '情報簿')
    oc = pg.locator('#orbitCanvas').bounding_box()
    cx, cy = oc['x'] + oc['width'] / 2, oc['y'] + oc['height'] / 2
    R = oc['width'] * 0.35
    pg.mouse.move(cx + R, cy); pg.mouse.down()
    for i in range(0, 91, 5):
        a = math.radians(i); pg.mouse.move(cx + R * math.cos(a), cy - R * math.sin(a)); pg.wait_for_timeout(30)
    pg.mouse.up(); pg.wait_for_timeout(200)
    name = pg.locator('#sheet .helper-top div div').nth(1).inner_text() if False else pg.evaluate("Array.prototype.slice.call(document.querySelectorAll('#sheet div')).filter(function(d){return d.style.fontSize==='26px'})[0].textContent")
    check(scn, '月亮拖到太陽光的 90 度位置，顯示上弦月', name == '上弦月', name)
    pg.locator('.phase-cell', has_text='滿月').first.click(); pg.wait_for_timeout(200)
    name2 = pg.evaluate("Array.prototype.slice.call(document.querySelectorAll('#sheet div')).filter(function(d){return d.style.fontSize==='26px'})[0].textContent")
    check(scn, '點「滿月」卡片，祕密圖切到滿月', name2 == '滿月', name2)
    shot(pg, 's1-notebook')
    board_click(pg, '收起情報簿')
    caption(pg, '切換聲音開關')
    btn = pg.locator('.tag-btn', has_text='聲音')
    before = btn.inner_text(); btn.click(); pg.wait_for_timeout(200)
    check(scn, '聲音按鈕可以切換', btn.inner_text() != before, before + ' > ' + btn.inner_text())
    return finish(scn, ctx, pg, errs)


def s2(p):
    scn = '2 新月夜出動得手'
    save = {'c': {'startLD': 1, 'night': 0, 'stock': 5, 'hungry': 0, 'raids': 0, 'journal': [], 'notes': [], 'over': False}, 'p': {'sound': False}}
    ctx, pg, errs = open_page(p, 's2', save=save)
    board_click(pg, '繼續行動')
    check(scn, '新月：拍立得寫「看不到月亮」', '看不到月亮' in pg.locator('.polaroid .cap').inner_text())
    caption(pg, '新月晚上 7 點出動。AI 自己操控石虎：抓田鼠、避開手電筒、回竹林')
    depart(pg, '晚上 7 點')
    check(scn, '新月夜田鼠最多（8 隻）', st(pg)['run']['total'] == 8, st(pg)['run']['total'])
    s0 = st(pg)
    check(scn, '進入 3D 行動畫面', s0['mode'] == 'run' and s0['run'] is not None)
    log = []
    s = bot_run(pg, 'win', max_sec=230, want_mice=4, log=log)
    check(scn, '新月整晚月光都是 0', all(x['curB'] == 0 for x in log))
    rep = pg.locator('.big-stamp').first.inner_text() if pg.locator('.big-stamp').count() else ''
    got = log[-1]['got'] if log else 0
    check(scn, 'AI 抓到田鼠並平安回到竹林（得手）', rep == '得手', '印章：' + rep + '，抓到 ' + str(got) + ' 隻')
    shot(pg, 's2-report')
    caption(pg, '戰報出來了，回到計畫板確認存糧與月相日記')
    pg.wait_for_timeout(900)
    board_click(pg, '回到計畫板')
    s2_ = st(pg)
    check(scn, '存糧 = 5 + 帶回的田鼠 - 1', s2_['stock'] == 5 + s2_['journal'][0]['got'] - 1, s2_['stock'])
    check(scn, '進入第 2 晚（農曆初二）', s2_['night'] == 1 and s2_['ld'] == 2, s2_['ld'])
    check(scn, '月相日記第 1 格蓋上得手印章', pg.locator('.jgrid .slot').first.locator('.mark.ok').count() == 1)
    pg.wait_for_timeout(800); shot(pg, 's2-plan-after')
    return finish(scn, ctx, pg, errs)


def s3(p):
    scn = '3 故意被發現（滿月附近的亮夜）'
    save = {'c': {'startLD': 12, 'night': 3, 'stock': 6, 'hungry': 0, 'raids': 1, 'journal': [{'ld': 12, 'raided': False}, {'ld': 13, 'raided': False}, {'ld': 14, 'raided': False}], 'notes': ['hello', 'gib', 'mice'], 'over': False}, 'p': {'sound': False}}
    ctx, pg, errs = open_page(p, 's3', save=save)
    board_click(pg, '繼續行動')
    s = st(pg)
    check(scn, '今晚是農曆十五（滿月）', s['ld'] == 15, s['ld'])
    caption(pg, '滿月晚上 7 點出動。AI 故意走向農夫，測試「被發現」')
    depart(pg, '晚上 7 點')
    r0 = st(pg)['run']
    check(scn, '滿月夜晚月光很亮（農夫看得遠）', r0['curB'] > 0.5, 'b=' + str(round(r0['curB'], 2)))
    s = bot_run(pg, 'caught', max_sec=60)
    rep = pg.locator('.big-stamp').first.inner_text() if pg.locator('.big-stamp').count() else ''
    check(scn, '被發現並出現戰報', rep == '被發現', rep)
    why = pg.locator('.why').first.inner_text() if pg.locator('.why').count() else ''
    check(scn, '戰報說明今晚是滿月與被發現原因', '滿月' in why and ('月光' in why or '手電筒' in why), why[:60])
    shot(pg, 's3-caught')
    pg.wait_for_timeout(1200)
    return finish(scn, ctx, pg, errs)


def s4(p):
    scn = '4 時間到，與站在起點不動'
    ctx, pg, errs = open_page(p, 's4')
    board_click(pg, '開始行動')
    caption(pg, '出動後先站在竹林起點不動 8 秒：不應該直接結束')
    depart(pg, '晚上 11 點')
    pg.wait_for_timeout(8000)
    s = st(pg)
    check(scn, '剛出發站著不動，不會自動結束行動', s['mode'] == 'run' and not s['run']['ended'], s['mode'])
    if s['mode'] == 'run' and not s['run']['ended']:
        caption(pg, '走進田裡躲進草叢，把時間快轉到 3 小時用完')
        pad = Pad(pg); pad.set({'U'}); pg.wait_for_timeout(2200); pad.set(set())
        pg.evaluate('window.__shihu.ff(73)'); pg.wait_for_timeout(1500)
    rep = pg.locator('.big-stamp').first.inner_text() if pg.locator('.big-stamp').count() else ''
    check(scn, '3 小時用完出現「時間到」', rep == '時間到', rep)
    shot(pg, 's4-timeout')
    return finish(scn, ctx, pg, errs)


def s5(p):
    scn = '5 循氣味追蹤的狗與水圳'
    save = {'c': {'startLD': 26, 'night': 0, 'stock': 5, 'hungry': 0, 'raids': 2, 'journal': [], 'notes': ['hello'], 'over': False}, 'p': {'sound': False}}
    ctx, pg, errs = open_page(p, 's5', save=save)
    board_click(pg, '繼續行動')
    check(scn, '計畫板顯示田裡有狗', pg.locator('.threat svg').count() >= 2)
    caption(pg, '出動第 3 次起有狗。AI 在田裡兜圈留下氣味，等狗醒來')
    depart(pg, '晚上 7 点'.replace('点', '點'))
    log = []
    t0 = time.time()
    woke = False
    pad = Pad(pg)
    while time.time() - t0 < 60:
        s = st(pg); w = world(pg); p_ = w['p']
        if s['run']['ended']: break
        d = s['run']['dog']
        if d and d['st'] == 'track': woke = True; break
        tx, tz = 6 * math.cos(time.time() * 0.5) + 6, 9 + 2 * math.sin(time.time() * 0.5)
        ax, az = danger_vec(w, p_, 1.0)
        pad.steer(tx - p_['x'] + ax, tz - p_['z'] + az)
        pg.wait_for_timeout(80)
    check(scn, '狗聞到氣味醒來開始追', woke)
    caption(pg, '狗追來了！AI 衝進水圳（不走橋），讓氣味斷掉')
    lost = False
    t0 = time.time()
    w = world(pg)
    fx = sum(f['x'] for f in w['farmers']) / max(1, len(w['farmers']))
    tx, tz = (-9 if fx > 0 else 9), -5
    while time.time() - t0 < 40 and woke:
        s = st(pg); w = world(pg); p_ = w['p']
        if s['run']['ended']: break
        d = s['run']['dog']
        if d and d['st'] in ('lost', 'home'): lost = True; break
        ax, az = danger_vec(w, p_, 0.0)
        pad.steer(tx - p_['x'] + ax * 0.15, tz - p_['z'] + az * 0.15)
        pg.wait_for_timeout(80)
    pad.set(set())
    s = st(pg)
    check(scn, '走進水圳後狗失去氣味（出現問號）', lost, (s['run']['dog'], 'ended', s['run']['ended'], s['run']['cause'], 'inWater', s['run']['inWater'], 'p', world(pg)['p']) if s['run'] else '')
    check(scn, '水圳裡的氣味點被清除', s['run'] and s['run']['trail'] <= 3, s['run']['trail'] if s['run'] else '')
    pg.wait_for_timeout(1500); shot(pg, 's5-ditch')
    caption(pg, '甩掉狗之後回竹林')
    bot_run(pg, 'win', max_sec=80, want_mice=1)
    return finish(scn, ctx, pg, errs)


def s6(p):
    scn = '6 下弦月：月亮在行動中途升起'
    save = {'c': {'startLD': 22, 'night': 0, 'stock': 5, 'hungry': 0, 'raids': 0, 'journal': [], 'notes': [], 'over': False}, 'p': {'sound': False}}
    ctx, pg, errs = open_page(p, 's6', save=save)
    board_click(pg, '繼續行動')
    leg = pg.locator('.tl-legend').inner_text()
    check(scn, '時間軸說明下弦月約半夜升起', '晚上 11 點' in leg or '半夜 12 點' in leg, leg)
    caption(pg, '農曆廿二（下弦月）晚上 11 點出門：等等月亮會升起，田裡會突然變亮')
    depart(pg, '晚上 11 點')
    r = st(pg)['run']
    check(scn, '出門時月亮還沒升起，天很暗', r['lastUp'] is False and r['curB'] == 0, 'b=' + str(r['curB']))
    log = []
    s = bot_run(pg, 'win', max_sec=150, want_mice=3, log=log)
    ups = [x['lastUp'] for x in log]
    rose = False in ups and True in ups and ups.index(True) > ups.index(False)
    check(scn, '月亮在行動中途升起，畫面變亮', rose, '最高亮度 ' + str(round(max([x['curB'] for x in log] or [0]), 2)))
    rep = pg.locator('.big-stamp').first.inner_text() if pg.locator('.big-stamp').count() else ''
    why = pg.locator('.why').first.inner_text() if pg.locator('.why').count() else ''
    check(scn, '戰報說明「出門時月亮還沒升起，後來才升上來」', '後來才升上來' in why, why[:70])
    shot(pg, 's6-report')
    return finish(scn, ctx, pg, errs)


def s7(p):
    scn = '7 一直睡覺會餓肚子失敗'
    ctx, pg, errs = open_page(p, 's7')
    board_click(pg, '開始行動')
    caption(pg, '一直按「躲起來，睡一晚」，存糧會吃光')
    n = 0
    while n < 12 and pg.locator('button', has_text='躲起來，睡一晚').count() and pg.locator('#sheetLayer').is_hidden():
        board_click(pg, '躲起來，睡一晚'); n += 1
    s = st(pg)
    check(scn, '睡 8 晚後餓 3 次，出現「行動失敗」', n == 8 and pg.locator('.big-stamp', has_text='行動失敗').count() == 1, '睡了 ' + str(n) + ' 晚，餓肚子 ' + str(s['hungry']) + ' 次')
    pg.wait_for_timeout(800); shot(pg, 's7-fail')
    return finish(scn, ctx, pg, errs)


def s8(p):
    scn = '8 撐過 30 晚結案與月相日記'
    jr = [{'ld': ((11 + i) % 30) + 1, 'raided': i % 5 == 0, 'ok': True, 'got': 5, 'h0': 19} for i in range(29)]
    save = {'c': {'startLD': 12, 'night': 29, 'stock': 8, 'hungry': 0, 'raids': 6, 'journal': jr, 'notes': ['hello', 'mice', 'cycle'], 'over': False}, 'p': {'sound': False}}
    ctx, pg, errs = open_page(p, 's8', save=save)
    board_click(pg, '繼續行動')
    check(scn, '第 30 晚的紅線串起出動過的夜晚', pg.locator('#jstring polyline').count() == 1)
    caption(pg, '第 30 晚，睡一晚就結案，檢查月相日記')
    board_click(pg, '躲起來，睡一晚')
    check(scn, '出現結案印章', pg.locator('.big-stamp', has_text='結案').count() == 1)
    names = pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.final-grid b'), function(b){return b.textContent})")
    expect = pg.evaluate("(function(){var s=window.__shihu.sci,o=[];for(var n=0;n<30;n++){var d=((11+n)%30)+1;o.push(s.PH[s.phaseIdx(d)].n);}return o;})()")
    check(scn, '月相日記 30 格的月相名稱都正確', names == expect, ' > '.join(names[:3]) + ' ... ' + ' > '.join(names[-3:]))
    order = []
    for x in names:
        if not order or order[-1] != x: order.append(x)
    check(scn, '月相順序：盈凸、滿月、虧凸、下弦、殘月、新月、眉形、上弦、盈凸', order == ['盈凸月', '滿月', '虧凸月', '下弦月', '殘月', '新月', '眉形月', '上弦月', '盈凸月'], ' > '.join(order))
    pg.wait_for_timeout(1000); shot(pg, 's8-final')
    return finish(scn, ctx, pg, errs)


def s9(p):
    scn = '9 科學正確性'
    ctx, pg, errs = open_page(p, 's9')
    caption(pg, '檢查月相計算、月出時間與北半球月亮亮面方向')
    sci = pg.evaluate("""(function(){var s=window.__shihu.sci,r={};
      r.names=[1,8,15,22,25,3].map(function(d){return s.PH[s.phaseIdx(d)].n});
      r.rise=[1,8,15,22].map(function(d){return Math.round(s.riseHour(d)*10)/10});
      r.newDark=[19,22,25,28].every(function(h){return s.brightAt(1,h)===0});
      r.firstAfterMid=s.moonAt(8,26).up; r.firstEvening=s.moonAt(8,20).up;
      r.lastEvening=s.moonAt(22,20).up; r.lastAfterMid=s.moonAt(22,26).up;
      r.fullAllNight=[19,22,25,28].every(function(h){return s.moonAt(15,h).up});
      function side(angle){var c=document.createElement('canvas');c.width=100;c.height=100;var x=c.getContext('2d');s.drawMoon(x,50,50,40,angle,{});
        var L=x.getImageData(20,50,1,1).data[0],R=x.getImageData(80,50,1,1).data[0];return L>R?'左亮':(R>L?'右亮':'一樣');}
      r.sides=[45,90,135,225,270,315].map(side);
      return r;})()""")
    check(scn, '農曆對應月相：初一新月、初八上弦、十五滿月、廿二下弦、廿五殘月、初三眉形', sci['names'] == ['新月', '上弦月', '滿月', '下弦月', '殘月', '眉形月'], sci['names'])
    check(scn, '月出時間：新月 6 點、上弦約中午、滿月約傍晚 6 點、下弦約半夜', abs(sci['rise'][0] - 6) < 0.1 and abs(sci['rise'][1] - 12) < 0.6 and abs(sci['rise'][2] - 18) < 0.8 and abs(sci['rise'][3] - 23.5) < 0.8, sci['rise'])
    check(scn, '新月整晚月光為 0', sci['newDark'])
    check(scn, '上弦月：傍晚在天上、後半夜已下山', sci['firstEvening'] and not sci['firstAfterMid'])
    check(scn, '下弦月：傍晚還沒升起、後半夜在天上', (not sci['lastEvening']) and sci['lastAfterMid'])
    check(scn, '滿月整晚都在天上', sci['fullAllNight'])
    check(scn, '漸盈（眉形、上弦、盈凸）右邊亮；漸虧（虧凸、下弦、殘月）左邊亮', sci['sides'] == ['右亮', '右亮', '右亮', '左亮', '左亮', '左亮'], sci['sides'])
    pg.wait_for_timeout(500)
    return finish(scn, ctx, pg, errs)


def s10(p):
    scn = '10 平板觸控搖桿與三種尺寸'
    ctx, pg, errs = open_page(p, 's10', w=1024, h=768, touch=True)
    board_click(pg, '開始行動')
    check(scn, '平板橫向計畫板沒有左右捲動', not pg.evaluate("document.getElementById('board').scrollWidth > document.getElementById('board').clientWidth + 1"))
    caption(pg, '平板模式：用左下角搖桿往上推，石虎應該往前走')
    depart(pg, '凌晨 2 點')
    check(scn, '平板出現搖桿', pg.locator('#joy').is_visible())
    z0 = world(pg)['p']['z']
    b = pg.locator('#joy').bounding_box()
    cx, cy = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx, cy - 50, steps=5)
    pg.wait_for_timeout(1800)
    z1 = world(pg)['p']['z']
    pg.mouse.up()
    check(scn, '推搖桿石虎會移動', z1 < z0 - 2, 'z ' + str(round(z0, 1)) + ' > ' + str(round(z1, 1)))
    shot(pg, 's10-tablet')
    vid = finish(scn, ctx, pg, errs)
    for name, w, h in [('phone-port', 390, 844), ('tablet-port', 768, 1024), ('laptop', 1366, 768)]:
        c2, p2, e2 = open_page(p, 's10-' + name, w=w, h=h, touch=(w < 1100))
        board_click(p2, '開始行動')
        ov = p2.evaluate("document.getElementById('board').scrollWidth > document.getElementById('board').clientWidth + 1")
        check(scn, name + ' ' + str(w) + 'x' + str(h) + ' 計畫板沒有破版', not ov)
        shot(p2, 's10-' + name)
        c2.close(); c2.browser.close()
    return vid


def s11(p):
    scn = '11 盈凸月：月亮在行動中途下山'
    ctx, pg, errs = open_page(p, 's11')
    board_click(pg, '開始行動')
    caption(pg, '第 1 晚（農曆十二）凌晨 2 點出門，月亮還低低掛在西邊')
    depart(pg, '凌晨 2 點')
    r = st(pg)['run']
    check(scn, '出門時月亮還在天上', r['lastUp'] is True, 'b=' + str(round(r['curB'], 2)))
    caption(pg, '躲在竹林裡等待，時間快轉 1 小時，月亮應該下山')
    pg.evaluate('window.__shihu.ff(25)'); pg.wait_for_timeout(2500)
    r = st(pg)['run']
    check(scn, '月亮下山後田裡變暗（月光 = 0）', r['lastUp'] is False and r['curB'] == 0, 'b=' + str(round(r['curB'], 2)))
    check(scn, '畫面出現「月亮下山了」提示', '下山' in pg.locator('#banner').inner_text())
    check(scn, '右上角天空小照片寫「月亮已經下山」', pg.locator('#hudSkyText').inner_text() == '月亮已經下山', pg.locator('#hudSkyText').inner_text())
    shot(pg, 's11-moonset')
    return finish(scn, ctx, pg, errs)


SCN = {'1': s1, '2': s2, '3': s3, '4': s4, '5': s5, '6': s6, '7': s7, '8': s8, '9': s9, '10': s10, '11': s11}
if __name__ == '__main__':
    which = sys.argv[1:] or list(SCN.keys())
    with sync_playwright() as p:
        for k in which:
            print('== 情境 ' + k, flush=True)
            try:
                v = SCN[k](p)
                print('  video: ' + str(v), flush=True)
            except Exception as e:
                check('情境 ' + k, '情境執行完成', False, repr(e)[:200])
    path = os.path.join(OUT, 'results.json')
    old = json.load(open(path)) if os.path.exists(path) else []
    old = [r for r in old if not any(r['scenario'].startswith(k + ' ') or r['scenario'] == '情境 ' + k for k in which)]
    json.dump(old + RESULTS, open(path, 'w'), ensure_ascii=False, indent=1)
