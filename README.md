# 电商运营平台

Version: 2.0.0

电商运营平台把电商视频生产、电商图片生产和模型配置整合到同一个本地工作台。当前可运行代码位于：

```text
ecommerce-ops-platform/ops-workbench/
```

业务文档按模块归档：

- `ecommerce-ops-platform/commerce-video-workbench/`：电商视频生产文档。
- `ecommerce-ops-platform/commerce-image-workbench/`：电商图片生产文档。
- `PROJECT_MEMORY.md`：当前最终业务口径和长期约定。

## 2.0 主要功能

### 电商图片生产

图片生产模块面向“实拍原图 → 产品档案 → AI 商品图 → 平台草稿”的流程：

- 摄影师上传商品实拍原图到摄影素材库。
- 运营人员人工勾选同一产品照片，填写唯一产品名称，创建产品组和产品档案。
- 系统生成不可修改的产品序列号；产品名称不可重复。
- 不使用 AI 自动分组，原始照片不会被多个产品组复用。
- 删除产品档案时，默认把原始照片退回待分配区；也可选择连同原图一起删除。
- AI 出图按产品执行，默认覆盖白底图、环境搭配图、佩戴图、商详图等类型。
- 出图任务支持进度、终止、删除、失败重试和结果审核。
- 只有人工选中的 AI 图进入平台图片槽位。
- 平台模板支持自定义字段和图片槽位，适配抖音、快手、视频号等不同平台字段要求。
- 用户先登录指定浏览器，系统基于已有登录态自动填写字段、上传图片，并只保存平台草稿，不自动发布。

### 电商视频生产

视频生产模块面向人工主导的短视频素材和剪映草稿生产：

- 维护产品、标签和素材归类。
- 按产品和标签移动并重命名原视频文件。
- 管理文案、旁白字幕、音色试听和背景音乐库。
- 从本地音频或短视频链接提取背景音乐。
- 人工选择文案、旁白字幕和背景音乐后生成可继续编辑的剪映草稿。
- 重复物料组合会提示历史生成次数，但不阻止继续生成。

### 模型配置

模型配置统一管理各业务环节的百炼兼容模型连接：

- 文案生成
- 原图分析与提示词
- AI 商品生图
- 音频转文案
- 字幕配音

API Key 和本机运行配置保存在运行目录 `.env`，不放入代码目录，不提交到 Git。

## 项目结构

```text
.
├── PROJECT_MEMORY.md
├── AGENTS.md
└── ecommerce-ops-platform/
    ├── README.md
    ├── ops-workbench/              # 可运行代码
    ├── ops-workbench-runtime/      # 本地运行数据，已 gitignore
    ├── commerce-video-workbench/   # 视频生产文档
    └── commerce-image-workbench/   # 图片生产文档
```

## 本地运行

```bash
cd ecommerce-ops-platform/ops-workbench
python3 -m venv /mnt/e/codexwork/.venv
source /mnt/e/codexwork/.venv/bin/activate
pip install -r requirements-dev.txt
/mnt/e/codexwork/.venv/bin/alembic upgrade head
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

本机打开：

```text
http://127.0.0.1:8000/workbench/
```

健康检查：

```bash
curl -sS http://127.0.0.1:8000/api/health
```

## 验证

```bash
cd ecommerce-ops-platform/ops-workbench
npm --prefix frontend run build
/mnt/e/codexwork/.venv/bin/python -B -m pytest tests/test_current_workflow.py -q
```

## 运行数据边界

日常使用中会增长的数据库、上传素材、AI 结果、浏览器 profile、缓存和构建产物默认放在：

```text
ecommerce-ops-platform/ops-workbench-runtime/
```

该目录已被 Git 忽略。仓库不提交数据库、素材、`.env`、node_modules、venv、缓存和本地构建产物。
