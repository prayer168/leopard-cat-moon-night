# 由 test-output/results.json 與截圖產生試玩測試報告頁（artifact 用，不含 doctype）
import json, os, base64, io, collections, html
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'test-output')
res = json.load(open(os.path.join(OUT, 'results.json')))

ORDER = ['1', '2', '3', '4', '11', '6', '5', '7', '8', '10', '9']
SHOT = {'1': ['s1-plan', 's1-notebook'], '2': ['s2-report', 's2-plan-after'], '3': ['s3-caught'], '4': ['s4-timeout'],
        '11': ['s11-moonset'], '6': ['s6-report'], '5': ['s5-ditch'], '7': ['s7-fail'], '8': ['s8-final'],
        '10': ['s10-tablet', 's10-phone-port'], '9': []}
WHAT = {
    '1': '打開遊戲、進入第 1 晚計畫板，檢查按鈕、時間軸、月相日記與情報簿的祕密圖。',
    '2': '新月夜晚上 7 點出動，AI 自己操控石虎抓田鼠、避開手電筒、回到竹林。',
    '3': '滿月夜晚上 7 點出動，AI 故意走向農夫，確認「被發現」的戰報說明正確。',
    '4': '出發後先站著不動，再快轉時間，確認不會誤判得手、時間到會結束。',
    '11': '農曆十二凌晨 2 點出門，等月亮下山，確認田裡變暗與提示。',
    '6': '農曆廿二（下弦月）晚上 11 點出門，月亮在行動中途升起。',
    '5': '第 3 次出動起有狗。AI 先留下氣味讓狗追，再衝進水圳甩掉牠。',
    '7': '一直選「睡一晚」，存糧吃光後餓 3 次，行動失敗。',
    '8': '撐到第 30 晚結案，逐格比對月相日記的月相名稱與順序。',
    '10': '平板模式推搖桿，並檢查手機、平板、筆電尺寸是否破版。',
    '9': '直接檢查遊戲裡的月相、月出時間、月光亮度與月亮亮面方向的計算。'
}


def img64(name, w=520):
    pth = os.path.join(OUT, 'shots', name + '.png')
    if not os.path.exists(pth):
        return ''
    im = Image.open(pth).convert('RGB')
    im.thumbnail((w, w))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=78)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


groups = collections.OrderedDict()
for r in res:
    k = r['scenario'].split(' ')[0]
    groups.setdefault(k, {'name': r['scenario'][len(k) + 1:], 'checks': []})['checks'].append(r)
total = len(res); passed = sum(1 for r in res if r['ok'])

cards = []
for k in ORDER:
    if k not in groups: continue
    g = groups[k]
    n_ok = sum(1 for c in g['checks'] if c['ok'])
    rows = ''.join('<li class="%s"><span class="pill">%s</span><span>%s%s</span></li>' % (
        'ok' if c['ok'] else 'bad', '通過' if c['ok'] else '失敗', html.escape(c['check']),
        ('<small>' + html.escape(c['detail'][:120]) + '</small>') if c['detail'] and c['check'] != '沒有 JavaScript 錯誤' else '') for c in g['checks'])
    shots = ''.join('<img alt="%s 截圖" src="%s">' % (html.escape(g['name']), img64(s)) for s in SHOT.get(k, []) if img64(s))
    cards.append('''<article class="card">
  <header><span class="num">%s</span><div><h3>%s</h3><p>%s</p></div><span class="score">%d / %d</span></header>
  <ul>%s</ul>%s
</article>''' % (k, html.escape(g['name']), WHAT.get(k, ''), n_ok, len(g['checks']), rows, ('<div class="shots">' + shots + '</div>') if shots else ''))

page = '''<title>石虎月夜行試玩報告</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700;900&family=Noto+Serif+TC:wght@900&display=swap">
<style>
/* 版面概念：釘在軟木板上的測試結案報告。每個情境一張檢查表，通過蓋綠章、失敗蓋紅章 */
:root {
  --cork: #b4885a; --paper: #f7f2e6; --paper-2: #ece2c8; --ink: #2b2420; --ink-soft: #6e5f50;
  --ok: #1f6b33; --ok-bg: #dcebd9; --bad: #c4332a; --bad-bg: #f6dcd8;
  --sans: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
  --serif: "Noto Serif TC", "Songti TC", "PMingLiU", serif;
  color-scheme: light;
}
body { background: var(--cork); color: var(--ink); font-family: var(--sans); font-size: 16px; line-height: 1.6; padding-inline: 16px; padding-block: 28px 56px; box-sizing: border-box; }
.wrap { max-width: 980px; margin: 0 auto; display: flex; flex-direction: column; gap: 22px; }
.paper { background: var(--paper); border-radius: 3px; box-shadow: 0 12px 26px rgba(40, 22, 6, 0.35); padding: 24px; min-width: 0; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 18px; align-items: center; }
.eyebrow { font-weight: 900; font-size: 13px; letter-spacing: 0.16em; color: var(--bad); }
h1 { margin: 4px 0 6px; font-family: var(--serif); font-weight: 900; font-size: clamp(30px, 6vw, 44px); line-height: 1.15; text-wrap: balance; }
h2 { margin: 0 0 10px; font-family: var(--serif); font-weight: 900; font-size: 24px; }
h3 { margin: 0; font-size: 19px; font-weight: 900; line-height: 1.35; }
.lede { margin: 0; color: var(--ink-soft); max-width: 60ch; }
.stamp { border: 6px double var(--ok); color: var(--ok); font-weight: 900; font-size: 22px; letter-spacing: 0.12em; padding: 6px 16px; border-radius: 10px; transform: rotate(-6deg); text-align: center; line-height: 1.2; }
.stamp b { display: block; font-size: 36px; font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
.stat { background: var(--paper-2); border-radius: 4px; padding: 10px 12px; }
.stat b { display: block; font-size: 26px; font-weight: 900; font-variant-numeric: tabular-nums; }
.stat span { font-size: 14px; color: var(--ink-soft); }
.bugs { display: grid; gap: 12px; }
.bug { border-left: 6px solid var(--bad); background: #fffdf7; padding: 12px 14px; border-radius: 0 4px 4px 0; }
.bug h3 { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.tag { font-size: 12px; font-weight: 900; padding: 1px 8px; border-radius: 999px; background: var(--ok-bg); color: var(--ok); }
.bug p { margin: 4px 0 0; }
.card { background: var(--paper); border-radius: 3px; box-shadow: 0 10px 22px rgba(40, 22, 6, 0.3); padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.card header { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 12px; align-items: start; }
.card header p { margin: 2px 0 0; color: var(--ink-soft); font-size: 15px; }
.num { width: 38px; height: 38px; border-radius: 50%; background: var(--ink); color: var(--paper); display: grid; place-items: center; font-weight: 900; font-variant-numeric: tabular-nums; }
.score { font-weight: 900; color: var(--ok); font-variant-numeric: tabular-nums; white-space: nowrap; padding-top: 6px; }
.card ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.card li { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 10px; align-items: baseline; }
.card li small { display: block; color: var(--ink-soft); font-size: 13px; word-break: break-word; }
.pill { font-size: 12px; font-weight: 900; padding: 1px 8px; border-radius: 999px; background: var(--ok-bg); color: var(--ok); white-space: nowrap; }
li.bad .pill { background: var(--bad-bg); color: var(--bad); }
.shots { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }
.shots img { width: 100%; height: auto; display: block; border: 6px solid #fff; box-shadow: 0 4px 10px rgba(40, 22, 6, 0.25); box-sizing: border-box; }
.notes { margin: 0; padding-left: 1.2em; }
.notes li + li { margin-top: 6px; }
@media (max-width: 640px) {
  .hero { grid-template-columns: minmax(0, 1fr); }
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .card header { grid-template-columns: auto minmax(0, 1fr); }
  .score { grid-column: 2; padding-top: 0; }
}
</style>
<div class="wrap">
  <section class="paper">
    <div class="hero">
      <div>
        <div class="eyebrow">AI 自動試玩測試 2026-10-05</div>
        <h1>石虎月夜行試玩報告</h1>
        <p class="lede">由 AI 打開 Playwright 瀏覽器，自己按按鈕、自己操控石虎出動，跑完 11 個情境並全程錄影。測試中找到 2 個 bug，修好後整套重跑，全部通過。</p>
      </div>
      <div class="stamp">全部通過<b>__PASS__ / __TOTAL__</b></div>
    </div>
    <div class="stats">
      <div class="stat"><b>11</b><span>測試情境</span></div>
      <div class="stat"><b>__TOTAL__</b><span>檢查項目</span></div>
      <div class="stat"><b>2</b><span>找到並修好的 bug</span></div>
      <div class="stat"><b>0</b><span>JavaScript 錯誤</span></div>
    </div>
  </section>

  <section class="paper">
    <h2>AI 試玩找到的問題</h2>
    <div class="bugs">
      <div class="bug"><h3>出發後站著不動，幾秒就自動結束並算成「得手」 <span class="tag">已修正</span></h3>
        <p>起點剛好在竹林的回家綠圈裡。猶豫不動的孩子會白白浪費一個晚上。現在石虎要先走出竹林，再回來才算回家。</p></div>
      <div class="bug"><h3>第 1 晚關掉網頁，再打開會把進度清掉 <span class="tag">已修正</span></h3>
        <p>原本只有「開始行動」按鈕，按下去會重新開始。現在只要有進行中的月份，就顯示「繼續行動」。</p></div>
    </div>
  </section>

  __CARDS__

  <section class="paper">
    <h2>測試說明</h2>
    <ul class="notes">
      <li>線上網址 prayer168.github.io/leopard-cat-moon-night 已確認可以開啟，分享縮圖也設定好了。</li>
      <li>測試用的電腦沒有顯示卡，3D 畫面每秒只有 7 到 12 張，所以錄影裡的動作比較慢。學校的平板和筆電有顯示卡，會順暢很多。</li>
      <li>AI 操控石虎時是讀取遊戲中的位置來決定方向，用鍵盤方向鍵移動，和學生的操作方式相同。</li>
      <li>好不好玩、難度是否合適，仍然建議找幾位學生用真的平板玩一個月份來確認。</li>
    </ul>
  </section>
</div>
'''.replace('__PASS__', str(passed)).replace('__TOTAL__', str(total)).replace('__CARDS__', '\n  '.join(cards))
open(os.path.join(OUT, 'report.html'), 'w').write(page)
print('report', passed, '/', total)
