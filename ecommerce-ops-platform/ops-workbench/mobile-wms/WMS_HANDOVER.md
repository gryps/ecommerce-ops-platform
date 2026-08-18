# 移动仓库管理系统交接文档

生成时间：2026-08-14
部署服务器：通过本地命令 `ssh center` 连接

## 1. 系统概况

本系统是一个兼容移动端浏览器的 H5 仓库管理系统，前端为静态 HTML/CSS/JavaScript，后端为 Python 标准库 HTTP API，数据存储使用 SQLite。

当前主要业务范围：

- 商品资料管理
- 到货入库
- 退货入库
- 领用入库
- 销售出库
- 领用出库
- 移动盘点
- 库存流水查询
- 流水作废与自动冲销
- CSV 流水导出
- 用户管理与角色权限

## 2. 访问地址

当前公网访问地址：

- `http://121.41.166.116:8000/`

域名解析生效后可访问：

- `http://www.grypszhang.com:8000/`

说明：当前尚未启用 HTTPS。正式公网使用建议后续开放 `443` 端口并配置 Let's Encrypt 免费证书，目标访问方式为：

- `https://www.grypszhang.com/`

## 3. 部署目录与核心文件

项目部署目录：

- `/opt/wms-h5/`

核心文件：

- `/opt/wms-h5/index.html`：前端 H5 页面
- `/opt/wms-h5/api.py`：Python 后端 API
- `/opt/wms-h5/wms.db`：SQLite 数据库
- `/etc/nginx/sites-available/wms-h5`：nginx 站点配置
- `/etc/nginx/sites-enabled/wms-h5`：nginx 启用配置链接或配置文件
- `wms-api`：systemd 后端服务名

## 4. 运行架构

当前端口：

- `8000`：nginx 对公网监听，提供 H5 页面并反向代理 API
- `8001`：Python API，仅监听 `127.0.0.1`，不直接对公网开放

请求路径：

```text
浏览器/手机 -> http://服务器:8000 -> nginx
nginx /api/* -> http://127.0.0.1:8001/api/* -> Python API -> SQLite
```

当前监听状态应类似：

```text
0.0.0.0:8000      nginx
127.0.0.1:8001   python3 / wms-api
```

## 5. 服务管理命令

查看后端服务状态：

```bash
systemctl status wms-api
systemctl is-active wms-api
```

重启后端：

```bash
systemctl restart wms-api
```

查看后端日志：

```bash
journalctl -u wms-api -n 100 --no-pager
journalctl -u wms-api -f
```

检查并重载 nginx：

```bash
nginx -t
systemctl reload nginx
```

检查端口：

```bash
ss -ltnp | grep -E ':8000|:8001'
```

健康检查：

```bash
curl -sS http://127.0.0.1:8001/api/health
curl -sS http://127.0.0.1:8000/api/health
```

## 6. 用户与权限

系统角色：

- `admin`：管理员，可管理用户、商品、库存、流水作废
- `keeper`：仓管员，可管理商品、入库、出库、盘点、流水作废
- `viewer`：只读用户，只能查看商品和流水，不能修改库存

登录安全：

- 密码已使用 `PBKDF2-SHA256` 哈希存储
- 旧的明文密码列已保留用于兼容字段结构，但当前用户明文密码已清空
- 新密码最低长度为 8 位
- 登录 token 只在服务端保存哈希
- token 有效期为 8 小时
- 退出登录会立即注销当前 token
- 同一账号和 IP 连续登录失败会触发限速，失败 5 次后锁定 10 分钟
- 如果账号处于 `must_change_password=1` 状态，登录后必须先修改密码，否则后端会拒绝库存接口

注意：不要在页面、文档或聊天中公开真实管理员密码。

## 7. 当前 API

无需登录：

- `GET /api/health`
- `POST /api/login`

需要登录：

- `POST /api/logout`
- `GET /api/me`
- `GET /api/products`
- `POST /api/products`
- `PUT /api/products/<id>`
- `POST /api/products/<id>/active`
- `POST /api/movements`
- `GET /api/logs`
- `POST /api/logs/<id>/void`
- `GET /api/export/logs.csv`
- `GET /api/users`
- `POST /api/users`
- `POST /api/change-password`

## 8. 业务类型

入库类型：

- 到货入库
- 退货入库
- 领用入库

出库类型：

- 销售出库
- 领用出库

盘点类型：

- 盘点

作废冲销：

- 作废原流水时，系统会生成一条 `作废冲销` 流水，并回滚对应库存变化
- 冲销流水不可再次作废
- 已作废流水不可重复作废

## 9. 单号规则

系统自动生成单号：

- 入库：`INYYYYMMDD0001`
- 出库：`OUTYYYYMMDD0001`
- 盘点：`STYYYYMMDD0001`
- 作废冲销：`RVYYYYMMDD0001`

示例：

```text
IN202608140001
OUT202608140001
ST202608140001
RV202608140001
```

## 10. 数据库表

数据库文件：

- `/opt/wms-h5/wms.db`

主要表：

### users

用户表。关键字段：

- `username`：账号
- `password`：旧兼容字段，当前应为空
- `password_hash`：密码哈希
- `role`：角色，取值 `admin` / `keeper` / `viewer`
- `must_change_password`：是否必须修改密码

### products

商品表。关键字段：

- `sku`：SKU，唯一
- `code`：条码
- `name`：商品名称
- `location`：库位
- `stock`：当前库存
- `min_stock`：安全库存
- `unit`：单位
- `active`：是否启用

### inventory_logs

库存流水表。关键字段：

- `product_id`：商品 ID
- `doc_no`：单号
- `type`：流水类型，`in` / `out` / `stocktake` / `void`
- `business`：业务类型
- `qty`：操作数量
- `before_stock`：操作前库存
- `after_stock`：操作后库存
- `operator`：操作人
- `voided`：是否已作废
- `reverse_of`：冲销来源流水 ID

### auth_tokens

登录 token 表。只保存 token 哈希，不保存原始 token。

### login_attempts

登录失败限速表，按账号和 IP 记录失败次数及锁定时间。

## 11. 数据库检查命令

服务器当前没有安装 `sqlite3` 命令行工具，可用 Python 检查：

```bash
python3 - <<'PY'
import sqlite3
con = sqlite3.connect('/opt/wms-h5/wms.db')
con.row_factory = sqlite3.Row
for row in con.execute('select username, role, length(password) as legacy_password_len, must_change_password from users'):
    print(dict(row))
PY
```

检查商品数量：

```bash
python3 - <<'PY'
import sqlite3
con = sqlite3.connect('/opt/wms-h5/wms.db')
print(con.execute('select count(1) from products').fetchone()[0])
PY
```

## 12. 备份与恢复

建议每天备份 SQLite 数据库。

手动备份：

```bash
mkdir -p /opt/wms-h5/backups
cp /opt/wms-h5/wms.db /opt/wms-h5/backups/wms-$(date +%F-%H%M%S).db
```

恢复前建议先停止后端：

```bash
systemctl stop wms-api
cp /opt/wms-h5/backups/某个备份文件.db /opt/wms-h5/wms.db
systemctl start wms-api
```

恢复后检查：

```bash
systemctl is-active wms-api
curl -sS http://127.0.0.1:8001/api/health
```

## 13. 前端移动端适配说明

已处理的移动端问题：

- iPhone Safari 输入框自动放大问题
- 搜索输入时键盘消失问题
- 商品数量较多时下拉选择过长问题

当前商品选择方案：

- 商品模块搜索框输入时只刷新列表，不重绘输入框
- 入库、出库、盘点不再默认展示全部商品
- 输入商品名、SKU、条码或库位后才显示匹配结果
- 匹配结果最多展示 30 条
- 选择商品后列表收起，只保留已选商品信息

## 14. nginx 安全配置

当前已配置基础安全头：

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: same-origin`
- `Permissions-Policy: camera=(self), microphone=(), geolocation=()`
- `Content-Security-Policy`

验证命令：

```bash
curl -I http://127.0.0.1:8000/api/health
```

## 15. 已知限制

- 当前仍是 HTTP，不是 HTTPS。公网正式使用建议尽快启用 HTTPS。
- 摄像头扫码需要 HTTPS 环境，HTTP 下多数手机浏览器无法授权摄像头。
- 当前是单机 SQLite，适合小团队和轻量仓库使用。
- 当前没有独立后台任务做自动备份，需要后续加 crontab 或 systemd timer。
- 当前没有完整登录审计表，仅有失败限速记录和库存流水操作人。
- 当前没有短信、邮箱或双因素认证。

## 16. 建议后续开发优先级

第一优先级：

- 配置 HTTPS 证书
- 增加自动数据库备份
- 增加登录审计和操作审计
- 增加入库/出库接口幂等，防止重复提交

第二优先级：

- 商品批量导入/导出
- 库存预警导出
- 按日期、商品、业务类型筛选流水
- 用户禁用、重置密码
- 更完善的角色权限配置

第三优先级：

- 摄像头扫码
- PWA 桌面图标和离线缓存
- 多仓库、多库区、多库位
- 数据迁移到 PostgreSQL 或 MySQL

## 17. 常见故障处理

### 页面打不开

检查 nginx：

```bash
systemctl status nginx
nginx -t
ss -ltnp | grep ':8000'
```

### 页面能打开但登录失败或接口失败

检查后端：

```bash
systemctl status wms-api
journalctl -u wms-api -n 100 --no-pager
curl -sS http://127.0.0.1:8001/api/health
```

### 修改后端代码后不生效

需要重启后端：

```bash
python3 -m py_compile /opt/wms-h5/api.py
systemctl restart wms-api
```

### 修改 nginx 后不生效

需要检查并 reload：

```bash
nginx -t
systemctl reload nginx
```

### 登录提示失败次数过多

说明账号和 IP 触发了登录限速。默认锁定 10 分钟。

如确认为自己误操作，可用 Python 清除某个账号的失败记录：

```bash
python3 - <<'PY'
import sqlite3
username = '要解锁的账号'
con = sqlite3.connect('/opt/wms-h5/wms.db')
con.execute('delete from login_attempts where username=?', (username,))
con.commit()
PY
```

## 18. 交接重点

接手人需要重点确认：

- 是否已拿到服务器 SSH 权限
- 是否知道当前管理员账号，但不要在文档中记录密码
- 是否能访问 `http://121.41.166.116:8000/`
- 是否能重启 `wms-api`
- 是否能备份 `/opt/wms-h5/wms.db`
- 是否准备启用 HTTPS

