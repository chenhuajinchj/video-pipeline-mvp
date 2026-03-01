"""FastAPI 应用入口"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import storyboard, images, projects

app = FastAPI(
    title="小陈的视频流水线",
    description="AI 视频生产流水线 API — 从逐字稿到视频素材",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(storyboard.router, prefix="/api", tags=["分镜"])
app.include_router(images.router, prefix="/api", tags=["图片"])
app.include_router(projects.router, prefix="/api", tags=["项目"])

# 挂载静态文件（放在最后，作为 fallback）
SITE_DIR = Path(__file__).parent.parent / "site"
if SITE_DIR.exists():
    app.mount("/", StaticFiles(directory=str(SITE_DIR), html=True), name="site")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8600, reload=True)
