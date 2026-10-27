"""
CosyVoice2 -> 本仓库 TTS 契约 的参考适配器（可选）
==================================================

把 CosyVoice2 包成：
    POST /api/tts  {"text": "...", "ref": "g-05.wav"}  ->  audio/wav

用法
----
    pip install fastapi uvicorn
    python config/adapter-cosyvoice.py \
        --model ./models/cosyvoice2 \
        --clips ./refs/elysia \
        --port 9880

注意
----
1. 需要先装好 CosyVoice（requirements 装完、模型下载完），本脚本只是薄封装。
2. CosyVoice 的调用签名会随版本变化。若报 `AttributeError: inference_xxx`，
   请对照你本地 `cosyvoice/cli/cosyvoice.py` 里的方法名改 `_synthesize()`。
3. 参照音如果没有对应文本（zero-shot 需要 prompt_text），默认走
   `inference_cross_lingual`（不需要文本，音色一致性略降）。
   想更好听：在 clips 目录放一个 `prompt-text.json`，内容形如
       {"g-05.wav": "希望你以后能够做的比我还好呦。"}
   本仓库的 20 条没有逐条转写，所以默认没有这个文件。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="elysia-tts-adapter")

_state: dict = {"model": None, "cv": None, "clips": None, "prompt_text": {}}
_lock = threading.Lock()


class TTSRequest(BaseModel):
    text: str
    ref: str = "g-05.wav"


def _load_prompt_text(clips_dir: str) -> dict:
    path = os.path.join(clips_dir, "prompt-text.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {str(k): str(v) for k, v in json.load(f).items()}
        except Exception:  # noqa: BLE001 - 转写文件坏了不该拖垮服务
            return {}
    return {}


def _get_engine(model_dir: str):
    """懒加载模型：第一次请求才吃内存/显存。"""
    with _lock:
        if _state["cv"] is None:
            from cosyvoice.cli.cosyvoice import CosyVoice2  # 延迟导入，便于无引擎环境语法检查

            _state["cv"] = CosyVoice2(model_dir, load_jit=False, load_trt=False, fp16=False)
        return _state["cv"]


def _resolve_ref(clips_dir: str, ref: str) -> str:
    name = ref if ref.endswith(".wav") else f"{ref}.wav"
    path = os.path.join(clips_dir, name)
    if not os.path.isfile(path):
        raise HTTPException(404, f"ref not found: {name}")
    return path


def _synthesize(text: str, ref: str) -> bytes:
    import torch
    import torchaudio
    from cosyvoice.utils.file_utils import load_wav

    cv = _get_engine(_state["model"])
    ref_path = _resolve_ref(_state["clips"], ref)
    prompt_speech = load_wav(ref_path, 16000)

    prompt_text = _state["prompt_text"].get(os.path.basename(ref_path))
    if prompt_text:
        gen = cv.inference_zero_shot(text, prompt_text, prompt_speech, stream=False)
    else:
        gen = cv.inference_cross_lingual(text, prompt_speech, stream=False)

    chunks = [out["tts_speech"] for out in gen]
    if not chunks:
        raise RuntimeError("empty tts output")

    wav = torch.cat(chunks, dim=1)
    buf = io.BytesIO()
    torchaudio.save(buf, wav, cv.sample_rate, format="wav")
    return buf.getvalue()


@app.get("/health")
def health():
    return {
        "ok": True,
        "model": _state["model"],
        "clips": _state["clips"],
        "loaded": _state["cv"] is not None,
        "prompt_text": len(_state["prompt_text"]),
    }


@app.post("/api/tts")
def tts(req: TTSRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "text is empty")
    try:
        audio = _synthesize(text, req.ref)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一转成 500
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc
    return Response(content=audio, media_type="audio/wav")


def main() -> None:
    parser = argparse.ArgumentParser(description="CosyVoice2 -> /api/tts 适配器")
    parser.add_argument("--model", required=True, help="CosyVoice2 模型目录，如 ./models/cosyvoice2")
    parser.add_argument("--clips", required=True, help="参照音目录，如 ./refs/elysia")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9880)
    args = parser.parse_args()

    _state["model"] = os.path.abspath(args.model)
    _state["clips"] = os.path.abspath(args.clips)
    _state["prompt_text"] = _load_prompt_text(_state["clips"])

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
