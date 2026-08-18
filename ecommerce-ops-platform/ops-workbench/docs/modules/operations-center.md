# 运营中心 / 直播电商运营作业流

## 边界

本模块负责直播电商运营链路中的商品、测品、直播、投流、订单退款、库存利润和复盘作业。

负责：

- 运营商品库、供应商、成本、售价、库存和商品状态；
- 选品测品等级与人工决策留痕；
- 直播场次、直播商品、排品顺序和下播数据；
- 投流计划、消耗、退款后 ROI、投流后利润和人工决策；
- 每日经营指标、库存预警、利润测算、日报周报；
- AI 生成卖点、上架资料、话术卡和复盘初稿。

不负责：

- 摄影素材分组和 AI 商品图生产；
- 视频素材归类和剪映草稿；
- 模型配置密钥管理；
- 直接操作抖店、巨量千川或平台后台；
- 自动发布、自动投流放量、自动采购或替代资金/合同/合规判断。

## 当前实现

已新增独立目录和骨架：

- 业务文档：`../commerce-operations-workbench/`
- 后端 API：`app/api/v1/operations/`
- 后端服务：`app/services/operations/`
- 前端模块：`frontend/src/modules/operations/`
- 数据表迁移：`migrations/versions/m05f7g9h2i36_add_operations_center.py`
- 运行态文件：`../ops-workbench-runtime/operations/`

已实现基础能力：

- 运营总览接口：`GET /api/v1/operations/overview`
- 商品库列表接口：`GET /api/v1/operations/products`
- 创建运营商品：`POST /api/v1/operations/products`
- 更新运营商品：`PATCH /api/v1/operations/products/{product_id}`
- 前端一级菜单：`运营中心`
- 二级页面：运营总览、业务拓扑、商品库、直播运营、投流复盘、库存利润、日报周报

当前仅商品库可编辑；直播、投流、库存利润和日报周报页面先保留模块入口。

## 目录归类

业务文档按视频/图片模块同样方式沉淀在：

```text
../commerce-operations-workbench/
├── README.md
└── docs/
    ├── 01_prd.md
    └── 02_automation_boundary.md
```

运行态文件不得进入代码目录或业务文档目录，统一放在：

```text
../ops-workbench-runtime/operations/
├── imports/   # 订单、退款、投流、库存等人工导入文件
├── exports/   # CSV、Excel、执行表等导出文件
├── reports/   # 日报、周报、D30/D60/D90 复盘报告
└── temp/      # 临时处理中间文件
```

## 关键代码

- 前端入口：`frontend/src/modules/operations/OperationsCenter.tsx`
- 前端数据 hook：`frontend/src/modules/operations/useOperationsData.ts`
- 后端路由：`app/api/v1/operations/__init__.py`
- 后端 schema：`app/api/v1/operations/schemas.py`
- 后端服务：`app/services/operations/products.py`
- 数据模型：`app/domain/models.py` 中 `OpsProduct`、`OpsLiveSession`、`OpsLiveProduct`、`OpsAdPlan`、`OpsDailyMetric`

## 禁止改动

- 不把运营中心代码塞进图片生产或视频生产目录；
- 不复用视频生产的 `wb_products` 作为运营商品库主表；
- 不把平台自动上传能力放到运营中心；
- 不把 AI 建议直接写成最终决策；
- 不自动发布、自动投流放量、自动补货或自动采购。

## 验收

- 侧边栏出现“运营中心”一级菜单；
- 运营中心下有 7 个二级页面；
- 业务拓扑页面展示总体业务逻辑拓扑、系统模块拓扑和自动化边界；
- 商品库可以新增和修改运营商品；
- 商品库表格在主工作区横向展开；
- 后端 OpenAPI 暴露 `/api/v1/operations/*`；
- 前端构建通过，后端测试通过。
