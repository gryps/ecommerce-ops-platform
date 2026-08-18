# 岗位中心 / 一级模块骨架

## 边界

本模块负责以下一级入口的前端骨架和岗位工作台上下文：

- 采后中心；
- 主播控场；
- 投流计划；
- 客服售后；
- 仓库管理；
- 财务管理；
- 项目中心。

这些中心是运营中心业务链路的岗位化拆分，不与视频生产、图片生产、模型配置混放。

## 当前实现

- 前端入口：`frontend/src/modules/role-centers/RoleCenter.tsx`
- 一级导航：`frontend/src/HumanApp.tsx`
- 类型枚举：`frontend/src/types.ts` 中 `PlatformModule`
- 运行态目录：`../ops-workbench-runtime/{procurement,host-control,ad-planning,customer-service,warehouse,finance,project}/`

当前只实现岗位中心骨架页面；后续每个中心按自身业务独立扩数据表、接口、服务和测试。

## 业务文档

- 采后中心：`../../commerce-procurement-workbench/`
- 主播控场：`../../commerce-host-control-workbench/`
- 投流计划：`../../commerce-ad-planning-workbench/`
- 客服售后：`../../commerce-customer-service-workbench/`
- 仓库管理：`../../commerce-warehouse-workbench/`
- 财务管理：`../../commerce-finance-workbench/`
- 项目中心：`../../commerce-project-workbench/`

## 运行态归类

每个岗位中心下统一使用：

```text
imports/
exports/
reports/
temp/
```

## 禁止改动

- 不把岗位中心业务文件写入 `ops-workbench/`；
- 不把岗位中心运行态文件写入业务文档目录；
- 不把投流、客服、仓库、财务等岗位数据继续塞回运营中心页面；
- 不让系统自动执行采购、投流放量、赔付、报废、资金、合同、合规和人员决策。
