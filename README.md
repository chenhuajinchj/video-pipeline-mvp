# Video Pipeline MVP — AI Video Production Pipeline

> Transform a script into storyboard shots and illustration images, fully automated with Gemini AI. Dual interface: REST API + MCP Server for Claude Desktop.

**Core capabilities:**
- Generate structured storyboards from script text (Gemini Flash)
- Batch-generate consistent illustration images per shot (Gemini Image API)
- Full project lifecycle management (create, edit, download)
- MCP Server for AI agent integration (Claude Desktop, etc.)

## What This Solves

Creating video content requires tedious manual work: reading a script, deciding what visuals to show for each sentence, then finding or creating those images one by one. This pipeline automates the entire process.

**Input:** A script (逐字稿) — the full text narration for your video.

**Output:** A complete storyboard with AI-generated illustration images, ready for video editing.

The pipeline uses Gemini Flash to analyze your script and decompose it into shots with visual descriptions, then uses Gemini Image API to generate consistent illustrations for each shot. Style presets ensure visual consistency across all images.

## How It Works

```
Script Text ──→ Gemini Flash ──→ Storyboard (JSON) ──→ Gemini Image API ──→ Images (PNG)
                                  ↓                                          ↓
                            shot-by-shot breakdown                    visuals/001.png
                            with image prompts                       visuals/002.png
                            and mood annotations                     visuals/003.png ...
```

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/chenhuajinchj/video-pipeline-mvp.git
cd video-pipeline-mvp
pip install -r requirements.txt

# 2. Set your Gemini API key
export GEMINI_API_KEY=your-key

# 3. Start the server
uvicorn api.app:app --host 0.0.0.0 --port 8600
# API docs at http://localhost:8600/docs
```

## API Reference

### Generate Storyboard

```bash
curl -X POST http://localhost:8600/api/storyboard \
  -H "Content-Type: application/json" \
  -d '{
    "script_text": "Your full script text here...",
    "style": "AI科技/知识分享",
    "duration": "6-10分钟"
  }'
```

**Response:**
```json
{
  "project_id": "a1b2c3d4e5f6",
  "shot_count": 25,
  "warnings": [],
  "shots": [
    {
      "shot_number": 1,
      "time_range": "0:00-0:15",
      "script_text": "First sentence of the script",
      "asset_type": "illustration",
      "image_prompt": "A detailed visual description...",
      "mood": "curious",
      "is_post_production": false
    }
  ]
}
```

### Generate Images

```bash
# SSE stream — get real-time progress
curl -N http://localhost:8600/api/images/PROJECT_ID \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"style": "default", "concurrency": 3}'
```

### All Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/storyboard` | Generate storyboard from script |
| `POST` | `/api/images/{id}` | Batch generate images (SSE stream) |
| `GET` | `/api/images/{id}` | Query image generation status |
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/{id}` | Get project details |
| `PUT` | `/api/projects/{id}/storyboard` | Edit storyboard |
| `DELETE` | `/api/projects/{id}` | Delete project |
| `GET` | `/api/download/{id}` | Download project as zip |

## MCP Server

Connect this pipeline to Claude Desktop or any MCP-compatible AI client.

**Configuration** (`claude_desktop_config.json`):

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

**Available MCP Tools:**

| Tool | Description |
|------|-------------|
| `create_storyboard` | Generate storyboard from script text |
| `list_projects` | List all video projects |
| `get_project` | Get project details with storyboard and images |
| `edit_storyboard` | Update project storyboard shots |
| `generate_images` | Batch generate images for a project |
| `get_image_status` | Check image generation progress |
| `download_project` | Get project file listing and download URL |

## Docker Deployment

```bash
# Create .env with your API key
echo "GEMINI_API_KEY=your-key" > .env

# Start
docker compose up -d

# Access at http://localhost:8600
```

## Architecture

```
video-pipeline-mvp/
├── api/                    # FastAPI application
│   ├── app.py              # App entry point, middleware, route mounting
│   ├── config.py           # Configuration
│   └── routes/             # API route handlers
│       ├── storyboard.py   # POST /api/storyboard
│       ├── images.py       # POST/GET /api/images/{id}
│       └── projects.py     # CRUD /api/projects
├── core/                   # Business logic
│   ├── models.py           # Pydantic models (Shot, Project, etc.)
│   ├── storyboard.py       # Gemini Flash storyboard generation
│   ├── images.py           # Gemini Image API batch generation
│   ├── prompts/            # Prompt templates
│   └── styles/             # Style presets (default.txt, tech.txt, etc.)
├── mcp_server/
│   └── server.py           # MCP stdio server with 7 tools
├── data/projects/          # Project storage (auto-created)
├── site/                   # Static frontend
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── llms.txt                # AI discovery metadata
```

## Use Cases

**1. YouTube / Douyin Knowledge Video Production**

Feed your script into the pipeline, get a complete storyboard with illustrations. Import images into your video editor (DaVinci Resolve, CapCut) and align with voiceover.

```bash
curl -X POST http://localhost:8600/api/storyboard \
  -d '{"script_text": "今天我们来聊聊 AI Agent 的未来发展方向..."}'
```

**2. AI Agent Workflow Integration**

Use the MCP server to let Claude Desktop manage the entire video production process — from script analysis to image generation — as part of a larger content creation workflow.

**3. Batch Content Production**

Use the REST API to programmatically create videos at scale. Each project is isolated with its own storyboard and image assets.

**4. Storyboard Iteration**

Generate an initial storyboard, review and edit shots via the API, then generate images only for the final version. The edit → regenerate cycle is fast and cheap.

## Limitations

- **Image generation uses Gemini Image API** — requires a valid `GEMINI_API_KEY` with image generation access
- **No video assembly** — this pipeline produces storyboard + images, not finished video files. Use a video editor for final assembly
- **No audio/voice generation** — script text is input only, not converted to speech
- **Style consistency is best-effort** — Gemini Image API produces consistent illustrations within a style preset, but results may vary across sessions
- **Chinese-optimized prompts** — storyboard generation prompts are designed for Chinese-language scripts, though other languages may work

## License

MIT
