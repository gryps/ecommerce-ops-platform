# 04 API 契约草案

## 约定

- Base path: `/api/v1`
- 请求和响应使用 JSON。
- 文件上传使用 multipart。
- 所有 ID 使用字符串 UUID。
- 异步生成任务通过 `GenerationTask` 查询状态。

## Project API

### 创建项目

`POST /projects`

请求：

```json
{
  "name": "某商品15秒推广视频",
  "target_platform": "douyin",
  "aspect_ratio": "9:16",
  "target_duration": 15
}
```

响应：

```json
{
  "id": "project_id",
  "status": "draft"
}
```

### 获取项目详情

`GET /projects/{project_id}`

### 获取项目看板

`GET /projects/{project_id}/board`

返回项目、商品、资产数量、镜头状态、成本概览。

## Product API

### 创建或更新商品档案

`PUT /projects/{project_id}/product`

请求：

```json
{
  "name": "商品名称",
  "category": "beauty",
  "price_range": "199-299",
  "target_audience": "25-35岁女性",
  "selling_points": ["清爽", "便携", "高颜值"],
  "forbidden_terms": ["绝对有效", "医疗功效"],
  "brand_rules": {
    "brand_color": "#FFFFFF",
    "logo_usage": "正面标签保持清晰"
  }
}
```

## Asset API

### 上传资产

`POST /projects/{project_id}/assets`

字段：

- `file`
- `type`
- `tags`
- `product_id`

### 获取资产列表

`GET /projects/{project_id}/assets?type=product`

## Director API

### 生成创意方向

`POST /projects/{project_id}/creative-directions/generate`

### 生成脚本

`POST /projects/{project_id}/scripts/generate`

请求：

```json
{
  "duration": 15,
  "style": "high_end_product_ad",
  "platform": "douyin"
}
```

### 生成分镜

`POST /projects/{project_id}/shots/generate`

## Shot API

### 获取镜头列表

`GET /projects/{project_id}/shots`

### 更新镜头

`PATCH /shots/{shot_id}`

### 生成镜头提示词

`POST /shots/{shot_id}/prompts/generate`

### 提交视频生成任务

`POST /shots/{shot_id}/generation-tasks`

请求：

```json
{
  "provider": "vidu",
  "model": "viduq3-turbo",
  "mode": "i2v",
  "input_asset_ids": ["asset_id"],
  "prompt_id": "prompt_id",
  "params": {
    "duration": 5,
    "resolution": "720p",
    "aspect_ratio": "9:16"
  }
}
```

响应：

```json
{
  "task_id": "generation_task_id",
  "status": "queued",
  "estimated_cost": 1.875
}
```

## Generation Task API

### 查询任务

`GET /generation-tasks/{task_id}`

### 重试任务

`POST /generation-tasks/{task_id}/retry`

### 下载结果

`POST /generation-tasks/{task_id}/download`

## Review API

### 标记镜头版本

`PATCH /shot-versions/{version_id}/review`

请求：

```json
{
  "review_status": "approved",
  "director_note": "产品角度可用，保留为最终镜头",
  "is_selected": true
}
```

## Export API

### 导出剪辑素材包

`POST /projects/{project_id}/exports/edit-package`

响应：

```json
{
  "export_id": "export_id",
  "status": "queued"
}
```

