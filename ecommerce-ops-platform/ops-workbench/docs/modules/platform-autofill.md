# 图片生产 / 平台上传与草稿

## 边界

本模块负责使用用户已登录浏览器，把产品档案字段和已选 AI 图填写到电商平台，并保存为草稿。

负责：

- 启动指定浏览器；
- 使用用户自行登录后的现有登录态；
- 根据模板字段 selector 填写页面字段；
- 根据图片槽位 selector 上传图片；
- 保存为平台草稿；
- 记录草稿链接、状态和过程日志；
- 遇到验证码、风控、失败时暂停并可继续或重试。

不负责：

- 自动登录；
- 绕过验证码、风控或二次确认；
- 自动发布商品；
- 生成 AI 图片；
- 平台模板字段维护。

## 当前实现

已实现：

- 浏览器会话启动：`POST /api/v1/images/browser-sessions`
- 查询会话：`GET /api/v1/images/browser-sessions/{session_id}`
- 停止会话：`DELETE /api/v1/images/browser-sessions/{session_id}`

未实现：

- 页面 selector 自动填写；
- 图片上传；
- 保存草稿；
- 草稿链接回写；
- 风控暂停/继续状态机。

## 关键代码

- 前端交付页：`frontend/src/modules/image-production/ImageDelivery.tsx`
- 前端浏览器会话 hook：`frontend/src/modules/image-production/usePlatformBrowserSession.ts`
- 后端路由：`app/api/v1/image/delivery.py`
- 浏览器服务：`app/services/platform_browser.py`
- 后续建议新增：`app/services/image/platform_autofill.py`

## 禁止改动

- 不自动发布；
- 不绕过平台安全校验；
- 不要求人工在本系统回填最终验收状态。

## 下一步开发建议

先实现一个平台的最小闭环，例如抖音：

1. 读取一个产品平台档案；
2. 打开发布页；
3. 按模板 selector 填字段；
4. 上传已选图片；
5. 点击保存草稿；
6. 回写草稿状态和草稿链接。
