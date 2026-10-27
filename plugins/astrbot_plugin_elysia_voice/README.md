# astrbot_plugin_elysia_voice

给 AstrBot 用的「爱莉希雅声线」语音插件：把文字交给本地 TTS 服务合成，再把音频作为语音消息发出去。

## 指令

| 指令 | 说明 |
|------|------|
| `/爱莉说 <文本>` | 主指令 |
| `/爱莉语音 <文本>` | 别名 |
| `/elysia <文本>` | 英文别名 |
| `/爱莉语音状态` | 查看接口、默认参照音、情绪映射 |

参照音可以在指令里临时指定：

```
/爱莉说 [g-11] 晚安啦，做个好梦♪
/爱莉说 [深情] 我会一直在这里的
```

`[深情]` 这种中文标签来自插件配置里的 `emotion_map`。

## 安装

```bash
cp -r astrbot_plugin_elysia_voice <AstrBot>/data/plugins/
```

重启 AstrBot，在 WebUI 插件管理里配置 `api_url`。

## 配置

见 [`_conf_schema.json`](_conf_schema.json)，或线上文档 `docs/03-AstrBot配置.md`。

最小配置：

| 项 | 值 |
|----|----|
| `api_url` | `http://127.0.0.1:9880/api/tts` |
| `default_ref` | `g-05.wav` |

## 接口契约

插件只要求你的 TTS 服务满足：

```
POST {api_url}
{"text": "...", "ref": "g-05.wav"}

→ 200 audio/*   或   {"audio_path": "..."}   或   {"url": "..."}
```

完整定义见仓库的 [`config/api-contract.md`](../../config/api-contract.md)，现成适配器见 [`config/`](../../config/)。

## 触发失败时

插件不会把技术错误丢到群里，只会俏皮地说一句「嗓子有点哑」，真实原因写到日志（前缀 `[elysia_voice]`）。

## 限制

- 只做**指令触发**，不做自动口播（避免刷屏）。
- 不做文本后处理（标点、数字读法交给 TTS 引擎）。
- 临时音频放在 `tmp/`，超过 1 小时自动清理。
