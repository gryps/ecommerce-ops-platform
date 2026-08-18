# 移动仓库 H5

这是从云主机 `/opt/wms-h5` 纳入电商运营平台统一 Git 的移动端仓库管理子系统。

## 边界

- 当前保持独立运行架构：静态 H5 前端、Python 标准库 HTTP API、SQLite 数据库。
- 本目录只放可维护源码和交接文档。
- 数据库、备份、日志和环境文件放到 `../../ops-workbench-runtime/warehouse/mobile-wms/` 或服务器运行目录，不纳入 Git。
- 证书私钥不进入仓库；nginx 配置只保留证书路径。

## 文件

- `index.html`：移动端 H5 前端。
- `api.py`：后端 API。
- `WMS_HANDOVER.md`：线上系统交接说明。

## 本地运行

```bash
export WMS_BASE_DIR=/mnt/e/codexwork/ecommerce-ops-platform/ops-workbench-runtime/warehouse/mobile-wms
python3 api.py
```

如果使用空数据库首次初始化，需要设置初始管理员密码：

```bash
export WMS_INITIAL_ADMIN_PASSWORD='换成服务器本地保存的强密码'
```

