"""task_detail_page.py - 任务详情页页面对象（评论 / 附件）"""

from pages.base_page import BasePage


class TaskDetailPage(BasePage):
    """任务详情页"""

    VIEW = "view-task"

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------

    def back(self):
        self.tid("btn-back").click()
        return self

    def title(self):
        return self.tid("detail-title").inner_text()

    def meta(self):
        return self.tid("detail-meta").inner_text()

    # ------------------------------------------------------------------
    # 评论
    # ------------------------------------------------------------------

    def comments(self):
        return self.tid("comment-item")

    def comment_count(self):
        return self.comments().count()

    def comment_texts(self):
        return self.tid("comment-content").all_inner_texts()

    def add_comment(self, content):
        self.tid("comment-input").fill(content)
        self.tid("btn-add-comment").click()
        return self

    def has_comment(self, content):
        return content in " ".join(self.comment_texts())

    def wait_comment_count(self, n, timeout=8000):
        """等待评论条数变为 n"""
        expr = "n => document.querySelectorAll('[data-testid=\"comment-item\"]').length === n"
        self.wait_until(expr, arg=n, timeout=timeout)
        return self

    # ------------------------------------------------------------------
    # 附件
    # ------------------------------------------------------------------

    def upload(self, file_path):
        self.tid("file-input").set_input_files(file_path)
        self.tid("btn-upload").click()
        return self

    def attachments(self):
        return self.tid("attachment-item")

    def attachment_count(self):
        return self.attachments().count()

    def attachment_names(self):
        return self.tid("attachment-link").all_inner_texts()
