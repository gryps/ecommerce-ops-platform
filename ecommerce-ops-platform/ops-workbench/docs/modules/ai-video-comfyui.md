# AI 宣传片 / ComfyUI 视频工作流

## 边界

本模块是电商平台侧的 AI 宣传片业务控制台，不是 ComfyUI 的替代品。

ComfyUI 负责节点画布、workflow 编排和生产链路调试；电商平台负责商品项目、业务资产、导演分镜、任务记录、输出回收、审核导出和运营闭环。

负责：

- 平台保存项目、资产、导演分镜、生成任务、厂商任务 ID、任务事件和输出路径；
- ComfyUI 作为画布和 workflow 编排工具，表达节点结构和参数映射；
- 厂商视频模型 API 执行真实生成；
- 小主机回收远程输出文件到运行态目录；
- 记录输入、输出、错误原因、耗时和人工确认状态。
- 从平台打开 ComfyUI、检测连接、登记并提交与业务项目关联的生成任务。

不负责：

- 本地 GPU 推理；
- 下载本地大模型、视频模型或 VAE/CLIP/UNet 权重；
- 把厂商 API Key 写入 workflow JSON；
- 让 ComfyUI 默认 workflow 变成业务模板；
- 在平台内一比一复刻 ComfyUI 节点画布；
- 把平台资产、项目、审核和导出迁移到 ComfyUI 浏览器本地状态；
- 自动发布成片到电商平台。

## 当前实现

已实现：

- 项目、资产、分镜、任务、事件使用 SQLite 表存储；
- 资产上传保存到 `ops-workbench-runtime/ai-video/uploads/`；
- `vendor_video` 和 `comfyui` 两种任务引擎边界；
- 厂商视频 API 标准 adapter：`app/services/ai_video/provider_adapters.py`；
- 任务提交：`POST /api/v1/ai-video/generation/tasks/{task_id}/submit`；
- 任务状态刷新：`POST /api/v1/ai-video/generation/tasks/{task_id}/refresh`；
- 厂商任务成功后，远程 `http(s)` 输出会下载到 `ops-workbench-runtime/ai-video/outputs/{project_id}/{task_id}/`。
- 前端已调整为“AI 宣传片控制台”：业务资产和任务留在平台，节点画布入口跳转 ComfyUI。

未完成：

- 真实厂商 payload、状态字段和输出字段校准；
- 真实文生视频或图生视频出片验收；
- ComfyUI workflow 注册表和业务模板选择；
- 自动轮询 worker；
- 业务侧成本、耗时、人工确认和导出归档。

## ComfyUI 约束

ComfyUI 只作为画布和编排层：

- 启动参数保留 `--cpu`；
- `models/` 目录不随项目打包迁移；
- workflow JSON 不保存密钥；
- workflow JSON 不写死业务数据库路径；
- 默认官方 workflow 不能作为业务工作流；
- 浏览器恢复默认 workflow 时，先清理浏览器缓存和本地状态，不下载默认模型。

## 关键代码

- 前端页面：`frontend/src/modules/ai-video-production/AiVideoProduction.tsx`，定位为 ComfyUI 业务控制台
- 后端路由：`app/api/v1/ai_video_production.py`
- 任务执行：`app/services/ai_video/executor.py`
- 厂商 adapter：`app/services/ai_video/provider_adapters.py`
- 数据仓储：`app/services/ai_video/store.py`
- 数据模型：`app/services/ai_video/models.py`
- ComfyUI 客户端：`app/services/ai_video/comfyui_client.py`

## 禁止改动

- 不下载本地视频模型；
- 不把本地显卡作为验收前提；
- 不把 API Key、代理口令或账号凭证写入 workflow；
- 不把 AI 宣传片资产录入迁到 ComfyUI 本地状态里；
- 不在平台内继续复制 ComfyUI 画布功能；
- 不绕过平台任务记录直接在 ComfyUI 里跑业务生产。

## 下一步建议

优先二选一跑通：

1. 文生视频：平台填写导演提示词，提交厂商 API，刷新状态，下载 MP4，平台展示输出。
2. 图生视频：平台上传首帧图，提交厂商 API，刷新状态，下载 MP4，平台展示输出。

验收要求：

- 有真实厂商任务 ID；
- 有本地输出文件；
- 有任务事件；
- 有失败错误回写；
- 有一次完整输入/输出记录。
