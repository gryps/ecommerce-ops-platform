# 图片生产 / 摄影素材与人工产品组

## 边界

本模块只负责摄影师原始照片进入素材库、运营人工勾选同一产品照片并创建产品组。

负责：

- 上传原始照片到运行目录素材库；
- 展示待分配素材和缩略图；
- 删除待分配原图；
- 勾选原图创建产品组；
- 自动生成不可修改的产品序列号；
- 保证一个原图只能归属一个产品组；
- 删除产品时让原图退回待分配区，或按用户明确选择一并删除。

不负责：

- AI 自动分组；
- AI 出图；
- 平台模板字段；
- 平台自动上传；
- 视频生产。

## 当前实现

已实现基础能力：

- 原图上传接口：`POST /api/v1/images/source-assets`
- 原图列表接口：`GET /api/v1/images/source-assets`
- 原图文件读取：`GET /api/v1/images/source-assets/{asset_id}/file`
- 删除原图：`DELETE /api/v1/images/source-assets/{asset_id}`
- 从原图创建产品：`POST /api/v1/images/source-assets/create-product`

删除已分配原图时，产品状态会变为 `needs_reshoot`，阻止继续出图。

## 关键代码

- 前端：`frontend/src/modules/image-production/ImageSourceGrouping.tsx`
- 前端 hook：`frontend/src/modules/image-production/useImageSourceAssets.ts`
- 后端路由：`app/api/v1/image/source_assets.py`
- 后端产品路由：`app/api/v1/image/products.py`
- 后端服务：`app/services/image/products.py`
- 数据模型：`app/domain/models.py` 中 `CommerceImageSourceAsset`、`CommerceImageSourceArchive`、`CommerceImageGroup`、`CommerceImageProduct`

## 禁止改动

- 不恢复 `AI 自动分组`、`AI 分组`、`拍摄批次` 等误导性入口；
- 不恢复固定 8 张参考图；
- 不允许一个原图被多个产品组复用。

## 验收

- 上传多张图片后能看到待分配素材；
- 缩略图完整展示；
- 可删除待分配素材；
- 勾选素材创建产品组后，素材不再出现在待分配区；
- 删除产品时默认原图退回待分配区。
