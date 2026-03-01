"""Pydantic 数据模型"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Style(str, Enum):
    DEFAULT = "default"
    TECH = "tech"
    KNOWLEDGE = "knowledge"


class StoryboardRequest(BaseModel):
    script_text: str = Field(..., description="逐字稿内容")
    style: str = Field(default="AI科技/知识分享", description="视频风格")
    duration: str = Field(default="6-10分钟", description="目标时长")


class Shot(BaseModel):
    shot_number: int
    time_range: str
    script_text: str
    asset_type: str
    image_prompt: str
    mood: str
    is_post_production: bool = False


class StoryboardResult(BaseModel):
    project_id: str
    shots: list[Shot]
    warnings: list[str] = []


class ImageGenRequest(BaseModel):
    style: Style = Style.DEFAULT
    concurrency: int = Field(default=3, ge=1, le=10)
    aspect_ratio: str = Field(default="16:9")


class ImageResult(BaseModel):
    shot_number: int
    file_path: str | None = None
    status: str  # success, failed, skipped
    error: str | None = None


class ProjectStatus(str, Enum):
    CREATED = "created"
    STORYBOARD_DONE = "storyboard_done"
    IMAGES_IN_PROGRESS = "images_in_progress"
    IMAGES_DONE = "images_done"


class ProjectInfo(BaseModel):
    id: str
    name: str
    created_at: datetime
    status: ProjectStatus = ProjectStatus.CREATED
    shot_count: int = 0
    style: str = ""
