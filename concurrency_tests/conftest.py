"""
concurrency_tests/conftest.py - 并发测试专用 fixtures

与接口测试（api_tests，内存库）不同，并发测试必须使用**文件型 SQLite**：
内存库配合 StaticPool 会把所有请求串行化到同一条连接上，
「先查后插」这类竞态窗口无法暴露，测出来的结果没有参考价值。

因此这里独立启动一个文件库实例（端口 5004），专门用于并发缺陷验证。

运行：
    python -m pytest concurrency_tests -v
"""

import os
import time
import tempfile
import threading

import pytest
import requests
from werkzeug.serving import make_server


RACE_PORT = 5004
RACE_BASE_URL = f"http://127.0.0.1:{RACE_PORT}"


@pytest.fixture(scope="session")
def base_url():
    return RACE_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def race_server():
    """文件型数据库 + 多线程 Flask（session 级只启动一次）"""
    from app import create_app

    tmpdir = tempfile.mkdtemp(prefix="taskflow_race_")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(tmpdir, "race.db"),
        "SECRET_KEY": "race-test-secret",
        "UPLOAD_FOLDER": os.path.join(tmpdir, "uploads"),
        "JWT_EXPIRATION_DELTA": 3600,
    })

    server = make_server("127.0.0.1", RACE_PORT, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    for _ in range(30):
        try:
            requests.get(RACE_BASE_URL + "/", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.2)

    yield app

    server.shutdown()
