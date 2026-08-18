# AI商品宣传片制作系统文档索引

目标：把产品、架构、接口、数据、提示词和工作流拆成小上下文文档，便于 AI 辅助开发时按需读取，降低 token 消耗和误改概率。

## 文档阅读顺序

1. `01_PRODUCT_BRIEF.md`：产品边界、MVP、用户流程。
2. `02_TECH_ARCHITECTURE.md`：系统架构、模块边界、解耦原则。
3. `03_DOMAIN_MODEL.md`：核心实体、状态机、目录规范。
4. `04_API_CONTRACTS.md`：后端接口草案。
5. `05_PROVIDER_ADAPTERS.md`：厂商视频 API 适配层。
6. `06_COMFYUI_INTEGRATION.md`：本地 ComfyUI 工作流规范。
7. `07_PROMPT_SYSTEM.md`：AI 导演提示词与镜头提示词体系。
8. `08_MVP_TASKS.md`：MVP 开发任务拆分。
9. `09_PROJECT_STRUCTURE.md`：项目目录、运行态文件和文档隔离规范。
10. `10_UI_STYLE_ALIGNMENT.md`：与电商平台工作台的界面风格对齐规范。

## AI 开发约定

- 每次开发只加载当前任务相关文档，避免一次性读完整 PRD。
- 每个模块只通过明确接口通信，不跨层直接访问实现细节。
- 厂商 API、ComfyUI workflow、提示词模板全部配置化。
- 生成任务必须可追踪：输入、参数、模型、成本、输出、错误原因都要落库。
- 任何外部服务调用都走 adapter，不在业务代码里写厂商专用逻辑。
- 前端实现必须参考 `E:\codexwork\ecommerce-ops-platform\ops-workbench`，保持同一套工作台视觉语言。
- 运行态文件必须写入 `ai-video-workbench-runtime/`，不得写入代码或文档目录。
