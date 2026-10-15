"""
test_ui_logs.py - 操作日志页 UI 自动化测试

覆盖：日志页渲染、登录/创建动作落库可见、按操作类型过滤
"""

import uuid

import allure

from pages.dashboard_page import DashboardPage
from pages.logs_page import LogsPage


@allure.epic("任务管理系统")
@allure.feature("UI 自动化 - 操作日志")
class TestLogsUI:

    @allure.story("渲染")
    @allure.title("操作日志页可正常打开并渲染表格")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_logs_page_render(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        dash.goto_logs()
        logs = LogsPage(authed_page, ui_base_url).wait_for_view()
        logs.wait_rows()
        assert logs.row_count() > 0
        logs.screenshot("操作日志页")

    @allure.story("日志内容")
    @allure.title("用户登录动作记录到操作日志")
    def test_login_action_logged(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        dash.goto_logs()
        logs = LogsPage(authed_page, ui_base_url).wait_for_view()
        logs.wait_action("login")
        assert "login" in logs.actions()

    @allure.story("日志内容")
    @allure.title("创建任务动作记录到操作日志")
    def test_create_action_logged(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        title = f"日志联动任务_{uuid.uuid4().hex[:6]}"
        dash.create_task(title)
        dash.wait_for_task(title)
        dash.goto_logs()
        logs = LogsPage(authed_page, ui_base_url).wait_for_view()
        logs.wait_action("create")
        assert "create" in logs.actions()

    @allure.story("过滤")
    @allure.title("按操作类型过滤日志生效")
    def test_filter_logs_by_action(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        dash.goto_logs()
        logs = LogsPage(authed_page, ui_base_url).wait_for_view()
        logs.filter_by_action("login")
        logs.wait_rows()
        actions = set(logs.actions())
        assert actions <= {"login"}, f"过滤后仍出现非 login 记录: {actions}"
