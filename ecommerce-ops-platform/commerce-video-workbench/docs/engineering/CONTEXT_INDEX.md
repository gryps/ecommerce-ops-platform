# 电商视频生产文档路由

> 新会话不要通读全部文档。先读 `/mnt/e/codexwork/PROJECT_MEMORY.md` 和
> `/mnt/e/codexwork/AGENTS.md`，再按任务选择下表中的最小文档集合。

## 当前有效入口

| 任务范围 | 必读文档 | 说明 |
| --- | --- | --- |
| 视频业务总览、PRD、流程 | `../02_prd.md`、`../03_workflow.md` | 对齐 `commerce-image-workbench` 的视频生产业务入口 |
| 原视频归类、文案/语音/音乐库、剪映草稿 | `../current/JIANYING_DRAFT_WORKFLOW_REQUIREMENTS.md` | 当前主流程细则，优先级最高 |
| 当前工程状态 | `PROJECT_CURRENT.md` | 运行实现、验证结果、废止结构 |
| 跨模块业务决定 | `PROJECT_DECISIONS.md` | 只记录代码不容易直接看出的当前决定 |
| 当前待办 | `NEXT_TASK.md` | 只记录真实未完成事项 |
| 新会话启动 | `NEW_SESSION_PROMPT.md` | 继续开发时的精简入口 |
| 模型配置、真实调用日志 | `model-call-logging-requirements.md` | 日志边界、留存、汇总和安全 |
| 已约定的界面功能名称、交互控件复用 | `UI_FUNCTION_CATALOG.md` | 固定名称、适用场景、功能介绍和调用说法 |

如果模块文档冲突，采用以下优先级：

```text
PROJECT_MEMORY.md
→ commerce-video-workbench/docs/02_prd.md
→ commerce-video-workbench/docs/03_workflow.md
→ docs/engineering/PROJECT_CURRENT.md
→ docs/engineering/PROJECT_DECISIONS.md
→ docs/current/JIANYING_DRAFT_WORKFLOW_REQUIREMENTS.md
→ 对应模块的其他当前文档
→ docs/archive/PROJECT_HANDOFF_ARCHIVE.md（只用于历史追溯）
```

## 历史资料

| 历史范围 | 文档 | 读取时机 |
| --- | --- | --- |
| 旧素材批次、自动分类、BBOX、颜色训练 | `../legacy/material-classification-workflow-requirements.md` | 追溯旧数据或旧迁移 |
| 旧混剪框架、编辑器、卡点和混音 | `../legacy/MIX_FRAMEWORK_LIBRARY_SPEC.md` | 追溯已退役框架功能 |
| 旧自动选片、30% 复用、队列和渲染 | `../legacy/AUTOMATIC_MIX_REQUIREMENTS.md` | 追溯已退役自动混剪 |
| 旧文案库存、三个月使用和热点归因 | `../legacy/COPY_CONTENT_LIBRARY_REQUIREMENTS.md` | 追溯旧文案库规则 |
| 历史交接记录 | `../archive/PROJECT_HANDOFF_ARCHIVE.md` | 按关键词查历史原因 |

旧文档与当前文档冲突时，以下顺序生效：

```text
PROJECT_CURRENT.md
→ PROJECT_DECISIONS.md
→ ../current/JIANYING_DRAFT_WORKFLOW_REQUIREMENTS.md
→ ../legacy/*
→ ../archive/PROJECT_HANDOFF_ARCHIVE.md
```

## 阅读纪律

- 不要为了“了解整个项目”读取历史归档。
- 处理一个页面问题时，优先读对应前端组件、API、服务和一份模块文档。
- 只有遇到规则冲突、数据迁移来源或用户询问历史原因时，才检索历史归档的相关段落。
- 代码、当前数据库迁移状态和自动化测试是实现事实；业务含义以当前文档为准。
