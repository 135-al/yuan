"""UI 自动化测试 - 页面对象包（Page Object 分层）"""

from pages.base_page import BasePage
from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage
from pages.task_detail_page import TaskDetailPage
from pages.logs_page import LogsPage

__all__ = ["BasePage", "LoginPage", "DashboardPage", "TaskDetailPage", "LogsPage"]
