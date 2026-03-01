"""API 共享配置"""

import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "projects"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("请设置 GEMINI_API_KEY 环境变量")
    return key
