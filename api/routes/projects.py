"""项目管理 API 路由"""

import json
import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.config import DATA_DIR
from core.models import ProjectInfo, Shot

router = APIRouter()


@router.get("/projects", response_model=list[ProjectInfo])
async def list_projects():
    """列出所有项目"""
    projects = []
    if not DATA_DIR.exists():
        return projects
    for d in sorted(DATA_DIR.iterdir()):
        meta_path = d / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            projects.append(ProjectInfo(**meta))
    return projects


@router.get("/projects/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str):
    """获取项目详情"""
    meta_path = DATA_DIR / project_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(404, "项目不存在")
    return ProjectInfo(**json.loads(meta_path.read_text(encoding="utf-8")))


@router.put("/projects/{project_id}/storyboard")
async def update_storyboard(project_id: str, shots: list[Shot]):
    """编辑分镜"""
    project_dir = DATA_DIR / project_id
    storyboard_path = project_dir / "storyboard.json"
    if not storyboard_path.exists():
        raise HTTPException(404, "项目不存在")
    storyboard_path.write_text(
        json.dumps([s.model_dump() for s in shots], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 更新 shot_count
    meta_path = project_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["shot_count"] = len(shots)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"message": "分镜已更新", "shot_count": len(shots)}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    project_dir = DATA_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(404, "项目不存在")
    shutil.rmtree(project_dir)
    return {"message": "项目已删除"}


@router.get("/download/{project_id}")
async def download_project(project_id: str):
    """打包下载项目"""
    project_dir = DATA_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(404, "项目不存在")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(project_dir)
                zf.write(file_path, arcname)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_id}.zip"},
    )
