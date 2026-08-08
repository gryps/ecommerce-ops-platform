# 图片生产 / 图片审核与交付选图

## 边界

本模块负责 AI 图生成后的人工审核、返工意见和平台槽位选图。

负责：

- 按产品查看出图任务；
- 按图片类型核对结果；
- 标记可用、需重做、废弃；
- 记录问题和修改意见；
- 只允许人工选择审核通过的 AI 图进入平台图片槽位；
- 不同平台模板可选择不同图片。

不负责：

- AI 真实生图；
- 模板字段定义；
- 浏览器自动填写；
- 电商平台发布。

## 当前实现

已实现基础能力：

- 审核状态更新：`PATCH /api/v1/images/tasks/{task_id}/review`
- 任务结果图片读取；
- 导出上传页的人工平台选图；
- 平台档案保存 `image_selections`。

当前“审核”仍是任务级展示，后续可优化为产品级、按图片类型分区。

## 关键代码

- 前端审核页：`frontend/src/modules/image-production/ImageReview.tsx`
- 前端任务列表：`frontend/src/modules/image-production/ImageTaskList.tsx`
- 前端交付选图：`frontend/src/modules/image-production/ImageDelivery.tsx`
- 后端路由：`app/api/v1/image/generation_tasks.py`
- 后端模板档案：`app/api/v1/image/platform_templates.py`

## 禁止改动

- 不允许未审核或未通过图片进入平台槽位；
- 不增加“系统自动验收通过”逻辑；
- 不把用户检查验收拉回本系统逐条标记，最终验收在电商平台内完成。

## 验收

- 无结果图不能标记为可用；
- 只有审核通过任务的图片能在平台选图区域出现；
- 图片槽位数量不能超过模板定义的 `max_count`。
