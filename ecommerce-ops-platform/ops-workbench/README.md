# 电商运营平台运行目录

`ops-workbench` 是当前可运行代码目录，承载电商视频生产、电商图片生产和模型配置。

当前版本：2.0.0

业务文档已迁出到同级文档目录：

- 视频生产：`../commerce-video-workbench/`
- 图片生产：`../commerce-image-workbench/`
- 运行代码模块上下文：`docs/modules/`
- 全局口径：`/mnt/e/codexwork/PROJECT_MEMORY.md`

## 运行数据目录

代码目录只放可维护的项目文件。日常使用中会增长的数据库、上传素材、AI 结果、浏览器 profile、缓存和临时工作文件，默认放在同级目录：

```text
../ops-workbench-runtime/
```

可通过环境变量覆盖：

```bash
PVA_RUNTIME_DIR=/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime
PVA_WORKSPACE_DIR=/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime/workspace
PVA_STATIC_DIR=/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime/static-workbench
PVA_WORKBENCH_DATABASE_URL=sqlite:////mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime/databases/workbench.db
```

本机 `.env` 放在 `../ops-workbench-runtime/.env`，不放在代码目录内。如果 `.env` 中配置了 `PVA_WORKBENCH_DATABASE_URL`，系统优先使用该数据库连接；否则默认使用 `../ops-workbench-runtime/databases/workbench.db`。

## 本地运行

```bash
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

## 常用验证

```bash
npm --prefix frontend run build
/mnt/e/codexwork/.venv/bin/python -m pytest tests/test_current_workflow.py -q
```

生产环境只需要 `requirements.txt`；运行测试时安装 `requirements-dev.txt`。

## 图片生产功能

图片生产模块面向“实拍原图 → 产品档案 → AI 商品图 → 平台草稿”的生产流程：

- 在“拍摄分组”上传摄影师交付的原始照片，并人工勾选同一产品照片创建产品组。
- 创建产品组时填写产品名称，系统生成唯一产品序列号；原始照片不会被多个产品复用。
- 删除产品档案时，默认把原始照片退回待分配区；也可选择连同原图一起删除。
- 在“产品资料”中维护产品名称、平台模板档案和批量字段值。
- 平台模板由用户自定义字段和图片槽位，不预设颜色、尺码、价格等固定字段。
- 在“出图方案”中基于产品实拍图生成提示词并提交 AI 商品图任务。
- 在“结果审核”中按产品和图片类型审核 AI 结果，满意的图片才能进入导出上传。
- 在“导出上传”中选择平台模板、映射图片槽位，并通过已登录浏览器保存平台草稿。
