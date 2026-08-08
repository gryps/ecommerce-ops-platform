# 数据结构草案

本文描述视频生产当前有效数据结构口径，字段名以实际代码和数据库迁移为准。

## 1. 产品与标签

### Product

| 字段 | 含义 |
| --- | --- |
| id | 产品 ID |
| name | 产品名称，人工维护 |
| created_at / updated_at | 创建和更新时间 |

### TagCategory

| 字段 | 含义 |
| --- | --- |
| id | 标签分类 ID |
| name | 分类名称 |
| created_at / updated_at | 创建和更新时间 |

### Tag

| 字段 | 含义 |
| --- | --- |
| id | 标签 ID |
| category_id | 所属标签分类 |
| name | 标签名称 |
| created_at / updated_at | 创建和更新时间 |

约束：

- `category_id + name` 唯一。
- 标签不能跨分类改所属关系。

## 2. 已归类素材

### ClassifiedMaterial

| 字段 | 含义 |
| --- | --- |
| id | 素材记录 ID |
| product_id | 归属产品 |
| original_path | 移动前路径 |
| current_path | 移动后路径 |
| filename | 当前文件名 |
| duration / width / height / codec | 媒体信息 |
| created_at | 归类时间 |

### ClassifiedMaterialTag

| 字段 | 含义 |
| --- | --- |
| material_id | 素材 ID |
| tag_id | 标签 ID |

约束：

- 同一素材在同一标签分类下只能保留一个标签。

## 3. 文案生产

### CopyAnalysis

| 字段 | 含义 |
| --- | --- |
| id | 分析任务 ID |
| source_text | 参考文案 |
| analysis_snapshot | 风格、受众、专家角色分析快照 |
| status | 生成状态 |
| created_at | 创建时间 |

### CopyCandidate

| 字段 | 含义 |
| --- | --- |
| id | 候选 ID |
| analysis_id | 所属分析任务 |
| round_no | 迭代轮次 |
| content | 候选文案 |
| review_status | 待审核、已采纳、不采纳 |
| reject_reason | 不采纳原因 |

### CopyLibraryItem

| 字段 | 含义 |
| --- | --- |
| id | 文案库条目 ID |
| content | 已采纳文案 |
| source_type | 参考原文、模型候选、音频转文案等来源 |
| created_at / updated_at | 创建和更新时间 |

候选和文案库物理分离，互相删除不连带。

## 4. 音色、旁白与字幕

### VoicePreview

| 字段 | 含义 |
| --- | --- |
| voice_index | 官方音色序号 |
| voice | 模型 voice 参数 |
| model_id | 生成模型 |
| audio_path | 库存试听音频路径 |
| bytes | 文件大小 |

### NarrationAsset

| 字段 | 含义 |
| --- | --- |
| id | 旁白资源 ID |
| text | 配音正文 |
| voice_index / voice | 音色序号和参数 |
| audio_path | 旁白音频路径 |
| subtitle_timeline | 字幕时间轴 |
| duration | 音频时长 |
| status | 待确认、已确认等状态 |

## 5. 背景音乐

### MusicResource

| 字段 | 含义 |
| --- | --- |
| id | 音乐资源 ID |
| name | 音乐名称 |
| source_type | 上传或链接提取 |
| source_url | 来源链接，可为空 |
| file_path | 音频文件路径 |
| duration | 时长 |
| tags | 自定义标签 |
| created_at / updated_at | 创建和更新时间 |

## 6. 剪映草稿

### JianyingDraft

| 字段 | 含义 |
| --- | --- |
| id | 草稿记录 ID |
| draft_name | 草稿名称 |
| draft_path | 磁盘草稿目录 |
| copy_snapshot | 文案快照 |
| narration_snapshot | 旁白与字幕快照 |
| music_snapshot | 背景音乐快照 |
| duplicate_count_before_create | 创建前同组合历史次数 |
| created_at | 创建时间 |

### DraftCombinationCounter

| 字段 | 含义 |
| --- | --- |
| combination_hash | 文案、旁白、音乐组合哈希 |
| total_count | 累计生成次数 |
| reset_baseline | 复位基线 |

重复提示计数不随草稿记录删除而减少。

## 7. 模型配置与调用日志

### ModelConfig

配置项包括：

- 文案生成；
- 音频转文案；
- 字幕配音。

每项独立保存接口地址、API Key、模型 ID 和模型类别。

### ModelCallLog

记录真实业务调用：

- 业务步骤；
- 模型 ID；
- 调用 ID；
- 尝试序号；
- 脱敏后的输入和响应；
- Token；
- 耗时；
- 成功或失败状态。

连接测试和模型列表读取不进入真实调用日志。
