# 07 提示词系统

## 目标

提示词系统把导演语言、商品信息、品牌规则和模型参数转成可复用的结构化提示词。

原则：

- 先结构化，后渲染成厂商提示词。
- 一镜头一提示词包。
- 商品一致性约束必须显式存在。
- 负面词按镜头类型自动生成。
- 不同厂商可有不同渲染模板。

## PromptSet 结构

```json
{
  "shot_type": "product_closeup",
  "subject": "一瓶白色高端精华液",
  "product": {
    "shape": "透明玻璃瓶身，银色泵头",
    "logo_rule": "正面标签保持清晰，不改变文字和Logo",
    "material": "玻璃、金属泵头"
  },
  "scene": "明亮浴室洗手台，浅灰石材台面",
  "action": "水珠缓慢滑过瓶身，产品保持稳定",
  "camera": "微距镜头，缓慢向前推进，轻微环绕",
  "lighting": "清晨自然光，柔和高光",
  "style": "高端护肤品TVC，真实摄影，浅景深",
  "consistency": [
    "产品形状、颜色、Logo、标签保持一致",
    "不要生成多余瓶身",
    "不要改变包装比例"
  ],
  "negative": [
    "错误Logo",
    "变形标签",
    "多余文字",
    "低清晰度",
    "手指畸形"
  ]
}
```

## 镜头类型

```text
product_hero
product_closeup
product_usage
person_holding_product
environment_mood
brand_end_card
comparison_demo
texture_macro
```

## 运镜词库

```text
slow push in
slow pull back
macro orbit
top-down reveal
handheld slight movement
smooth tracking shot
tilt down
pan right
locked-off product shot
```

## 景别词库

```text
extreme close-up
close-up
medium shot
wide shot
over-the-shoulder
top-down shot
product packshot
```

## 负面词模板

### 商品镜头

```text
wrong logo, distorted label, extra text, duplicate product, melted shape,
incorrect packaging, low resolution, blurry, noisy, overexposed
```

### 人物拿商品

```text
deformed hands, extra fingers, missing fingers, broken wrist, wrong grip,
distorted product, face distortion, unnatural pose
```

### 环境镜头

```text
cluttered background, messy composition, unrelated objects, low quality,
bad lighting, flickering, distorted perspective
```

## 厂商渲染策略

### 通用中文渲染

适合国内 API 和人工审核：

```text
镜头类型：{shot_type}
主体：{subject}
商品：{product}
场景：{scene}
动作：{action}
运镜：{camera}
光线：{lighting}
风格：{style}
一致性要求：{consistency}
负面：{negative}
```

### 英文摄影渲染

适合偏英文提示词表现更稳定的模型：

```text
{shot_type}, {subject}, {scene}, {action}.
Camera: {camera}. Lighting: {lighting}. Style: {style}.
Product consistency: {consistency}.
Avoid: {negative}.
```

## AI 导演输出格式

分镜生成必须输出结构化 JSON，避免后续解析自然语言。

```json
{
  "shots": [
    {
      "index": 1,
      "duration": 3,
      "shot_type": "product_hero",
      "shot_size": "close-up",
      "camera_motion": "slow push in",
      "visual_description": "产品置于干净台面，背景柔和虚化",
      "product_action": "产品正面标签面向镜头",
      "caption": "核心卖点短句"
    }
  ]
}
```

