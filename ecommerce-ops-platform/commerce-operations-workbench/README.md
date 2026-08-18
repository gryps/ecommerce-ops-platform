# 电商运营中心

这是电商运营平台中的运营作业流业务文档目录，用于沉淀商品库、选品测品、上架资料、直播排品、投流复盘、库存利润和日报周报的当前口径。

实际运行代码在：

```text
/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
```

本目录只保存业务和交接文档，结构对齐 `commerce-video-workbench/` 和 `commerce-image-workbench/`。

## 项目定位

电商运营中心不是 ERP，也不是全自动代运营系统，而是面向直播电商早期团队的运营 AI 辅助系统。

当前目标是把运营负责人每天需要处理的选品、测品、上架准备、直播排品、脚本生成、投流复盘、库存预警、利润测算和日报周报整理成可录入、可计算、可复盘、可交接的流程。

## 核心边界

- 系统提供录入、计算、预警、AI 初稿和复盘建议。
- 人工确认最终选品、定价、投流放量、补货、平台发布、资金、合同、合规和人员事项。
- 第一阶段支持人工导入、表格上传、截图录入、CSV 导入和 AI 辅助生成，不直接调用抖店、巨量千川或平台后台接口。
- 运行代码、数据库、导入文件、导出文件、报告和临时文件不得混入本目录。

## 当前文档

- `docs/01_prd.md`：运营 AI 辅助系统产品需求手册。
- `docs/02_automation_boundary.md`：业务逻辑拓扑与自动化边界。

## 当前实现入口

- 前端模块：`../ops-workbench/frontend/src/modules/operations/`
- 后端 API：`../ops-workbench/app/api/v1/operations/`
- 后端服务：`../ops-workbench/app/services/operations/`
- 模块上下文：`../ops-workbench/docs/modules/operations-center.md`
- 运行态目录：`../ops-workbench-runtime/operations/`

## 后续开发读取顺序

1. `/mnt/e/codexwork/PROJECT_MEMORY.md`
2. `/mnt/e/codexwork/AGENTS.md`
3. `../docs/DEVELOPMENT_COLLABORATION.md`
4. 本 README
5. `docs/01_prd.md`
6. `docs/02_automation_boundary.md`
7. `../ops-workbench/docs/modules/operations-center.md`
8. 对应前后端代码
