# 03 领域模型

## 核心实体

```text
Project
Product
Asset
CreativeDirection
Script
Shot
PromptSet
ComfyWorkflow
GenerationTask
ShotVersion
ReviewComment
ExportPackage
ProviderConfig
CostRecord
```

## Project

项目是生产管理单位，绑定商品、目标平台、视频比例和交付状态。

关键字段：

- `id`
- `name`
- `product_id`
- `target_platform`
- `aspect_ratio`
- `target_duration`
- `status`
- `created_at`
- `updated_at`

状态：

```text
draft
asset_ready
script_ready
in_production
reviewing
exported
archived
```

## Product

商品是内容创作的中心，所有资产、脚本、镜头都围绕商品一致性服务。

关键字段：

- `id`
- `name`
- `category`
- `price_range`
- `target_audience`
- `selling_points`
- `forbidden_terms`
- `brand_rules`

## Asset

资产统一管理图片、视频、音频和文档。

资产类型：

```text
product
person
environment
prop
style_reference
audio
video_reference
document
```

关键字段：

- `id`
- `project_id`
- `product_id`
- `type`
- `file_path`
- `mime_type`
- `metadata`
- `tags`
- `quality_score`
- `usage_status`

## Shot

镜头是最小生产单位。所有生成任务、提示词、版本审核都绑定到镜头。

关键字段：

- `id`
- `project_id`
- `index`
- `duration`
- `shot_type`
- `shot_size`
- `camera_motion`
- `visual_description`
- `product_action`
- `dialogue_or_caption`
- `status`

状态：

```text
draft
prompt_ready
keyframe_ready
generating
needs_review
approved
rejected
locked
```

## PromptSet

保存镜头级结构化提示词。

关键字段：

- `id`
- `shot_id`
- `mode`
- `positive_prompt`
- `negative_prompt`
- `structured_prompt`
- `provider_overrides`
- `version`

模式：

```text
keyframe
t2v
i2v
first_last_frame
reference_to_video
```

## GenerationTask

记录一次外部或本地生成任务。

关键字段：

- `id`
- `shot_id`
- `provider`
- `model`
- `mode`
- `request_payload`
- `status`
- `provider_task_id`
- `estimated_cost`
- `actual_cost`
- `error_code`
- `error_message`
- `created_at`
- `finished_at`

状态：

```text
queued
submitted
running
succeeded
failed
canceled
expired
```

## ShotVersion

一个镜头可能有多个生成结果，ShotVersion 负责对比、选择和返修。

关键字段：

- `id`
- `shot_id`
- `generation_task_id`
- `file_path`
- `thumbnail_path`
- `duration`
- `resolution`
- `review_status`
- `director_note`
- `is_selected`

## 文件目录规范

```text
projects/
  {project_id}/
    product/
    assets/
      product/
      person/
      environment/
      prop/
      style/
      audio/
      video_reference/
    shots/
      shot_001/
        prompts/
        keyframes/
        generations/
        selected/
        review/
    exports/
      edit_package/
      reports/
```

