"""
test_ui_task_detail.py - 任务详情页 UI 自动化测试（评论 / 附件）

覆盖：详情页渲染、评论发布与展示、附件上传、返回导航、列表计数联动
"""

import uuid

import allure
import pytest

from pages.dashboard_page import DashboardPage
from pages.task_detail_page import TaskDetailPage


def _t(name=""):
    return f"{name}_{uuid.uuid4().hex[:6]}"


@allure.epic("任务管理系统")
@allure.feature("UI 自动化 - 任务详情")
class TestTaskDetailUI:

    @pytest.fixture
    def detail(self, authed_page, ui_base_url):
        """新建一个任务并进入其详情页"""
        dash = DashboardPage(authed_page, ui_base_url)
        title = _t("详情页任务")
        dash.create_task(title, description="详情页用例")
        dash.wait_for_task(title)
        dash.open_task(title)
        return TaskDetailPage(authed_page, ui_base_url).wait_for_view()

    @allure.story("详情渲染")
    @allure.title("进入详情页标题与元信息正确")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_detail_render(self, detail):
        assert "详情页任务" in detail.title()
        assert "状态" in detail.meta()
        detail.screenshot("任务详情页")

    @allure.story("评论")
    @allure.title("发布评论后评论列表出现该内容")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_comment(self, detail):
        content = f"这是一条自动化评论 {uuid.uuid4().hex[:6]}"
        detail.add_comment(content)
        detail.tid("comment-item").first.wait_for(state="visible")
        assert detail.has_comment(content)

    @allure.story("评论")
    @allure.title("连续发布多条评论，数量正确累加")
    def test_multiple_comments(self, detail):
        detail.add_comment("第一条评论")
        detail.tid("comment-item").first.wait_for(state="visible")
        detail.add_comment("第二条评论")
        detail.wait_comment_count(2)
        assert detail.comment_count() == 2

    @allure.story("评论")
    @allure.title("评论内容为空时前端拦截")
    def test_empty_comment_blocked(self, detail):
        detail.tid("btn-add-comment").click()
        assert detail.comment_count() == 0

    @allure.story("附件")
    @allure.title("上传附件后附件列表出现文件名")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_upload_attachment(self, detail, tmp_path):
        f = tmp_path / "test_upload.txt"
        f.write_text("自动化测试上传的附件内容", encoding="utf-8")
        detail.upload(str(f))
        detail.tid("attachment-item").first.wait_for(state="visible")
        assert "test_upload.txt" in detail.attachment_names()
        detail.screenshot("附件上传成功")

    @allure.story("附件")
    @allure.title("【观察项】中文文件名的附件会被 ASCII 化，文件名信息丢失")
    def test_chinese_filename_mangled(self, detail, tmp_path):
        """
        观察到的缺陷：后端使用 werkzeug.utils.secure_filename() 处理原始文件名，
        非 ASCII 字符（中文）被直接剔除，导致「测试附件.txt」被存成「txt」，
        用户下载时无法识别原文件名。
        修法：保留原始显示名（原始 filename 仅用于存储层做安全化，展示层存原名）。
        """
        f = tmp_path / "中文附件.txt"
        f.write_text("content", encoding="utf-8")
        detail.upload(str(f))
        detail.tid("attachment-item").first.wait_for(state="visible")
        assert "中文附件.txt" not in detail.attachment_names()

    @allure.story("导航")
    @allure.title("返回按钮回到看板页")
    def test_back_to_dashboard(self, detail):
        detail.back()
        detail.tid("view-dashboard").wait_for(state="visible")
        assert detail.tid("view-dashboard").is_visible()
