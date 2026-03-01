# 小陈的视频流水线

AI 驱动的视频生产流水线 — 从逐字稿到视频素材。

## 功能

- **分镜生成**：输入逐字稿，通过 Gemini Flash API 自动生成结构化分镜表
- **图片批量生成**：基于分镜表，通过 Gemini Image API 并发生成图片素材
- **项目管理**：创建、查看、编辑、删除、打包下载
- **双入口**：REST API + MCP Server

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key
export GEMINI_API_KEY=your-key

# 启动服务
python -m api.app
# 或
uvicorn api.app:app --host 0.0.0.0 --port 8600

# 访问
# API 文档: http://localhost:8600/docs
# 官网: http://localhost:8600/
```

## Docker 部署

```bash
# 创建 .env 文件
cp .env.example .env
# 编辑 .env 设置 GEMINI_API_KEY

# 启动
docker compose up -d
```

## MCP 配置

在 Claude Desktop 的 `claude_desktop_config.json` 中添加：

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

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/storyboard` | 生成分镜表 |
| POST | `/api/images/{id}` | 批量生成图片（SSE） |
| GET | `/api/images/{id}` | 查询图片状态 |
| GET | `/api/projects` | 列出项目 |
| GET | `/api/projects/{id}` | 项目详情 |
| PUT | `/api/projects/{id}/storyboard` | 编辑分镜 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| GET | `/api/download/{id}` | 打包下载 |
