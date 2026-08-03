# ShortsFlow Studio

An asset library and draft generator for CapCut/Jianying-ready projects using copy, narration, subtitles, and background music.

## English

ShortsFlow Studio is a human-first short video production workbench. It helps teams accumulate reusable copy, narration, subtitle, voice, and background music assets, then combine selected assets into editable Jianying/CapCut draft folders.

Current workflow:

```text
Select source videos -> confirm product and tags -> move and rename videos by product
-> prepare copy, narration/subtitles, and background music -> select assets manually
-> generate a Jianying/CapCut draft
```

Key features:

- Classify source videos by product and tags, then move and rename original files without copying them into a separate workspace.
- Maintain content, narration/subtitle, voice, and background music libraries.
- Search and select assets manually before generating a draft.
- Generate video-free draft folders directly inside the confirmed Jianying draft directory.
- Add timestamps to draft names.
- Warn when the same asset combination has been generated before, without blocking generation.
- Keep draft records in the workbench while allowing records to be deleted independently from disk folders.

For detailed requirements and current engineering state, see [PROJECT_CURRENT.md](PROJECT_CURRENT.md).

## Screenshots

Production overview shows material counts, result status, and the manual production flow.

![Production overview](docs/images/production-overview.png)

The content library stores copy, narration/subtitle, and voice resources.

![Content library voices](docs/images/content-library-voices.png)

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
npm --prefix frontend run build
```

Development server:

```bash
bash scripts/run_dev.sh
```

User-level systemd service:

```bash
systemctl --user status product-video-automation
systemctl --user restart product-video-automation
journalctl --user -u product-video-automation -f
```

Open `http://127.0.0.1:8000/workbench/` locally. The service can also be accessed from other computers on the LAN through `http://SERVER_LAN_IP:8000/workbench/`. On first access, initialize the administrator account.

## Current Workflow API

Business APIs are under `/api/v1`. Human-first material, copy, narration, and draft APIs are under `/api/v1/human`:

```text
POST      /material-classifications
GET       /classified-materials
GET       /classified-materials/{asset_id}/video

GET/POST  /api/v1/products
PATCH     /api/v1/products/{product_id}
GET/POST  /tag-categories
GET/POST  /tags

POST      /copies/iterations
POST      /copies/iterations/{record_id}/continue
GET/DELETE /copies/iterations[/{record_id}]
GET       /copies/library
PATCH     /copies/{content_id}/review

POST      /copies/audio-to-text
GET/POST  /narrations/...
GET       /narrations/{id}/audio
DELETE    /narrations/{id}
POST      /voice-preview
GET       /voice-catalog
GET       /voice-catalog/{sequence}
GET/POST  /jianying-drafts
POST      /jianying-drafts/duplicate-count
POST      /jianying-drafts/duplicate-counter/reset
DELETE    /jianying-drafts/{draft_id}

GET/PUT   /api/v1/model-profiles
GET/POST  /api/v1/music-resources/...
```

APIs require an administrator Bearer Token. The complete contract is available from `/openapi.json`.

## Output

- Jianying/CapCut draft baseline: vertical 1080x1920, 30fps.
- Drafts are written directly into the confirmed Jianying draft directory.
- Draft folders contain `draft_content.json`, `draft_info.json`, and `draft_meta_info.json`.
- Drafts do not generate video tracks.
- Copy, subtitles/narration, and background music are written into text and audio tracks.
- Audio files are copied into the draft-local `assets/audio` directory to avoid missing audio references when opened in Jianying.

Media probing and music extraction require `ffmpeg` and `ffprobe`.

Health check:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

## 中文

ShortsFlow Studio 是一个人工主导的产品短视频生产工作台。系统用于积累文案、旁白、字幕、音色和背景音乐素材，并把人工选择的物料组合直接生成可在剪映专业版继续编辑的草稿目录。

当前流程：

```text
选择原视频 -> 确认产品和标签 -> 移动到产品文件夹并重命名
-> 准备文案内容、旁白/字幕和背景音乐 -> 人工选择资源 -> 生成剪映草稿
```

主要功能：

- 素材归类：维护产品与标签，按产品和标签移动并重命名原视频，不复制到工作区。
- 内容文库：沉淀文案内容、旁白字幕和音色资源。
- 背景音乐：上传本地音频或从短视频链接提取音频，试听后维护名称和标签。
- 剪映草稿：确认剪映草稿目录，从三库中模糊查询并选择物料，生成不含视频轨道的半成品草稿。
- 草稿名称带时间戳。
- 重复物料组合会弹窗提示历史生成次数，但不阻止继续生成。
- 剪映草稿记录可在工作台删除，删除记录不会删除磁盘上的草稿目录。

详细规则和当前工程状态见 [PROJECT_CURRENT.md](PROJECT_CURRENT.md)。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
npm --prefix frontend run build
```

开发方式：

```bash
bash scripts/run_dev.sh
```

用户级 systemd 服务：

```bash
systemctl --user status product-video-automation
systemctl --user restart product-video-automation
journalctl --user -u product-video-automation -f
```

本机打开 `http://127.0.0.1:8000/workbench/`。服务监听局域网接口，其他电脑可使用 `http://服务器局域网IP:8000/workbench/` 访问；首次访问时初始化管理员账号。

生产环境只需要 `requirements.txt`；运行测试时安装 `requirements-dev.txt`。模型日志留存清理由 Web 服务内置任务执行，不需要 Redis 或独立 Worker。

当前源码、ORM 和数据库不再包含旧人工粗剪、批次扫描、候选片段、质量审核、框架、卡点、自动混剪、系统内渲染、成片和热播模块。历史 Alembic 文件保留用于旧库顺序升级。
