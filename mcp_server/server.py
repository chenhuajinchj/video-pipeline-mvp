"""MCP Server — 通过 stdio 为 AI 客户端提供视频流水线工具"""

import asyncio
import json
import os
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from core.models import (
    ImageGenRequest,
    Shot,
    StoryboardRequest,
    ProjectInfo,
    ProjectStatus,
)
from core.storyboard import generate_storyboard
from core.images import generate_images

DATA_DIR = Path(__file__).parent.parent / "data" / "projects"
DATA_DIR.mkdir(parents=True, exist_ok=True)

server = Server("video-pipeline")


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("请设置 GEMINI_API_KEY 环境变量")
    return key


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_storyboard",
            description="从逐字稿生成分镜表。输入完整逐字稿文本，返回结构化分镜数据。",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_text": {"type": "string", "description": "逐字稿内容"},
                    "style": {"type": "string", "description": "视频风格", "default": "AI科技/知识分享"},
                    "duration": {"type": "string", "description": "目标时长", "default": "6-10分钟"},
                },
                "required": ["script_text"],
            },
        ),
        Tool(
            name="list_projects",
            description="列出所有视频项目",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_project",
            description="获取项目详情，包括分镜数据和图片状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目 ID"},
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="edit_storyboard",
            description="编辑项目的分镜表",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目 ID"},
                    "shots": {
                        "type": "array",
                        "description": "修改后的分镜数组",
                        "items": {"type": "object"},
                    },
                },
                "required": ["project_id", "shots"],
            },
        ),
        Tool(
            name="generate_images",
            description="为项目批量生成图片素材",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目 ID"},
                    "style": {
                        "type": "string",
                        "description": "风格: default, tech, knowledge",
                        "default": "default",
                    },
                    "concurrency": {
                        "type": "integer",
                        "description": "并发数 (1-10)",
                        "default": 3,
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_image_status",
            description="查询图片生成进度和结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目 ID"},
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="download_project",
            description="获取项目下载信息（文件路径）",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目 ID"},
                },
                "required": ["project_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "create_storyboard":
        import uuid
        api_key = _get_api_key()
        project_id = uuid.uuid4().hex[:12]
        project_dir = DATA_DIR / project_id

        request = StoryboardRequest(
            script_text=arguments["script_text"],
            style=arguments.get("style", "AI科技/知识分享"),
            duration=arguments.get("duration", "6-10分钟"),
        )
        result = await generate_storyboard(request, api_key, project_id, project_dir)

        # 保存元数据
        from datetime import datetime, timezone
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

        # 保存逐字稿
        (project_dir / "script.md").write_text(request.script_text, encoding="utf-8")

        return [TextContent(
            type="text",
            text=json.dumps({
                "project_id": project_id,
                "shot_count": len(result.shots),
                "warnings": result.warnings,
                "shots_preview": [
                    {"shot_number": s.shot_number, "time_range": s.time_range, "asset_type": s.asset_type}
                    for s in result.shots[:5]
                ],
            }, ensure_ascii=False, indent=2),
        )]

    elif name == "list_projects":
        projects = []
        if DATA_DIR.exists():
            for d in sorted(DATA_DIR.iterdir()):
                meta_path = d / "meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    projects.append({
                        "id": meta["id"],
                        "name": meta["name"],
                        "status": meta["status"],
                        "shot_count": meta.get("shot_count", 0),
                        "created_at": meta["created_at"],
                    })
        return [TextContent(type="text", text=json.dumps(projects, ensure_ascii=False, indent=2))]

    elif name == "get_project":
        project_id = arguments["project_id"]
        project_dir = DATA_DIR / project_id
        meta_path = project_dir / "meta.json"
        if not meta_path.exists():
            return [TextContent(type="text", text=f"错误：项目 {project_id} 不存在")]

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        storyboard_path = project_dir / "storyboard.json"
        if storyboard_path.exists():
            meta["shots"] = json.loads(storyboard_path.read_text(encoding="utf-8"))

        # 图片状态
        visuals_dir = project_dir / "visuals"
        if visuals_dir.exists():
            meta["images"] = [f.name for f in sorted(visuals_dir.glob("*.png"))]

        return [TextContent(type="text", text=json.dumps(meta, ensure_ascii=False, indent=2))]

    elif name == "edit_storyboard":
        project_id = arguments["project_id"]
        project_dir = DATA_DIR / project_id
        storyboard_path = project_dir / "storyboard.json"
        if not storyboard_path.exists():
            return [TextContent(type="text", text=f"错误：项目 {project_id} 不存在")]

        shots = [Shot(**s) for s in arguments["shots"]]
        storyboard_path.write_text(
            json.dumps([s.model_dump() for s in shots], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return [TextContent(type="text", text=f"分镜已更新，共 {len(shots)} 个镜头")]

    elif name == "generate_images":
        project_id = arguments["project_id"]
        project_dir = DATA_DIR / project_id
        storyboard_path = project_dir / "storyboard.json"
        if not storyboard_path.exists():
            return [TextContent(type="text", text=f"错误：项目 {project_id} 不存在")]

        api_key = _get_api_key()
        raw = json.loads(storyboard_path.read_text(encoding="utf-8"))
        shots = [Shot(**s) for s in raw]

        results = await generate_images(
            project_id=project_id,
            shots=shots,
            style=arguments.get("style", "default"),
            api_key=api_key,
            project_dir=project_dir,
            concurrency=arguments.get("concurrency", 3),
        )

        summary = {
            "total": len(results),
            "success": sum(1 for r in results if r.status == "success"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "skipped": sum(1 for r in results if r.status == "skipped"),
            "results": [r.model_dump() for r in results],
        }
        return [TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))]

    elif name == "get_image_status":
        project_id = arguments["project_id"]
        project_dir = DATA_DIR / project_id
        visuals_dir = project_dir / "visuals"

        if not visuals_dir.exists():
            return [TextContent(type="text", text="尚未开始生成图片")]

        images = sorted(visuals_dir.glob("*.png"))
        storyboard_path = project_dir / "storyboard.json"
        total = 0
        if storyboard_path.exists():
            raw = json.loads(storyboard_path.read_text(encoding="utf-8"))
            total = sum(1 for s in raw if not s.get("is_post_production"))

        return [TextContent(type="text", text=json.dumps({
            "completed": len(images),
            "total_to_generate": total,
            "files": [f.name for f in images],
        }, ensure_ascii=False, indent=2))]

    elif name == "download_project":
        project_id = arguments["project_id"]
        project_dir = DATA_DIR / project_id
        if not project_dir.exists():
            return [TextContent(type="text", text=f"错误：项目 {project_id} 不存在")]

        files = [str(f.relative_to(project_dir)) for f in project_dir.rglob("*") if f.is_file()]
        return [TextContent(type="text", text=json.dumps({
            "project_id": project_id,
            "project_path": str(project_dir),
            "file_count": len(files),
            "files": files,
            "api_download_url": f"/api/download/{project_id}",
        }, ensure_ascii=False, indent=2))]

    return [TextContent(type="text", text=f"未知工具: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
