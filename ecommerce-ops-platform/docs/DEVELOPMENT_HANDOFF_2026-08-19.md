# 2026-08-19 开发收尾交接

日期：2026-08-19（Asia/Shanghai）

## 1. 今日主线

今天围绕电商运营平台的移动端入口做收尾，目标是把原“移动仓库管理系统”改造为“Gryps 电商运营系统”的移动端统一入口，同时保持仓储功能独立可用。

当前移动端线上入口：

```text
http://120.26.176.178:8000/
```

当前代码位置：

```text
/Users/gryps/ecom/ops-workbench/mobile-wms
```

当前部署位置：

```text
/opt/wms-h5
```

## 2. 已完成事项

- 将移动端登录前、登录后系统名称统一为 `Gryps电商运营系统`。
- 将页面标题统一为 `Gryps 电商运营平台`。
- 登录页取消模块下拉框，固定登录窗口。
- 移动端横屏时不切换业务布局，显示旋转提示。
- 登录后首页作为移动端模块入口。
- 右上角账号菜单只处理本人相关操作。
- 用户列表和新增用户迁入“用户与权限”模块。
- 用户与权限模块放在仓储管理模块上方。
- 模块卡片恢复紧凑显示，避免大面积空白。
- 取消首页的当前身份、启用 SKU、预警 SKU、最近流水统计。
- 用户字段扩展为账号、姓名、电话、密码、模块授权。
- 涉及新密码的表单都要求输入两次并校验一致。
- 取消系统角色作为业务权限分配方式，改为按账号分配可用模块。
- 移动仓储后端迁移到阿里云 ECS，数据库使用阿里云 RDS 独立库 `mobile_wms`。

## 3. 当前版本状态

Git 主分支已包含移动端近期改造：

```text
7445712 Use module-based mobile WMS user permissions
20b7858 Separate mobile WMS user admin entry
1b65fb9 Split mobile WMS frontend assets
3823f7a Fix mobile portal card stretching
8753c01 Compact mobile portal module cards
```

当前已知无关工作区改动：

```text
../AGENTS.md
../PROJECT_MEMORY.md
../.tools/
../ComfyUI/
../WORKSTATIONS.md
../run-comfyui-wsl-api.sh
../singbox-headless-github/
../ssh-inventory/
```

这些不是今天移动端改造的目标文件，收尾时不要误删或回滚。

## 4. 架构约定

移动端当前分层：

```text
index.html          页面骨架
assets/styles.css   样式
assets/app.js       前端状态、渲染、交互和 API 调用
api.py              后端 API
RDS mobile_wms      业务数据
```

已经完成的解耦：

- 不再把 CSS/JS 内联在 `index.html`。
- 运行配置和数据库凭据放在服务器环境文件，不进入 Git。
- 移动 WMS 独立在 `ops-workbench/mobile-wms/`，作为电商平台的移动端子系统纳入同一个 Git。
- 权限判断从角色名切到模块授权，便于后续扩展成多个移动端业务模块。

后续建议继续做的解耦：

- 将 `assets/app.js` 拆成 `apiClient`、`portal`、`warehouse`、`users` 等职责文件。
- 将模块权限进一步抽象为能力权限，例如查看、编辑、管理。
- 将部署命令沉淀为脚本，但脚本不得包含真实密码或连接串。

## 5. 线上运行边界

云服务器：

```text
SSH 别名：aliyun-ecom
公网入口：120.26.176.178:8000
后端：127.0.0.1:8001
服务：wms-api.service
部署目录：/opt/wms-h5
```

数据库：

```text
类型：阿里云 RDS PostgreSQL
业务库：mobile_wms
应用账号：mobile_wms_app
配置文件：/etc/wms-h5.env
```

敏感信息规则：

- 不在 Git 中保存 SSH 私钥。
- 不在 Git 中保存数据库密码。
- 不在文档中写完整连接串。
- 不在提交信息中写密码、API key、密钥片段。
- 服务器环境文件权限保持仅 root 可读写。

## 6. 验证命令

本地语法检查：

```bash
python3 -m py_compile /Users/gryps/ecom/ops-workbench/mobile-wms/api.py
node --check /Users/gryps/ecom/ops-workbench/mobile-wms/assets/app.js
git -C /Users/gryps/ecom diff --check
```

远程服务检查：

```bash
ssh aliyun-ecom 'systemctl is-active wms-api nginx'
ssh aliyun-ecom 'curl -fsS http://127.0.0.1:8000/api/health'
curl -fsS http://120.26.176.178:8000/api/health
```

## 7. 明日继续建议

优先处理：

- 增加编辑已有用户资料、禁用用户、重置别人密码。
- 明确是否需要“只读仓储”和“可编辑仓储”的权限差异。
- 给 RDS 备份策略做一次显式检查，并记录恢复步骤。

随后处理：

- 拆分 `assets/app.js`，降低前端单文件上下文消耗。
- 增加入库、出库、盘点接口幂等，降低重复提交风险。
- 配置 HTTPS，为扫码和 PWA 做准备。

暂停处理：

- 不急于加入视频、图片、AI 生成等重功能到移动端。
- 不把大文件长期放云服务器系统盘。
- 不在当前轻量 API 上直接叠加复杂后台任务。
