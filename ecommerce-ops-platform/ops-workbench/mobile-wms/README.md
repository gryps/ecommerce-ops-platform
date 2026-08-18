# 移动仓库 H5

这是从云主机 `/opt/wms-h5` 纳入电商运营平台统一 Git 的移动端仓库管理子系统。

## 边界

- 当前保持独立运行架构：静态 H5 前端、Python HTTP API、独立数据库。
- 本地默认使用 SQLite；服务器可通过 `WMS_DATABASE_URL` 切换到 PostgreSQL/RDS。
- 本目录只放可维护源码和交接文档。
- 数据库、备份、日志和环境文件放到 `../../ops-workbench-runtime/warehouse/mobile-wms/` 或服务器运行目录，不纳入 Git。
- 证书私钥不进入仓库；nginx 配置只保留证书路径。

## 文件

- `index.html`：移动端 H5 页面骨架，只保留结构和资源引用。
- `assets/styles.css`：移动端样式。
- `assets/app.js`：移动端交互、页面渲染和 API 调用。
- `api.py`：后端 API。
- `WMS_HANDOVER.md`：线上系统交接说明。

## 前端维护约定

- 页面结构、样式、交互分开维护，避免再把 CSS/JS 内联回 `index.html`。
- 移动入口页、仓储业务页、用户权限页的业务入口先集中在 `assets/app.js`，后续功能增多时再按模块继续拆分。
- 新增静态资源放入 `assets/`，部署时与 `index.html` 一起同步到 `/opt/wms-h5/`。

## 本地运行

```bash
export WMS_BASE_DIR=/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime/warehouse/mobile-wms
python3 api.py
```

如果使用空数据库首次初始化，需要设置初始管理员密码：

```bash
export WMS_INITIAL_ADMIN_PASSWORD='换成服务器本地保存的强密码'
```

## 服务器 PostgreSQL

```bash
export WMS_DATABASE_URL='postgresql://用户:密码@RDS私网地址:5432/业务库'
export WMS_INITIAL_ADMIN_PASSWORD='换成服务器本地保存的强密码'
python3 api.py
```
