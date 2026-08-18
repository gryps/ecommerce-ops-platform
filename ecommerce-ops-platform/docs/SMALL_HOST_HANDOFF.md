# 小主机部署交接文档

> 更新时间：2026-08-17（Asia/Shanghai）
>
> 用途：记录当前小主机运行环境、服务状态、迁移边界和下一阶段 ComfyUI 文生视频/图生视频开发入口。

## 1. 机器定位

这台小主机适合作为：

- 电商运营平台运行服务器。
- ComfyUI 画布、工作流编排和 API 调度中控。
- 文生视频、图生视频任务的业务参数管理、提交、回收和记录节点。

这台小主机不适合作为：

- 本地 AI 算力服务器。
- 本地文生图、图生图、文生视频、图生视频推理机器。
- 本地大模型、视频模型或显卡依赖环境。

后续原则：**小主机管业务流程和工作流，模型 API 管生成。**

## 2. 硬件和系统

```text
主机：gryps@192.168.31.24
CPU：Intel Celeron J3455，4 核
内存：约 6.7 GiB 可见内存，4.0 GiB swap
磁盘：根分区约 98G，当前约 82G 可用
系统：Ubuntu 26.04 LTS minimal
Python 运行时：/home/gryps/runtime/python/current -> Python 3.12.14
Node.js：v22.22.1
npm registry：https://registry.npmmirror.com/
apt 源：上海交通大学镜像
```

SSH 建议使用：

```bash
ssh -F /dev/null gryps@192.168.31.24
```

说明：WSL 本地默认 SSH 配置曾出现 systemd ssh proxy 配置权限问题，因此继续使用 `-F /dev/null` 避开本地全局配置干扰。

## 3. 当前访问地址

```text
电商运营平台：http://192.168.31.24:8000/workbench/
ComfyUI：http://192.168.31.24:8188/
```

服务均已配置为用户级 systemd 服务，且已开启用户 linger，机器重启后应随用户服务恢复。

## 3.1 当前开发主环境

后续开发直接在小主机上进行，小主机项目目录已经初始化为 Git 工作树：

```text
源码根目录：/home/gryps/apps/ecommerce-ops-platform
当前分支：master
版本文件：/home/gryps/apps/ecommerce-ops-platform/VERSION
忽略规则：/home/gryps/apps/ecommerce-ops-platform/.gitignore
```

约定：

- 运行态、数据库、日志、虚拟环境、`node_modules`、ComfyUI 运行目录和密钥配置不进入 Git。
- 小主机上的源码是后续开发主线；本机 WSL 只作为必要时的辅助环境。
- 每次阶段性修改后先在小主机运行测试和部署自检，再提交 Git。
- 不要把 `ops-workbench/UBUNTU_TEST_SECRET.txt` 这类本地测试文件提交进主线。

## 4. 电商运营平台服务

```text
服务名：product-video-automation
源码目录：/home/gryps/apps/ecommerce-ops-platform
运行目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime
后端代码：/home/gryps/apps/ecommerce-ops-platform/ops-workbench
虚拟环境：/home/gryps/apps/ecommerce-ops-platform/.venv
静态资源：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/static-workbench
数据库：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/databases/workbench.db
```

常用命令：

```bash
systemctl --user status product-video-automation
systemctl --user restart product-video-automation
journalctl --user -u product-video-automation -f
curl -sS http://127.0.0.1:8000/api/health
cd /home/gryps/apps/ecommerce-ops-platform/ops-workbench
scripts/verify_deploy.sh
scripts/write_deploy_manifest.py
```

当前健康检查应返回：

```json
{"ok":true,"ffmpeg_available":true,"ffprobe_available":true}
```

数据库说明：

- 小主机当前使用 SQLite，便于低资源部署和迁移打包。
- 远端 fresh DB 使用 `init_workbench_schema()` 初始化后 `alembic stamp head`。
- 旧 Alembic 全量历史里有 PostgreSQL 风格约束迁移，不适合直接对 fresh SQLite 从头 upgrade。
- 当前 SQLite 已升级到 `n06g8h0i3j47 (head)`。
- AI 宣传片已经从 `ops-workbench-runtime/ai-video/databases/workbench.json` 迁入 SQLite 表；旧 JSON 不再作为正常读写主库。
- 旧 JSON 导入现在有一次性 marker 防重复机制：`ops-workbench-runtime/ai-video/databases/workbench.json.imported`。
- 曾反复出现的 10 个 `ces` 当前项目来自旧 JSON 在数据库清空后再次导入；已删除空项目，并把旧 JSON 归档为 `workbench.json.archived-ces-20260817`。
- 当前 AI 宣传片项目表应为空，可用下面命令确认：

```bash
sqlite3 /home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/databases/workbench.db \
  "select count(*) from wb_ai_video_projects;"
```

期望结果：

```text
0
```

## 5. ComfyUI 服务

```text
服务名：comfyui
源码目录：/home/gryps/apps/ComfyUI
启动脚本：/home/gryps/apps/run-comfyui-smallhost.sh
虚拟环境：/home/gryps/apps/ComfyUI/.venv
运行目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui
模型目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/models
数据库：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/user/comfyui.db
访问地址：http://192.168.31.24:8188/
ComfyUI：0.33.0
PyTorch：2.6.0+cpu
```

常用命令：

```bash
systemctl --user status comfyui
systemctl --user restart comfyui
journalctl --user -u comfyui -f
curl -sS http://127.0.0.1:8188/system_stats
```

当前启动参数重点：

```text
--listen 0.0.0.0
--port 8188
--cpu
--disable-auto-launch
--input-directory /home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/input
--output-directory /home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/output
--temp-directory /home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/temp
--user-directory /home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/user
--models-directory /home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/models
--database-url sqlite:////home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/user/comfyui.db
```

环境变量重点：

```text
COMFYUI_DISABLE_BLUEPRINTS=1
COMFYUI_DISABLE_WORKFLOW_TEMPLATES=1
NO_PROXY 包含 localhost、127.0.0.1、192.168.31.24
```

## 6. ComfyUI 迁移和依赖注意

已按“小主机只做工作流中控”的原则清理：

- 没有迁移本地大模型权重。
- 远端 ComfyUI models 目录当前应为空。
- 没有配置本地 GPU 推理路线。
- PyTorch 仅保留 CPU 版，用于 ComfyUI 启动、节点注册和轻量工作流依赖。

依赖注意：

- 使用 `torch==2.6.0+cpu`、`torchvision==0.21.0+cpu`、`torchaudio==2.6.0+cpu`。
- J3455 CPU 不兼容 `kornia-rs`，曾触发 `Illegal instruction`，远端已卸载。
- `kornia` 使用 `0.7.1`。
- 远端 venv 内 `comfy_kitchen/backends/eager/na.py` 做过 typing 兼容补丁：把内建 `list[int]` 改成 `typing.List[int]` 和 `Optional[...]` 形式。若重建 venv 后 ComfyUI 启动失败，应优先检查该兼容问题或升级到已修复的上游版本。

同步 ComfyUI 源码时注意：

- 排除顶层 `/models/`、`/input/`、`/output/`、`/temp/`、`/user/` 和顶层 `.venv`。
- 不要使用未锚定的 `models/`、`input/` 排除规则，否则会误删 `comfy/ldm/models`、`comfy_api/input` 等源码目录。

## 7. 默认工作流处理

当前目标是打开 ComfyUI 时不被官方默认 Z-Image workflow 误导。

已使用的约束：

- `COMFYUI_DISABLE_BLUEPRINTS=1`
- `COMFYUI_DISABLE_WORKFLOW_TEMPLATES=1`
- 不下载默认 workflow 依赖模型。
- 浏览器如仍显示默认节点，优先检查浏览器缓存、Cache Storage、Service Worker，而不是下载模型。

注意：ComfyUI 官方前端有时会从浏览器本地状态恢复上次未保存 workflow。若页面看到默认 workflow，不等于远端 models 目录已有模型，也不等于后端正在加载本地大模型。

## 8. 下一阶段开发边界

下一阶段另起会话，围绕 ComfyUI 制作文生视频、图生视频。

建议第一个闭环：

```text
模块：AI 宣传片 / ComfyUI 视频工作流
范围：文生视频或图生视频二选一；平台 adapter、workflow 配置、任务记录和结果回收
目标：平台录入参数 -> ComfyUI/API 提交任务 -> 回收结果 -> 平台展示任务状态和结果
禁止：不下载本地大模型；不把厂商 API Key 写进画布 JSON；不改运营中心、图片生产和导航
验收：用一个真实模型 API 跑通一次任务，记录输入、输出、厂商任务 ID、错误原因和耗时
执行：先设计字段和 adapter，再接 ComfyUI workflow 和页面
```

开发原则：

- 平台保存业务资产、任务、成本、状态和人工确认。
- ComfyUI 负责画布表达、节点参数调试、workflow 编排和 API 节点桥接。
- 厂商模型调用优先放在平台后端 adapter，ComfyUI 节点只做可视化和可替换编排。
- workflow JSON 只保存节点结构和参数映射，不写死业务数据库路径和敏感凭证。

当前已完成的工程化收口：

- 小主机源码已纳入 Git 管理。
- 前端入口已拆出壳层：`frontend/src/components/shell/` 存放导航配置、侧边栏、顶部栏、账号弹窗、`useNavigationState.ts`、`useWorkbenchData.ts` 和 `useAccountDialogState.ts`；`HumanApp.tsx` 只保留启动判断、导航装配和页面分发。
- 全局 API 入口已收口：`app/api/v1/router.py` 只负责挂载子路由；认证、产品库、音乐资源和模型配置分别拆到 `auth.py`、`products.py`、`music_resources.py`、`model_profiles.py`，外部 URL 保持 `/api/v1/...` 不变。
- AI 宣传片已新增厂商视频 API adapter 边界：`app/services/ai_video/provider_adapters.py` 定义标准请求、提交结果、状态结果和 OpenAI 兼容视频调用；`executor.py` 可按 `comfyui` / `vendor_video` 分派，并在厂商任务成功后把远程输出下载到 `ops-workbench-runtime/ai-video/outputs/{project_id}/{task_id}/`。
- 模型配置新增 `ai_video_generation`（AI 视频生成）业务卡；API Key 仍保存在平台模型配置，不写入 workflow JSON。
- 新增 `/api/v1/ai-video/generation/tasks/{task_id}/refresh`，用于按厂商任务 ID 同步状态和输出路径。
- AI 宣传片画布中的“生成视频片段”会创建 `vendor_video` 任务并提交；任务清单展示厂商任务 ID、错误和输出路径。
- `deploy/product-video-automation.service` 改成模板，不再写死 WSL 路径。
- `scripts/install_systemd_service.sh` 可按当前目录生成用户级 systemd service。
- `scripts/verify_deploy.sh` 可检查平台服务、ComfyUI、数据库版本、静态资源和健康接口。
- `scripts/write_deploy_manifest.py` 会写入 `ops-workbench-runtime/DEPLOY_MANIFEST.json`。
- 远端 venv 已安装 `requirements-dev.txt`，可直接运行 `../.venv/bin/python -m pytest -q`。
- AI 宣传片页面已按生产型工作台重新整理布局：左侧只放项目选择和新建项目，商品图、导演/分镜、任务提交和任务清单放到主工作区。
- AI 宣传片的资产口径已收敛为“用户/平台提供商品图，其他场景图、关键帧、风格参考图、过渡画面和最终视频由模型生成”。
- AI 宣传片商品图可手动上传，也可引用图片生产模块已审核结果；引用入口会创建 `kind=product` 的 AI 视频资产。
- AI 宣传片项目删除样式已与平台通用危险操作保持一致。
- AI 宣传片旧 JSON 防重复导入已修复：`store.py` 会创建并识别 `.imported` marker，避免重启后把旧测试项目再次导入。

当前最近验证：

```text
../.venv/bin/python -m pytest -q：37 passed
../.venv/bin/python -m pytest -q tests/test_ai_video_workflow.py：5 passed
npm --prefix frontend run build：通过
scripts/verify_deploy.sh：通过
product-video-automation：active
comfyui：active
AI 宣传片项目数：0
```

注意：

- 前端交互本轮只做了构建和部署自检，没有引入浏览器自动化点击测试；项目当前没有 Playwright/E2E 脚本。
- 当前没有配置真实视频厂商 API Key，因此本轮只完成 adapter mock 测试、任务事件落库和前端构建；尚未完成真实文生视频或图生视频出片验收。
- AI 宣传片新增数据库表：项目、资产、分镜、生成任务、任务事件。
- AI 宣传片新增任务提交边界：占位 workflow 会明确失败并写入事件；真实 ComfyUI API workflow 可沿同一入口提交。
- AI 宣传片导入图片生产结果时目前引用原图片生产输出文件，不做物理复制；如果未来图片生产输出被删除，AI 宣传片资产可能失效。后续需要按业务决定是否改为导入时复制到 AI 视频资产目录。
- 如果浏览器仍看到 10 个 `ces` 当前项目，优先硬刷新或清理站点缓存；服务端数据库当前应已清空。若仍复现，先查 `/api/v1/ai-video/projects` 返回和上面的 SQL 计数，不要先恢复旧 JSON。

仍建议后续继续处理：

1. 选择并配置真实视频厂商 API，校准提交 payload、状态字段和输出 URL 字段。
2. 增加 AI 视频任务自动轮询 worker。
3. 把 ComfyUI workflow 注册表做成数据库或配置文件，不靠临时文件名约定。
4. 用真实文生视频或图生视频跑通一次出片验收，记录输入、输出、厂商任务 ID、错误和耗时。
5. 继续拆分视频生产旧大文件：优先处理 `app/services/jianying_drafts.py`、`app/services/music_resources.py`。
6. 为 AI 宣传片补真实浏览器交互测试，覆盖项目新建/删除、商品图上传、引用图片生产结果、任务提交和任务刷新。

## 9. 仍未完成的平台模块

本地项目没有完结，后续仍会继续补：

- 经营看板
- 运营中心
- 采后中心
- 主播控场
- 投流计划
- 客服售后
- 仓库管理
- 财务管理
- 项目中心
- 图片生产
- 视频生产
- 模型配置

这次阶段性收尾只是把运行环境迁到小主机，并把下一阶段重点切到 ComfyUI 文生视频、图生视频。
