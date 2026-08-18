# 09 项目结构与文件隔离

## 目标

参考 `E:\codexwork\ecommerce-ops-platform` 的组织方式，本项目也采用“业务文档、运行代码、运行态文件”分离。

这样做有三个目的：

- AI 开发时上下文更小。
- 代码目录不会被上传素材、生成结果、缓存污染。
- 后续可以把业务文档、运行服务、运行数据分别备份或迁移。

## 目录结构

```text
E:\wincodexwork\
  ai-video-workbench\
    README.md
    app\
    frontend\
    docs\
    scripts\
    tests\
    deploy\

  ai-video-workbench-runtime\
    databases\
    workspace\
    uploads\
    outputs\
    exports\
    cache\
    temp\
```

## 代码目录

`ai-video-workbench/` 只存放可维护文件：

- 后端代码。
- 前端代码。
- 测试。
- 部署配置。
- 脚本。
- Markdown 文档。
- 示例配置。

禁止写入：

- 用户上传图片、视频、音频。
- 生成结果。
- 数据库文件。
- 浏览器 profile。
- ComfyUI 临时输出。
- 厂商 API 下载结果。
- 大体积模型文件。

## 运行态目录

`ai-video-workbench-runtime/` 存放会增长、可清理、可迁移的运行数据。

```text
databases/  # 本地数据库
workspace/  # 项目工作区
uploads/    # 原始上传
outputs/    # AI生成结果
exports/    # 导出素材包
cache/      # API缓存、缩略图缓存
temp/       # 临时文件
```

## 环境变量

后续实现默认读取：

```text
AIV_RUNTIME_DIR=E:\wincodexwork\ai-video-workbench-runtime
AIV_DATABASE_URL=sqlite:///E:/wincodexwork/ai-video-workbench-runtime/databases/workbench.db
AIV_WORKSPACE_DIR=E:\wincodexwork\ai-video-workbench-runtime\workspace
AIV_UPLOADS_DIR=E:\wincodexwork\ai-video-workbench-runtime\uploads
AIV_OUTPUTS_DIR=E:\wincodexwork\ai-video-workbench-runtime\outputs
AIV_EXPORTS_DIR=E:\wincodexwork\ai-video-workbench-runtime\exports
```

本机 `.env` 应放在 `ai-video-workbench-runtime/.env`，不放在代码目录。

## AI 开发读文档策略

按任务读取最小文档集：

- 做页面：读 `10_UI_STYLE_ALIGNMENT.md` 和对应业务文档。
- 做数据库：读 `03_DOMAIN_MODEL.md`。
- 做接口：读 `04_API_CONTRACTS.md`。
- 做厂商 API：读 `05_PROVIDER_ADAPTERS.md`。
- 做 ComfyUI：读 `06_COMFYUI_INTEGRATION.md`。
- 做提示词：读 `07_PROMPT_SYSTEM.md`。
- 做任务排期：读 `08_MVP_TASKS.md`。

