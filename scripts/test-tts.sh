#!/usr/bin/env bash
# 自测 TTS 接口是否满足插件契约
# 用法: bash scripts/test-tts.sh [url] [text] [ref]
set -uo pipefail

URL="${1:-http://127.0.0.1:9880/api/tts}"
TEXT="${2:-你好呀，我是爱莉希雅，今天也请多指教啦。}"
REF="${3:-g-05.wav}"

OUT="$(mktemp -t elysia-tts-XXXXXX.wav)"
trap 'rm -f "$OUT"' EXIT

echo "POST $URL"
echo "  text = $TEXT"
echo "  ref  = $REF"
echo

CODE=$(curl -sS -o "$OUT" -w "%{http_code}|%{content_type}" \
  -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "$(printf '{"text":"%s","ref":"%s"}' "$TEXT" "$REF")" \
  --max-time 120) || {
    echo "请求失败：服务没起来？地址写错？防火墙？" >&2
    exit 1
  }

STATUS="${CODE%%|*}"
CTYPE="${CODE##*|}"
SIZE=$(wc -c <"$OUT" | tr -d ' ')

echo "HTTP $STATUS   Content-Type: $CTYPE   大小: $SIZE bytes"

if [ "$STATUS" != "200" ]; then
  echo
  echo "响应体（前 300 字节）："
  head -c 300 "$OUT"; echo
  exit 1
fi

if [ "$SIZE" -lt 1024 ]; then
  echo "返回内容太小，可能不是音频。" >&2
  head -c 300 "$OUT"; echo
  exit 1
fi

case "$CTYPE" in
  audio/*) echo "OK：返回的是音频 ✔" ;;
  application/json) echo "返回 JSON（插件支持 audio_path / url / base64 三种，确认字段对得上）" ;;
  *) echo "⚠ Content-Type 不是 audio/*，插件可能走 JSON 分支而失败" ;;
esac

echo "试听：$OUT（脚本退出时会删除，想保留就先 cp 出去）"
command -v ffplay >/dev/null 2>&1 && ffplay -autoexit -nodisp -loglevel quiet "$OUT" || true
