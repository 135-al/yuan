"""logs_page.py - 操作日志页页面对象"""

from pages.base_page import BasePage


class LogsPage(BasePage):
    """操作日志页"""

    VIEW = "view-logs"

    def refresh(self):
        self.tid("btn-refresh-logs").click()
        return self

    def filter_by_action(self, action):
        """action: '' | create | update | delete | login | upload"""
        self.tid("filter-action").select_option(action)
        return self

    def rows(self):
        return self.tid("log-row")

    def row_count(self):
        return self.rows().count()

    def actions(self):
        """返回当前列表中出现的操作类型集合"""
        return self.rows().locator(".badge").all_inner_texts()

    def is_empty_state_visible(self):
        return self.tid("log-empty").is_visible()

    # ------------------------------------------------------------------
    # 显式等待
    # ------------------------------------------------------------------

    def wait_rows(self, min_count=1, timeout=8000):
        """等待日志表格至少渲染出 min_count 行"""
        expr = "n => document.querySelectorAll('[data-testid=\"log-row\"]').length >= n"
        self.wait_until(expr, arg=min_count, timeout=timeout)
        return self

    def wait_action(self, action, timeout=8000):
        """等待某类操作（create/login/...）出现在日志表格中"""
        expr = (
            "a => [...document.querySelectorAll('[data-testid=\"log-list\"] .badge')]"
            ".some(e => e.innerText.trim() === a)"
        )
        self.wait_until(expr, arg=action, timeout=timeout)
        return self
