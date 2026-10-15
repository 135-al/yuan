"""
conftest.py - pytest 公共 fixtures
提供 Flask 测试应用、测试客户端、认证头等
"""

import pytest
import os
import tempfile
from app import create_app, db


@pytest.fixture
def app():
    """创建测试用 Flask 应用（内存数据库）"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_path,
            "SECRET_KEY": "test-secret-key",
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    # 清理：先释放数据库引擎连接，再删除临时文件
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except (PermissionError, OSError):
        pass  # Windows 下文件可能仍被锁定，跳过删除


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """注册并登录用户1，返回认证头"""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    token = resp.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers2(client):
    """注册并登录用户2，返回认证头（用于测试跨用户操作）"""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "testpass456",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser2", "password": "testpass456"},
    )
    token = resp.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
