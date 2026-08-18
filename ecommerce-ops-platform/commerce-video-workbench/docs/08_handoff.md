# 交接文档

## 1. 当前目录关系

```text
/mnt/e/codexwork/ecommerce-ops-platform/
├── ops-workbench/                  # 实际运行项目：视频 + 图片 + 模型配置
├── commerce-image-workbench/        # 电商图片生产文档
└── commerce-video-workbench/        # 电商视频生产文档
```

视频生产代码不在本目录，本目录只作为业务文档入口。

## 2. 运行项目

实际运行项目：

```text
/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
```

主要位置：

- 前端入口：`frontend/src/HumanApp.tsx`
- 前端样式：`frontend/src/human.css`
- 后端入口：`app/main.py`
- API：`app/api/v1/`
- 服务：`app/services/`
- ORM：`app/domain/models.py`
- 迁移：`migrations/versions/`
- 测试：`tests/test_current_workflow.py`

## 3. 服务

当前仍使用用户级 systemd 服务：

```bash
systemctl --user status product-video-automation
systemctl --user restart product-video-automation
```

服务名暂未改名。服务 WorkingDirectory 应指向：

```text
/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
```

## 4. 当前业务口径

以后处理视频生产需求时，优先采用以下文档顺序：

1. `/mnt/e/codexwork/PROJECT_MEMORY.md`
2. `/mnt/e/codexwork/AGENTS.md`
3. `commerce-video-workbench/README.md`
4. `commerce-video-workbench/docs/02_prd.md`
5. `commerce-video-workbench/docs/03_workflow.md`
6. `commerce-video-workbench/docs/engineering/PROJECT_DECISIONS.md`
7. `commerce-video-workbench/docs/engineering/CONTEXT_INDEX.md`

如果文档与代码冲突：

- 业务含义以 `PROJECT_MEMORY.md` 和本目录文档为准。
- 实现事实以当前代码、迁移和测试为准。
- 历史归档只用于追溯，不得恢复已退役功能。

## 5. 已退役功能

不要按旧文档恢复以下能力：

- 人工粗剪与代理片段；
- 音乐卡点和混剪框架；
- 自动选片和系统内精修；
- 成片渲染和成片库；
- 热播短链接跟踪；
- 无人值守自动生产；
- 框架库和框架布局。

## 6. 验证命令

在运行项目目录执行：

```bash
cd /mnt/e/codexwork/ecommerce-ops-platform/ops-workbench
npm --prefix frontend run build
/mnt/e/codexwork/.venv/bin/python -m pytest tests/test_current_workflow.py -q
curl --max-time 5 -sS http://127.0.0.1:8000/api/health
```

如 curl 访问本机服务被沙箱限制，需要提升权限重试。

## 7. 未完成验收

仍需真实业务环境验收：

- 真实素材盘多视频归类移动；
- 当前剪映专业版打开生成草稿；
- 实际抖音链接音频提取；
- 真实百炼 ASR/TTS 调用；
- 真实运营文案迭代质量。

## 8. 修改提醒

涉及视频生产业务口径变更时，应同步更新：

- 本目录对应文档；
- `/mnt/e/codexwork/PROJECT_MEMORY.md`；
- `docs/engineering/PROJECT_DECISIONS.md` 或对应模块文档；
- 如涉及交互名称，更新 `docs/engineering/UI_FUNCTION_CATALOG.md`。

## 9. 后续协作方式

继续开发视频生产时，优先按以下格式给任务，减少上下文并避免误改图片生产或模型配置：

```text
模块：
范围：
目标：
禁止：
验收：
执行：
```

详细规范见：

```text
/mnt/e/codexwork/ecommerce-ops-platform/docs/DEVELOPMENT_COLLABORATION.md
```

如果任务只涉及视频生产，应明确写出“不改电商图片生产、不改模型配置”。

## 10. 本阶段收口：小主机迁移与 ComfyUI 画布

本地项目当前阶段告一段落，但不是整个平台完结。经营看板、运营中心、采后中心、主播控场、投流计划、客服售后、仓库管理、财务管理、项目中心、图片生产、视频生产、模型配置等模块仍会在后续继续完成。

当前已完成的小主机迁移结果：

```text
小主机：gryps@192.168.31.24
电商运营平台：http://192.168.31.24:8000/workbench/
ComfyUI：http://192.168.31.24:8188/
平台服务：product-video-automation，active
ComfyUI 服务：comfyui，active
运行根目录：/home/gryps/apps/ecommerce-ops-platform
运行态目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime
开发主环境：小主机本地 Git 工作树
当前数据库版本：n06g8h0i3j47
```

详细部署交接见：

```text
/home/gryps/apps/ecommerce-ops-platform/docs/SMALL_HOST_HANDOFF.md
```

已完成的方向性决策：

- AI 宣传片后续引入 ComfyUI 风格画布，用画布表达资产、导演、分镜、任务、导出等生产逻辑。
- 电商平台仍作为业务资产、项目状态、成本、任务记录和人工确认入口；ComfyUI 不替代业务系统。
- ComfyUI 用作工作流编排和可视化参考，不直接承载电商运营平台的业务数据库。
- 后续视频生成重点转向模型 API 辅助，不要求本地显卡和本地大模型资源。
- 小主机适合作为平台服务器和 ComfyUI/API 中控，不适合作为本地 AI 推理算力机器。
- AI 宣传片数据已从 JSON 原型文件迁入 SQLite 表；后续任务、事件、结果回收都应继续走数据库。
- 后端已建立 ComfyUI 任务提交边界；占位 workflow 会明确失败并记录事件，真实 API workflow 接入后复用同一入口。
- 前端平台壳层已拆出：导航配置、侧边栏、顶部状态栏、账号弹窗分别位于 `ops-workbench/frontend/src/components/shell/`；壳层和登录样式位于 `ops-workbench/frontend/src/styles/`。

当前 ComfyUI 小主机状态：

```text
ComfyUI 源码：/home/gryps/apps/ComfyUI
启动脚本：/home/gryps/apps/run-comfyui-smallhost.sh
运行态目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui
模型目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/models
访问地址：http://192.168.31.24:8188/
Python：/home/gryps/runtime/python/current，Python 3.12.14
虚拟环境：/home/gryps/apps/ComfyUI/.venv
PyTorch：2.6.0+cpu
```

注意：

- 远端 ComfyUI models 目录不应存放本地视频大模型权重。
- 不要为了文生视频、图生视频再下载本地大模型包；后续优先通过模型 API 节点或后端 adapter 调用外部视频模型。
- ComfyUI 冷启动仍可能需要几十秒。慢点主要在 Python、PyTorch CPU 包、节点定义、前端包、SQLite 迁移和资源服务初始化，不代表正在加载本地视频模型。
- 如果页面再次出现默认工作流，优先检查浏览器缓存、Service Worker、ComfyUI 前端本地状态和模板/blueprint 设置，而不是下载模型。

## 11. 下一阶段：围绕 ComfyUI 制作文生视频、图生视频

下一阶段近期重点是围绕 ComfyUI 制作文生视频、图生视频；平台其他未完成模块后续按业务优先级继续推进。

ComfyUI 视频方向工作重点：

1. 梳理文生视频、图生视频的业务输入字段：商品资产、卖点、导演意图、镜头时长、画幅、风格、人物/产品一致性、参考图、首帧/尾帧等。
2. 在平台侧定义标准任务模型和 API adapter，不把厂商调用逻辑和敏感凭证写死在画布 JSON 里。
3. 在 ComfyUI 侧制作最小可用 workflow：文生视频 workflow、图生视频 workflow、首帧/尾帧辅助 workflow。
4. 建立平台字段到 ComfyUI 节点参数的映射表。
5. 明确输出回收规则：视频文件、封面图、prompt、厂商任务 ID、成本、错误原因、重试记录。
6. 再把成熟 workflow 接回 AI 宣传片页面，形成“平台录入资产和任务，画布呈现与调参，平台记录生产结果”的闭环。

当前建议不要继续扩大前端页面，先做一个真实模型 API adapter。adapter 要记录厂商任务 ID、请求参数摘要、错误原因、耗时和输出文件路径；API Key 继续放后端配置，不写入 ComfyUI workflow JSON。

建议下一次开发先从一个最小闭环开始：

```text
模块：AI 宣传片 / ComfyUI 视频工作流
范围：只做文生视频或只做图生视频二选一
目标：平台录入参数 -> ComfyUI/API 提交任务 -> 回收结果 -> 在平台任务记录中展示
禁止：不下载本地大模型；不改图片生产；不改运营中心导航；不把 API Key 写入 workflow JSON
验收：能用一个真实模型 API 跑通一次任务，并记录输入、输出、厂商任务 ID、耗时和错误信息
执行：先设计字段和 adapter，再接画布
```
