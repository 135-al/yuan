"""
conftest.py - pytest 全局 fixtures

职责：
  1. 启动 Flask 测试服务器（后台线程，独立端口 5001）
  2. setup：自动创建两个测试用户（user_a / user_b），获取 Token
  3. teardown：测试结束后清理所有测试数据并关闭服务器

使用 requests 库发起真实 HTTP 请求，模拟真实调用场景。
"""

import os
import time
import uuid
import tempfile
import threading
import requests
import pytest
import allure

from app import create_app, db
from app.models import User, Task, Tag, Attachment, Comment, OperationLog


# ---------------------------------------------------------------------------
# 服务器管理
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url():
    """返回测试服务器基础 URL"""
    return "http://127.0.0.1:5001"


@pytest.fixture(scope="session", autouse=True)
def flask_server(base_url):
    """
    启动 Flask 测试服务器（session 级别，整个测试会话只启动一次）
    使用独立端口 5001，不影响开发服务器 5000
    """
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-for-automation",
        # 上传目录隔离到临时目录，避免测试污染项目目录、并保证可清理
        "UPLOAD_FOLDER": os.path.join(tempfile.mkdtemp(prefix="taskflow_uploads_"), "uploads"),
        # 不覆盖 JWT_EXPIRATION_DELTA，保留原始 7 天配置以测试缺陷⑦
    })

    from werkzeug.serving import make_server
    server = make_server("127.0.0.1", 5001, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # 等待服务器就绪
    for _ in range(20):
        try:
            requests.get(base_url + "/", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.2)

    # 把 app 存到 pytest 属性，供后续 fixture 使用
    pytest._flask_app = app

    yield app

    server.shutdown()


# ---------------------------------------------------------------------------
# HTTP 请求封装
# ---------------------------------------------------------------------------

class ApiClient:
    """封装 requests，自动附加 Token，记录 Allure 附件"""

    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()

    def _headers(self, extra=None):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def _attach(self, method, path, resp):
        """将请求/响应信息附加到 Allure 报告"""
        allure.attach(
            f"Method: {method}\nURL: {self.base_url}{path}\n"
            f"Status: {resp.status_code}\n\n"
            f"Response Body:\n{resp.text}",
            name=f"{method} {path}",
            attachment_type=allure.attachment_type.TEXT,
        )

    def request(self, method, path, json=None, params=None, headers=None):
        url = self.base_url + path
        resp = self.session.request(
            method, url, json=json, params=params, headers=self._headers(headers)
        )
        self._attach(method, path, resp)
        return resp

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, json=None, **kw):
        return self.request("POST", path, json=json, **kw)

    def put(self, path, json=None, **kw):
        return self.request("PUT", path, json=json, **kw)

    def patch(self, path, json=None, **kw):
        return self.request("PATCH", path, json=json, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

    def upload(self, path, file_path, field_name="file"):
        """上传文件（multipart/form-data）"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        with open(file_path, "rb") as f:
            files = {field_name: f}
            resp = self.session.post(self.base_url + path, files=files, headers=headers)
        self._attach("POST (upload)", path, resp)
        return resp


# ---------------------------------------------------------------------------
# 用户 & Token fixtures
# ---------------------------------------------------------------------------

def _unique_suffix():
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="function")
def test_users(flask_server):
    """
    setup: 创建两个测试用户（user_a, user_b）
    teardown: 测试结束后清理数据库
    """
    app = flask_server
    suffix = _unique_suffix()

    users = {}
    with app.app_context():
        for role in ["a", "b"]:
            username = f"testuser_{role}_{suffix}"
            email = f"testuser_{role}_{suffix}@test.com"
            user = User(username=username, email=email)
            user.set_password("Test@1234")
            db.session.add(user)
        db.session.commit()

        for role, user in zip(["a", "b"], User.query.order_by(User.id.desc()).limit(2).all()):
            users[role] = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "password": "Test@1234",
            }

    yield users

    # teardown: 清理所有测试数据
    with app.app_context():
        Comment.query.delete()
        Attachment.query.delete()
        OperationLog.query.delete()
        Task.query.delete()
        Tag.query.delete()
        # 只删本次创建的测试用户
        for info in users.values():
            u = User.query.get(info["id"])
            if u:
                db.session.delete(u)
        db.session.commit()


@pytest.fixture
def user_a(test_users):
    return test_users["a"]


@pytest.fixture
def user_b(test_users):
    return test_users["b"]


@pytest.fixture
def client_a(base_url, user_a):
    """用户 A 的 ApiClient（带 Token）"""
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": user_a["username"], "password": user_a["password"]},
    )
    token = resp.json()["token"]
    return ApiClient(base_url, token=token)


@pytest.fixture
def client_b(base_url, user_b):
    """用户 B 的 ApiClient（带 Token）"""
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": user_b["username"], "password": user_b["password"]},
    )
    token = resp.json()["token"]
    return ApiClient(base_url, token=token)


@pytest.fixture
def anonymous_client(base_url):
    """无 Token 的 ApiClient"""
    return ApiClient(base_url)


@pytest.fixture
def created_task(client_a):
    """创建一个任务，返回任务数据，测试结束后自动清理"""
    resp = client_a.post("/api/tasks", json={
        "title": "Auto Test Task",
        "description": "Created by automation",
        "status": "pending",
        "priority": "high",
    })
    task = resp.json()["task"]
    yield task
    # 清理（如果还存在）
    client_a.delete(f"/api/tasks/{task['id']}")
