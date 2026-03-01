"""图片生成服务 — 从现有 generate_images.py 提取"""

import asyncio
import base64
import json
from pathlib import Path
from typing import AsyncIterator

import httpx

from .models import ImageResult, Shot

GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
STYLES_DIR = Path(__file__).parent / "styles"


def _load_style(style_name: str) -> str:
    style_path = STYLES_DIR / f"{style_name}.txt"
    if not style_path.exists():
        style_path = STYLES_DIR / "default.txt"
    if not style_path.exists():
        return ""
    return style_path.read_text(encoding="utf-8").strip()


async def _generate_single_image(
    shot: Shot,
    style_prefix: str,
    aspect_ratio: str,
    output_dir: Path,
    api_key: str,
    client: httpx.AsyncClient,
) -> ImageResult:
    """为单个镜头生成图片"""
    filename = f"{str(shot.shot_number).zfill(3)}.png"
    output_path = output_dir / filename

    full_prompt = (
        f"{style_prefix}\n\n"
        f"Subject: {shot.image_prompt}\n\n"
        f"Aspect ratio: {aspect_ratio}.\n"
        f"IMPORTANT: Follow the STYLE REQUIREMENTS above exactly. "
        f"Do NOT add text, letters, or words into the image. "
        f"Do NOT use photorealistic style. "
        f"Keep the illustration style consistent with the style requirements."
    )

    url = GEMINI_API_URL.format(model=GEMINI_IMAGE_MODEL) + f"?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    max_retries = 2
    for attempt in range(max_retries):
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            resp_data = resp.json()

            parts = resp_data["candidates"][0]["content"]["parts"]
            image_data = None
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"]["data"]
                    break

            if image_data is None:
                raise RuntimeError("响应中未找到图片数据")

            img_bytes = base64.b64decode(image_data)
            output_path.write_bytes(img_bytes)

            return ImageResult(
                shot_number=shot.shot_number,
                file_path=f"visuals/{filename}",
                status="success",
            )
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                return ImageResult(
                    shot_number=shot.shot_number,
                    file_path=None,
                    status="failed",
                    error=str(e),
                )

    # Should not reach here
    return ImageResult(shot_number=shot.shot_number, status="failed", error="unknown")


async def generate_images(
    project_id: str,
    shots: list[Shot],
    style: str,
    api_key: str,
    project_dir: Path,
    concurrency: int = 3,
    aspect_ratio: str = "16:9",
) -> list[ImageResult]:
    """批量生成图片，返回结果列表"""
    style_prefix = _load_style(style)
    visuals_dir = project_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    results: list[ImageResult] = []
    to_generate: list[Shot] = []

    for shot in shots:
        if shot.is_post_production:
            results.append(ImageResult(
                shot_number=shot.shot_number,
                status="skipped",
            ))
        else:
            to_generate.append(shot)

    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded_generate(shot: Shot) -> ImageResult:
        async with semaphore:
            async with httpx.AsyncClient(timeout=120) as client:
                return await _generate_single_image(
                    shot, style_prefix, aspect_ratio, visuals_dir, api_key, client
                )

    tasks = [_bounded_generate(shot) for shot in to_generate]
    gen_results = await asyncio.gather(*tasks)
    results.extend(gen_results)

    results.sort(key=lambda r: r.shot_number)
    return results


async def generate_images_stream(
    project_id: str,
    shots: list[Shot],
    style: str,
    api_key: str,
    project_dir: Path,
    concurrency: int = 3,
    aspect_ratio: str = "16:9",
) -> AsyncIterator[ImageResult]:
    """逐张生成图片并 yield 结果（用于 SSE）"""
    style_prefix = _load_style(style)
    visuals_dir = project_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    to_generate: list[Shot] = []
    for shot in shots:
        if shot.is_post_production:
            yield ImageResult(shot_number=shot.shot_number, status="skipped")
        else:
            to_generate.append(shot)

    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded_generate(shot: Shot) -> ImageResult:
        async with semaphore:
            async with httpx.AsyncClient(timeout=120) as client:
                return await _generate_single_image(
                    shot, style_prefix, aspect_ratio, visuals_dir, api_key, client
                )

    tasks = {asyncio.create_task(_bounded_generate(s)): s for s in to_generate}
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield result
