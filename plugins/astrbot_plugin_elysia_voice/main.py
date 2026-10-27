"""爱莉希雅语音 · AstrBot 插件

把一段文字交给本地 TTS 服务，用爱莉希雅的声线合成，再作为语音消息发出去。

指令：
    /爱莉说 <文本>
    /爱莉语音 <文本>
    /elysia <文本>
    /爱莉语音状态

接口契约见仓库 config/api-contract.md。
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time
import uuid

import aiohttp

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Record
from astrbot.api.star import Context, Star, register

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(PLUGIN_DIR, "tmp")

MSG_EMPTY = "唔…要让爱莉念什么呢？说一句给爱莉听嘛～♪"
MSG_NO_URL = "唔…爱莉还没找到自己的声音在哪呢，让管理员先帮爱莉把接口配好呀♪"
MSG_FAIL = "唔…这会儿爱莉的嗓子有点哑，等会儿再念给你听好不好呀～"
MSG_TOO_LONG = "这话有点长呢，爱莉一口气念不完啦～拆短一点再说给爱莉听嘛♪"


@register("elysia_voice", "elysia-astrbot", "用爱莉希雅声线把文字念成语音", "1.0.0")
class ElysiaVoicePlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self.api_url = str(self._cfg("api_url", "http://127.0.0.1:9880/api/tts")).strip()
        self.api_key = str(self._cfg("api_key", "")).strip()
        self.text_field = str(self._cfg("text_field", "text")).strip() or "text"
        self.ref_field = str(self._cfg("ref_field", "ref")).strip() or "ref"
        self.default_ref = self._normalize_ref(self._cfg("default_ref", "g-05.wav"))
        self.timeout = int(self._cfg("timeout", 60) or 60)
        self.max_chars = int(self._cfg("max_chars", 200) or 200)
        self.emotion_map = self._parse_emotion_map(self._cfg("emotion_map", ""))
        os.makedirs(TMP_DIR, exist_ok=True)
        logger.info(
            "[elysia_voice] 已加载：api_url=%s default_ref=%s 情绪映射=%d 条",
            self.api_url,
            self.default_ref,
            len(self.emotion_map),
        )

    # ── 指令 ────────────────────────────────────────────────────────────

    @filter.command("爱莉说")
    async def say_zh(self, event: AstrMessageEvent):
        async for item in self._handle(event):
            yield item

    @filter.command("爱莉语音")
    async def say_voice(self, event: AstrMessageEvent):
        async for item in self._handle(event):
            yield item

    @filter.command("elysia")
    async def say_en(self, event: AstrMessageEvent):
        async for item in self._handle(event):
            yield item

    @filter.command("爱莉语音状态")
    async def status(self, event: AstrMessageEvent):
        refs = "、".join(f"{k}={v}" for k, v in self.emotion_map.items()) or "（未配置）"
        yield event.plain_result(
            "爱莉的嗓子是这样的♪\n"
            f"接口：{self.api_url}\n"
            f"默认参照音：{self.default_ref}\n"
            f"情绪映射：{refs}\n"
            f"单次上限：{self.max_chars} 字 / 超时 {self.timeout}s"
        )

    # ── 主流程 ──────────────────────────────────────────────────────────

    async def _handle(self, event: AstrMessageEvent):
        text = self._strip_cmd(getattr(event, "message_str", "") or "")
        if not text:
            yield event.plain_result(MSG_EMPTY)
            return

        if len(text) > self.max_chars:
            text = text[: self.max_chars].strip()
            logger.info("[elysia_voice] 文本超长，已截断到 %d 字", self.max_chars)

        ref, text = self._pick_ref(text)
        if not self.api_url:
            yield event.plain_result(MSG_NO_URL)
            return

        audio, err = await self._tts(text, ref)
        if not audio:
            logger.error("[elysia_voice] 合成失败 ref=%s err=%s", ref, err)
            yield event.plain_result(MSG_FAIL)
            return

        try:
            path = self._save(audio)
        except OSError as exc:
            logger.error("[elysia_voice] 落盘失败: %s", exc)
            yield event.plain_result(MSG_FAIL)
            return

        self._cleanup()
        yield event.chain_result([Record(file=path)])

    # ── TTS 调用 ────────────────────────────────────────────────────────

    async def _tts(self, text: str, ref: str) -> tuple[bytes | None, str]:
        payload = {self.text_field: text, self.ref_field: ref}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.api_url, json=payload, headers=headers) as resp:
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    if resp.status != 200:
                        body = (await resp.text())[:200]
                        return None, f"HTTP {resp.status}: {body}"
                    raw = await resp.read()
        except asyncio.TimeoutError:
            return None, f"timeout after {self.timeout}s"
        except aiohttp.ClientError as exc:
            return None, f"client error: {exc}"
        except Exception as exc:  # noqa: BLE001 - 网络层意外统一兜底
            return None, f"{type(exc).__name__}: {exc}"

        if ctype.startswith("audio/"):
            return raw, ""
        return await self._from_json(raw)

    async def _from_json(self, raw: bytes) -> tuple[bytes | None, str]:
        """兼容 {audio_path} / {url} / {audio: base64} 三种返回。"""
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            return None, f"非音频响应且不是 JSON（{len(raw)} bytes）"

        path = data.get("audio_path") or data.get("path")
        if path and os.path.isfile(str(path)):
            try:
                with open(str(path), "rb") as f:
                    return f.read(), ""
            except OSError as exc:
                return None, f"读取 audio_path 失败: {exc}"

        url = data.get("url")
        if url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(url), timeout=aiohttp.ClientTimeout(total=self.timeout)) as r:
                        if r.status != 200:
                            return None, f"下载音频失败 HTTP {r.status}"
                        return await r.read(), ""
            except Exception as exc:  # noqa: BLE001
                return None, f"下载音频异常: {exc}"

        b64 = data.get("audio") or data.get("data")
        if isinstance(b64, str) and b64:
            try:
                return base64.b64decode(b64), ""
            except Exception as exc:  # noqa: BLE001
                return None, f"base64 解码失败: {exc}"

        return None, "响应里没有音频字段"

    # ── 工具 ────────────────────────────────────────────────────────────

    def _cfg(self, key: str, default):
        value = self.config.get(key, default)
        return default if value is None or value == "" else value

    @staticmethod
    def _normalize_ref(ref) -> str:
        name = str(ref or "").strip() or "g-05.wav"
        return name if name.endswith(".wav") else f"{name}.wav"

    @staticmethod
    def _parse_emotion_map(value) -> dict:
        if isinstance(value, dict):
            data = value
        else:
            try:
                data = json.loads(str(value or "{}"))
            except Exception:  # noqa: BLE001
                logger.warning("[elysia_voice] emotion_map 不是合法 JSON，已忽略")
                return {}
        out = {}
        for key, ref in data.items():
            if str(key).startswith("_"):
                continue
            if ref:
                out[str(key)] = ElysiaVoicePlugin._normalize_ref(ref)
        return out

    def _commands(self) -> tuple[str, ...]:
        return ("爱莉说", "爱莉语音", "elysia", "爱莉语音状态")

    def _strip_cmd(self, raw: str) -> str:
        text = (raw or "").strip()
        text = re.sub(r"^[/!！.]", "", text).strip()
        for name in self._commands():
            if text.startswith(name):
                text = text[len(name):].strip()
                break
        return text

    def _pick_ref(self, text: str) -> tuple[str, str]:
        """优先级：指令内 [标签] > 文本关键词命中 > 默认参照音。"""
        m = re.match(r"^[\[【]([^\]】]{1,32})[\]】]\s*(.*)$", text, flags=re.S)
        if m:
            tag, rest = m.group(1).strip(), m.group(2).strip()
            ref = self.emotion_map.get(tag)
            if ref is None and re.fullmatch(r"g-\d{1,2}(\.wav)?", tag):
                ref = self._normalize_ref(tag)
            if ref:
                return ref, rest or text

        for key, ref in self.emotion_map.items():
            if key and key in text:
                return ref, text

        return self.default_ref, text

    def _save(self, audio: bytes) -> str:
        ext = ".wav"
        if audio[:3] == b"ID3" or audio[:2] == b"\xff\xfb":
            ext = ".mp3"
        elif audio[:4] == b"RIFF":
            ext = ".wav"
        name = f"{int(time.time())}-{uuid.uuid4().hex[:8]}{ext}"
        path = os.path.join(TMP_DIR, name)
        with open(path, "wb") as f:
            f.write(audio)
        return path

    def _cleanup(self, max_age: int = 3600) -> None:
        """清理一小时前的临时音频，避免目录越积越大。"""
        now = time.time()
        try:
            for name in os.listdir(TMP_DIR):
                path = os.path.join(TMP_DIR, name)
                if os.path.isfile(path) and now - os.path.getmtime(path) > max_age:
                    os.remove(path)
        except OSError:
            pass

    async def terminate(self):
        logger.info("[elysia_voice] 插件已卸载")
