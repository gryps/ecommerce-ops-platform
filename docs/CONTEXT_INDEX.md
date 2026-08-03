# 项目上下文路由

> 新会话不要通读全部文档。先读 `PROJECT_CURRENT.md`，再根据任务选择下表中的最小文档集合。

## 当前有效入口

| 任务范围 | 必读文档 | 说明 |
| --- | --- | --- |
| 原视频归类、文案/语音/音乐库、剪映草稿 | `docs/JIANYING_DRAFT_WORKFLOW_REQUIREMENTS.md` | 当前主流程规范，优先级最高 |
| 旧素材批次、自动分类、BBOX、颜色训练 | `docs/material-classification-workflow-requirements.md` | 历史兼容模块；当前页面不使用 |
| 旧混剪框架、编辑器、卡点和混音 | `docs/MIX_FRAMEWORK_LIBRARY_SPEC.md` | 历史兼容模块；仅追溯旧数据时读取 |
| 旧自动选片、30% 复用、队列和渲染 | `docs/AUTOMATIC_MIX_REQUIREMENTS.md` | 已退役流程，仅历史追溯使用 |
| 旧文案库存、三个月使用和热点归因 | `docs/COPY_CONTENT_LIBRARY_REQUIREMENTS.md` | 已被当前独立文案库规则取代 |
| 模型配置、真实调用日志 | `docs/model-call-logging-requirements.md` | 日志边界、留存、汇总和安全 |
| 已约定的界面功能名称、交互控件复用 | `docs/UI_FUNCTION_CATALOG.md` | 固定名称、适用场景、功能介绍和调用说法 |
| 运行、依赖、服务、打包 | `README.md` | 工程操作说明，不作为业务规则最高口径 |

跨模块业务决定可查 `PROJECT_DECISIONS.md`。如果模块文档冲突，采用以下优先级：

```text
PROJECT_CURRENT.md
→ PROJECT_DECISIONS.md
→ JIANYING_DRAFT_WORKFLOW_REQUIREMENTS.md
→ 对应模块的其他需求文档
→ PROJECT_HANDOFF_ARCHIVE.md（只用于历史追溯）
```

## 历史资料

- `PROJECT_HANDOFF_ARCHIVE.md`：按日期追加的开发记录，默认不读。
- `COPY_CONTENT_LIBRARY_REQUIREMENTS.md` 第 10 节以后：包含迁移建议和阶段性开发结果，不能据此推断当前待办。
- Alembic 历史迁移：必须保留迁移链，但其中的表和字段不一定仍属于当前运行架构。

## 阅读纪律

- 不要为了“了解整个项目”读取历史归档。
- 处理一个页面问题时，优先读对应前端组件、API、服务和一份模块文档。
- 只有遇到规则冲突、数据迁移来源或用户询问历史原因时，才检索历史归档的相关段落。
- 代码、当前数据库迁移状态和自动化测试是实现事实；业务含义以当前文档为准。
