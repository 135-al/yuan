"""dashboard_page.py - 任务看板页面对象"""

from pages.base_page import BasePage


class DashboardPage(BasePage):
    """任务看板页（统计 + 新建 + 列表）"""

    VIEW = "view-dashboard"

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------

    def goto_logs(self):
        self.tid("nav-logs").click()
        return self

    def goto_dashboard(self):
        self.tid("nav-dashboard").click()
        return self

    def logout(self):
        self.tid("btn-logout").click()
        return self

    def refresh(self):
        self.tid("btn-refresh").click()
        return self

    def filter_by_status(self, status):
        """status: '' | pending | doing | done"""
        self.tid("filter-status").select_option(status)
        return self

    # ------------------------------------------------------------------
    # 新建任务
    # ------------------------------------------------------------------

    def create_task(self, title, priority="medium", tags=None, description=""):
        self.fill_task_form(title, priority, tags, description)
        self.tid("btn-create-task").click()
        return self

    def fill_task_form(self, title, priority="medium", tags=None, description=""):
        self.tid("task-title").fill(title)
        self.tid("task-priority").select_option(priority)
        if tags:
            self.tid("task-tags").fill(",".join(tags) if isinstance(tags, list) else tags)
        if description:
            self.tid("task-desc").fill(description)
        return self

    # ------------------------------------------------------------------
    # 列表
    # ------------------------------------------------------------------

    def task_rows(self):
        return self.tid("task-item")

    def task_count(self):
        return self.task_rows().count()

    def row_by_title(self, title):
        """按任务标题定位列表行"""
        return self.task_rows().filter(has_text=title).first

    def open_task(self, title):
        self.row_by_title(title).get_by_test_id("task-item-title").click()
        return self

    def advance_task(self, title):
        """点击该行的状态流转按钮"""
        self.row_by_title(title).get_by_test_id("btn-advance").click()
        return self

    def delete_task(self, title):
        self.row_by_title(title).get_by_test_id("btn-delete").click()
        return self

    def status_of(self, title):
        return self.row_by_title(title).get_by_test_id("task-status").inner_text()

    def titles(self):
        return self.tid("task-item-title").all_inner_texts()

    def wait_for_task(self, title, timeout=8000):
        """等待指定任务出现在列表中"""
        self.row_by_title(title).wait_for(state="visible", timeout=timeout)
        return self

    def wait_task_gone(self, title, timeout=8000):
        """等待指定任务从列表中消失"""
        self.row_by_title(title).wait_for(state="detached", timeout=timeout)
        return self

    def wait_task_status(self, title, status_text, timeout=8000):
        """等待列表中该任务行的状态文案变为期望值（如 待办/进行中/已完成）"""
        expr = (
            "p => [...document.querySelectorAll('[data-testid=\"task-item\"]')]"
            ".some(r => r.innerText.includes(p[0]) && r.innerText.includes(p[1]))"
        )
        self.wait_until(expr, arg=[title, status_text], timeout=timeout)
        return self

    def wait_all_titles(self, text, timeout=8000):
        """等待列表内所有任务标题都包含指定文本（筛选类断言用）"""
        expr = (
            "t => { const els = document.querySelectorAll('[data-testid=\"task-item-title\"]');"
            " return els.length > 0 && [...els].every(e => e.innerText.includes(t)); }"
        )
        self.wait_until(expr, arg=text, timeout=timeout)
        return self

    def wait_titles_exclude(self, text, timeout=8000):
        """等待列表内不再出现包含指定文本的标题"""
        expr = (
            "t => ![...document.querySelectorAll('[data-testid=\"task-item-title\"]')]"
            ".some(e => e.innerText.includes(t))"
        )
        self.wait_until(expr, arg=text, timeout=timeout)
        return self

    def is_empty_state_visible(self):
        return self.tid("task-empty").is_visible()

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stat(self, name):
        """name: total | pending | doing | done | overdue | rate"""
        return self.tid(f"stat-{name}").inner_text()

    def total(self):
        return int(self.stat("total"))

    def wait_for_stat(self, name, value, timeout=8000):
        """
        等待某个统计值变为期望值。

        看板刷新时 /api/stats 与 /api/tasks 是并发请求，二者返回存在先后差，
        直接断言统计值会产生不稳定用例，这里统一用显式等待消除时序差。
        """
        import json

        selector = json.dumps(f'[data-testid="stat-{name}"]')
        expected = json.dumps(str(value))
        expr = (
            "() => {"
            f"  const el = document.querySelector({selector});"
            f"  return !!el && el.textContent.trim() === {expected};"
            "}"
        )
        self.page.wait_for_function(expr, timeout=timeout)
        return self
