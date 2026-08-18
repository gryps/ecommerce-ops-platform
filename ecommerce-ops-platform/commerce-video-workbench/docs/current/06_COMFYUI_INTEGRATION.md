# 06 ComfyUI 集成规范

## 定位

ComfyUI 是 AI 宣传片的工作流画布和视觉生产编排工具，不直接承担完整业务流程。

负责：

- 呈现文生视频、图生视频、首帧/尾帧、关键帧、局部重绘、放大、补帧等生产流程。
- 作为工作流编辑、参数调试和节点映射参考。
- 承接平台侧任务参数，提交给本地节点或模型 API 节点。
- 将生成结果、错误和任务 ID 回传给平台侧记录。

## 不负责

- 不管理项目状态。
- 不记录成本。
- 不直接访问业务数据库。
- 不替代电商平台资产录入、任务审批和结果管理。
- 不要求本地显卡或本地大模型资源。

## 当前部署状态

当前采用“小主机 + CPU + 模型 API 辅助”路线。小主机只负责平台、ComfyUI 画布、workflow 编排和 API 调度，不承担本地 AI 视频推理。

小主机环境：

```text
主机：gryps@192.168.31.24
电商运营平台：http://192.168.31.24:8000/workbench/
ComfyUI：http://192.168.31.24:8188/
ComfyUI 源码：/home/gryps/apps/ComfyUI
启动脚本：/home/gryps/apps/run-comfyui-smallhost.sh
运行态目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui
模型目录：/home/gryps/apps/ecommerce-ops-platform/ops-workbench-runtime/comfyui/models
虚拟环境：/home/gryps/apps/ComfyUI/.venv
Python：/home/gryps/runtime/python/current，Python 3.12.14
PyTorch：2.6.0+cpu
ComfyUI：0.33.0
```

本地 WSL 开发环境仍保留：

```text
本地项目：/mnt/e/codexwork/ecommerce-ops-platform
本地 ComfyUI：/mnt/e/codexwork/ComfyUI
本地运行态：/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime/comfyui
```

启动脚本默认设置：

```bash
export COMFYUI_DISABLE_BLUEPRINTS=1
export COMFYUI_DISABLE_WORKFLOW_TEMPLATES=1
```

当前不下载本地视频大模型，不依赖本地显卡。文生视频、图生视频优先通过模型 API adapter 或 ComfyUI API 节点完成。

详细小主机交接见：`../../../docs/SMALL_HOST_HANDOFF.md`。

## 默认工作流处理

为避免 ComfyUI 官方默认 workflow 误导后续开发，当前运行环境已关闭默认模板和 blueprints：

- `ComfyUI/blueprints` 是空运行目录。
- 原官方 blueprints 备份在 `ComfyUI/blueprints.disabled-api-workflows`。
- `/global_subgraphs` 和 `/api/global_subgraphs` 应返回 `{}`。
- `/workflow_templates` 应返回 `{}`。
- `/templates/index.json` 应返回 `404`。
- 前端默认 workflow 已改为空白画布。

如果页面再次出现默认 Z-Image 工作流，优先检查：

1. 浏览器缓存、Cache Storage、Service Worker。
2. `comfyui_frontend_package/static/assets/settingStore-*.js` 是否再次包含默认模型名。
3. `ComfyUI/blueprints` 是否被更新或恢复了官方 JSON。

## Workflow 注册

每个 workflow 需要配置：

```json
{
  "id": "product_keyframe_flux",
  "name": "产品关键帧生成",
  "workflow_path": "workflows/product_keyframe_flux.json",
  "comfyui_base_url": "http://127.0.0.1:8188",
  "input_schema": {
    "positive_prompt": "string",
    "negative_prompt": "string",
    "product_image": "file",
    "width": "number",
    "height": "number",
    "seed": "number"
  },
  "output_schema": {
    "images": "array"
  },
  "node_mappings": {
    "positive_prompt": {
      "node_id": "6",
      "field": "inputs.text"
    },
    "product_image": {
      "node_id": "12",
      "field": "inputs.image"
    }
  }
}
```

## 标准调用流程

```text
业务层创建 ComfyTask
-> 读取 workflow 配置
-> 根据 node_mappings 注入参数
-> 提交 ComfyUI /prompt
-> WebSocket 或轮询进度
-> 从 output 目录收集结果
-> 复制到项目 shot 目录
-> 创建 Asset 或 ShotVersion
```

## 目录约定

```text
comfy_workflows/
  product_keyframe/
  product_cleanup/
  person_consistency/
  inpaint_fix/
  upscale/

projects/{project_id}/shots/shot_001/keyframes/
```

## 输入输出约束

- 所有输入文件必须先进入项目目录。
- Workflow 不能使用绝对业务路径写死。
- 输出文件必须由 StorageService 复制到项目目录。
- 同一 workflow 的输出必须可通过配置识别。
- 失败时保存 ComfyUI prompt_id 和错误信息。

## MVP 工作流清单

1. `text_to_video`：文生视频，输入导演提示词、产品卖点、画幅、时长、风格和模型参数。
2. `image_to_video`：图生视频，输入商品图、首帧/参考图、运动描述、画幅、时长和模型参数。
3. `first_last_frame`：首帧/尾帧辅助生成，用于增强图生视频可控性。
4. `product_keyframe`：商品广告关键帧。
5. `scene_keyframe`：场景关键帧。
6. `inpaint_fix`：局部修复。
7. `upscale_image`：图片放大。

## 环境检查

启动时检测：

- ComfyUI 是否可连接。
- Python/ComfyUI 版本。
- 是否为当前约定的 WSL + CPU/API 模式。
- 必要 API 配置是否存在。
- workflow 依赖节点是否存在。

检测结果只做提示，不阻塞整个系统启动。
