"""
test_ui_login.py - 登录 / 注册 页面自动化测试

覆盖：页面渲染、表单切换、输入校验、登录成功/失败、注册、退出登录
"""

import allure
import pytest

from pages.login_page import LoginPage


@allure.epic("任务管理系统")
@allure.feature("UI 自动化 - 登录注册")
class TestLoginUI:

    @allure.story("页面渲染")
    @allure.title("登录页默认展示登录表单")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_page_default(self, login_page):
        assert login_page.is_login_form_visible()
        assert not login_page.is_register_form_visible()
        assert not login_page.is_logged_in()
        login_page.screenshot("登录页初始状态")

    @allure.story("页面渲染")
    @allure.title("切换到注册表单")
    def test_switch_to_register(self, login_page):
        login_page.switch_to_register()
        assert login_page.is_register_form_visible()
        assert not login_page.is_login_form_visible()

    @allure.story("输入校验")
    @allure.title("空用户名/密码时提示错误")
    def test_login_empty_fields(self, login_page):
        login_page.submit_login()
        assert "请输入用户名和密码" in login_page.message()

    @allure.story("登录")
    @allure.title("错误密码登录失败并提示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_wrong_password(self, login_page, ui_user):
        login_page.login(ui_user["username"], "wrong-password")
        login_page.tid("auth-message").wait_for(state="visible")
        assert "invalid" in login_page.message().lower()
        assert not login_page.is_logged_in()

    @allure.story("登录")
    @allure.title("正确账号登录成功并进入看板")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_login_success(self, login_page, ui_user):
        login_page.login(ui_user["username"], ui_user["password"])
        login_page.tid("view-dashboard").wait_for(state="visible")
        assert login_page.is_logged_in()
        assert login_page.current_user() == ui_user["username"]
        login_page.screenshot("登录成功-看板页")

    @allure.story("注册")
    @allure.title("新用户注册成功后自动进入看板")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_success(self, page, ui_base_url):
        import uuid
        suffix = uuid.uuid4().hex[:8]
        lp = LoginPage(page, ui_base_url).open()
        lp.register(f"reg_{suffix}", f"reg_{suffix}@test.com", "RegTest@123")
        page.get_by_test_id("view-dashboard").wait_for(state="visible")
        assert lp.is_logged_in()
        assert lp.current_user() == f"reg_{suffix}"

    @allure.story("注册")
    @allure.title("缺少字段时注册校验拦截")
    def test_register_missing_fields(self, login_page):
        login_page.switch_to_register()
        login_page.tid("reg-username").fill("only_name")
        login_page.tid("btn-register").click()
        assert "请填写完整" in login_page.message()

    @allure.story("退出")
    @allure.title("退出登录后回到登录页")
    def test_logout(self, authed_page):
        from pages.dashboard_page import DashboardPage
        dash = DashboardPage(authed_page, "")
        dash.logout()
        authed_page.get_by_test_id("view-auth").wait_for(state="visible")
        assert not authed_page.get_by_test_id("topbar").is_visible()
