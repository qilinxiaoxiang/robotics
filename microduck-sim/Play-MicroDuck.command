#!/bin/zsh
set -euo pipefail

microduck_root="$(cd -- "$(dirname -- "$0")" && pwd)"
microduck_app="$microduck_root/microduck-simulator/app"
microduck_url="http://127.0.0.1:5173/?boot=1"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  print "需要先安装 Node.js 20 或更新版本。"
  print "按任意键关闭。"
  read -r -k 1
  exit 1
fi

if curl --fail --silent --max-time 1 "http://127.0.0.1:5173/" 2>/dev/null \
  | grep -q '<title>Microduck</title>'; then
  open "$microduck_url"
  exit 0
fi

cd "$microduck_app"

if [[ ! -d node_modules ]]; then
  print "首次启动：正在安装 MicroDuck 网页依赖……"
  npm ci
fi

print "MicroDuck 正在启动。浏览器会自动打开。"
print "退出时在这里按 Control-C。"

(
  sleep 1
  open "$microduck_url"
) &

exec npm run dev -- --host 127.0.0.1 --strictPort
