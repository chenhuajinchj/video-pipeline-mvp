"""分镜 API 路由"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.config import DATA_DIR, get_api_key
from core.models import StoryboardRequest, StoryboardResult, ProjectInfo, ProjectStatus
from core.storyboard import generate_storyboard

router = APIRouter()


@router.post("/storyboard", response_model=StoryboardResult)
async def create_storyboard(request: StoryboardRequest):
    """从逐字稿生成分镜表，同时创建项目"""
    api_key = get_api_key()
    project_id = uuid.uuid4().hex[:12]
    project_dir = DATA_DIR / project_id

    result = await generate_storyboard(request, api_key, project_id, project_dir)

    # 保存项目元数据
    import json
    meta = ProjectInfo(
        id=project_id,
        name=f"项目-{project_id[:6]}",
        created_at=datetime.now(timezone.utc),
        status=ProjectStatus.STORYBOARD_DONE,
        shot_count=len(result.shots),
        style=request.style,
    )
    meta_path = project_dir / "meta.json"
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")

    # 保存原始逐字稿
    script_path = project_dir / "script.md"
    script_path.write_text(request.script_text, encoding="utf-8")

    return result
