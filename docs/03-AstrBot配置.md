# AstrBot 配置

本文覆盖：插件装哪、配置项怎么填、指令怎么改、怎么接自己写的 TTS、怎么排错。

---

## 一、插件装在哪

AstrBot 的插件是「目录即插件」。把 `plugins/astrbot_plugin_elysia_voice/` 整个复制到：

```
<AstrBot>/data/plugins/astrbot_plugin_elysia_voice/
```

目录里应该有：

```
astrbot_plugin_elysia_voice/
├─ main.py            ← 逻辑
├─ metadata.yaml      ← 插件元信息
├─ _conf_schema.json  ← WebUI 配置项定义
└─ README.md
```

放好后**重启 AstrBot**。WebUI → 插件管理 → 能看到「爱莉希雅语音」= 加载成功。

> 若日志报 `No module named astrbot`，说明目录层级错了（常见是把 `plugins/` 也一起复制了进去）。要保证 `main.py` 直接在插件目录下。

---

## 二、配置项

| 配置项 | 类型 | 默认 | 说明 |
|--------|------|------|------|
| `api_url` | string | `http://127.0.0.1:9880/api/tts` | TTS 接口地址，必须能返回音频 |
| `api_key` | string | 空 | 需要鉴权时填，插件会加 `Authorization: Bearer <key>` |
| `text_field` | string | `text` | 请求体里「文本」的字段名 |
| `ref_field` | string | `ref` | 请求体里「参照音」的字段名 |
| `default_ref` | string | `g-05.wav` | 默认参照音 |
| `emotion_map` | string(JSON) | `{"元气":"g-05.wav","深情":"g-11.wav"}` | 关键词 → 参照音 |
| `timeout` | int | `60` | 单次合成超时（秒） |
| `max_chars` | int | `200` | 单次最多念多少字，超出截断 |

### 参照音怎么选

三种优先级，从高到低：

1. **指令里显式指定**：`/爱莉说 [g-11] 晚安啦，做个好梦♪`
   - 方括号里可以是文件名（`g-11.wav` / `g-11`），也可以是 `emotion_map` 里的键（`[深情]`）。
2. **文本里出现关键词**：`emotion_map` 的键出现在文本中就用对应参照音。
3. **`default_ref`**。

`emotion_map` 建议先按试听结果自己定。已确认的只有两条：`g-05` 元气、`g-11` 深情；其它 18 条请听一遍再归类，别照抄别人的表。

---

## 三、指令

| 写法 | 说明 |
|------|------|
| `/爱莉说 你好呀` | 主指令 |
| `/爱莉语音 你好呀` | 别名 |
| `/elysia 你好呀` | 别名（英文键盘更顺手） |
| `/爱莉语音状态` | 打印当前配置与连通性 |

改指令名：编辑 `main.py` 里的 `@filter.command("爱莉说")` 等三个装饰器字符串（各一行）。
改前缀：AstrBot 的指令前缀在全局配置里（默认 `/`），插件不强行覆盖。

> 想让 LLM 自己决定什么时候发语音：把 `persona/elysia-simulation.md` 里的「十六、语音」那一节保留，模型会按语境调用 `/爱莉说`（前提是 AstrBot 允许模型发指令，或你用了支持工具调用的桥接）。

---

## 四、接自己的 TTS

插件只认一个契约，见 [../config/api-contract.md](../config/api-contract.md)：

```
POST {api_url}
Content-Type: application/json

{"text": "要念的话", "ref": "g-05.wav"}

→ 200, Content-Type: audio/*
   或 200, JSON {"audio_path": "/abs/path.wav"}
   或 200, JSON {"url": "http://..."}
```

只要你的服务返回上面任意一种，插件就能用。三种落地方式：

**① 引擎自带 HTTP API**（最简单）
直接填它的地址；字段名不一致就改 `text_field` / `ref_field`。

**② 起一个薄适配器**
- CosyVoice：[`config/adapter-cosyvoice.py`](../config/adapter-cosyvoice.py)
- GPT-SoVITS：[`config/adapter-gpt-sovits.py`](../config/adapter-gpt-sovits.py)

```bash
python config/adapter-cosyvoice.py --port 9880 --clips ./refs/elysia
```

**③ 自己写 30 行**
照着契约实现 `POST` → 返回 `audio/wav` 即可，参考两个适配器的错误处理。

---

## 五、自动口播（可选）

本插件刻意**只做指令触发**，避免刷屏和烧钱。如果确实想「每条回复都转语音」，两条路：

- 装 `astrbot_plugin_universal_tts` 之类的通用 TTS 插件，让它指向同一个 TTS 服务（它的配置里一般能填自定义 API）；
- 自己在插件里加一个「回复后钩子」，把文本结果换成 `Record`。

无论哪种，都建议：

- 加频率限制（比如每人每 10 分钟最多 1 条）；
- 只对私聊或 @ 生效；
- 文本超过 60 字就只发文字。

---

## 六、排错

| 现象 | 排查 |
|------|------|
| 指令没反应 | 插件没加载：看启动日志有没有 `elysia_voice` 注册成功；确认目录层级 |
| 回复「唔…这会儿爱莉的嗓子有点哑」 | 插件侧失败：先 `bash scripts/test-tts.sh <api_url>` 单独验证服务 |
| 回复「接口地址好像没配对」 | `api_url` 写错，或服务没启动 |
| 返回 401/403 | 填 `api_key`，或服务端关了鉴权 |
| 有返回但群里没声音 | 音频格式问题：确认 ffmpeg 在 PATH；把输出改成 mp3 试 |
| 念到一半截断 | 文本超 `max_chars`，调大或拆句 |
| 每次都同一个音色 | 没触发情绪映射：用 `[g-XX]` 显式指定试一下 |

日志位置：AstrBot 控制台或 `data/logs/`。插件失败时会打 `[elysia_voice]` 前缀的 error。
