# 图片生产 / AI 出图任务

## 边界

本模块负责从已确认产品组生成 AI 商品图任务，包括提示词、模型调用、任务进度和结果入库。

负责：

- 出图类型和数量配置；
- 基于原图分析模型生成可编辑提示词；
- 将提示词和原图交给生图模型；
- 记录模型、参数、提示词、任务阶段和结果；
- 显示任务进度；
- 未完成任务禁止重复提交；
- 支持终止、删除、失败阶段重试；
- 生成图保存到素材库/结果库。

不负责：

- 摄影素材人工分组；
- 平台模板字段维护；
- 平台自动填报；
- 视频生产。

## 当前实现

已实现任务记录骨架：

- 图片模板列表：`GET /api/v1/images/templates`
- 生成提示词：`POST /api/v1/images/products/{product_id}/prompt`
- 创建任务记录：`POST /api/v1/images/products/{product_id}/tasks`
- 任务列表：`GET /api/v1/images/tasks`
- 任务控制：`POST /api/v1/images/tasks/{task_id}/control`
- 删除任务：`DELETE /api/v1/images/tasks/{task_id}`
- 人工关联结果：`POST /api/v1/images/tasks/{task_id}/outputs`
- 结果文件读取：`GET /api/v1/images/tasks/{task_id}/outputs/{index}/file`

未实现：

- 真实原图分析模型调用；
- 真实生图模型调用；
- 后台 worker/队列；
- 分阶段进度；
- 模型结果自动入库。

## 关键代码

- 前端方案页：`frontend/src/modules/image-production/ImagePlans.tsx`
- 前端任务列表：`frontend/src/modules/image-production/ImageTaskList.tsx`
- 前端 hook：`frontend/src/modules/image-production/useImageTaskActions.ts`
- 后端路由：`app/api/v1/image/generation_tasks.py`
- 服务模板：`app/services/image/templates.py`
- 服务任务：`app/services/image/tasks.py`
- 模型配置：`app/ai.py`
- 数据模型：`app/domain/models.py` 中 `CommerceImageTask`

## 禁止改动

- 不恢复 AI 分组；
- 不绕过人工审核直接进入平台槽位；
- 不把平台字段逻辑塞进出图任务。

## 下一步开发建议

优先新增：

- `app/services/image/generation_worker.py`
- `app/services/image/model_pipeline.py`

先接通“原图分析模型 → 生图模型 → 结果入库”的最小闭环，再扩展批量队列和失败阶段重试。
