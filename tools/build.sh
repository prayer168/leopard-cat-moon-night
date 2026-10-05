#!/bin/sh
# 把 game.html 包成可直接放上 GitHub Pages 的完整 index.html
{
  printf '<!DOCTYPE html>\n<html lang="zh-Hant-TW">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n</head>\n<body>\n'
  cat "$(dirname "$0")/../game.html"
  printf '\n</body>\n</html>\n'
} > "$(dirname "$0")/../index.html"
