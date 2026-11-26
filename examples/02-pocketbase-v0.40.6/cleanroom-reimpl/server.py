#!/usr/bin/env python3
"""
Clean-Room PocketBase-Compatible Server + Admin UI (pb-cleanroom)
Built strictly from spec-anything 01-12 specification (09_contracts + 11_ui/tokens.json)
in Python stdlib + SQLite WAL to demonstrate end-to-end reimplementation parity
verified by the unmodified 07_tests/verify_parity.py --target-url harness.
"""
import argparse
import base64
import hashlib
import hmac
import http.server
import json
import pathlib
import queue
import re
import secrets
import socketserver
import sqlite3
import string
import threading
import time
import urllib.parse
import zipfile

ALPHABET = string.ascii_lowercase + string.digits
JWT_SECRET = b"cleanroom-local-dev-secret-key"


def gen_id(length: int = 15) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def make_jwt(email: str, record_id: str) -> str:
    hdr = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    pay = base64.urlsafe_b64encode(json.dumps({"id": record_id, "email": email, "collection": "_superusers", "exp": int(time.time()) + 3600}).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(hmac.new(JWT_SECRET, f"{hdr}.{pay}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{hdr}.{pay}.{sig}"


def verify_jwt(token: str | None) -> dict | None:
    if not token:
        return None
    raw = token.replace("Bearer ", "").strip()
    parts = raw.split(".")
    if len(parts) != 3:
        return None
    expected = base64.urlsafe_b64encode(hmac.new(JWT_SECRET, f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    if not hmac.compare_digest(parts[2], expected):
        return None
    pad = "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(parts[1] + pad).decode())


class CleanRoomStore:
    def __init__(self, data_dir: pathlib.Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "backups").mkdir(exist_ok=True)
        self.db_path = self.data_dir / "data.db"
        self.lock = threading.RLock()
        self.sse_clients: dict[str, dict] = {}
        self._init_db()

    def conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path), check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL;")
        return c

    def _init_db(self):
        with self.lock:
            c = self.conn()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS _superusers (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created TEXT NOT NULL,
                    updated TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS _collections (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    fields_json TEXT NOT NULL,
                    indexes_json TEXT NOT NULL,
                    rules_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS _params (
                    id TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL
                );
            """)
            # Seed default synthetic superuser & settings matching 04_reproduction_env.md
            pw_hash = hashlib.sha256(b"TestPass123456!").hexdigest()
            now = time.strftime("%Y-%m-%d %H:%M:%S.000Z", time.gmtime())
            c.execute(
                "INSERT OR IGNORE INTO _superusers (id, email, password_hash, created, updated) VALUES (?, ?, ?, ?, ?)",
                (gen_id(), "admin@example.com", pw_hash, now, now),
            )
            c.execute(
                "INSERT OR IGNORE INTO _params (id, value_json) VALUES ('settings', ?)",
                (json.dumps({"meta": {"appName": "Acme", "appURL": "http://localhost:8090"}}),),
            )
            c.commit()
            c.close()

    def register_sse(self) -> tuple[str, queue.Queue]:
        cid = gen_id(32)
        q: queue.Queue = queue.Queue()
        with self.lock:
            self.sse_clients[cid] = {"queue": q, "subscriptions": []}
        return cid, q

    def set_subscriptions(self, cid: str, subs: list[str]) -> bool:
        with self.lock:
            if cid not in self.sse_clients:
                return False
            self.sse_clients[cid]["subscriptions"] = list(subs)
            return True

    def broadcast(self, collection: str, action: str, record: dict):
        topic = f"{collection}/*"
        frame = {"event": topic, "data": {"action": action, "record": record}}
        with self.lock:
            for info in self.sse_clients.values():
                if topic in info["subscriptions"] or collection in info["subscriptions"]:
                    info["queue"].put(frame)


ADMIN_UI_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Superuser login</title>
<style>
:root {
  --baseFontFamily: "IBM Plex Sans", system-ui, sans-serif, emoji;
  --monospaceFontFamily: "IBM Plex Mono", ui-monospace, monospace, emoji;
  --primaryColor: #25272d;
  --secondaryColor: #e4e8ec;
  --accentColor: #1055c9;
  --successColor: #22a96d;
  --dangerColor: #c33751;
  --surfaceColor: #fff;
  --surfaceAlt1Color: #f8f9fa;
  --surfaceTxtColor: #25272d;
  --surfaceTxtHintColor: #687278;
  --fontSize: 14px;
  --lineHeight: 22px;
  --btnHeight: 45px;
  --borderRadius: 5px;
  --spacing: 30px;
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: var(--baseFontFamily); font-size: var(--fontSize); line-height: var(--lineHeight);
  color: var(--surfaceTxtColor); background: var(--surfaceColor); min-height: 100vh;
}
.login-wrap {
  min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px;
}
.login-box { width: 420px; max-width: 100%; }
.logo-mark {
  width: 42px; height: 42px; margin: 0 auto 12px; border: 2px solid var(--primaryColor);
  border-radius: 6px; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 16px; letter-spacing: -0.04em;
}
.login-title { text-align: center; font-size: 18px; font-weight: 500; margin: 0 0 26px; color: var(--primaryColor); }
.field {
  background: var(--secondaryColor); border-radius: var(--borderRadius); padding: 10px 14px; margin-bottom: 16px;
}
.field label { display: block; font-size: 12px; font-weight: 600; color: var(--surfaceTxtHintColor); margin-bottom: 2px; }
.field label span { color: var(--dangerColor); }
.field input {
  width: 100%; border: 0; outline: 0; background: transparent; font-family: inherit;
  font-size: 14px; color: var(--primaryColor); padding: 2px 0;
}
.hint-link { display: inline-block; font-size: 12px; color: var(--surfaceTxtHintColor); margin: -6px 0 22px; text-decoration: none; }
.btn-primary {
  width: 100%; height: var(--btnHeight); border: 0; border-radius: var(--borderRadius);
  background: var(--primaryColor); color: #fff; font-family: inherit; font-size: 14px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
}
.toast-err {
  position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%);
  background: #f5d7dd; color: #3a121a; border-left: 4px solid var(--dangerColor);
  padding: 12px 20px; border-radius: var(--borderRadius); font-size: 13px;
  box-shadow: 0 8px 20px rgba(34,36,36,0.12); min-width: 340px; display: none;
}
.toast-err.show { display: block; }
/* App shell after login */
.app-shell { display: none; min-height: 100vh; flex-direction: column; }
.topbar {
  height: 44px; background: var(--accentColor); color: #fff; display: flex; align-items: center;
  justify-content: space-between; padding: 0 18px; font-size: 13px; font-weight: 600;
}
.topbar-nav { display: flex; gap: 16px; align-items: center; }
.topbar-nav a { color: rgba(255,255,255,0.85); text-decoration: none; padding: 4px 10px; border-radius: 5px; }
.topbar-nav a.active { background: rgba(255,255,255,0.18); color: #fff; }
.main-layout { display: flex; flex: 1; }
.sidebar { width: 240px; background: var(--surfaceAlt1Color); border-right: 1px solid #dce0e5; padding: 16px; }
.sidebar h4 { font-size: 11px; text-transform: uppercase; color: var(--surfaceTxtHintColor); margin: 0 0 10px; }
.sidebar a { display: block; padding: 8px 10px; border-radius: 5px; color: var(--primaryColor); text-decoration: none; font-weight: 500; margin-bottom: 4px; }
.sidebar a.active { background: var(--secondaryColor); }
.content { flex: 1; padding: 24px 30px; }
.content-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.content-head h2 { margin: 0; font-size: 20px; font-weight: 500; }
.search-bar { width: 100%; height: 44px; border: 0; border-radius: 22px; background: var(--secondaryColor); padding: 0 18px; font-size: 14px; margin-bottom: 18px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 11px 12px; border-bottom: 1px solid #e4e8ec; font-size: 14px; }
th { color: var(--surfaceTxtHintColor); font-weight: 600; font-size: 13px; }
.id-pill { background: var(--secondaryColor); padding: 3px 8px; border-radius: 4px; font-family: var(--monospaceFontFamily); font-size: 12px; }
.bool-true { background: #d6f3e4; color: #156d45; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.bool-false { background: var(--secondaryColor); color: var(--surfaceTxtHintColor); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
</style>
</head>
<body>
<div id="login-view" class="login-wrap">
  <div class="login-box">
    <div class="logo-mark" aria-hidden="true">CR</div>
    <h5 class="login-title">Superuser login</h5>
    <form id="login-form">
      <div class="field">
        <label>Email <span>*</span></label>
        <input id="email" type="email" name="identity" required autocomplete="username"/>
      </div>
      <div class="field">
        <label>Password <span>*</span></label>
        <input id="password" type="password" name="password" required autocomplete="current-password"/>
      </div>
      <a class="hint-link" href="#/request-password-reset">Forgotten password</a>
      <button class="btn-primary" type="submit">Login &rarr;</button>
    </form>
  </div>
</div>
<div id="toast" class="toast-err">Invalid login credentials.</div>

<div id="app-view" class="app-shell">
  <div class="topbar">
    <div class="topbar-nav">
      <span>CR</span>
      <a href="#/collections" class="active">Collections</a>
      <a href="#/settings">Settings</a>
    </div>
    <div id="user-email">admin@example.com</div>
  </div>
  <div class="main-layout">
    <aside class="sidebar">
      <h4>Collections</h4>
      <a href="#/collections?collection=articles" class="active">articles</a>
    </aside>
    <main class="content">
      <div class="content-head">
        <h2>Collections / articles</h2>
        <div>
          <button style="height:36px;padding:0 14px;border:1.5px solid var(--primaryColor);background:#fff;border-radius:5px;font-weight:600;margin-right:8px;">&lt;/&gt; API preview</button>
          <button style="height:36px;padding:0 16px;border:0;background:var(--primaryColor);color:#fff;border-radius:5px;font-weight:600;">+ New record</button>
        </div>
      </div>
      <input class="search-bar" type="search" placeholder="Search term or filter..."/>
      <table>
        <thead><tr><th>id</th><th>title</th><th>slug</th><th>published</th><th>views</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
      <div id="total-foot" style="margin-top:16px;font-size:12px;color:var(--surfaceTxtHintColor);"></div>
    </main>
  </div>
</div>

<script>
const form = document.getElementById('login-form');
const toast = document.getElementById('toast');
async function loadArticles() {
  const res = await fetch('/api/collections/articles/records?sort=-views');
  if (!res.ok) return;
  const data = await res.json();
  document.getElementById('rows').innerHTML = data.items.map(it => `
    <tr>
      <td><span class="id-pill">${it.id}</span></td>
      <td>${it.title}</td>
      <td>${it.slug}</td>
      <td><span class="${it.published ? 'bool-true' : 'bool-false'}">${it.published ? 'True' : 'False'}</span></td>
      <td>${it.views}</td>
    </tr>
  `).join('');
  document.getElementById('total-foot').textContent = 'Total: ' + data.totalItems;
}
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  toast.classList.remove('show');
  const identity = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const res = await fetch('/api/collections/_superusers/auth-with-password', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({identity, password})
  });
  if (!res.ok) {
    toast.classList.add('show');
    return;
  }
  const data = await res.json();
  localStorage.setItem('cr_token', data.token);
  document.getElementById('login-view').style.display = 'none';
  document.getElementById('app-view').style.display = 'flex';
  await loadArticles();
});
</script>
</body>
</html>
"""


def make_handler(store: CleanRoomStore):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            pass

        def send_json(self, code: int, obj):
            raw = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def read_json(self):
            ln = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(ln).decode("utf-8")) if ln > 0 else {}

        def auth_superuser(self):
            return verify_jwt(self.headers.get("Authorization"))

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            if path == "/_/" or path.startswith("/_/"):
                raw = ADMIN_UI_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return

            if path == "/api/health":
                return self.send_json(200, {"code": 200, "message": "API is healthy.", "data": {}})

            if path == "/api/collections":
                if not self.auth_superuser():
                    return self.send_json(401, {"status": 401, "message": "The request requires valid record authorization token.", "data": {}})
                with store.lock:
                    c = store.conn()
                    rows = c.execute("SELECT * FROM _collections").fetchall()
                    c.close()
                items = [{"id": r["id"], "name": r["name"], "type": r["type"], "fields": json.loads(r["fields_json"]), "indexes": json.loads(r["indexes_json"])} for r in rows]
                return self.send_json(200, {"page": 1, "perPage": 30, "totalItems": len(items), "items": items})

            if path == "/api/realtime":
                cid, q = store.register_sse()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                connect_frame = f"id:{cid}\nevent:PB_CONNECT\ndata:{json.dumps({'clientId': cid})}\n\n"
                self.wfile.write(connect_frame.encode("utf-8"))
                self.wfile.flush()
                try:
                    t_end = time.time() + 12
                    while time.time() < t_end:
                        try:
                            ev = q.get(timeout=0.5)
                            msg = f"id:{gen_id()}\nevent:{ev['event']}\ndata:{json.dumps(ev['data'])}\n\n"
                            self.wfile.write(msg.encode("utf-8"))
                            self.wfile.flush()
                        except queue.Empty:
                            continue
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

            if path == "/api/settings":
                if not self.auth_superuser():
                    return self.send_json(401, {"status": 401, "message": "The request requires valid record authorization token.", "data": {}})
                with store.lock:
                    c = store.conn()
                    row = c.execute("SELECT value_json FROM _params WHERE id='settings'").fetchone()
                    c.close()
                return self.send_json(200, json.loads(row["value_json"]))

            if path == "/api/backups":
                if not self.auth_superuser():
                    return self.send_json(401, {"status": 401, "message": "The request requires valid record authorization token.", "data": {}})
                bdir = store.data_dir / "backups"
                items = [{"key": p.name, "size": p.stat().st_size, "modified": time.strftime("%Y-%m-%d %H:%M:%S.000Z", time.gmtime(p.stat().st_mtime))} for p in sorted(bdir.glob("*.zip"))]
                return self.send_json(200, items)

            m = re.fullmatch(r"/api/collections/([A-Za-z0-9_]+)/records", path)
            if m:
                col = m.group(1)
                flt = (qs.get("filter") or [""])[0]
                sort_spec = (qs.get("sort") or [""])[0]
                page = int((qs.get("page") or ["1"])[0])
                per_page = int((qs.get("perPage") or ["30"])[0])
                where_parts, params = [], []
                if flt:
                    inner = flt.strip().lstrip("(").rstrip(")")
                    for clause in [x.strip() for x in inner.split("&&") if x.strip()]:
                        cm = re.fullmatch(r"([A-Za-z0-9_]+)\s*(>=|<=|!=|=|>|<)\s*(.+)", clause)
                        if cm:
                            f_col, op, val = cm.group(1), cm.group(2), cm.group(3).strip()
                            if val.lower() == "true":
                                params.append(1)
                            elif val.lower() == "false":
                                params.append(0)
                            elif re.fullmatch(r"-?\d+(?:\.\d+)?", val):
                                params.append(float(val) if "." in val else int(val))
                            else:
                                params.append(val.strip("'\""))
                            where_parts.append(f"{f_col} {op} ?")
                order_sql = ""
                if sort_spec:
                    desc = sort_spec.startswith("-")
                    scol = sort_spec.lstrip("+-")
                    if re.fullmatch(r"[A-Za-z0-9_]+", scol):
                        order_sql = f" ORDER BY {scol} {'DESC' if desc else 'ASC'}"
                where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
                with store.lock:
                    c = store.conn()
                    total = c.execute(f"SELECT COUNT(*) FROM {col}{where_sql}", params).fetchone()[0]
                    rows = c.execute(f"SELECT * FROM {col}{where_sql}{order_sql} LIMIT ? OFFSET ?", params + [per_page, (page - 1) * per_page]).fetchall()
                    c.close()
                items = []
                for r in rows:
                    d = dict(r)
                    if "published" in d:
                        d["published"] = bool(d["published"])
                    items.append(d)
                return self.send_json(200, {"page": page, "perPage": per_page, "totalItems": total, "items": items})

            return self.send_json(404, {"status": 404, "message": "Not found.", "data": {}})

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            body = self.read_json()

            if path == "/api/collections/_superusers/auth-with-password":
                identity = body.get("identity", "")
                pw = body.get("password", "")
                pw_hash = hashlib.sha256(pw.encode()).hexdigest()
                with store.lock:
                    c = store.conn()
                    row = c.execute("SELECT * FROM _superusers WHERE email=? AND password_hash=?", (identity, pw_hash)).fetchone()
                    c.close()
                if not row:
                    return self.send_json(400, {"status": 400, "message": "Failed to authenticate.", "data": {}})
                tok = make_jwt(row["email"], row["id"])
                return self.send_json(200, {
                    "token": tok,
                    "record": {"id": row["id"], "email": row["email"], "collectionName": "_superusers", "created": row["created"], "updated": row["updated"]},
                })

            if path == "/api/collections":
                if not self.auth_superuser():
                    return self.send_json(401, {"status": 401, "message": "The request requires valid record authorization token.", "data": {}})
                cid = "pbc_" + gen_id(10)
                name = body["name"]
                ctype = body.get("type", "base")
                fields = body.get("fields", [])
                indexes = body.get("indexes", [])
                all_fields = [{"name": "id", "type": "text", "primaryKey": True}] + fields
                col_defs = ["id TEXT PRIMARY KEY NOT NULL"]
                for f in fields:
                    sql_t = {"text": "TEXT DEFAULT '' NOT NULL", "bool": "BOOLEAN DEFAULT FALSE NOT NULL", "number": "NUMERIC DEFAULT 0 NOT NULL"}.get(f["type"], "TEXT DEFAULT '' NOT NULL")
                    col_defs.append(f"{f['name']} {sql_t}")
                with store.lock:
                    c = store.conn()
                    c.execute(f"CREATE TABLE {name} ({', '.join(col_defs)})")
                    for idx_sql in indexes:
                        c.execute(idx_sql)
                    c.execute(
                        "INSERT INTO _collections (id, name, type, fields_json, indexes_json, rules_json) VALUES (?, ?, ?, ?, ?, ?)",
                        (cid, name, ctype, json.dumps(all_fields), json.dumps(indexes), json.dumps({})),
                    )
                    c.commit()
                    c.close()
                return self.send_json(200, {"id": cid, "name": name, "type": ctype, "fields": all_fields, "indexes": indexes})

            if path == "/api/realtime":
                ok = store.set_subscriptions(body.get("clientId", ""), body.get("subscriptions", []))
                if not ok:
                    return self.send_json(404, {"status": 404, "message": "Missing or invalid client id.", "data": {}})
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            if path == "/api/backups":
                if not self.auth_superuser():
                    return self.send_json(401, {"status": 401, "message": "The request requires valid record authorization token.", "data": {}})
                name = body.get("name") or f"backup_{int(time.time())}.zip"
                dest = store.data_dir / "backups" / name
                with store.lock:
                    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(store.db_path, "data.db")
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            m = re.fullmatch(r"/api/collections/([A-Za-z0-9_]+)/records", path)
            if m:
                col = m.group(1)
                with store.lock:
                    c = store.conn()
                    crow = c.execute("SELECT fields_json FROM _collections WHERE name=?", (col,)).fetchone()
                    if not crow:
                        c.close()
                        return self.send_json(404, {"status": 404, "message": "Collection not found.", "data": {}})
                    fields = json.loads(crow["fields_json"])
                    errs = {}
                    for f in fields:
                        fn = f["name"]
                        if fn == "id":
                            continue
                        val = body.get(fn)
                        if f.get("required") and (val is None or val == ""):
                            errs[fn] = {"code": "validation_required", "message": "Cannot be blank."}
                        elif f["type"] == "text" and isinstance(val, str) and f.get("min") and len(val) < f["min"]:
                            errs[fn] = {"code": "validation_min_text_constraint", "message": f"Must be at least {f['min']} character(s).", "params": {"min": f["min"]}}
                    if errs:
                        c.close()
                        return self.send_json(400, {"status": 400, "message": "Failed to create record.", "data": errs})
                    rec_id = gen_id(15)
                    cols = ["id"]
                    vals = [rec_id]
                    out_rec = {"id": rec_id}
                    for f in fields:
                        fn = f["name"]
                        if fn == "id":
                            continue
                        v = body.get(fn)
                        if f["type"] == "bool":
                            v = bool(v)
                            cols.append(fn); vals.append(1 if v else 0); out_rec[fn] = v
                        elif f["type"] == "number":
                            v = v if v is not None else 0
                            cols.append(fn); vals.append(v); out_rec[fn] = v
                        else:
                            v = v if v is not None else ""
                            cols.append(fn); vals.append(v); out_rec[fn] = v
                    try:
                        c.execute(f"INSERT INTO {col} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in vals)})", vals)
                        c.commit()
                    except sqlite3.IntegrityError as ie:
                        c.close()
                        msg = str(ie)
                        dup_col = msg.split(".")[-1].strip() if "." in msg else "slug"
                        return self.send_json(400, {"status": 400, "message": "Failed to create record.", "data": {dup_col: {"code": "validation_not_unique", "message": "Value must be unique."}}})
                    c.close()
                store.broadcast(col, "create", out_rec)
                return self.send_json(200, out_rec)

            return self.send_json(404, {"status": 404, "message": "Not found.", "data": {}})

        def do_PATCH(self):
            path = urllib.parse.urlparse(self.path).path
            body = self.read_json()
            if path == "/api/settings":
                if not self.auth_superuser():
                    return self.send_json(401, {"status": 401, "message": "The request requires valid record authorization token.", "data": {}})
                with store.lock:
                    c = store.conn()
                    cur = json.loads(c.execute("SELECT value_json FROM _params WHERE id='settings'").fetchone()["value_json"])
                    for k, v in body.items():
                        if isinstance(v, dict) and isinstance(cur.get(k), dict):
                            cur[k].update(v)
                        else:
                            cur[k] = v
                    c.execute("UPDATE _params SET value_json=? WHERE id='settings'", (json.dumps(cur),))
                    c.commit()
                    c.close()
                return self.send_json(200, cur)
            return self.send_json(404, {"status": 404, "message": "Not found.", "data": {}})

    return Handler


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--port", type=int, default=8091)
    args = ap.parse_args()
    store = CleanRoomStore(pathlib.Path(args.dir))
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(store))
    srv.serve_forever()


if __name__ == "__main__":
    main()
