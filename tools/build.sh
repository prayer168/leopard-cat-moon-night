#!/bin/sh
# 把 game.html 包成可直接放上 GitHub Pages 的完整 index.html（含社群分享縮圖設定）
DIR="$(dirname "$0")/.."
URL="https://prayer168.github.io/leopard-cat-moon-night/"
DESC="看懂月亮，撐過 30 個夜晚。國小四年級月相 3D 遊戲：石虎媽媽挑最暗的時段溜進田裡抓田鼠。"
{
  printf '<!DOCTYPE html>\n<html lang="zh-Hant-TW">\n<head>\n<meta charset="utf-8">\n'
  printf '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  printf '<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n'
  printf '<meta name="description" content="%s">\n' "$DESC"
  printf '<meta property="og:type" content="website">\n'
  printf '<meta property="og:title" content="石虎月夜行 Leopard Cat Moon Night">\n'
  printf '<meta property="og:description" content="%s">\n' "$DESC"
  printf '<meta property="og:url" content="%s">\n' "$URL"
  printf '<meta property="og:image" content="%sdocs/og-image.png">\n' "$URL"
  printf '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
  printf '<meta property="og:locale" content="zh_TW">\n'
  printf '<meta name="twitter:card" content="summary_large_image">\n'
  printf '<meta name="twitter:image" content="%sdocs/og-image.png">\n' "$URL"
  printf '</head>\n<body>\n'
  cat "$DIR/game.html"
  printf '\n</body>\n</html>\n'
} > "$DIR/index.html"
