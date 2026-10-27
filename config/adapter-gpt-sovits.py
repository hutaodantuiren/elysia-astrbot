"""
GPT-SoVITS -> 本仓库 TTS 契约 的参考适配器（可选）
=================================================

把 GPT-SoVITS 的 api_v2 包成：
    POST /api/tts  {"text": "...", "ref": "g-05.wav"}  ->  audio/wav

用法
----
1. 先启动 GPT-SoVITS 的 API 服务（默认 http://127.0.0.1:9880）。
2. 起本适配器：
       pip install fastapi uvicorn requests
       python config/adapter-gpt-sovits.py \
           --upstream http://127.0.0.1:9880 \
           --clips ./refs/elysia \
           --port 9881

说明
----
- GPT-SoVITS 的 zero-shot 需要参照音**文本**。ai_v2 接口里 `prompt_text` 必填，
  所以请在 clips 目录放 `prompt-text.json`：
      {"g-05.wav": "希望你以后能够做的比我还好呦。"}
  没有转写就先用 ASR 跑一遍，或改用它的 webui 手动合成。
- 字段名以你本地 GPT-SoVITS 版本为准（`api_v2.py` 里的 `tts_fn` 签名）。
"""

from __future__ import annotations

import argparse
import json
import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="elysia-gpt-sovits-adapter")

_state: dict = {"upstream": "", "clips": "", "prompt_text": {}, "lang": "zh", "timeout": 120}


class TTSRequest(BaseModel):
    text: str
    ref: str = "g-05.wav"


def _load_prompt_text(clips_dir: str) -> dict:
    path = os.path.join(clips_dir, "prompt-text.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {str(k): str(v) for k, v in json.load(f).items()}
        except Exception:  # noqa: BLE001
            return {}
    return {}


@app.get("/health")
def health():
    return {"ok": True, "upstream": _state["upstream"], "prompt_text": len(_state["prompt_text"])}


@app.post("/api/tts")
def tts(req: TTSRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "text is empty")

    name = req.ref if req.ref.endswith(".wav") else f"{req.ref}.wav"
    ref_path = os.path.join(_state["clips"], name)
    if not os.path.isfile(ref_path):
        raise HTTPException(404, f"ref not found: {name}")

    prompt_text = _state["prompt_text"].get(name, "")
    if not prompt_text:
        raise HTTPException(
            400,
            f"missing prompt_text for {name}; create prompt-text.json in clips dir",
        )

    params = {
        "text": text,
        "text_lang": _state["lang"],
        "ref_audio_path": ref_path,
        "prompt_text": prompt_text,
        "prompt_lang": _state["lang"],
        "media_type": "wav",
        "streaming_mode": "false",
    }

    try:
        r = requests.get(f"{_state['upstream']}/tts", params=params, timeout=_state["timeout"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"upstream unreachable: {exc}") from exc

    if r.status_code != 200:
        detail = r.text[:300] if r.text else "(empty body)"
        raise HTTPException(r.status_code, f"upstream error: {detail}")

    return Response(content=r.content, media_type="audio/wav")


def main() -> None:
    parser = argparse.ArgumentParser(description="GPT-SoVITS -> /api/tts 适配器")
    parser.add_argument("--upstream", required=True, help="GPT-SoVITS API 地址，如 http://127.0.0.1:9880")
    parser.add_argument("--clips", required=True, help="参照音目录")
    parser.add_argument("--lang", default="zh", help="文本与参照音语言：zh/ja/en")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9881)
    args = parser.parse_args()

    _state["upstream"] = args.upstream.rstrip("/")
    _state["clips"] = os.path.abspath(args.clips)
    _state["lang"] = args.lang
    _state["prompt_text"] = _load_prompt_text(_state["clips"])

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
