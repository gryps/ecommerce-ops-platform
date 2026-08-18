#!/usr/bin/env python3
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(os.environ.get('WMS_BASE_DIR', '/opt/wms-h5'))
DB = BASE / 'wms.db'
TOKEN_TTL = 8 * 60 * 60
LOGIN_LOCK_SECONDS = 10 * 60
LOGIN_MAX_FAILS = 5
PBKDF2_ITERATIONS = 260000
INITIAL_ADMIN_PASSWORD_ENV = 'WMS_INITIAL_ADMIN_PASSWORD'

BUSINESS = {
    'in': ['到货入库', '退货入库', '领用入库'],
    'out': ['销售出库', '领用出库'],
    'stocktake': ['盘点']
}

SEED_PRODUCTS = [
    ('SKU-10001', '69000010001', '标准纸箱 40x30x20', 'A-01-01', 126, 30, '个'),
    ('SKU-20018', '69000020018', '蓝牙扫描枪', 'B-02-03', 8, 5, '台'),
    ('SKU-31006', '69000031006', '防静电手套 L', 'C-04-02', 0, 20, '双'),
]

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('pragma foreign_keys=on')
    return con

def now_ts():
    return int(time.time())

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return 'pbkdf2_sha256${}${}${}'.format(PBKDF2_ITERATIONS, base64.b64encode(salt).decode('ascii'), base64.b64encode(digest).decode('ascii'))

def verify_password(stored, password):
    stored = stored or ''
    if not stored.startswith('pbkdf2_sha256$'):
        return hmac.compare_digest(stored, password)
    try:
        _, rounds, salt_b64, digest_b64 = stored.split('$', 3)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), base64.b64decode(salt_b64), int(rounds))
        return hmac.compare_digest(base64.b64encode(digest).decode('ascii'), digest_b64)
    except Exception:
        return False

def token_hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def initial_admin_password():
    password = os.environ.get(INITIAL_ADMIN_PASSWORD_ENV, '')
    if len(password) < 8:
        raise RuntimeError(f'{INITIAL_ADMIN_PASSWORD_ENV} must be set to initialize the first admin user')
    return password

def client_ip(handler):
    xff = handler.headers.get('x-forwarded-for') or ''
    if xff:
        return xff.split(',')[0].strip()[:64]
    return (handler.headers.get('x-real-ip') or handler.client_address[0] or '')[:64]

def init_db():
    BASE.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript('''
        create table if not exists users (
            id integer primary key autoincrement,
            username text not null unique,
            password text not null,
            role text not null default 'admin',
            created_at text not null default current_timestamp
        );
        create table if not exists products (
            id integer primary key autoincrement,
            sku text not null unique,
            code text,
            name text not null,
            location text,
            stock integer not null default 0,
            min_stock integer not null default 0,
            unit text not null default '件',
            updated_at text not null default current_timestamp
        );
        create table if not exists inventory_logs (
            id integer primary key autoincrement,
            product_id integer,
            doc_no text,
            type text not null,
            business text not null,
            qty integer not null,
            before_stock integer not null,
            after_stock integer not null,
            remark text,
            operator text not null,
            created_at text not null default current_timestamp,
            foreign key(product_id) references products(id)
        );
        create table if not exists auth_tokens (
            token_hash text primary key,
            username text not null,
            role text not null,
            expires_at integer not null,
            created_at text not null default current_timestamp,
            last_seen_at text,
            revoked_at text
        );
        create table if not exists login_attempts (
            username text not null,
            ip text not null,
            fail_count integer not null default 0,
            locked_until integer not null default 0,
            last_failed_at text,
            primary key(username, ip)
        );
        ''')
        user_cols = [r[1] for r in con.execute('pragma table_info(users)').fetchall()]
        if 'password_hash' not in user_cols:
            con.execute('alter table users add column password_hash text')
        if 'must_change_password' not in user_cols:
            con.execute('alter table users add column must_change_password integer not null default 0')
        if con.execute('select count(*) from users').fetchone()[0] == 0:
            con.execute('insert into users(username,password,password_hash,role,must_change_password) values(?,?,?,?,?)', ('admin', '', hash_password(initial_admin_password()), 'admin', 1))
        product_cols = [r[1] for r in con.execute('pragma table_info(products)').fetchall()]
        if 'active' not in product_cols:
            con.execute('alter table products add column active integer not null default 1')
        log_cols = [r[1] for r in con.execute('pragma table_info(inventory_logs)').fetchall()]
        if 'doc_no' not in log_cols:
            con.execute('alter table inventory_logs add column doc_no text')
        if 'voided' not in log_cols:
            con.execute('alter table inventory_logs add column voided integer not null default 0')
        if 'void_reason' not in log_cols:
            con.execute('alter table inventory_logs add column void_reason text')
        if 'voided_by' not in log_cols:
            con.execute('alter table inventory_logs add column voided_by text')
        if 'voided_at' not in log_cols:
            con.execute('alter table inventory_logs add column voided_at text')
        if 'reverse_of' not in log_cols:
            con.execute('alter table inventory_logs add column reverse_of integer')
        for u in con.execute('select id,username,password,password_hash,must_change_password from users').fetchall():
            legacy = u['password'] or ''
            pwd_hash = u['password_hash'] or ''
            must_change = int(u['must_change_password'] or 0)
            if not pwd_hash:
                pwd_hash = hash_password(legacy)
            con.execute('update users set password=?,password_hash=?,must_change_password=? where id=?', ('', pwd_hash, must_change, u['id']))
        if con.execute('select count(*) from products').fetchone()[0] == 0:
            con.executemany('insert into products(sku,code,name,location,stock,min_stock,unit) values(?,?,?,?,?,?,?)', SEED_PRODUCTS)
        con.execute('delete from auth_tokens where expires_at<? or revoked_at is not null', (now_ts(),))

def rows(sql, args=()):
    with db() as con:
        return [dict(r) for r in con.execute(sql, args).fetchall()]

def one(sql, args=()):
    with db() as con:
        r = con.execute(sql, args).fetchone()
        return dict(r) if r else None

def parse_body(handler):
    n = int(handler.headers.get('content-length') or 0)
    if n == 0:
        return {}
    if n > 1024 * 1024:
        raise ValueError('request too large')
    raw = handler.rfile.read(n).decode('utf-8')
    return json.loads(raw or '{}')

def product_dict(r):
    return {
        'id': r['id'], 'sku': r['sku'], 'code': r['code'] or '', 'name': r['name'],
        'loc': r['location'] or '', 'stock': r['stock'], 'min': r['min_stock'], 'unit': r['unit'], 'active': int(r['active']) if 'active' in r.keys() else 1
    }

def make_doc_no(con, move_type):
    prefix = {'in': 'IN', 'out': 'OUT', 'stocktake': 'ST', 'void': 'RV'}.get(move_type, 'DOC')
    day = time.strftime('%Y%m%d')
    like = prefix + day + '%'
    row = con.execute('select doc_no from inventory_logs where doc_no like ? order by doc_no desc limit 1', (like,)).fetchone()
    seq = int(row['doc_no'][-4:]) + 1 if row and row['doc_no'] else 1
    return f'{prefix}{day}{seq:04d}'

class Handler(BaseHTTPRequestHandler):
    server_version = 'wms-api/1.1'

    def log_message(self, fmt, *args):
        return

    def send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('content-type', 'application/json; charset=utf-8')
        self.send_header('cache-control', 'no-store')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def error_json(self, status, msg):
        self.send_json(status, {'ok': False, 'error': msg})

    def user(self):
        auth = self.headers.get('authorization') or ''
        token = auth.replace('Bearer ', '', 1).strip()
        if not token:
            return None
        th = token_hash(token)
        with db() as con:
            con.execute('delete from auth_tokens where expires_at<? or revoked_at is not null', (now_ts(),))
            row = con.execute('''select t.username,t.role,t.expires_at,u.must_change_password from auth_tokens t join users u on u.username=t.username where t.token_hash=? and t.expires_at>=? and t.revoked_at is null''', (th, now_ts())).fetchone()
            if not row:
                return None
            con.execute('update auth_tokens set last_seen_at=current_timestamp where token_hash=?', (th,))
            return {'username': row['username'], 'role': row['role'], 'must_change_password': int(row['must_change_password'] or 0), 'token_hash': th}

    def require_user(self, allow_password_change=False):
        u = self.user()
        if not u:
            self.error_json(401, '未登录或登录已过期')
            return None
        if u.get('must_change_password') and not allow_password_change:
            self.error_json(403, '请先修改默认密码')
            return None
        return u

    def current_user_payload(self, u):
        return {'username': u['username'], 'role': u['role'], 'must_change_password': int(u.get('must_change_password') or 0), 'token_expires_in': TOKEN_TTL}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            return self.send_json(200, {'ok': True})
        u = self.require_user(allow_password_change=(path == '/api/me'))
        if not u:
            return
        if path == '/api/me':
            return self.send_json(200, {'ok': True, 'user': self.current_user_payload(u)})
        if path == '/api/users':
            if u['role'] != 'admin':
                return self.error_json(403, '只有管理员可以查看用户')
            data = rows('select id,username,role,created_at,must_change_password from users order by id')
            return self.send_json(200, {'ok': True, 'users': data})
        if path == '/api/products':
            data = rows('select * from products order by active desc, id desc')
            return self.send_json(200, {'ok': True, 'products': [product_dict(r) for r in data]})
        if path == '/api/logs':
            data = rows('''select l.*, p.sku, p.name from inventory_logs l left join products p on p.id=l.product_id order by l.id desc limit 200''')
            logs = [{'id': r['id'], 'doc_no': r['doc_no'] or '', 't': r['business'], 'kind': r['type'], 'sku': r['sku'] or '', 'name': r['name'] or '', 'n': r['qty'], 'before': r['before_stock'], 'stock': r['after_stock'], 'remark': r['remark'] or '', 'time': r['created_at'], 'operator': r['operator'], 'voided': int(r['voided'] or 0), 'void_reason': r['void_reason'] or '', 'voided_by': r['voided_by'] or '', 'voided_at': r['voided_at'] or '', 'reverse_of': r['reverse_of']} for r in data]
            return self.send_json(200, {'ok': True, 'logs': logs})
        if path == '/api/export/logs.csv':
            return self.export_logs()
        return self.error_json(404, '接口不存在')

    def export_logs(self):
        data = rows('''select l.*, p.sku, p.name from inventory_logs l left join products p on p.id=l.product_id order by l.id desc limit 1000''')
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(['单号', '时间', '业务类型', '状态', 'SKU', '商品名称', '数量', '变更前库存', '变更后库存', '操作人', '备注', '作废人', '作废时间', '作废原因'])
        for r in data:
            status = '已作废' if int(r['voided'] or 0) else ('冲销单' if r['reverse_of'] else '正常')
            writer.writerow([r['doc_no'] or '', r['created_at'], r['business'], status, r['sku'] or '', r['name'] or '', r['qty'], r['before_stock'], r['after_stock'], r['operator'], r['remark'] or '', r['voided_by'] or '', r['voided_at'] or '', r['void_reason'] or ''])
        raw = ('\ufeff' + out.getvalue()).encode('utf-8')
        self.send_response(200)
        self.send_header('content-type', 'text/csv; charset=utf-8')
        self.send_header('content-disposition', 'attachment; filename=wms-logs.csv')
        self.send_header('cache-control', 'no-store')
        self.send_header('content-length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = parse_body(self)
        except Exception:
            return self.error_json(400, '请求 JSON 格式错误')
        if path == '/api/login':
            return self.login(data)
        if path == '/api/logout':
            return self.logout()
        u = self.require_user(allow_password_change=(path == '/api/change-password'))
        if not u:
            return
        if path == '/api/users':
            return self.create_user(data, u)
        if path == '/api/change-password':
            return self.change_password(data, u)
        if path == '/api/products':
            if u['role'] == 'viewer':
                return self.error_json(403, '只读用户不能修改商品')
            return self.save_product(data)
        if path == '/api/movements':
            if u['role'] == 'viewer':
                return self.error_json(403, '只读用户不能操作库存')
            return self.movement(data, u['username'])
        if path.startswith('/api/products/') and path.endswith('/active'):
            if u['role'] == 'viewer':
                return self.error_json(403, '只读用户不能修改商品')
            return self.set_product_active(path, data)
        if path.startswith('/api/logs/') and path.endswith('/void'):
            if u['role'] == 'viewer':
                return self.error_json(403, '只读用户不能作废流水')
            return self.void_log(path, data, u['username'])
        return self.error_json(404, '接口不存在')

    def do_PUT(self):
        path = urlparse(self.path).path
        u = self.require_user()
        if not u:
            return
        if path.startswith('/api/products/'):
            if u['role'] == 'viewer':
                return self.error_json(403, '只读用户不能修改商品')
            try:
                data = parse_body(self)
            except Exception:
                return self.error_json(400, '请求 JSON 格式错误')
            data['id'] = path.rsplit('/', 1)[-1]
            return self.save_product(data)
        return self.error_json(404, '接口不存在')

    def login(self, data):
        username = str(data.get('username') or '').strip()
        password = str(data.get('password') or '')
        ip = client_ip(self)
        now = now_ts()
        if not username or not password:
            return self.error_json(400, '账号和密码必填')
        with db() as con:
            attempt = con.execute('select fail_count,locked_until from login_attempts where username=? and ip=?', (username, ip)).fetchone()
            if attempt and int(attempt['locked_until'] or 0) > now:
                wait = max(1, int((int(attempt['locked_until']) - now + 59) / 60))
                return self.error_json(429, f'登录失败次数过多，请 {wait} 分钟后再试')
            user = con.execute('select id,username,password,password_hash,role,must_change_password from users where username=?', (username,)).fetchone()
            ok = bool(user and verify_password(user['password_hash'] or user['password'], password))
            if not ok:
                fail_count = int(attempt['fail_count']) + 1 if attempt else 1
                locked_until = now + LOGIN_LOCK_SECONDS if fail_count >= LOGIN_MAX_FAILS else 0
                con.execute('insert into login_attempts(username,ip,fail_count,locked_until,last_failed_at) values(?,?,?,?,current_timestamp) on conflict(username,ip) do update set fail_count=?,locked_until=?,last_failed_at=current_timestamp', (username, ip, fail_count, locked_until, fail_count, locked_until))
                return self.error_json(401, '账号或密码错误')
            con.execute('delete from login_attempts where username=? and ip=?', (username, ip))
            if not user['password_hash']:
                con.execute('update users set password=?,password_hash=? where id=?', ('', hash_password(password), user['id']))
            token = secrets.token_urlsafe(32)
            expires_at = now + TOKEN_TTL
            con.execute('insert into auth_tokens(token_hash,username,role,expires_at) values(?,?,?,?)', (token_hash(token), username, user['role'], expires_at))
            payload = {'username': username, 'role': user['role'], 'must_change_password': int(user['must_change_password'] or 0), 'token_expires_in': TOKEN_TTL}
            return self.send_json(200, {'ok': True, 'token': token, 'user': payload})

    def logout(self):
        auth = self.headers.get('authorization') or ''
        token = auth.replace('Bearer ', '', 1).strip()
        if token:
            with db() as con:
                con.execute('update auth_tokens set revoked_at=current_timestamp where token_hash=?', (token_hash(token),))
        return self.send_json(200, {'ok': True})

    def create_user(self, data, current_user):
        if current_user['role'] != 'admin':
            return self.error_json(403, '只有管理员可以新增用户')
        username = str(data.get('username') or '').strip()
        password = str(data.get('password') or '').strip()
        role = str(data.get('role') or 'keeper').strip()
        if role not in ('admin', 'keeper', 'viewer'):
            return self.error_json(400, '角色无效')
        if not username or len(username) < 3:
            return self.error_json(400, '账号至少 3 个字符')
        if not password or len(password) < 8:
            return self.error_json(400, '密码至少 8 个字符')
        try:
            with db() as con:
                cur = con.execute('insert into users(username,password,password_hash,role,must_change_password) values(?,?,?,?,0)', (username, '', hash_password(password), role))
                uid = cur.lastrowid
        except sqlite3.IntegrityError:
            return self.error_json(409, '账号已存在')
        user = one('select id,username,role,created_at,must_change_password from users where id=?', (uid,))
        return self.send_json(200, {'ok': True, 'user': user})

    def change_password(self, data, current_user):
        old_password = str(data.get('old_password') or '')
        new_password = str(data.get('new_password') or '')
        if len(new_password) < 8:
            return self.error_json(400, '新密码至少 8 个字符')
        if old_password == new_password:
            return self.error_json(400, '新密码不能和原密码相同')
        with db() as con:
            row = con.execute('select id,password,password_hash from users where username=?', (current_user['username'],)).fetchone()
            if not row or not verify_password(row['password_hash'] or row['password'], old_password):
                return self.error_json(400, '原密码错误')
            con.execute('update users set password=?,password_hash=?,must_change_password=0 where id=?', ('', hash_password(new_password), row['id']))
            con.execute('update auth_tokens set revoked_at=current_timestamp where username=? and token_hash<>?', (current_user['username'], current_user.get('token_hash') or ''))
        return self.send_json(200, {'ok': True})

    def save_product(self, data):
        name = str(data.get('name') or '').strip()
        sku = str(data.get('sku') or '').strip()
        if not name or not sku:
            return self.error_json(400, '商品名称和 SKU 必填')
        vals = (sku, str(data.get('code') or '').strip(), name, str(data.get('loc') or data.get('location') or '').strip(), int(data.get('stock') or 0), int(data.get('min') or data.get('min_stock') or 0), str(data.get('unit') or '件').strip())
        try:
            with db() as con:
                if data.get('id'):
                    con.execute('update products set sku=?,code=?,name=?,location=?,stock=?,min_stock=?,unit=?,updated_at=current_timestamp where id=?', vals + (int(data['id']),))
                    pid = int(data['id'])
                else:
                    cur = con.execute('insert into products(sku,code,name,location,stock,min_stock,unit) values(?,?,?,?,?,?,?)', vals)
                    pid = cur.lastrowid
        except sqlite3.IntegrityError:
            return self.error_json(409, 'SKU 已存在')
        r = one('select * from products where id=?', (pid,))
        return self.send_json(200, {'ok': True, 'product': product_dict(r)})

    def set_product_active(self, path, data):
        try:
            pid = int(path.split('/')[-2])
        except Exception:
            return self.error_json(400, '商品 ID 无效')
        active = 1 if data.get('active') else 0
        with db() as con:
            row = con.execute('select id from products where id=?', (pid,)).fetchone()
            if not row:
                return self.error_json(404, '商品不存在')
            con.execute('update products set active=?,updated_at=current_timestamp where id=?', (active, pid))
        r = one('select * from products where id=?', (pid,))
        return self.send_json(200, {'ok': True, 'product': product_dict(r)})

    def void_log(self, path, data, operator):
        try:
            lid = int(path.split('/')[-2])
        except Exception:
            return self.error_json(400, '流水 ID 无效')
        reason = str(data.get('reason') or '').strip()
        if len(reason) < 2:
            return self.error_json(400, '请填写作废原因')
        with db() as con:
            log = con.execute('select * from inventory_logs where id=?', (lid,)).fetchone()
            if not log:
                return self.error_json(404, '流水不存在')
            if log['type'] == 'void' or log['reverse_of']:
                return self.error_json(400, '冲销流水不能再次作废')
            if int(log['voided'] or 0):
                return self.error_json(409, '该流水已作废')
            prod = con.execute('select * from products where id=?', (log['product_id'],)).fetchone()
            if not prod:
                return self.error_json(404, '商品不存在')
            before = int(prod['stock'])
            delta = int(log['after_stock']) - int(log['before_stock'])
            after = before - delta
            if after < 0:
                return self.error_json(409, '作废后库存会小于 0，请先核对后续流水')
            doc_no = make_doc_no(con, 'void')
            remark = f'作废 {log["doc_no"] or log["id"]}：{reason}'
            con.execute('update products set stock=?,updated_at=current_timestamp where id=?', (after, log['product_id']))
            con.execute('update inventory_logs set voided=1,void_reason=?,voided_by=?,voided_at=current_timestamp where id=?', (reason, operator, lid))
            con.execute('insert into inventory_logs(product_id,doc_no,type,business,qty,before_stock,after_stock,remark,operator,reverse_of) values(?,?,?,?,?,?,?,?,?,?)', (log['product_id'], doc_no, 'void', '作废冲销', abs(delta), before, after, remark, operator, lid))
        r = one('select * from products where id=?', (log['product_id'],))
        return self.send_json(200, {'ok': True, 'product': product_dict(r)})

    def movement(self, data, operator):
        pid = int(data.get('id') or data.get('product_id') or 0)
        move_type = str(data.get('type') or '').strip()
        business = str(data.get('business') or '').strip()
        qty = int(data.get('qty') or data.get('n') or 0)
        remark = str(data.get('remark') or '').strip()
        if move_type not in BUSINESS or business not in BUSINESS[move_type]:
            return self.error_json(400, '业务类型无效')
        if qty < 0 or (move_type != 'stocktake' and qty <= 0):
            return self.error_json(400, '数量无效')
        with db() as con:
            r = con.execute('select * from products where id=?', (pid,)).fetchone()
            if not r:
                return self.error_json(404, '商品不存在')
            if int(r['active']) == 0:
                return self.error_json(409, '商品已停用，不能操作库存')
            before = int(r['stock'])
            if move_type == 'in':
                after = before + qty
            elif move_type == 'out':
                if before < qty:
                    return self.error_json(409, '库存不足')
                after = before - qty
            else:
                after = qty
                qty = abs(after - before)
            doc_no = make_doc_no(con, move_type)
            con.execute('update products set stock=?,updated_at=current_timestamp where id=?', (after, pid))
            con.execute('insert into inventory_logs(product_id,doc_no,type,business,qty,before_stock,after_stock,remark,operator) values(?,?,?,?,?,?,?,?,?)', (pid, doc_no, move_type, business, qty, before, after, remark, operator))
        r = one('select * from products where id=?', (pid,))
        return self.send_json(200, {'ok': True, 'product': product_dict(r)})

def main():
    init_db()
    srv = ThreadingHTTPServer(('127.0.0.1', 8001), Handler)
    print('wms api listening on 127.0.0.1:8001', flush=True)
    srv.serve_forever()

if __name__ == '__main__':
    main()
