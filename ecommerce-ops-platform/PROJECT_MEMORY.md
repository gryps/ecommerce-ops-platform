# 工作区长期约定与需求索引

> 适用范围：`/mnt/e/codexwork` 下的当前项目和后续新项目。
>
> 用途：新会话或新项目开发前，先读本文件，再按索引读取具体项目文档。若本文件与旧文档冲突，以本文件和用户最新口径为准。

## 1. 固定工作边界

- 默认只在 WSL 的 `/mnt/e/codexwork` 目录及其子目录内操作。
- 尽量减少确认，能根据现有代码、文档和用户已给口径判断的事项，直接推进。
- 不还原用户已有改动，不执行破坏性操作，除非用户明确要求。
- 需要启动或检查当前电商运营平台服务时，优先使用已有 `product-video-automation` 用户级 systemd 服务。

## 2. 跨项目界面设计约定

- 布局前必须先估算栏目容量和操作密度：这个区域未来可能有多少条记录、多少字段、是否需要筛选、排序、批量选择、批量编辑、审核、导出。
- 产品清单、素材清单、任务清单、批量编辑表格、结果审核列表、平台字段模板等可能增长到几十到几百项的栏目，默认使用页面主工作区或全宽区域。
- 高容量栏目不得放进窄侧栏、小卡片、压缩面板或装饰性容器。侧栏只适合放筛选、状态、快捷操作和摘要。
- 批量生产流程中的清单和表格，需要优先保证横向信息完整、批量选择、批量编辑、筛选、排序、分页或虚拟滚动空间。
- 如果一个区域承载实际业务处理，它的布局优先级高于说明文字和装饰视觉。
- 新功能应采用生产型工具布局：信息密度适中、栏目分层清楚、重要操作显眼、流程状态可追踪。

## 2.1 验证约定

- 涉及按钮、菜单、编辑入口、文件选择器、批量操作等交互改动时，不能只做构建验证；应尽量做浏览器交互测试或用现有测试工具验证关键路径。
- 如果当前项目没有可用的交互测试工具或测试条件不足，交付时必须明确说明未做真实交互测试，并说明已完成哪些替代验证。

## 3. 通用交互术语

- **模糊联想输入框**：适用于候选条目较多、主要依靠输入文字缩小范围的场景。输入后按相似度显示建议，不单独提供“展开全部”。
- **可输入下拉框**：适用于候选条目较少的场景。支持手动输入、输入时模糊筛选、点击箭头展开完整列表，选择新项目后覆盖已有文字。
- **系统原生文件选择器**：页面按钮调用操作系统文件选择窗口，不让用户在网页内手填路径。多选或单选由业务决定；明确说“多文件选择器”时必须支持多选。

## 4. 电商运营平台统一口径

- `运营中心`、`采后中心`、`主播控场`、`投流计划`、`客服售后`、`仓库管理`、`财务管理`、`项目中心`、`视频生产`、`图片生产`、`模型配置`属于同一个一级平台：电商运营平台。
- 顶部一级菜单包括运营中心、采后中心、主播控场、投流计划、客服售后、仓库管理、财务管理、项目中心、视频生产、图片生产、模型配置。
- 导航按钮保留既有两种颜色，选中项使用亮色，未选中项使用暗色。
- 网页标题应显示“电商运营平台”，不得继续显示旧的“视频生产工作台”。
- 新的图片生产要参照视频生产的样式、二级标签页、生产总览、状态记录、菜单分层和工作台排版，不把大量信息堆在一个页面。

## 4.1 运营中心有效口径

详细规则见：

- `ecommerce-ops-platform/commerce-operations-workbench/README.md`
- `ecommerce-ops-platform/commerce-operations-workbench/docs/01_prd.md`
- `ecommerce-ops-platform/commerce-operations-workbench/docs/02_automation_boundary.md`
- `ecommerce-ops-platform/ops-workbench/docs/modules/operations-center.md`

当前关键原则：

- 运营中心覆盖商品库、选品测品、上架资料、直播排品、投流复盘、订单退款、库存利润和日报周报。
- 系统是运营 AI 辅助系统，不是 ERP，也不是全自动代运营系统。
- 第一阶段优先支持人工导入、表格上传、截图录入、CSV 导入和 AI 辅助生成，不直接调用抖店、巨量千川或平台后台接口。
- AI 只能生成卖点、上架资料、话术卡、复盘初稿、检查清单和建议；最终选品、定价、投流放量、补货、平台发布、资金、合同、合规和人员事项必须人工确认。
- 运营中心代码独立放在 `ops-workbench/app/api/v1/operations/`、`ops-workbench/app/services/operations/`、`ops-workbench/frontend/src/modules/operations/`。
- 运营中心运行态导入、导出、报告和临时文件统一放在 `ecommerce-ops-platform/ops-workbench-runtime/operations/`。
- 采后中心、主播控场、投流计划、客服售后、仓库管理、财务管理、项目中心按一级中心部署；业务文档分别放在 `commerce-procurement-workbench/`、`commerce-host-control-workbench/`、`commerce-ad-planning-workbench/`、`commerce-customer-service-workbench/`、`commerce-warehouse-workbench/`、`commerce-finance-workbench/`、`commerce-project-workbench/`。
- 这些岗位中心的运行态文件分别放在 `ops-workbench-runtime/procurement/`、`host-control/`、`ad-planning/`、`customer-service/`、`warehouse/`、`finance/`、`project/`，每个目录下统一使用 `imports/`、`exports/`、`reports/`、`temp/`。

## 5. 视频生产有效口径

详细规则见：

- `ecommerce-ops-platform/commerce-video-workbench/README.md`
- `ecommerce-ops-platform/commerce-video-workbench/docs/02_prd.md`
- `ecommerce-ops-platform/commerce-video-workbench/docs/03_workflow.md`
- `ecommerce-ops-platform/commerce-video-workbench/docs/engineering/PROJECT_DECISIONS.md`
- `ecommerce-ops-platform/commerce-video-workbench/docs/engineering/CONTEXT_INDEX.md`

当前关键原则：

- 人工决定视频归属、产品标签、视频顺序、文案、字幕/旁白和背景音乐。
- 系统自动执行文件移动/重命名、模型文案与语音辅助、音频提取、剪映草稿组装。
- 模型结果必须经过人工采纳或确认，不能直接进入生产草稿。
- “确认归类”是移动原视频文件，不是复制或导入。
- 工作台输出是可交给剪映继续编辑的半成品草稿，不是 MP4 成片。
- 模型配置统一使用阿里云百炼兼容连接，真实调用需要记录脱敏日志。

## 6. 图片生产最终业务口径

原始资料见：

- `ecommerce-ops-platform/commerce-image-workbench/README.md`
- `ecommerce-ops-platform/commerce-image-workbench/docs/02_prd.md`
- `ecommerce-ops-platform/commerce-image-workbench/docs/03_workflow.md`
- `ecommerce-ops-platform/commerce-image-workbench/docs/05_data_model.md`
- `ecommerce-ops-platform/commerce-image-workbench/docs/06_ai_prompting.md`

但这些旧文档中的“每个产品固定 8 张参考图”和“上传参考图”不是最终口径。以用户后续修正为准：

- 用户拿到的只有商品实拍图。
- 摄影师把实拍图上传到平台的摄影素材库；素材缩略图完整展示，可删除。未分配素材可被人工勾选。
- 人工从同一产品的实拍图创建一个产品组；不使用 AI 自动分组。一个产品只对应一个产品组，原始照片不能被多个产品组复用。
- 创建产品组时填写唯一产品名称，系统自动生成且不可修改的产品序列号；产品名称也不得重复。
- 产品组确认后不允许补充、移除或替换原始照片。若删除其中任一原图，产品变为“素材缺失需重拍”，不能继续出图或平台填报；删除产品档案时，原图回到待分配素材区，AI 任务、AI 图和平台资料删除。
- 产品档案字段均由人工填写；字段可按选中的产品档案批量修改。
- AI 先由原图分析/艺术风格模型提出各图类型的可编辑提示词，再由擅长生图的模型使用提示词和原图出图；模型、参数和任务记录需保留。各图类型可自定义，默认包括白底图、环境搭配图、佩戴图、商详图，数量可自由配置。
- 提交出图后显示进度，未结束不得重复提交，可终止或删除任务；终止保留已经成功的结果，删除任务及其结果。失败只重试失败阶段。
- 商详图是实际电商详情图，包含文案、布局、卖点、参数等；AI 可起草，人工可表格化修改。
- 审核按产品进行，并按图片类型分区；不满意的结果可写修改意见并重生成。
- 只有人工选中的 AI 图才可进入平台对应图片槽位；不同平台可选用不同的图。
- 导出时按批次和产品分类归档，建议结构为：`批次名称/产品唯一索引号_产品名称/白底图|环境搭配图|佩戴图|商详图`。

## 7. 平台链接与自动上传口径

- 图片结果既可以导出保存，也可以直接上传到平台创建商品链接。
- 用户会先自行登录平台，系统脚本使用现有登录态执行填写和上传，不绕过验证码、登录风控或平台安全限制。
- 抖音、快手、视频号等平台各维护一份独立模板，不需要模板复制；新模板可为空，再由用户自定义字段。
- 平台大部分字段相通，但不同平台、不同模板字段不同，必须允许自定义字段，包含名称、类型、必填、默认值、页面选择器和图片槽位映射；规格字段需支持颜色×尺码的 SKU 矩阵及库存、价格、SKU。
- 模板字段要记录填写方式，例如文本框、下拉列表、图片上传控件、富文本等。
- 为避免重复上传，产品名称不能重复，或由 AI/系统生成产品唯一索引号作为唯一键。
- 上传失败、需要人工处理或遇到风控时，系统应暂停并记录原因。
- 用户选定产品档案和平台模板后启动指定浏览器，并自行登录；确认登录后才继续自动填写、上传已选 AI 图并仅保存为平台草稿，绝不自动发布。遇验证码、风控、失败时暂停并保留当前步骤，人工处理后可继续或重试，避免重复创建草稿。
- 系统记录草稿保存状态、草稿入口和过程日志；用户在电商平台直接检查、修改、发布，不再回本系统验收标记。最终清单可导出 Excel/CSV，包含产品信息、图片路径、平台草稿链接和上传状态。

## 8. 后续开发阅读顺序

开发电商运营平台时：

1. 先读本文件。
2. 再读 `AGENTS.md`。
3. 再读 `ecommerce-ops-platform/docs/DEVELOPMENT_COLLABORATION.md`，按“模块、范围、目标、禁止、验收、执行”界定任务。
4. 视频相关先读 `ecommerce-ops-platform/commerce-video-workbench/README.md` 和 `docs/02_prd.md`、`docs/03_workflow.md`，再读 `ecommerce-ops-platform/commerce-video-workbench/docs/engineering/PROJECT_DECISIONS.md` 和 `docs/engineering/CONTEXT_INDEX.md`。
5. 运营中心相关先读 `ecommerce-ops-platform/commerce-operations-workbench/README.md`、`docs/01_prd.md`、`docs/02_automation_boundary.md`，再读 `ecommerce-ops-platform/ops-workbench/docs/modules/operations-center.md`。
6. 图片相关先读本文件第 6、7 节和 `ecommerce-ops-platform/commerce-image-workbench/docs/08_handoff.md`；若是具体子模块开发，再优先读取 `ecommerce-ops-platform/ops-workbench/docs/modules/` 下对应的小上下文文档：
   - 摄影素材与人工产品组：`image-source-grouping.md`
   - 产品档案与平台模板：`image-platform-templates.md`
   - AI 出图任务：`image-generation-tasks.md`
   - 图片审核与交付选图：`image-review-delivery.md`
   - 平台上传与草稿：`platform-autofill.md`
7. 只有需要追溯业务背景时，再读取 `commerce-image-workbench/docs/` 原始文档。
8. 若旧文档与用户后续修正冲突，采用用户后续修正。

## 9. 后续协作范式

为降低上下文消耗、防止跨模块误改，后续开发任务优先按以下格式沟通：

```text
模块：
范围：
目标：
禁止：
验收：
执行：
```

- **模块**：本次只处理哪个业务模块。
- **范围**：允许阅读和修改哪些文件、页面、接口或数据库结构。
- **目标**：用户最终要看到的业务结果。
- **禁止**：本次明确不能改动或不能恢复的旧能力。
- **验收**：完成标准和测试方式。
- **执行**：只分析、修改代码、跑测试、提交、推送等动作边界。

如果需求还没界定清楚，先要求助手“拆成模块、范围、目标、禁止、验收、执行，再开发”。

前端细节修改另按以下格式补充定位信息：

```text
前端修改：
页面：
区域：
元素文字：
当前问题：
期望效果：
不要动：
验收：
执行：
```

定位优先使用一级菜单、二级页面、区域名称、元素文字和截图红框/箭头。若只需调整按钮、文本、对齐、间距、弹窗、缩略图或表格列，应明确“只改前端/只改样式/不改后台逻辑”。
