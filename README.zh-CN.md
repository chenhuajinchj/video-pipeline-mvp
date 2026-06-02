[**English**](README.md) | 中文

# Video Pipeline MVP — AI 视频制作流水线

> 把脚本（逐字稿）自动转化为分镜图和插画，全程由 Gemini AI 驱动。双接口：REST API + MCP Server（兼容 Claude Desktop）。

**核心功能：**
- 用 Gemini Flash 从脚本文本生成结构化分镜
- 用 Gemini Image API 批量生成每个镜头的一致性插画
- 完整的项目生命周期管理（创建、编辑、下载）
- MCP Server，支持 AI Agent 集成（Claude Desktop 等）

## 解决什么问题

制作视频内容需要繁琐的手工劳动：逐句读脚本、决定每句配什么画面，再一张一张找图或出图。这套流水线把整个过程自动化。

**输入：** 脚本（逐字稿）——视频的完整旁白文本。

**输出：** 带 AI 生成插画的完整分镜，可直接导入视频剪辑软件。

流水线用 Gemini Flash 分析脚本并拆解为带视觉描述的镜头，再用 Gemini Image API 为每个镜头生成一致风格的插画。风格预设确保所有图片的视觉统一性。

## 工作流程

```
脚本文本 ──→ Gemini Flash ──→ 分镜（JSON）──→ Gemini Image API ──→ 图片（PNG）
                                ↓                                     ↓
                          逐镜头拆解                           visuals/001.png
                          含图片提示词                         visuals/002.png
                          和情绪标注                          visuals/003.png ...
```

## 快速开始

```bash
# 1. 克隆并安装依赖
git clone https://github.com/chenhuajinchj/video-pipeline-mvp.git
cd video-pipeline-mvp
pip install -r requirements.txt

# 2. 设置 Gemini API Key
export GEMINI_API_KEY=your-key

# 3. 启动服务
uvicorn api.app:app --host 0.0.0.0 --port 8600
# API 文档地址：http://localhost:8600/docs
```

## API 参考

### 生成分镜

```bash
curl -X POST http://localhost:8600/api/storyboard \
  -H "Content-Type: application/json" \
  -d '{
    "script_text": "你的完整脚本内容...",
    "style": "AI科技/知识分享",
    "duration": "6-10分钟"
  }'
```

**返回示例：**
```json
{
  "project_id": "a1b2c3d4e5f6",
  "shot_count": 25,
  "warnings": [],
  "shots": [
    {
      "shot_number": 1,
      "time_range": "0:00-0:15",
      "script_text": "脚本第一句话",
      "asset_type": "illustration",
      "image_prompt": "详细的视觉描述...",
      "mood": "curious",
      "is_post_production": false
    }
  ]
}
```

### 生成图片

```bash
# SSE 流式推送 — 实时获取进度
curl -N http://localhost:8600/api/images/PROJECT_ID \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"style": "default", "concurrency": 3}'
```

### 全部接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/storyboard` | 从脚本生成分镜 |
| `POST` | `/api/images/{id}` | 批量生成图片（SSE 流式） |
| `GET` | `/api/images/{id}` | 查询图片生成状态 |
| `GET` | `/api/projects` | 列出所有项目 |
| `GET` | `/api/projects/{id}` | 获取项目详情 |
| `PUT` | `/api/projects/{id}/storyboard` | 编辑分镜 |
| `DELETE` | `/api/projects/{id}` | 删除项目 |
| `GET` | `/api/download/{id}` | 下载项目为 zip |

## MCP Server

将此流水线接入 Claude Desktop 或任何支持 MCP 的 AI 客户端。

**配置方式**（`claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "video-pipeline": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/video-pipeline-mvp",
      "env": {
        "GEMINI_API_KEY": "your-api-key"
      }
    }
  }
}
```

**可用 MCP 工具：**

| 工具 | 说明 |
|------|------|
| `create_storyboard` | 从脚本文本生成分镜 |
| `list_projects` | 列出所有视频项目 |
| `get_project` | 获取项目详情（含分镜和图片） |
| `edit_storyboard` | 更新项目的分镜镜头 |
| `generate_images` | 为项目批量生成图片 |
| `get_image_status` | 检查图片生成进度 |
| `download_project` | 获取项目文件列表和下载链接 |

## Docker 部署

```bash
# 创建含 API Key 的 .env 文件
echo "GEMINI_API_KEY=your-key" > .env

# 启动
docker compose up -d

# 访问地址：http://localhost:8600
```

## 项目结构

```
video-pipeline-mvp/
├── api/                    # FastAPI 应用
│   ├── app.py              # 入口、中间件、路由挂载
│   ├── config.py           # 配置
│   └── routes/             # 路由处理器
│       ├── storyboard.py   # POST /api/storyboard
│       ├── images.py       # POST/GET /api/images/{id}
│       └── projects.py     # CRUD /api/projects
├── core/                   # 业务逻辑
│   ├── models.py           # Pydantic 数据模型（Shot、Project 等）
│   ├── storyboard.py       # Gemini Flash 分镜生成
│   ├── images.py           # Gemini Image API 批量生成
│   ├── prompts/            # Prompt 模板
│   └── styles/             # 风格预设（default.txt、tech.txt 等）
├── mcp_server/
│   └── server.py           # MCP stdio server，含 7 个工具
├── data/projects/          # 项目存储（自动创建）
├── site/                   # 静态前端
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── llms.txt                # AI 发现元数据
```

## 使用场景

**1. YouTube / 抖音知识类视频制作**

把脚本输入流水线，得到带插画的完整分镜。把图片导入剪辑软件（DaVinci Resolve、剪映），与配音对齐。

```bash
curl -X POST http://localhost:8600/api/storyboard \
  -d '{"script_text": "今天我们来聊聊 AI Agent 的未来发展方向..."}'
```

**2. AI Agent 工作流集成**

通过 MCP Server 让 Claude Desktop 管理整个视频制作流程——从脚本分析到图片生成——作为更大内容创作工作流的一环。

**3. 批量内容生产**

通过 REST API 程序化批量创建视频项目。每个项目相互独立，有各自的分镜和图片资产。

**4. 分镜迭代**

先生成初版分镜，通过 API 检视并编辑镜头，再只对最终版本生成图片。"编辑 → 重新生成"的循环既快又省钱。

## 局限性

- **图片生成依赖 Gemini Image API** — 需要有效的 `GEMINI_API_KEY` 且已开通图片生成权限
- **不含视频合成** — 此流水线产出分镜 + 图片，不产出成片。最终合成需使用视频剪辑软件
- **不含音频/配音生成** — 脚本文本仅作为输入，不会转化为语音
- **风格一致性为尽力而为** — Gemini Image API 在同一风格预设下生成的插画具有一致性，但跨会话结果可能有差异
- **提示词针对中文优化** — 分镜生成提示词为中文脚本设计，其他语言也可使用但效果不保证

## 许可证

MIT
