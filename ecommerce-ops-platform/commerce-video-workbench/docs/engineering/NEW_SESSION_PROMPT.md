# 新会话启动提示词

请在项目 `/mnt/e/codexwork` 中继续开发电商运营平台。当前近期重点已经切到 **AI 宣传片 / ComfyUI 文生视频、图生视频工作流**。

开始工作前：

1. 先读 `/mnt/e/codexwork/PROJECT_MEMORY.md` 和 `/mnt/e/codexwork/AGENTS.md`。
2. 再读远端或本地项目中的 `ecommerce-ops-platform/docs/SMALL_HOST_HANDOFF.md`，确认小主机部署、服务和资源边界。
3. ComfyUI 相关任务继续读 `commerce-video-workbench/docs/current/06_COMFYUI_INTEGRATION.md`。
4. 视频生产业务规则需要追溯时，再读 `commerce-video-workbench/docs/08_handoff.md` 和 `commerce-video-workbench/docs/engineering/CONTEXT_INDEX.md`。
5. 不要默认通读 `../archive/PROJECT_HANDOFF_ARCHIVE.md`；只有追溯历史原因时才按关键词读取局部。
6. 以当前代码、最新数据库状态、服务状态和真实测试结果判断实现状态，不要把历史文档中的旧路线图当作当前待办。

当前运行环境：

```text
小主机：gryps@192.168.31.24
电商运营平台：http://192.168.31.24:8000/workbench/
ComfyUI：http://192.168.31.24:8188/
SSH：ssh -F /dev/null gryps@192.168.31.24
```

协作规则：

- 除高风险、不可逆操作，或我明确说“先讨论”外，所有开发需求默认直接执行，无须等待我确认。
- 不要下载本地视频大模型，不要把小主机当成本地推理机器。
- 小主机只做平台运行、ComfyUI 画布、workflow 编排、模型 API 调度和结果回收。
- 模型 API Key 不写入 ComfyUI workflow JSON；优先放在平台后端 adapter 或受控配置里。
- 保留工作区中已有改动，不覆盖或回退无关内容。
- 完成开发后按影响范围运行 Python 测试、React 生产构建和必要的服务健康检查。
- 完成后更新对应交接文档或模块文档；只把真实未完成事项写入 `NEXT_TASK.md`。

建议下一项开发按以下范围启动：

```text
模块：AI 宣传片 / ComfyUI 视频工作流
范围：文生视频或图生视频二选一；平台 adapter、workflow 配置、任务记录和结果回收
目标：平台录入参数 -> ComfyUI/API 提交任务 -> 回收结果 -> 平台展示任务状态和结果
禁止：不下载本地大模型；不把 API Key 写入 workflow JSON；不改运营中心、图片生产和导航
验收：用一个真实模型 API 跑通一次任务，记录输入、输出、厂商任务 ID、错误原因和耗时
执行：先设计字段和 adapter，再接 ComfyUI workflow 和页面
```
