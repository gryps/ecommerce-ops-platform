# 模块上下文索引

本目录用于降低后续开发上下文体积。改动某个业务能力时，优先读取对应模块文档，再读取其中列出的代码文件；不要默认通读整个电商运营平台。

## 电商图片生产模块

| 模块 | 文档 | 适用任务 |
| --- | --- | --- |
| 摄影素材与人工产品组 | `image-source-grouping.md` | 上传原始照片、待分配素材、人工创建产品组、删除原图 |
| 产品档案与平台模板 | `image-platform-templates.md` | 抖音/快手/视频号模板、自定义字段、图片槽位、批量字段修改 |
| AI 出图任务 | `image-generation-tasks.md` | 提示词、模型调用、后台出图任务、进度、终止、重试 |
| 图片审核与交付选图 | `image-review-delivery.md` | 结果审核、修改意见、选择进入平台槽位的 AI 图 |
| 平台上传与草稿 | `platform-autofill.md` | 浏览器登录态、自动填写字段、上传图片、保存草稿、风控暂停 |

## 固定前置

开发前仍需先读：

- `/mnt/e/codexwork/PROJECT_MEMORY.md`
- `/mnt/e/codexwork/AGENTS.md`

若本目录文档与 `PROJECT_MEMORY.md` 冲突，以 `PROJECT_MEMORY.md` 和用户最新口径为准。
