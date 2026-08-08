# 数据结构草案

## Product 产品

```json
{
  "id": "HZ001",
  "name": "珍珠流苏金色发簪",
  "category": "发簪",
  "materials": ["合金", "珍珠", "流苏"],
  "primaryColor": "金色",
  "secondaryColor": "白色",
  "styleTags": ["新中式", "温柔", "日常"],
  "structureDescription": "金色簪杆，头部三颗珍珠，右侧一条流苏。",
  "sellingPoints": ["珍珠光泽", "流苏灵动", "适合汉服和日常盘发"],
  "preserveRules": [
    "保持三颗珍珠",
    "保持右侧一条流苏",
    "保持金色簪杆",
    "不要改变整体长度比例"
  ],
  "notes": "",
  "createdAt": "2026-08-07T00:00:00+08:00",
  "updatedAt": "2026-08-07T00:00:00+08:00"
}
```

## ProductImage 产品参考图

```json
{
  "id": "IMG-HZ001-01",
  "productId": "HZ001",
  "type": "front",
  "fileName": "01_front.jpg",
  "filePath": "products/HZ001/01_front.jpg",
  "status": "uploaded",
  "createdAt": "2026-08-07T00:00:00+08:00"
}
```

## ImageTemplate 图片模板

```json
{
  "id": "template-main-white",
  "name": "白底主图",
  "imageType": "main",
  "aspectRatio": "1:1",
  "promptZh": "电商白底商品图，保持产品结构、颜色、材质完全一致。",
  "negativePromptZh": "不要改变颜色，不要增加珠子，不要改变流苏数量，不要改变簪杆长度。",
  "recommendedModels": ["通义万相", "混元"]
}
```

## GenerationTask 生成任务

```json
{
  "id": "TASK-20260807-0001",
  "productId": "HZ001",
  "templateId": "template-main-white",
  "model": "通义万相",
  "prompt": "生成用提示词",
  "negativePrompt": "负面提示词",
  "inputImages": [
    "products/HZ001/01_front.jpg",
    "products/HZ001/03_left_45.jpg",
    "products/HZ001/06_detail_head.jpg"
  ],
  "outputImages": [],
  "status": "pending",
  "reviewStatus": "unreviewed",
  "createdAt": "2026-08-07T00:00:00+08:00"
}
```

## Review 审核记录

```json
{
  "id": "REVIEW-20260807-0001",
  "taskId": "TASK-20260807-0001",
  "productId": "HZ001",
  "result": "need_redo",
  "issues": ["珠子数量错误", "流苏位置错误"],
  "comment": "原图为三颗珍珠，生成图变成五颗；流苏从右侧变为左侧。",
  "createdAt": "2026-08-07T00:00:00+08:00"
}
```

## 状态枚举

### 任务状态

- pending
- generating
- generated
- failed
- archived

### 审核状态

- unreviewed
- approved
- need_redo
- rejected

### 图片类型

- front
- back
- left_45
- right_45
- side
- detail_head
- detail_material
- scale
- generated_main
- generated_scene
- generated_wearing
- generated_detail
- generated_mobile_detail
