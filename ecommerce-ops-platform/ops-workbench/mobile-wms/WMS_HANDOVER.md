# Gryps 电商运营系统移动端交接文档

更新时间：2026-08-19（Asia/Shanghai）

## 1. 系统定位

本目录承载电商运营平台里的移动 H5 终端。当前页面名称统一为：

- 登录前：`Gryps电商运营系统`
- 登录后：`Gryps电商运营系统`
- 浏览器标题：`Gryps 电商运营平台`

移动端当前作为统一入口使用：用户登录后，根据账号被分配的模块，进入对应业务模块。当前已接入：

- 用户与权限
- 仓储管理

仓储管理来自原“移动仓库管理系统”，业务能力继续保留：

- 商品资料
- 到货入库、退货入库、领用入库
- 销售出库、领用出库
- 盘点
- 库存流水
- 流水作废与自动冲销
- CSV 流水导出

## 2. 当前部署

线上入口：

```text
http://120.26.176.178:8000/
```

云服务器：

```text
SSH 别名：aliyun-ecom
部署目录：/opt/wms-h5
公网端口：8000
后端端口：127.0.0.1:8001
服务名：wms-api.service
```

数据库：

```text
类型：阿里云 RDS PostgreSQL
业务库：mobile_wms
应用账号：mobile_wms_app
连接配置：/etc/wms-h5.env
```

注意：

- 文档和 Git 里不记录数据库密码、SSH 私钥、API key 或完整数据库连接串。
- 后端只监听本机 `127.0.0.1:8001`，公网只开放 nginx 入口。
- 当前阿里云安全组只开放 `8000-8010` 等指定端口，移动端生产入口使用 `8000`。
- 当前仍为 HTTP。摄像头扫码、PWA 安装等能力需要后续配置 HTTPS 后再启用。

## 3. 代码与运行文件边界

本地源码目录：

```text
/Users/gryps/ecom/ops-workbench/mobile-wms
```

线上运行目录：

```text
/opt/wms-h5
```

运行配置：

```text
/etc/wms-h5.env
```

本目录纳入 Git 的文件：

- `index.html`：页面骨架和静态资源引用。
- `assets/styles.css`：移动端样式。
- `assets/app.js`：移动端交互、路由、渲染和 API 调用。
- `api.py`：Python HTTP API。
- `README.md`：本地维护说明。
- `WMS_HANDOVER.md`：本交接文档。

不纳入 Git 的内容：

- 数据库密码和连接串。
- SSH 私钥。
- 服务器备份。
- 日志。
- 本地或服务器运行态数据库文件。
- 大文件素材、视频、模型输出。

## 4. 当前架构

```text
手机/浏览器
  -> http://120.26.176.178:8000/
  -> nginx 静态页面
  -> /api/* 反向代理到 127.0.0.1:8001
  -> wms-api.service / Python api.py
  -> 阿里云 RDS PostgreSQL mobile_wms
```

设计边界：

- 移动 H5 是岗位终端，不承担大文件加工。
- 结构化业务数据进入 RDS。
- 视频、剪辑工程、音乐库、AI 中间产物长期留在本地或专门文件存储。
- 当前后端保持轻量 Python 标准库实现，适合早期验证和小团队使用。

## 5. 用户与权限规则

当前已取消“系统角色”作为业务分配方式。账号权限按可用模块分配。

用户字段：

- 账号
- 姓名
- 电话
- 密码哈希
- 可用模块

当前模块：

- `warehouse`：仓储管理
- `users`：用户与权限

账号菜单职责：

- 右上角账号菜单只负责“自己”。
- 当前保留退出登录、修改本人密码等个人动作。

用户与权限模块职责：

- 管理“别人”的账号。
- 查看用户列表。
- 新增用户。
- 为账号分配可使用模块。

密码规则：

- 新增用户必须输入两次新密码，并由前端和后端同时校验一致。
- 修改密码必须输入两次新密码，并由前端和后端同时校验一致。
- 新密码最短 8 位。
- 密码只保存 PBKDF2-SHA256 哈希。
- 登录 token 只保存哈希。
- 登录 token 有效期为 8 小时。
- 连续登录失败会触发限速。

兼容字段：

- 数据库里仍保留旧 `role` 字段，原因是兼容旧表结构和历史 token 约束。
- 当前业务权限判断不再使用 `role`，只看 `modules`。

## 6. API 清单

无需登录：

- `GET /api/health`
- `POST /api/login`

登录后通用：

- `POST /api/logout`
- `GET /api/me`
- `POST /api/change-password`

需要 `users` 模块：

- `GET /api/users`
- `POST /api/users`

需要 `warehouse` 模块：

- `GET /api/products`
- `POST /api/products`
- `PUT /api/products/<id>`
- `POST /api/products/<id>/active`
- `POST /api/movements`
- `GET /api/logs`
- `POST /api/logs/<id>/void`
- `GET /api/export/logs.csv`

## 7. 服务管理

查看服务：

```bash
ssh aliyun-ecom 'systemctl status wms-api --no-pager'
ssh aliyun-ecom 'systemctl status nginx --no-pager'
```

重启后端：

```bash
ssh aliyun-ecom 'systemctl restart wms-api'
```

查看后端日志：

```bash
ssh aliyun-ecom 'journalctl -u wms-api -n 100 --no-pager'
```

检查端口：

```bash
ssh aliyun-ecom "ss -ltnp | grep -E ':8000|:8001'"
```

健康检查：

```bash
ssh aliyun-ecom 'curl -fsS http://127.0.0.1:8000/api/health'
curl -fsS http://120.26.176.178:8000/api/health
```

## 8. 部署流程

部署前先检查本地语法：

```bash
python3 -m py_compile /Users/gryps/ecom/ops-workbench/mobile-wms/api.py
node --check /Users/gryps/ecom/ops-workbench/mobile-wms/assets/app.js
```

部署前备份线上文件：

```bash
ssh aliyun-ecom 'ts=$(date +%Y%m%d%H%M%S); mkdir -p /opt/wms-h5/backups/deploy-$ts; cp /opt/wms-h5/api.py /opt/wms-h5/index.html /opt/wms-h5/backups/deploy-$ts/; cp -a /opt/wms-h5/assets /opt/wms-h5/backups/deploy-$ts/'
```

同步文件：

```bash
scp /Users/gryps/ecom/ops-workbench/mobile-wms/api.py aliyun-ecom:/opt/wms-h5/api.py
scp /Users/gryps/ecom/ops-workbench/mobile-wms/index.html aliyun-ecom:/opt/wms-h5/index.html
scp /Users/gryps/ecom/ops-workbench/mobile-wms/assets/app.js /Users/gryps/ecom/ops-workbench/mobile-wms/assets/styles.css aliyun-ecom:/opt/wms-h5/assets/
```

重启和验证：

```bash
ssh aliyun-ecom 'systemctl restart wms-api && systemctl is-active wms-api nginx'
curl -fsS http://120.26.176.178:8000/api/health
```

## 9. 数据库结构重点

主要表：

- `users`
- `products`
- `inventory_logs`
- `auth_tokens`
- `login_attempts`

`users` 关键字段：

- `username`：账号。
- `name`：姓名。
- `phone`：电话。
- `password_hash`：密码哈希。
- `modules`：逗号分隔的模块授权。
- `must_change_password`：是否必须修改密码。
- `role`：历史兼容字段，当前业务权限不依赖它。

## 10. 当前已完成的移动端优化

- 登录前系统名称改为 `Gryps电商运营系统`。
- 登录页取消业务下拉框。
- 登录窗口固定，减少页面上下滑动。
- 移动端横屏时显示旋转提示，不切换为横屏布局。
- 登录后标题改为 `Gryps电商运营系统`。
- 右上角用户与退出整合为账号菜单。
- 入口页只展示当前账号可用模块。
- 移除“当前身份、启用 SKU、预警 SKU、最近流水”等首页统计。
- 用户与权限模块排在仓储管理上方。
- 修复模块卡片过高、内容纵向不齐的问题。
- 账号菜单里的用户管理只负责本人。
- 用户列表和新增用户移入用户与权限模块。
- 新增用户支持账号、姓名、电话、密码、模块分配。
- 涉及新密码的表单都要求连续输入两次新密码。

## 11. 已知限制

- 当前仍是 HTTP，不建议直接启用摄像头扫码。
- 当前没有编辑已有用户资料和重置别人密码的 UI。
- 当前权限粒度是“模块级”，不是“按钮级”或“只读/可写级”。
- 当前没有完整登录审计表。
- 当前没有自动数据库备份任务文档化。
- 当前前端 `assets/app.js` 仍较集中，后续继续增加模块时应继续拆分。

## 12. 下一步建议

优先级高：

- 给 `mobile_wms` 配置自动备份或 RDS 备份策略检查清单。
- 增加编辑用户、禁用用户、重置用户密码功能。
- 权限从模块级扩展为能力级，例如 `warehouse_view`、`warehouse_edit`、`users_manage`。
- 配置 HTTPS，解除扫码和 PWA 限制。

优先级中：

- 将 `assets/app.js` 继续拆成 `apiClient`、`portal`、`warehouse`、`users` 等文件。
- 增加入库、出库、盘点接口幂等，防止重复提交。
- 增加商品批量导入、库存预警导出、流水筛选。

优先级低：

- PWA 桌面图标和离线缓存。
- 多仓库、多库区、多库位。
- 更完整的操作审计和报表。

## 13. 收尾检查清单

接手或次日继续开发前确认：

- `git status --short` 只剩已知无关改动。
- `python3 -m py_compile api.py` 通过。
- `node --check assets/app.js` 通过。
- `wms-api` 和 `nginx` 为 active。
- `http://120.26.176.178:8000/api/health` 返回成功。
- Git 最新提交已推送到 GitHub。
- 没有把密钥、密码、API key、数据库连接串提交进仓库。
