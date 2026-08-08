# 图片生产 / 产品档案与平台模板

## 边界

本模块只负责平台模板、自定义字段、图片槽位和产品档案字段值。

负责：

- 抖音、快手、视频号等平台各自独立维护模板；
- 模板可为空；
- 用户在模板中新增、删除、调整字段，这才叫自定义字段；
- 字段定义包含字段键、显示名称、类型、必填、默认值/选项、页面选择器；
- 图片槽位单独定义；
- 产品档案只填写所选模板已有字段；
- 支持按选中产品批量修改模板字段值。

不负责：

- 系统预设颜色、尺码、库存、价格等固定字段；
- AI 出图；
- 浏览器自动填报执行；
- 导出包生成。

## 当前实现

已实现基础接口：

- `GET /api/v1/images/platform-templates`
- `POST /api/v1/images/platform-templates`
- `PATCH /api/v1/images/platform-templates/{template_id}`
- `DELETE /api/v1/images/platform-templates/{template_id}`
- `GET /api/v1/images/platform-profiles`
- `POST /api/v1/images/products/{product_id}/platform-profiles/{template_id}`
- `PATCH /api/v1/images/platform-profiles/{profile_id}`
- `PATCH /api/v1/images/platform-profile-batch-fields`

## 关键代码

- 前端产品资料：`frontend/src/modules/image-production/ImageProducts.tsx`
- 前端模板管理：`frontend/src/modules/image-production/PlatformTemplateManager.tsx`
- 前端模板 hook：`frontend/src/modules/image-production/usePlatformTemplateEditor.ts`
- 后端路由：`app/api/v1/image/platform_templates.py`
- 序列化：`app/api/v1/image/serializers.py`
- 数据模型：`app/domain/models.py` 中 `CommercePlatformTemplate`、`CommerceProductPlatformProfile`

## 禁止改动

- 不把模板字段管理移动到“导出上传”模块；
- 不给产品资料恢复固定字段；
- 不在字段外单独硬编码颜色、尺码、库存、价格、规格。

## 验收

- 可创建空模板；
- 可新增、删除、修改模板字段；
- 产品档案只显示当前模板字段；
- 批量字段修改只作用于选中产品和选中模板；
- 删除模板会清理对应平台档案。
