"""分镜生成服务 — 从现有 generate_storyboard.py 提取"""

import json
import re
from pathlib import Path
from string import Template

import httpx

from .models import Shot, StoryboardRequest, StoryboardResult

PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "storyboard_prompt.txt"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _load_prompt_template() -> str:
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


def _build_prompt(script_content: str, video_style: str, total_duration: str) -> str:
    template = Template(_load_prompt_template())
    return template.safe_substitute(
        script_content=script_content,
        video_style=video_style,
        total_duration=total_duration,
    )


def _parse_json_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"期望 JSON 数组，实际得到 {type(data).__name__}")
    return data


def _validate_storyboard(shots: list[dict]) -> list[str]:
    warnings = []
    required = ["shot_number", "time_range", "script_text", "asset_type", "image_prompt", "mood", "is_post_production"]
    for i, shot in enumerate(shots):
        missing = [k for k in required if k not in shot]
        if missing:
            warnings.append(f"镜头 {i+1}: 缺少字段 {missing}")
        if shot.get("asset_type") in ("数据", "文字", "分屏") and not shot.get("is_post_production"):
            warnings.append(f"镜头 {shot.get('shot_number', i+1)}: {shot['asset_type']} 类型应标记 is_post_production=true")
    return warnings


async def generate_storyboard(
    request: StoryboardRequest,
    api_key: str,
    project_id: str,
    project_dir: Path,
) -> StoryboardResult:
    """生成分镜表，保存到项目目录"""
    prompt = _build_prompt(request.script_text, request.style, request.duration)
    url = GEMINI_API_URL.format(model=GEMINI_MODEL) + f"?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    max_retries = 2
    last_error = None
    async with httpx.AsyncClient(timeout=120) as client:
        for attempt in range(max_retries):
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                raw_shots = _parse_json_response(text)
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(3)
        else:
            raise RuntimeError(f"分镜生成失败: {last_error}")

    warnings = _validate_storyboard(raw_shots)
    shots = [Shot(**s) for s in raw_shots]

    # 保存到项目目录
    project_dir.mkdir(parents=True, exist_ok=True)
    storyboard_path = project_dir / "storyboard.json"
    storyboard_path.write_text(
        json.dumps([s.model_dump() for s in shots], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return StoryboardResult(project_id=project_id, shots=shots, warnings=warnings)
