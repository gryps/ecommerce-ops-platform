# 02 技术架构

## 架构目标

- 模块解耦：产品、资产、分镜、提示词、ComfyUI、视频 API、成本统计独立演进。
- 上下文小：每个模块有清晰输入输出，便于 AI 单独修改。
- 厂商可替换：所有视频模型通过 Provider Adapter 接入。
- 工作流可配置：ComfyUI workflow 不写死在代码里。
- 任务可追踪：所有生成任务必须有状态、成本、输入、输出和错误记录。

## 推荐技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vite / React / TypeScript / CSS |
| 后端 | FastAPI |
| 数据库 | SQLite 起步，PostgreSQL 扩展 |
| 队列 | RQ / Celery |
| 缓存 | Redis，可在 MVP 后引入 |
| 文件存储 | 独立 runtime 目录，后续可扩展 OSS/S3 |
| ComfyUI | HTTP API + WebSocket 进度 |
| 视频 API | Provider Adapter |

## 模块划分

```text
frontend
  project workspace
  asset manager
  director board
  shot production
  review compare

backend
  project_service
  product_service
  asset_service
  script_service
  prompt_service
  comfyui_service
  provider_service
  generation_service
  cost_service
  export_service
```

## 与电商平台对齐

参考项目 `E:\codexwork\ecommerce-ops-platform\ops-workbench` 已形成稳定的工作台结构。本项目后续实现时优先保持同构：

```text
ai-video-workbench/
  app/
    api/v1/
    services/
    domain/
    core/
  frontend/
    src/
      modules/ai-video-production/
      components/
      api/
  docs/
  scripts/
  tests/
```

运行态文件写入同级目录：

```text
../ai-video-workbench-runtime/
```

## 分层原则

### API Layer

只负责请求校验、鉴权、响应格式，不写业务流程。

### Service Layer

编排业务流程，例如创建镜头生成任务、调用提示词模块、提交厂商 API。

### Adapter Layer

隔离外部系统：

- `VideoProviderAdapter`
- `ComfyUIAdapter`
- `StorageAdapter`
- `LLMAdapter`

### Domain Layer

保存领域实体、状态枚举、规则函数，不依赖外部服务。

## 任务流

```text
用户点击生成镜头
-> generation_service 创建 GenerationTask
-> prompt_service 准备提示词
-> provider_service 选择 adapter
-> adapter 提交厂商 API
-> 队列轮询任务状态
-> 下载结果到本地
-> 更新 ShotVersion
-> cost_service 记录成本
```

## 解耦边界

- Shot 不知道具体厂商模型。
- Prompt 不知道任务是由哪个厂商生成。
- Provider Adapter 不知道项目业务，只接收标准请求。
- ComfyUI workflow 只接收映射后的参数，不读取业务表。
- 文件路径由 StorageService 统一生成。

## 配置优先

以下内容必须配置化：

- 厂商 base_url、model_name、价格、能力、时长、比例。
- ComfyUI 地址、workflow JSON、节点输入映射。
- 提示词模板、负面词模板、平台风格模板。
- 输出目录规则。
