# 10 UI 风格对齐规范

## 参考项目

UI 参考：

```text
E:\codexwork\ecommerce-ops-platform\ops-workbench
```

重点参考文件：

```text
frontend/src/human.css
frontend/src/HumanApp.tsx
frontend/src/modules/image-production/
frontend/src/modules/video-production/
frontend/src/components/
```

## 技术栈对齐

本项目后续前端使用：

- Vite
- React
- TypeScript
- CSS 文件样式，不优先引入大型 UI 框架
- lucide-react 图标

暂不使用 Next.js，除非后续明确需要服务端渲染。这样可以和电商平台保持一致。

## 页面骨架

沿用电商平台工作台结构：

```text
固定左侧侧边栏
  -> 平台/模块切换
  -> 当前模块导航

主内容区
  -> sticky 顶部栏
  -> 页面标题
  -> 操作状态
  -> 用户入口

页面内容
  -> 高密度业务卡片
  -> 表格/列表/工作区
  -> 右侧配置或审核栏
```

## 视觉基准

| 项目 | 规范 |
|---|---|
| 字体 | `Inter`, `Microsoft YaHei`, `PingFang SC`, system-ui |
| 页面背景 | 浅灰绿 `#f2f4f0` 附近 |
| 侧边栏 | 深绿黑 `#19231e` 附近 |
| 主色 | 绿色 `#587a3f` 附近 |
| 正文色 | `#1e2823` / `#2f3b34` |
| 次级文字 | `#748078` |
| 卡片 | 白底、1px 细边框、顶部深色线 |
| 圆角 | 小圆角，通常 5-7px |
| 阴影 | 轻阴影，不做强装饰 |

## 组件风格

### 按钮

- 主按钮：绿色背景、白字。
- 次按钮：白底、灰绿边框。
- 危险按钮：浅红底、红字。
- 按钮内优先使用 lucide 图标。

### 卡片

使用 `.human-card` 类似结构：

```text
border: 1px solid #dce1dc
border-top: 3px solid #26332b
background: white
box-shadow: 0 8px 24px rgb(31 42 34 / 4%)
```

不要做大面积渐变、营销页式 hero、装饰性光斑。

### 工作台布局

产品视频系统的核心页面应采用高密度布局：

- 项目总览：指标条 + 流程卡 + 最近任务。
- 资产管理：左侧分类/筛选，中间素材网格，右侧资产详情。
- AI 导演：左侧商品/卖点，中间脚本分镜，右侧导演建议。
- 镜头生产：左侧镜头列表，中间预览/版本，右侧提示词和模型参数。
- 审核导出：中间镜头时间线，右侧导出设置。

## 模块命名建议

```text
frontend/src/modules/ai-video-production/
  AiVideoProduction.tsx
  AiVideoOverview.tsx
  AiVideoAssets.tsx
  AiVideoDirector.tsx
  AiVideoShots.tsx
  AiVideoReview.tsx
  AiVideoExport.tsx
  useAiVideoProductionController.ts
```

公共组件放：

```text
frontend/src/components/
```

类型放：

```text
frontend/src/types.ts
```

API 客户端放：

```text
frontend/src/api/
```

## 导航建议

左侧模块名：

```text
AI视频制作
```

模块内导航：

```text
生产总览
商品资产
AI导演
镜头生产
结果审核
导出交付
模型配置
```

## 后端结构对齐

参考电商平台 FastAPI 分层：

```text
app/
  main.py
  config.py
  models.py
  core/
  domain/
  services/
  api/
    v1/
```

本项目建议：

```text
app/
  main.py
  config.py
  models.py
  core/
    database.py
    security.py
  domain/
    models.py
    enums.py
  services/
    projects.py
    assets.py
    director.py
    prompts.py
    comfyui.py
    providers/
  api/
    v1/
      router.py
      schemas.py
      projects.py
      assets.py
      shots.py
      generation_tasks.py
```

## 验收标准

后续第一版页面完成时，需要满足：

- 页面第一眼和电商平台属于同一产品族。
- 侧边栏、顶部栏、按钮、卡片、表格密度一致。
- 不出现营销落地页风格。
- 不出现大圆角玻璃卡片、紫蓝渐变、大面积插画。
- 文档、代码、运行态文件没有混放。

