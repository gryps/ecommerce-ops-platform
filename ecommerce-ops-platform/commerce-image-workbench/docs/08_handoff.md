# 交接文档

## 项目概述

本项目是一个面向发簪电商图批量生产的 AI 工作台。

核心不是单纯生成图片，而是管理从产品拍摄、AI 生成、人工审核到商详素材归档的完整流程。

## 当前资产

当前已建立前期文档：

- `README.md`
- `docs/01_project_brief.md`
- `docs/02_prd.md`
- `docs/03_workflow.md`
- `docs/04_shooting_spec.md`
- `docs/05_data_model.md`
- `docs/06_ai_prompting.md`
- `docs/07_mvp_plan.md`
- `docs/08_handoff.md`

## 业务重点

发簪商品图的核心风险：

- AI 改变产品结构
- AI 改变颜色
- AI 增加或减少珠子
- AI 改变流苏数量和方向
- AI 把发簪变成发夹、发钗或头饰
- 佩戴图比例失真
- 商详图风格不统一

因此系统必须围绕“产品保真”和“批量流程”设计。

## 开发优先级

第一优先级：

- 产品管理
- 8 张参考图管理
- 拍摄完整性检查
- 提示词生成
- 生成任务记录
- 审核状态

第二优先级：

- 文件导出
- 素材包归档
- 模板管理
- 批量任务

第三优先级：

- 模型 API 接入
- 自动生成
- 自动商详图排版

## 建议目录结构

```text
hairpin-ai-commerce-studio/
  README.md
  docs/
  app/
  server/
  data/
  storage/
    products/
    outputs/
```

## 产品参考图标准

每个产品必须围绕以下 8 张图建档：

- `01_front.jpg`
- `02_back.jpg`
- `03_left_45.jpg`
- `04_right_45.jpg`
- `05_side.jpg`
- `06_detail_head.jpg`
- `07_detail_material.jpg`
- `08_scale.jpg`

## 数据设计原则

- 产品编号稳定。
- 原始参考图不能被覆盖，替换需要记录。
- 生成任务必须记录模型、提示词、模板版本。
- 审核结论必须保留。
- 可用图和废图分开归档。

## 后续开发提醒

- 不要一开始把模型 API 接得太重。
- 先让人工流程跑通。
- 不要把发簪当普通饰品处理，结构保真是关键。
- 提示词模板需要版本管理。
- 每次生成都要能追溯到产品、参考图、模板、模型。

## 下一步建议

下一步可以进入 MVP 原型开发：

1. 创建 React + TypeScript 前端。
2. 创建 FastAPI + SQLite 后端。
3. 实现产品 CRUD。
4. 实现 8 张参考图上传和缺图检查。
5. 实现提示词模板和任务记录。
