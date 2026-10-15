"""login_page.py - 登录 / 注册页页面对象"""

from pages.base_page import BasePage


class LoginPage(BasePage):
    """登录 / 注册页"""

    VIEW = "view-auth"

    # ------------------------------------------------------------------
    # 页面动作
    # ------------------------------------------------------------------

    def open(self, path="/"):
        return super().open(path)

    def switch_to_login(self):
        self.tid("tab-login").click()
        return self

    def switch_to_register(self):
        self.tid("tab-register").click()
        return self

    def fill_login(self, username, password):
        self.tid("login-username").fill(username)
        self.tid("login-password").fill(password)
        return self

    def submit_login(self):
        self.tid("btn-login").click()
        return self

    def login(self, username, password):
        """完整登录流程"""
        self.fill_login(username, password)
        self.submit_login()
        return self

    def register(self, username, email, password):
        """完整注册流程"""
        self.switch_to_register()
        self.tid("reg-username").fill(username)
        self.tid("reg-email").fill(email)
        self.tid("reg-password").fill(password)
        self.tid("btn-register").click()
        return self

    # ------------------------------------------------------------------
    # 断言辅助
    # ------------------------------------------------------------------

    def message(self):
        return self.tid("auth-message").inner_text()

    def is_login_form_visible(self):
        return self.tid("form-login").is_visible()

    def is_register_form_visible(self):
        return self.tid("form-register").is_visible()

    def is_logged_in(self):
        """顶部导航出现 = 已登录"""
        return self.tid("topbar").is_visible()

    def current_user(self):
        return self.tid("current-user").inner_text()
