"""
ui_tests/conftest.py - Playwright UI 自动化测试全局 fixtures

职责：
  1. 提供被测服务 —— 自包含模式本机拉起 Flask（端口 5002 + 临时库）；
     集成模式（UI_BASE_URL）转接外部实例，容器编排时使用
  2. 提供浏览器 / 上下文（由 pytest-playwright 提供 page）
  3. 提供「已登录页面」fixture，复用登录流程
  4. 通过 API 预置测试用户，保证用例彼此独立

运行：
    python -m pytest -c pytest_ui.ini                       # 自包含模式（本地）
    UI_BASE_URL=http://app:5000 python -m pytest -c ...     # 集成模式（容器内）
"""

import os
import time
import uuid
import tempfile
import threading

import pytest
import requests
from werkzeug.serving import make_server

from app import create_app

UI_PORT = 5002

# ---------------------------------------------------------------------------
#  被测服务地址：「自包含」与「集成」双模
#
#   自包含模式（默认，本地回归）：
#       由本 fixture 在进程内拉起临时 Flask 服务 + 临时库，会话结束即销毁，
#       环境干净、零外部依赖 —— 与其余三个测试层保持一致。
#
#   集成模式（容器编排 / CI 对接已部署实例）：
#       外部注入 UI_BASE_URL（compose 中指向 app 服务：http://app:5000），
#       此时不再自行拉起服务，直接验证「已部署的那个实例」，
#       走真实跨容器 HTTP 链路，由编排层的健康检查保证服务就绪。
#
#  为什么 UI 层适合远程化：它的测试数据准备走 ApiHelper（黑盒调 /api/auth/register），
#  不依赖同进程内的 ORM session —— 这是它能接外部服务的前提。
#  而接口层/并发层的 fixture 需要直接操作 ORM 造数据并清理，必须同进程持有
#  app 实例，因此保持自包含模式，不强行远程化。
# ---------------------------------------------------------------------------
INTEGRATION_BASE_URL = os.environ.get("UI_BASE_URL")
UI_BASE_URL = INTEGRATION_BASE_URL or f"http://127.0.0.1:{UI_PORT}"


def _wait_server_ready(url, tries=30, interval=0.2):
    """轮询等待被测服务可用"""
    for _ in range(tries):
        try:
            requests.get(url + "/", timeout=1)
            return True
        except requests.RequestException:
            time.sleep(interval)
    return False


# ---------------------------------------------------------------------------
# 被测系统
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def ui_base_url():
    return UI_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def app_server(ui_base_url):
    """
    启动/确认被测服务（session 级只执行一次）

    - 集成模式（UI_BASE_URL 已注入）：不拉起服务，仅确认外部实例已就绪。
      返回 None —— UI 层的其他 fixture 只依赖 ui_base_url，不消费 app 对象。
    - 自包含模式：拉起「独立端口 + 独立临时数据库」的 Flask 实例，互不污染。
    """
    # ---- 集成模式 ----
    if INTEGRATION_BASE_URL:
        if not _wait_server_ready(INTEGRATION_BASE_URL, tries=60):
            pytest.fail(
                f"集成模式下被测服务未就绪: {INTEGRATION_BASE_URL}\n"
                f"  请确认 app 容器已 healthy（compose 已声明 depends_on 健康检查）"
            )
        yield None
        return

    # ---- 自包含模式 ----
    tmpdir = tempfile.mkdtemp(prefix="taskflow_ui_")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(tmpdir, "ui_test.db"),
        "SECRET_KEY": "ui-test-secret-key",
        "UPLOAD_FOLDER": os.path.join(tmpdir, "uploads"),
        "JWT_EXPIRATION_DELTA": 3600,
    })

    server = make_server("127.0.0.1", UI_PORT, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if not _wait_server_ready(UI_BASE_URL, tries=30):
        server.shutdown()
        pytest.fail(f"本地测试服务启动失败: {UI_BASE_URL}")

    yield app

    server.shutdown()


# ---------------------------------------------------------------------------
# 测试用户（通过 API 预置，UI 用例只负责「用」，不负责「造」）
# ---------------------------------------------------------------------------

class ApiHelper:
    """极简 API 客户端，用于测试数据准备/清理"""

    def __init__(self, base_url):
        self.base_url = base_url

    def register(self, username, email, password):
        r = requests.post(f"{self.base_url}/api/auth/register",
                          json={"username": username, "email": email, "password": password})
        return r

    def login(self, username, password):
        r = requests.post(f"{self.base_url}/api/auth/login",
                          json={"username": username, "password": password})
        return r


@pytest.fixture(scope="session")
def api(app_server, ui_base_url):
    return ApiHelper(ui_base_url)


@pytest.fixture
def ui_user(api):
    """每个用例一个全新用户，避免数据串扰"""
    suffix = uuid.uuid4().hex[:8]
    user = {
        "username": f"ui_{suffix}",
        "email": f"ui_{suffix}@test.com",
        "password": "UiTest@1234",
    }
    resp = api.register(user["username"], user["email"], user["password"])
    assert resp.status_code == 201, f"测试用户注册失败: {resp.text}"
    return user


# ---------------------------------------------------------------------------
# 登录态页面
# ---------------------------------------------------------------------------

@pytest.fixture
def login_page(page, ui_base_url):
    """未登录的登录页对象"""
    from pages.login_page import LoginPage
    return LoginPage(page, ui_base_url).open()


@pytest.fixture
def authed_page(page, ui_base_url, ui_user):
    """已完成登录、停在看板页的 page（真实走一遍 UI 登录流程）"""
    from pages.login_page import LoginPage
    lp = LoginPage(page, ui_base_url).open()
    lp.login(ui_user["username"], ui_user["password"])
    page.get_by_test_id("view-dashboard").wait_for(state="visible")
    return page


# ---------------------------------------------------------------------------
# Allure 环境信息
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _allure_env():
    try:
        import allure
        allure.dynamic.label("layer", "ui")
    except Exception:
        pass
    yield
