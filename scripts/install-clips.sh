#!/usr/bin/env bash
# 把 voice-clips 里的参照音复制到 TTS 引擎的参照音目录
# 用法: bash scripts/install-clips.sh <目标目录>
set -euo pipefail

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  cat <<'EOF'
用法: bash scripts/install-clips.sh <目标目录>

例子:
  bash scripts/install-clips.sh ~/CosyVoice/refs/elysia
  bash scripts/install-clips.sh "D:/AI/CosyVoice/refs/elysia"
EOF
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/voice-clips"

if ! ls "$SRC"/g-*.wav >/dev/null 2>&1; then
  echo "找不到参照音: $SRC/g-*.wav" >&2
  exit 1
fi

mkdir -p "$TARGET"
cp -f "$SRC"/g-*.wav "$TARGET"/

COUNT=$(ls -1 "$TARGET"/g-*.wav | wc -l | tr -d ' ')
echo "已复制 $COUNT 条参照音 -> $TARGET"
ls -1 "$TARGET"/g-*.wav | sed 's#.*/##' | paste -sd' ' -
echo
echo "下一步: 起你的 TTS 服务，然后 bash scripts/test-tts.sh http://127.0.0.1:9880/api/tts"
