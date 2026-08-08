# 电商图片生产交接文档（2026-08-08）

## 项目与验证

- 项目根目录：`/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench`
- 前端：`frontend/src/HumanApp.tsx`
- 接口：`app/api/v1/image_production.py`
- 数据模型：`app/domain/models.py`
- 服务：`systemctl --user restart product-video-automation`
- 开始前阅读：`/mnt/e/codexwork/PROJECT_MEMORY.md` 第 6、7 节，以及 `/mnt/e/codexwork/AGENTS.md`。
- 工作区有大量用户已有未提交改动；不要 reset、checkout 或清理工作区。

本轮已验证：`npm run build` 通过；`/mnt/e/codexwork/.venv/bin/python -m pytest tests/test_current_workflow.py -q` 为 **32 passed**；服务健康检查 `/api/health` 返回 200。未做真实浏览器点击测试。

## 已确认的业务口径

### 原图、分组与产品

- 摄影师上传实拍原图到素材库；人工选择同款照片创建产品组，不要 AI 自动分组。
- 一个产品只对应一个产品组，照片不可复用。
- 创建组时输入唯一产品名称，系统生成不可修改的唯一索引；产品名称不可重复。
- 组确认后不补充、移除、替换原图；有问题则删除原图、重新拍摄、重新分组。
- 删除产品档案时，原图默认退回待分配区；可选一并永久删除。

### AI 出图

- 分析/艺术风格模型先根据原图给出可编辑提示词；生图模型再用提示词和原图生成白底、场景、模特/佩戴、商详等图。
- 任务需显示进度，未完成不可重复提交，可终止、删除，失败只重试失败阶段。
- 只有人工选中的审核通过 AI 图可进入平台图片槽位。

### 模板、自定义字段、产品档案

- 抖音、快手、视频号等各维护独立模板；不需要模板复制。
- 模板可以为空。
- **用户在模板中新增、删除、调整字段，才叫“自定义字段”。** 系统不能预设颜色、尺码、库存、价格、规格等字段让用户任意填写；这些仅是用户可自行创建的示例。
- 模板字段定义：字段键、显示名称、类型、必填、默认值/下拉选项、页面选择器；图片槽位单独定义。
- 产品档案只填写所选模板已经定义的字段值，且可按模板字段批量修改。
- SKU 要支持颜色 × 尺码，以及库存、价格、SKU 的矩阵。当前仅有 `sku_matrix` 文本类型，尚未实现结构化矩阵编辑器。

### 平台填报

- 用户在指定浏览器自行登录，系统使用既有登录态；不得绕过验证码、风控或二次确认。
- 系统填写字段、上传已选 AI 图，只保存草稿，绝不自动发布。
- 风控/验证码/失败时暂停记录；验收、修改、发布在电商平台内完成，不回本系统逐条标记。

## 当前实现

已具备：人工素材上传与缩略图、产品组、产品编号、照片不可复用、删除原图、删除产品时原图返还或随同删除、平台模板/字段/图片槽位/单产品平台档案基础接口、浏览器会话启动/停止。

浏览器尚未真正实现网页自动填写、上传、保存草稿。

本轮刚做的代码改动：

- `HumanApp.tsx` 产品清单已移除类目、材质、主辅色、风格、卖点这些固定列。
- 产品资料页新增按所选模板动态显示字段值。
- 批量操作改为：勾选产品 → 选模板 → 选模板字段 → 填值。
- `image_production.py` 新增 `PATCH /api/images/platform-profile-batch-fields`，按模板批量更新产品档案；缺少该模板档案时自动创建并带入默认值。

## 2026-08-08 后续修正状态

已修正用户明确指出的问题：**自定义字段/平台模板管理不应放在“导出上传”模块。**

当前布局：

- `products`（产品资料）负责平台模板新增/删除、字段定义、图片槽位定义、产品档案字段填写和批量修改。
- `delivery`（导出上传）只保留选择产品、选择已保存模板、选择审核通过 AI 图、启动浏览器保存平台草稿。
- 产品资料页提示已改为在本页新建模板并添加自定义字段。

已清理：

- 旧固定产品字段运行时代码已移除：类目、材质、主辅色、风格、结构、卖点、保真规则、备注不再作为产品资料字段。
- 旧 `/images/products/batch-fields` 接口已移除，批量修改改用模板字段接口 `/images/platform-profile-batch-fields`。
- 旧固定 8 张参考图运行时代码已移除，产品完整度改为已确认实拍图数量。
- 新迁移 `k83d5f7h9q21_remove_fixed_image_product_fields.py` 删除旧固定字段列和旧参考图表。

## 定位与命令

| 用途 | 位置 |
| --- | --- |
| 产品资料、模板、导出上传 UI | `frontend/src/HumanApp.tsx`，约 995–1110 行 |
| 模板与档案 API | `app/api/v1/image_production.py`，约 127–350 行 |
| 清理旧固定字段迁移 | `migrations/versions/k83d5f7h9q21_remove_fixed_image_product_fields.py` |
| 模板和档案数据表 | `app/domain/models.py` 中 `CommercePlatformTemplate`、`CommerceProductPlatformProfile` |

验证命令：`cd frontend && npm run build`；回到项目根目录执行 `/mnt/e/codexwork/.venv/bin/python -m pytest tests/test_current_workflow.py -q` 和 `git diff --check`。
