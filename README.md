# 爱莉希雅 · AstrBot 语音人格包

> 把《崩坏3》的「粉色妖精小姐♪」爱莉希雅装进 AstrBot：**用她的人格说话，用她的声线发语音。**

<p align="left">
  <img alt="license" src="https://img.shields.io/badge/素材-同人非商用-pink">
  <img alt="platform" src="https://img.shields.io/badge/AstrBot-v4+-blue">
  <img alt="tts" src="https://img.shields.io/badge/TTS-CosyVoice2%20%7C%20GPT--SoVITS-9cf">
</p>

---

## 这是什么

三样东西打包在一起：

| 组成 | 内容 | 位置 |
|------|------|------|
| **人格提示词** | 爱莉希雅的人设、说话方式、语气、雷点、示例 | [`persona/`](persona/) |
| **仿真协议** | 何时发消息、怎么分条、怎么发语音、怎么潜水与收尾 | [`persona/elysia-simulation.md`](persona/elysia-simulation.md) |
| **声线素材** | 20 条爱莉声线参照音（`g-01.wav` ~ `g-20.wav`） | [`voice-clips/`](voice-clips/) |

外加让它「开箱能调用」的东西：

- **AstrBot 插件** [`astrbot_plugin_elysia_voice`](plugins/astrbot_plugin_elysia_voice/)：一条指令，把文字念成爱莉的声音发出去。
- **接口契约 + 参考适配器** [`config/`](config/)：不管你用 CosyVoice、GPT-SoVITS 还是别的，都能在半小时内接上。
- **安装脚本** [`scripts/`](scripts/)：复制参照音、连通性自检。

> 它**不是**一键安装的成品 TTS 引擎。声音克隆引擎（约 3GB）需要你自己部署一次，之后所有角色共用。

---

## 30 秒理解工作原理

```
群友：/爱莉说 今天也要开心呀
        │
        ▼
  AstrBot（人格提示词 → 生成爱莉腔的文字）
        │
        ▼  指令触发
  插件 astrbot_plugin_elysia_voice
        │  POST /api/tts  {"text": "...", "ref": "g-05.wav"}
        ▼
  本地 TTS 服务（CosyVoice2 / GPT-SoVITS …，用 g-0X.wav 克隆声线）
        │  返回 audio/wav
        ▼
  AstrBot 以「语音消息」发回 QQ
```

人格决定**说什么**，插件决定**怎么发出去**，声线素材决定**听起来是谁**。三件事互相独立，可以分别替换。

---

## 三步开始

### 1. 部署声音克隆引擎（一次性，约 3GB）

见 [docs/02-语音引擎部署.md](docs/02-语音引擎部署.md)。最短路径：

```bash
pip install modelscope
modelscope download --model iic/CosyVoice2-0.5B --local_dir ./models/cosyvoice2
git clone https://github.com/FunAudioLLM/CosyVoice.git && cd CosyVoice
pip install -r requirements.txt
```

把 [`voice-clips/`](voice-clips/) 里的 20 条 wav 复制到引擎的参照音目录：

```bash
bash scripts/install-clips.sh /path/to/CosyVoice/refs/elysia
# Windows:  powershell -ExecutionPolicy Bypass -File scripts/install-clips.ps1 -Target "D:\AI\CosyVoice\refs\elysia"
```

### 2. 安装插件并指向你的 TTS 服务

把 [`plugins/astrbot_plugin_elysia_voice`](plugins/astrbot_plugin_elysia_voice/) 整个目录复制到 AstrBot 的插件目录：

```
<AstrBot>/data/plugins/astrbot_plugin_elysia_voice/
```

重启 AstrBot，在 WebUI「插件管理」里配置 `api_url`（默认 `http://127.0.0.1:9880/api/tts`），细节见 [docs/03-AstrBot配置.md](docs/03-AstrBot配置.md)。

### 3. 把人格贴进去

打开 AstrBot 的「人格 / 系统提示」，把 [`persona/elysia-all-in-one.md`](persona/elysia-all-in-one.md) 整份粘贴进去（单字段就够）。想分开管理就用 `elysia-persona.md` + `elysia-simulation.md`。

装好后在群里发：

```
/爱莉说 你好呀，我是爱莉希雅
```

---

## 插件指令

| 指令 | 作用 |
|------|------|
| `/爱莉说 <文本>` | 用爱莉声线念出这段文本 |
| `/爱莉语音 <文本>` | 同上（别名） |
| `/elysia <文本>` | 同上（英文别名，方便手机输入） |
| `/爱莉语音状态` | 查看当前 TTS 地址、默认参照音、情绪映射条数 |

指令表可扩展：直接改 `main.py` 里的 `@filter.command("...")` 装饰器字符串，加一个方法就是一条新指令。

## 参照音与情绪

`voice-clips/` 里 20 条是不同语气的样本。默认用 `g-05.wav`（最元气）；想看每条多长、怎么归类，见 [voice-clips/README.md](voice-clips/README.md)。

情绪→参照音的映射写在 [`config/emotion-map.json`](config/emotion-map.json)，插件配置项 `emotion_map` 可以直接粘这个 JSON。留空就用 `default_ref`。

## 目录结构

```
elysia-astrbot/
├─ README.md                  ← 你在这里
├─ LICENSE                    ← 代码 MIT
├─ NOTICE.md                  ← 素材版权与使用边界（先看这个）
├─ persona/                   ← 人格 + 仿真提示词（3 个版本）
├─ voice-clips/               ← 20 条爱莉参照音 + 清单
├─ plugins/
│  └─ astrbot_plugin_elysia_voice/   ← 发语音的 AstrBot 插件
├─ config/                    ← 接口契约、参考适配器、情绪映射
├─ docs/                      ← 分步说明 + 原始人格资料
└─ scripts/                   ← 一键复制参照音、TTS 连通性自检
```

## 文档索引

| 我想…… | 看这里 |
|--------|--------|
| 从零跑起来 | [docs/01-快速开始.md](docs/01-快速开始.md) |
| 部署 CosyVoice / GPT-SoVITS | [docs/02-语音引擎部署.md](docs/02-语音引擎部署.md) |
| 配插件、改触发词、接自己写的 TTS | [docs/03-AstrBot配置.md](docs/03-AstrBot配置.md) |
| 三个提示词文件怎么选、怎么注入 | [docs/04-提示词说明.md](docs/04-提示词说明.md) |
| 人格为什么这么写 | [docs/reference/](docs/reference/)（ELY_PERSONA / ELY_ANALYSIS / 台词库） |

## 常见问题

**Q：语音发不出来，日志报错。**
先跑 `bash scripts/test-tts.sh http://127.0.0.1:9880/api/tts`，确认服务本身能返回音频；再查 AstrBot 日志里是否有 ffmpeg 转码失败。协议端一般要求 `mp3` / `silk`，插件会原样交给 AstrBot 转码。

**Q：听起来不像爱莉。**
换参照音（`g-01` 温柔、`g-05` 元气、`g-11` 深情…逐条试听），或改用 GPT-SoVITS 做微调。参照音越贴当前语气，克隆越像。

**Q：我不想每条都发语音。**
默认就是**指令触发**，只有 `/爱莉说` 才发。想全自动口播，用 `astrbot_plugin_universal_tts` 这类插件做兜底，别在本插件里开自动模式。

**Q：能换成别的角色吗？**
能。人格换成任意角色卡，`voice-clips` 换成该角色的参照音，插件不用动。

**Q：会不会说脏话 / 答不上来就糊弄？**
不会。人格文件开头有「人设红线」，明确禁止脏话与对线黑话，并规定不会答时温柔如实（坦白 + 去查 + 不编造）。

## 版权与免责

- **代码**：MIT，见 [LICENSE](LICENSE)。
- **声线素材与台词**：来源于《崩坏3》，版权归米哈游所有。本仓库仅作**同人、个人学习与非商业用途**，禁止商用、禁止用于冒充真人或诈骗。详见 [NOTICE.md](NOTICE.md)。
- 如果你要公开发布二次作品，请自行确认所在地法律与平台规则。

## 致谢

人格资料与声线素材来自社区整理的「爱莉希雅语音包」（原包为 DeepSeek Harness 预设）。本仓库把它们改写为 AstrBot 可用的形态，并补上插件与文档。
