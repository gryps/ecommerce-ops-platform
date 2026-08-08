# 交接文档

## 1. 当前目录关系

```text
/mnt/e/codexwork/ecommerce-ops-platform/
├── ops-workbench/                  # 实际运行项目：视频 + 图片 + 模型配置
├── commerce-image-workbench/        # 电商图片生产文档
└── commerce-video-workbench/        # 电商视频生产文档
```

视频生产代码不在本目录，本目录只作为业务文档入口。

## 2. 运行项目

实际运行项目：

```text
/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
```

主要位置：

- 前端入口：`frontend/src/HumanApp.tsx`
- 前端样式：`frontend/src/human.css`
- 后端入口：`app/main.py`
- API：`app/api/v1/`
- 服务：`app/services/`
- ORM：`app/domain/models.py`
- 迁移：`migrations/versions/`
- 测试：`tests/test_current_workflow.py`

## 3. 服务

当前仍使用用户级 systemd 服务：

```bash
systemctl --user status product-video-automation
systemctl --user restart product-video-automation
```

服务名暂未改名。服务 WorkingDirectory 应指向：

```text
/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
```

## 4. 当前业务口径

以后处理视频生产需求时，优先采用以下文档顺序：

1. `/mnt/e/codexwork/PROJECT_MEMORY.md`
2. `/mnt/e/codexwork/AGENTS.md`
3. `commerce-video-workbench/README.md`
4. `commerce-video-workbench/docs/02_prd.md`
5. `commerce-video-workbench/docs/03_workflow.md`
6. `commerce-video-workbench/docs/engineering/PROJECT_DECISIONS.md`
7. `commerce-video-workbench/docs/engineering/CONTEXT_INDEX.md`

如果文档与代码冲突：

- 业务含义以 `PROJECT_MEMORY.md` 和本目录文档为准。
- 实现事实以当前代码、迁移和测试为准。
- 历史归档只用于追溯，不得恢复已退役功能。

## 5. 已退役功能

不要按旧文档恢复以下能力：

- 人工粗剪与代理片段；
- 音乐卡点和混剪框架；
- 自动选片和系统内精修；
- 成片渲染和成片库；
- 热播短链接跟踪；
- 无人值守自动生产；
- 框架库和框架布局。

## 6. 验证命令

在运行项目目录执行：

```bash
cd /mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
npm --prefix frontend run build
/mnt/e/codexwork/.venv/bin/python -m pytest tests/test_current_workflow.py -q
curl --max-time 5 -sS http://127.0.0.1:8000/api/health
```

如 curl 访问本机服务被沙箱限制，需要提升权限重试。

## 7. 未完成验收

仍需真实业务环境验收：

- 真实素材盘多视频归类移动；
- 当前剪映专业版打开生成草稿；
- 实际抖音链接音频提取；
- 真实百炼 ASR/TTS 调用；
- 真实运营文案迭代质量。

## 8. 修改提醒

涉及视频生产业务口径变更时，应同步更新：

- 本目录对应文档；
- `/mnt/e/codexwork/PROJECT_MEMORY.md`；
- `docs/engineering/PROJECT_DECISIONS.md` 或对应模块文档；
- 如涉及交互名称，更新 `docs/engineering/UI_FUNCTION_CATALOG.md`。
