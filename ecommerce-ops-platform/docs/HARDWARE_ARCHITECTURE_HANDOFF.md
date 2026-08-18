# 电商平台硬件架构交接文档

> 更新时间：2026-08-18（Asia/Shanghai）
>
> 用途：记录电商业务系统从本地工作台向“云端数据中心 + 本地生产节点 + 移动 H5 终端”演进时的硬件、网络、账号边界和交接事项。

## 1. 架构定位

当前目标不是把所有东西都搬到云端，而是把数据中心放到云端，把大文件和加工算力留在本地。

总体分工：

- 云服务器：对外入口、API、管理后台、移动 H5、定时任务和部署中控。
- 云数据库：统一保存业务结构化数据，作为商品、仓库、运营、财务、项目、任务状态的中心库。
- 本地工作台：保留开发、总控、素材加工、拍剪工作流和本地大文件管理能力。
- 移动 H5 终端：给仓管、主播、老板、运营等岗位提供手机端录入、确认和查看。
- 本地大文件存储：长期保存原始视频、工程文件、音乐库、AI 中间产物和历史成片。

原则：

- 数据上云，文件分层。
- 数据库不直接暴露公网。
- 云服务器只通过私网连接云数据库。
- 视频、工程、模型和大素材不长期堆在云端。
- 账号、密码、密钥、API key 不进入 Git，不写进交接文档。

## 2. 当前云资源

### 2.1 云服务器

```text
供应商：阿里云
公网地址：120.26.176.178
SSH 用户：root
本机 SSH 别名：aliyun-ecom
系统：Ubuntu 24.04.4 LTS
磁盘：系统盘约 20G
内存：约 401MiB，已存在约 2G swap
当前公网监听：22
```

macOS 登录：

```bash
ssh aliyun-ecom
```

Windows 登录：

```powershell
ssh aliyun-ecom
```

密钥位置：

```text
macOS：/Users/gryps/.ssh/aliyun_120_26_176_178.pem
Windows：C:\Users\Administrator\.ssh\aliyun_120_26_176_178.pem
```

注意：

- 密钥文件只用于 SSH 登录，不能提交到 Git。
- 下载目录里的原始密钥建议删除，或至少保持仅本人可读权限。
- 服务器目前规格偏小，适合早期 API/H5/验证环境；不适合本地视频转码、AI 推理或大并发。

### 2.2 云数据库

```text
类型：阿里云 RDS PostgreSQL
私网域名：pgm-bp10121ct7x0e7x4.pg.rds.aliyuncs.com
私网解析：172.25.216.22
端口：5432
业务库：ecommerce_ops
应用账号：ecommerce_app
```

云服务器到 RDS 已验证：

```text
DNS 私网解析正常
TCP 5432 连通正常
应用账号可连接 ecommerce_ops
```

应用连接配置保存在云服务器：

```text
/root/ecommerce-ops/db.env
```

文件权限要求：

```text
所属用户：root
权限：600
```

安全边界：

- 应用服务只使用 `ecommerce_app`。
- RDS 管理账号只用于建库、建用户、授权、迁移和维护。
- 管理账号密码不应写入项目文件、Shell 历史、聊天记录或 Git。
- 建议在确认应用账号可用后，轮换管理账号密码，或禁用临时管理账号。

## 3. 本地和内网资源

### 3.1 macOS 本地开发机

```text
用户目录：/Users/gryps
电商平台本地仓库：/Users/gryps/codexwork-import-20260818/wsl/codexwork/ecommerce-ops-platform
Git 外层仓库：/Users/gryps/codexwork-import-20260818/wsl/codexwork
当前远程仓库：git@github.com:gryps/ecommerce-ops-platform.git
```

用途：

- 统一版本管理。
- 代码审查、合并、提交和推送。
- 本地开发、测试和部署脚本整理。
- 作为 Windows、WSL、小主机、云服务器之间的同步中控。

### 3.2 Windows 工作机

```text
主机：administrator@192.168.31.31
Windows 工作目录：E:\wincodexwork
WSL 入口：wsl -d Ubuntu --cd /mnt/e/codexwork
WSL 工作目录：/mnt/e/codexwork
云服务器 SSH 别名：aliyun-ecom
```

用途：

- Windows 原生工具、浏览器登录态、剪辑软件和素材处理。
- WSL 内进行 Linux 侧开发、同步和命令行操作。
- 可直接 SSH 登录云服务器做部署验证。

### 3.3 小主机

```text
主机：gryps@192.168.31.24
项目目录：/home/gryps/apps/ecommerce-ops-platform
历史定位：电商运营平台、小主机服务、ComfyUI 中控
```

用途：

- 内网轻量运行服务。
- ComfyUI 工作流编排和 API 调度中控。
- 可作为本地任务节点或素材处理入口。

限制：

- 不适合作为 AI 算力机器。
- 不适合承载长期大视频归档。
- 不应成为唯一主库，后续业务结构化数据以云 RDS 为准。

## 4. 数据和文件分层

### 4.1 云端保存

云端适合保存：

- 商品、SKU、供应商、采购、质检、库存、订单相关结构化数据。
- 仓库出入库、盘点、退货、报废、二销记录。
- 主播排品、场控记录、下播复盘。
- 投流、素材、ROI、停投建议和运营报表。
- 财务口径、成本、利润、现金流和项目决策记录。
- 文件索引、缩略图、低清预览、近期成片和导出报表。

### 4.2 本地保存

本地适合保存：

- 原始拍摄视频。
- 剪辑工程文件。
- 背景音乐库。
- AI 生成中间文件。
- 高码率成片。
- 历史归档视频。
- 大模型权重和本地推理缓存。

### 4.3 数据库文件索引

业务数据库记录文件的索引，不直接承担大文件长期存储。

建议字段：

```text
file_id
business_type
owner_module
original_filename
size_bytes
sha256
duration_seconds
resolution
storage_tier
local_machine
local_path
preview_url
thumbnail_url
status
created_by
created_at
last_used_at
```

`storage_tier` 建议枚举：

```text
cloud_preview
cloud_recent
local_hot
local_archive
external_drive
missing
```

## 5. 业务终端分工

### 5.1 数据输入

- 仓管手机 H5：入库、出库、盘点、退货、报废、二销。
- 主播手机 H5：排品、话术、场控、下播反馈。
- 拍摄/剪辑电脑：原片导入、剪辑工程、音乐素材、成片输出。
- 运营后台：商品资料、平台模板、投流计划、复盘。
- AI 工作站：图片生成、视频生成、任务回收。

### 5.2 数据汇总计算存储

- 云服务器提供 API、鉴权、审计、任务调度和数据校验。
- 云 RDS 保存中心结构化数据。
- 本地节点只保存运行缓存、大文件和必要的离线工作目录。

### 5.3 数据输出

- 老板/运营手机 H5：日报、库存风险、利润、投流 ROI、项目状态。
- 总控平台：完整经营看板、模块管理、任务中心和异常处理。
- 拍剪工作站：剪辑清单、素材包、工程索引和成片任务。
- 仓库终端：拣货、库存、异常件和退货处理。

## 6. 网络安全边界

必须保持：

- RDS 使用私网地址，数据库端口不对公网开放。
- 公网只开放必要入口：SSH、HTTP、HTTPS。
- API、管理后台和 H5 走 HTTPS。
- 数据库账号分级：管理账号和应用账号分离。
- `.env`、密钥、数据库密码、云厂商 API key 不进入仓库。

建议后续补充：

- 为云服务器创建非 root 部署用户。
- SSH 禁止密码登录，仅保留密钥登录。
- 开启防火墙，只允许 `22/80/443` 等必要端口。
- 部署 nginx，后端 API 只监听 `127.0.0.1`。
- 绑定正式域名并配置 TLS。
- 对 `/root/ecommerce-ops/db.env` 做受控备份，不直接复制到普通工作目录。

## 7. 推荐部署拓扑

```text
手机 / 浏览器 / 总控平台
        |
        | HTTPS
        v
阿里云 ECS：nginx + 前端静态文件 + 后端 API + 定时任务
        |
        | VPC 私网 5432
        v
阿里云 RDS PostgreSQL：ecommerce_ops

本地 Windows / WSL / 小主机 / 拍剪电脑 / AI 工作站
        |
        | HTTPS API 同步结构化数据和任务状态
        v
阿里云 ECS

本地 NAS / 工作站磁盘 / 移动硬盘
        |
        | 保存原片、工程、大文件和历史归档
        v
数据库只保存文件索引和预览地址
```

## 8. 运维检查命令

macOS 检查云服务器：

```bash
ssh aliyun-ecom 'hostname; whoami; cat /etc/os-release | sed -n "1,4p"'
ssh aliyun-ecom 'ss -lntp'
ssh aliyun-ecom 'df -h; free -h'
```

云服务器检查 RDS 端口：

```bash
getent hosts pgm-bp10121ct7x0e7x4.pg.rds.aliyuncs.com
timeout 5 bash -lc '</dev/tcp/pgm-bp10121ct7x0e7x4.pg.rds.aliyuncs.com/5432' && echo OK
```

云服务器检查应用数据库连接：

```bash
set -a
. /root/ecommerce-ops/db.env
set +a
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c 'select current_user, current_database();'
```

Windows 检查云服务器：

```powershell
ssh aliyun-ecom "hostname; whoami"
```

## 9. 当前已完成事项

- macOS 已配置 `aliyun-ecom` SSH 别名。
- Windows 已配置 `aliyun-ecom` SSH 别名。
- Windows 已复制云服务器私钥，并验证可直接登录。
- 云服务器可访问 RDS 私网域名和 5432 端口。
- 已创建业务库 `ecommerce_ops`。
- 已创建应用账号 `ecommerce_app`。
- 已在云服务器保存应用数据库连接配置 `/root/ecommerce-ops/db.env`。
- 已验证应用账号可连接业务库。

## 10. 待完成事项

优先级从高到低：

1. 轮换或停用临时 RDS 管理账号密码。
2. 创建云服务器非 root 部署用户。
3. 部署电商平台后端 API 和前端静态文件。
4. 配置 nginx、HTTPS、域名和反向代理。
5. 将后端数据库配置改为读取 `/root/ecommerce-ops/db.env` 或受控部署环境变量。
6. 设计云 RDS PostgreSQL 的正式 schema 迁移路径。
7. 明确本地大文件目录规范和文件索引表。
8. 建立 RDS 备份、代码发布、日志、监控和恢复流程。
9. 决定是否引入 OSS 作为缩略图、低清预览和近期成片的临时交换区。

## 11. 交接注意

- 任何部署、同步、提交前都要先做敏感信息扫描。
- 不要把 `/root/ecommerce-ops/db.env` 拉回本地仓库。
- 不要把 `.pem`、`.env`、数据库导出、SQLite 运行库、日志和视频素材提交到 Git。
- 云服务器当前内存较小，后端应先按轻量部署处理，避免在云上跑视频转码或 AI 推理。
- 视频长期存储策略应以本地 NAS、工作站磁盘或移动硬盘为主，云端只保留索引、缩略图、低清预览和近期文件。
- 后续每次新增硬件节点，应记录：节点用途、访问方式、数据边界、运行目录、备份方式、不能提交的敏感文件。
