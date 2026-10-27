# TTS 接口契约

插件只认这一套契约。任何 TTS 引擎，包一层就能用。

## 请求

```
POST {api_url}
Content-Type: application/json
Authorization: Bearer {api_key}        ← 可选，配置了 api_key 才发

{
  "text": "你好呀，我是爱莉希雅♪",
  "ref":  "g-05.wav"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 要合成的文本（插件已按 `max_chars` 截断） |
| `ref` | string | 参照音文件名 |

> 字段名可在插件配置里改（`text_field` / `ref_field`），以适配已有服务。

## 响应（三种任选其一）

**A. 直接返回音频字节**（推荐）

```
200 OK
Content-Type: audio/wav        （或 audio/mpeg、audio/silk）

<binary>
```

**B. 返回本地文件路径**

```json
{ "audio_path": "/abs/path/out.wav" }
```

**C. 返回可下载 URL**

```json
{ "url": "http://127.0.0.1:9880/static/out.wav" }
```

插件会下载到临时目录再发出去。

## 错误

| 情况 | 期望 |
|------|------|
| 参数缺失 | `400` + JSON `{"error": "..."}` |
| 参照音不存在 | `404` + `{"error": "ref not found: g-99.wav"}` |
| 合成失败（显存/模型） | `500` + `{"error": "..."}` |
| 超时 | 插件侧按 `timeout` 截断，返回「嗓子哑了」提示 |

错误信息会进日志，不会原样丢到群里。

## 自测

```bash
curl -X POST http://127.0.0.1:9880/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"你好呀，我是爱莉希雅♪","ref":"g-05.wav"}' \
  --output /tmp/t.wav -w "%{http_code} %{content_type}\n"
```

期望 `200 audio/wav`，且 `/tmp/t.wav` 能播放。仓库里的 `scripts/test-tts.sh` 就是这条命令的封装。
