"""
test_ui_tasks.py - 任务看板 UI 自动化测试

覆盖：空态、创建任务、标签/优先级、刻意缺陷（空标题、状态回退）、
      状态流转、删除、状态过滤、统计看板联动
"""

import uuid

import allure
import pytest

from pages.dashboard_page import DashboardPage


def _t(name=""):
    return f"{name}_{uuid.uuid4().hex[:6]}"


@allure.epic("任务管理系统")
@allure.feature("UI 自动化 - 任务看板")
class TestTaskBoardUI:

    @allure.story("空态")
    @allure.title("新用户看板为空：统计全 0、展示空态提示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_empty_dashboard(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        dash.wait_for_view()
        assert dash.total() == 0
        assert dash.stat("rate") == "0%"
        assert dash.is_empty_state_visible()
        dash.screenshot("看板空态")

    @allure.story("创建任务")
    @allure.title("创建任务后列表出现该任务且统计同步")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_task(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        title = _t("编写测试用例")
        dash.create_task(title, priority="high")
        dash.wait_for_task(title)
        dash.wait_for_stat("total", 1)
        assert dash.stat("pending") == "1"
        assert dash.status_of(title) == "待办"
        dash.screenshot("创建任务成功")

    @allure.story("创建任务")
    @allure.title("创建带标签与优先级的任务")
    def test_create_task_with_tags(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        title = _t("带标签任务")
        dash.create_task(title, priority="low", tags=["测试", "自动化"], description="标签用例")
        dash.wait_for_task(title)
        assert title in dash.titles()

    @allure.story("创建任务")
    @allure.title("【缺陷①】空标题任务可以被创建")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_task_with_empty_title_defect(self, authed_page, ui_base_url):
        """刻意缺陷：前端与后端均未校验 title 非空，空标题可成功创建"""
        dash = DashboardPage(authed_page, ui_base_url)
        dash.fill_task_form("", priority="medium")
        dash.tid("btn-create-task").click()
        dash.wait_for_task("(空标题)")
        assert "(空标题)" in dash.titles()
        dash.wait_for_stat("total", 1)

    @allure.story("状态流转")
    @allure.title("状态正常流转：待办 → 进行中 → 已完成")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_status_flow(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        title = _t("状态流转任务")
        dash.create_task(title)
        dash.wait_for_task(title)

        assert dash.status_of(title) == "待办"
        dash.advance_task(title)
        dash.wait_task_status(title, "进行中")
        assert dash.status_of(title) == "进行中"

        dash.advance_task(title)
        dash.wait_task_status(title, "已完成")
        assert dash.status_of(title) == "已完成"
        dash.screenshot("状态流转完成")

    @allure.story("状态流转")
    @allure.title("【缺陷②】已完成任务可以回退为待办")
    def test_status_rollback_defect(self, authed_page, ui_base_url):
        """刻意缺陷：无状态机校验，done 可直接回退 pending"""
        dash = DashboardPage(authed_page, ui_base_url)
        title = _t("回退任务")
        dash.create_task(title)
        dash.wait_for_task(title)
        dash.advance_task(title)   # -> doing
        dash.advance_task(title)   # -> done
        dash.wait_task_status(title, "已完成")
        dash.advance_task(title)   # -> pending（缺陷表现）
        dash.wait_task_status(title, "待办")
        assert dash.status_of(title) == "待办"

    @allure.story("删除任务")
    @allure.title("删除任务后列表移除且统计归零")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_task(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        title = _t("待删除任务")
        dash.create_task(title)
        dash.wait_for_task(title)
        dash.delete_task(title)
        dash.wait_task_gone(title)
        assert title not in dash.titles()
        dash.wait_for_stat("total", 0)

    @allure.story("筛选")
    @allure.title("按状态筛选任务列表")
    def test_filter_by_status(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        todo = _t("待办任务")
        done = _t("已完成任务")
        dash.create_task(todo)
        dash.wait_for_task(todo)
        dash.create_task(done)
        dash.wait_for_task(done)

        # 把 done 推到已完成
        dash.advance_task(done)
        dash.wait_task_status(done, "进行中")
        dash.advance_task(done)
        dash.wait_task_status(done, "已完成")

        dash.filter_by_status("done")
        dash.wait_all_titles(done)
        dash.wait_titles_exclude(todo)
        titles = dash.titles()
        assert done in titles and todo not in titles

    @allure.story("统计看板")
    @allure.title("完成率随任务完成正确计算")
    def test_completion_rate(self, authed_page, ui_base_url):
        dash = DashboardPage(authed_page, ui_base_url)
        t1, t2 = _t("任务A"), _t("任务B")
        dash.create_task(t1)
        dash.wait_for_task(t1)
        dash.create_task(t2)
        dash.wait_for_task(t2)

        dash.advance_task(t1)
        dash.wait_task_status(t1, "进行中")
        dash.advance_task(t1)  # t1 -> done
        dash.wait_task_status(t1, "已完成")
        # 完成率 1/2：服务端 round(50.0, 2) 返回 50.0，前端 50.0 + '%' 得到 "50%"
        dash.wait_for_stat("rate", "50%")
        assert dash.stat("done") == "1"
