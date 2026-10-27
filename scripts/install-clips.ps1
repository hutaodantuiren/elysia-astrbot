# 把 voice-clips 里的参照音复制到 TTS 引擎的参照音目录
# 用法: powershell -ExecutionPolicy Bypass -File scripts/install-clips.ps1 -Target "D:\AI\CosyVoice\refs\elysia"
param(
    [Parameter(Mandatory = $true, HelpMessage = "参照音目标目录")]
    [string]$Target
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "voice-clips"

$clips = Get-ChildItem -Path $src -Filter "g-*.wav" -File
if ($clips.Count -eq 0) {
    Write-Error "找不到参照音: $src\g-*.wav"
}

if (-not (Test-Path $Target)) {
    New-Item -ItemType Directory -Path $Target | Out-Null
}

foreach ($clip in $clips) {
    Copy-Item -Path $clip.FullName -Destination $Target -Force
}

Write-Host ("已复制 {0} 条参照音 -> {1}" -f $clips.Count, $Target) -ForegroundColor Green
$clips | ForEach-Object { $_.Name } | Write-Host
Write-Host ""
Write-Host "下一步: 起你的 TTS 服务，然后 bash scripts/test-tts.sh http://127.0.0.1:9880/api/tts"
