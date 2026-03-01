"""图片生成 API 路由"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.config import DATA_DIR, get_api_key
from core.models import ImageGenRequest, ImageResult, Shot, ProjectStatus
from core.images import generate_images, generate_images_stream

router = APIRouter()


def _load_project_shots(project_id: str) -> tuple[Path, list[Shot]]:
    project_dir = DATA_DIR / project_id
    storyboard_path = project_dir / "storyboard.json"
    if not storyboard_path.exists():
        raise HTTPException(404, f"项目 {project_id} 不存在或未生成分镜")
    raw = json.loads(storyboard_path.read_text(encoding="utf-8"))
    return project_dir, [Shot(**s) for s in raw]


def _update_project_status(project_dir: Path, status: ProjectStatus):
    meta_path = project_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = status.value
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/images/{project_id}")
async def create_images(project_id: str, request: ImageGenRequest | None = None):
    """批量生成图片，返回 SSE 流"""
    if request is None:
        request = ImageGenRequest()

    api_key = get_api_key()
    project_dir, shots = _load_project_shots(project_id)
    _update_project_status(project_dir, ProjectStatus.IMAGES_IN_PROGRESS)

    async def event_stream():
        async for result in generate_images_stream(
            project_id=project_id,
            shots=shots,
            style=request.style.value,
            api_key=api_key,
            project_dir=project_dir,
            concurrency=request.concurrency,
            aspect_ratio=request.aspect_ratio,
        ):
            yield f"data: {result.model_dump_json()}\n\n"
        _update_project_status(project_dir, ProjectStatus.IMAGES_DONE)
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/images/{project_id}", response_model=list[ImageResult])
async def get_images(project_id: str):
    """获取项目的图片生成结果"""
    project_dir = DATA_DIR / project_id
    visuals_dir = project_dir / "visuals"
    if not visuals_dir.exists():
        raise HTTPException(404, "尚未生成图片")

    storyboard_path = project_dir / "storyboard.json"
    raw = json.loads(storyboard_path.read_text(encoding="utf-8"))

    results = []
    for shot in raw:
        num = shot["shot_number"]
        filename = f"{str(num).zfill(3)}.png"
        filepath = visuals_dir / filename
        if shot.get("is_post_production"):
            results.append(ImageResult(shot_number=num, status="skipped"))
        elif filepath.exists():
            results.append(ImageResult(shot_number=num, file_path=f"visuals/{filename}", status="success"))
        else:
            results.append(ImageResult(shot_number=num, status="pending"))

    return results
